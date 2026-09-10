#!/usr/bin/env python3
"""Fail-closed validator for an astra-prep pre-work plan sidecar.

Usage:
    python scripts/validate_prework.py path/to/prework-plan.yaml
    python scripts/validate_prework.py path/to/prework-plan.json

Exit codes:
    0  plan is valid
    1  one or more validation checks failed (each printed as "FAIL: <id> - <detail>")
    2  the file could not be read or parsed

Stdlib only. Reads UTF-8 explicitly. Accepts JSON, or a block-style YAML subset
(also real YAML if PyYAML happens to be importable). The schema in
schemas/prework-plan.schema.json is the structural contract; this script adds the
cross-field rules a plain schema cannot express (C1, C2, C4, C5, C6, C7, C8) and a
minimal structural check (C3, C9) so it runs with no third-party dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
REQ_ID = re.compile(r"^R-[0-9]+$")
CELL = re.compile(r"^E[1-5]/R[0-2]$")
EVIDENCE_LEVELS = {"E1", "E2", "E3", "E4", "E5"}
REVIEW_LEVELS = {"R0", "R1", "R2"}
CAP_DECISIONS = {"acquire", "rescope", "accept-as-open"}


# --------------------------------------------------------------------------- #
# parsing
# --------------------------------------------------------------------------- #
def _split_flow(s: str) -> list[str]:
    """Split a single-line flow collection body on top-level commas."""
    parts: list[str] = []
    buf: list[str] = []
    quote = None
    depth = 0
    for ch in s:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _parse_scalar(tok: str):
    tok = tok.strip()
    if tok == "" or tok == "~" or tok == "null":
        return None
    if tok in ("true", "True"):
        return True
    if tok in ("false", "False"):
        return False
    if tok.startswith("[") and tok.endswith("]"):
        return [_parse_scalar(x) for x in _split_flow(tok[1:-1])]
    if tok.startswith("{") and tok.endswith("}"):
        out = {}
        for pair in _split_flow(tok[1:-1]):
            key, _, val = pair.partition(":")
            out[key.strip().strip("'\"")] = _parse_scalar(val.strip())
        return out
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    if re.fullmatch(r"-?[0-9]+", tok):
        return int(tok)
    return tok


def _strip_comment(line: str) -> str:
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#":
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _minimal_yaml(text: str):
    """Block-style YAML subset: nested maps, lists of maps/scalars, 2-space indent."""
    lines = []
    for raw in text.splitlines():
        s = _strip_comment(raw)
        if s.strip() == "" or s.strip() == "---":
            continue
        lead = s[: len(s) - len(s.lstrip())]
        if "\t" in lead:
            raise ValueError(f"tab indentation is not allowed: {s!r}")
        indent = len(s) - len(s.lstrip(" "))
        lines.append((indent, s.strip()))

    pos = 0

    def parse_block(min_indent: int):
        nonlocal pos
        if pos >= len(lines):
            return None
        indent, content = lines[pos]
        if content.startswith("- "):
            return parse_list(indent)
        return parse_map(indent) if indent >= min_indent else None

    def parse_map(cur_indent: int):
        nonlocal pos
        result = {}
        while pos < len(lines):
            indent, content = lines[pos]
            if indent < cur_indent:
                break
            if indent > cur_indent:
                raise ValueError(f"unexpected indent: {content!r}")
            if content.startswith("- "):
                break
            m = re.match(r"^([A-Za-z0-9_]+):(.*)$", content)
            if not m:
                raise ValueError(f"cannot parse line: {content!r}")
            key, rest = m.group(1), m.group(2).strip()
            pos += 1
            if rest == "":
                if pos < len(lines) and lines[pos][0] > cur_indent:
                    result[key] = parse_block(cur_indent + 1)
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(rest)
        return result

    def parse_list(cur_indent: int):
        nonlocal pos
        result = []
        while pos < len(lines):
            indent, content = lines[pos]
            if indent < cur_indent or not content.startswith("- "):
                break
            if indent > cur_indent:
                raise ValueError(f"unexpected indent in list: {content!r}")
            item = content[2:].strip()
            inline = re.match(r"^([A-Za-z0-9_]+):(.*)$", item)
            if inline:
                # rewrite so the first key sits at cur_indent + 2
                lines[pos] = (cur_indent + 2, item)
                item_map = parse_map(cur_indent + 2)
                result.append(item_map)
            else:
                pos += 1
                result.append(_parse_scalar(item))
        return result

    doc = parse_block(0)
    return doc if doc is not None else {}


def load_plan(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    try:
        import yaml  # type: ignore
    except ImportError:
        # stdlib-only fallback: the bundled block-style-subset parser
        return _minimal_yaml(text)
    # PyYAML is available -- a parse error here is a real error, not a reason to
    # retry with the more lenient hand parser.
    return yaml.safe_load(text)


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def validate(plan) -> list[str]:
    fails: list[str] = []

    def fail(cid: str, detail: str):
        fails.append(f"FAIL: {cid} - {detail}")

    if not isinstance(plan, dict):
        return ["FAIL: C9 - top-level document is not a mapping"]

    # C9 - required top-level keys present
    for key in (
        "work_unit", "actor", "generated_at", "baseline_id", "starting_candidate",
        "provenance", "requirements", "review", "forecast",
    ):
        if key not in plan or plan[key] in (None, ""):
            fail("C9", f"missing or empty top-level key: {key}")

    # C1 - exactly one starting candidate, 64-hex sha256, baseline_id present
    sc = plan.get("starting_candidate")
    if not isinstance(sc, dict):
        fail("C1", "starting_candidate is not a mapping (exactly one required)")
    else:
        if not isinstance(sc.get("sha256"), str) or not HEX64.match(sc.get("sha256", "")):
            fail("C1", f"starting_candidate.sha256 is not 64 lowercase hex: {sc.get('sha256')!r}")
        if sc.get("type") not in ("commit", "tree", "rev", "doc"):
            fail("C1", f"starting_candidate.type invalid: {sc.get('type')!r}")
        if not sc.get("ref"):
            fail("C1", "starting_candidate.ref is empty")
    if not plan.get("baseline_id"):
        fail("C1", "baseline_id is empty")

    # C2 - requirement ids unique and well-formed
    reqs = plan.get("requirements")
    seen = set()
    if not isinstance(reqs, list) or not reqs:
        fail("C2", "requirements must be a non-empty list")
        reqs = []
    for i, r in enumerate(reqs):
        if not isinstance(r, dict):
            fail("C2", f"requirements[{i}] is not a mapping")
            continue
        rid = r.get("id")
        if not isinstance(rid, str) or not REQ_ID.match(rid):
            fail("C2", f"requirements[{i}].id not matching ^R-[0-9]+$: {rid!r}")
        elif rid in seen:
            fail("C2", f"duplicate requirement id: {rid}")
        else:
            seen.add(rid)

    # C3 - every requirement has a valid target cell
    any_r2_target = False
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        tgt = r.get("target")
        if not isinstance(tgt, dict):
            fail("C3", f"{rid}: target missing or not a mapping")
            continue
        el, ri = tgt.get("evidence_level"), tgt.get("review_independence")
        if el not in EVIDENCE_LEVELS:
            fail("C3", f"{rid}: target.evidence_level invalid: {el!r}")
        if ri not in REVIEW_LEVELS:
            fail("C3", f"{rid}: target.review_independence invalid: {ri!r}")
        if ri == "R2":
            any_r2_target = True

    # C4 - unreachable requirement needs a capability decision
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        if r.get("reachable") is False:
            dec = r.get("capability_decision")
            if dec not in CAP_DECISIONS:
                fail("C4", f"{rid}: reachable=false but capability_decision is {dec!r}")
            elif dec == "accept-as-open" and not r.get("accept_as_open_end_state"):
                fail("C4", f"{rid}: accept-as-open but accept_as_open_end_state is empty")
        elif r.get("reachable") is not True:
            fail("C4", f"{rid}: reachable must be an explicit boolean, got {r.get('reachable')!r}")

    # C5 - drift must be reconciled and rebound to the plan's baseline
    prov = plan.get("provenance")
    if not isinstance(prov, dict):
        fail("C5", "provenance missing or not a mapping")
    else:
        drift = prov.get("drift_at_start")
        if drift is True:
            rec = prov.get("reconciliation")
            if not isinstance(rec, dict):
                fail("C5", "drift_at_start=true but reconciliation block is missing")
            else:
                if rec.get("action") not in ("reconcile", "accept"):
                    fail("C5", f"reconciliation.action invalid: {rec.get('action')!r}")
                if rec.get("rebound") is not True:
                    fail("C5", "reconciliation.rebound must be true (three live pointers may not be carried past rebind)")
                if rec.get("new_baseline_id") != plan.get("baseline_id"):
                    fail("C5", f"reconciliation.new_baseline_id ({rec.get('new_baseline_id')!r}) != baseline_id ({plan.get('baseline_id')!r})")
        elif drift is not False:
            fail("C5", f"provenance.drift_at_start must be an explicit boolean, got {drift!r}")

    # C6 - any R2 target requires proven author/reviewer separation
    review = plan.get("review")
    if not isinstance(review, dict):
        fail("C6", "review missing or not a mapping")
        review = {}
    if review.get("independence_target") == "R2":
        any_r2_target = True
    if any_r2_target and review.get("author_reviewer_distinct") is not True:
        fail("C6", "an R2 target exists but review.author_reviewer_distinct is not true")

    # C7 - synced artifact needs a retention reason
    for i, a in enumerate(plan.get("artifact_hygiene") or []):
        if not isinstance(a, dict):
            fail("C7", f"artifact_hygiene[{i}] is not a mapping")
            continue
        if a.get("location") == "synced" and not a.get("retention_reason"):
            fail("C7", f"artifact_hygiene[{i}] ({a.get('artifact')!r}) is synced with no retention_reason")
        elif a.get("location") not in ("host-local", "synced"):
            fail("C7", f"artifact_hygiene[{i}].location invalid: {a.get('location')!r}")

    # C8 - forecast cell well-formed
    fc = plan.get("forecast")
    if not isinstance(fc, dict):
        fail("C8", "forecast missing or not a mapping")
    else:
        cell = fc.get("best_reachable_cell")
        if not isinstance(cell, str) or not CELL.match(cell):
            fail("C8", f"forecast.best_reachable_cell not matching ^E[1-5]/R[0-2]$: {cell!r}")
        for fld in ("dispositions", "raise_with_caller"):
            if not isinstance(fc.get(fld), list):
                fail("C8", f"forecast.{fld} must be a list")

    return fails


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate an astra-prep pre-work plan sidecar.")
    ap.add_argument("plan", type=Path, help="path to prework-plan.yaml or .json")
    args = ap.parse_args(argv)

    try:
        plan = load_plan(args.plan)
    except FileNotFoundError:
        print(f"ERROR: file not found: {args.plan}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - report any parse failure as exit 2
        print(f"ERROR: could not parse {args.plan}: {exc}", file=sys.stderr)
        return 2

    fails = validate(plan)
    if fails:
        for line in fails:
            print(line)
        print(f"\n{len(fails)} check(s) failed.")
        return 1
    print("OK: pre-work plan is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
