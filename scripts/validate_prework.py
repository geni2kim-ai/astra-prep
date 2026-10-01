#!/usr/bin/env python3
"""Fail-closed validator for an astra-prep pre-work plan sidecar (v7.1 candidate,
post-1X006-remediation revision, 2026-09-19).

Usage:
    python scripts/validate_prework.py path/to/prework-plan.yaml
    python scripts/validate_prework.py path/to/prework-plan.json

Exit codes:
    0  plan is valid
    1  one or more validation checks failed (each printed as "FAIL: <id> - <detail>")
    2  the file could not be read or parsed

Reads UTF-8 explicitly. Accepts JSON, or YAML under one deterministic parser contract:
when PyYAML is importable it is the single YAML authority, wrapped in a strict contract
(duplicate mapping keys rejected, implicit timestamps kept as strings, YAML 1.1
booleans as-is); without PyYAML the bundled block-style-subset parser applies the SAME
contract for its accepted corpus (same boolean set incl. yes/no/on/off, same null set,
duplicate-key rejection). JSON duplicate keys are rejected too. The parser identity and
Python version are printed with every run; the negative-corpus tests run in BOTH modes.

Check inventory (this revision):
    C1   exactly one starting candidate; sha256 is 64 lowercase hex (FULLMATCH - a
         trailing newline is rejected); baseline_id present
    C2   requirement ids unique and fully matching ^R-[0-9]+$ (fullmatch - trailing
         newlines are rejected)
    C3   every requirement has a valid target cell (E1-E5 / R0-R2)
    C4   reachable=false requires a capability decision; accept-as-open requires a
         non-empty honest end state naming a cell (E[1-5]/R[0-2])
    C5   drift_at_start=true requires a concrete reconciliation (action, rebound=true,
         new_baseline_id == baseline_id)
    C6   any R2 target requires PROVEN review independence, not self-attested booleans
         (F-04 / REPRO-03): author_reviewer_distinct=true PLUS a real reviewer_id, a
         non-placeholder route_id and bundle_path, a review receipt pointer carrying a
         64-hex receipt hash, and a bound result_ref. Placeholders (TBD / NOT_RUN /
         NONE_RESOLVED / ...) are rejected. Same-lineage review is R1 by default (see
         references/evidence-model.md).
    C7   synced artifact needs a retention reason
    C8   forecast.best_reachable_cell well-formed; dispositions/raise_with_caller lists
    C9   required top-level keys present (incl. starting_point_readback)
    C10  conformance to schemas/prework-plan.schema.json (F-02 / REPRO-04/05): required
         keys, additionalProperties=false, local $ref targets, enum, leaf types (incl.
         union types), minLength, minItems, pattern, const, oneOf, and if/then. Schema
         patterns are fully anchored (^...\\Z) so trailing newlines fail; pointer hashes
         are validated through a oneOf (64-hex or NONE_RESOLVED). Any schema keyword
         outside the enforced subset fails closed.
    C11  evidence_outputs: immutable write mechanism per self-writing output
    C12  control_copies: pinned, verified-before-use, recreation procedure when
         execution is allowed after verification
    C13  requirements[].coverage: item/demonstration/target present
    C14  forecast semantics (F-01 / REPRO-01/02): dispositions are a closed vocabulary
         (unknown values rejected); CANDIDATE_READY is exclusive and forbidden when any
         requirement is reachable=false, carries an open (accept-as-open) capability
         decision, or when drift_at_start=true; drift_at_start=true must disclose
         PROVENANCE_DRIFT_AT_START in forecast.dispositions - reconciled start drift
         REMAINS a disclosed disposition, so empty disposition lists are not accepted
         for a drifted start
    C15  starting-point readback (F-05 / REPRO-07): the plan must bind its provenance
         pointers to the actual candidate - starting_point_readback with
         candidate_path + candidate_sha256 equal to starting_candidate.sha256
         (candidate_path must also equal starting_candidate.ref for doc candidates),
         points_at_candidate=true, and a git_state block (HEAD/branch/clean) or an
         explicit non-git declaration

History: v7 ran only hand-rolled checks C1-C9. v7.1 candidate added C10 (structural
schema conformance - the S-0 fix), C11-C13 (v1.1 optional sections). This revision
closes the gaps reproduced by the 1X review of 2026-09-19 (REPRO-01..07).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

VALIDATOR_VERSION = "7.1.1-r54"

HEX64 = re.compile(r"[0-9a-f]{64}")  # used with fullmatch: trailing newlines rejected
REQ_ID = re.compile(r"R-[0-9]+")     # used with fullmatch
CELL = re.compile(r"E[1-5]/R[0-2]")  # used with fullmatch
CELL_IN_TEXT = re.compile(r"E[1-5]/R[0-2]")  # used with search (end-state prose)

EVIDENCE_LEVELS = {"E1", "E2", "E3", "E4", "E5"}
REVIEW_LEVELS = {"R0", "R1", "R2"}
CAP_DECISIONS = {"acquire", "rescope", "accept-as-open"}
IMMUTABILITY_MECHANISMS = {"timestamped-path", "copy-before-rerun", "append-only"}

# F-01: the closed forecast disposition vocabulary (SKILL.md step 6). CANDIDATE_READY
# is exclusive; every other word is a disclosed residual. Unknown values are rejected
# (schema enum + C14).
DISPOSITION_VOCABULARY = {
    "CANDIDATE_READY",
    "RUNTIME_NOT_RUN",
    "PROVENANCE_DRIFT_AT_START",
    "INDEPENDENT_REVIEW_NOT_RUN",
    "TRANSPORT_UNVERIFIED",
    "CAPABILITY_GAP",
    "SCOPE_RENEGOTIATION_NEEDED",
    "EVIDENCE_TREE_BLOAT_RISK",
}

# F-04: values that are placeholders, never evidence. Compared case-insensitively
# after whitespace-strip.
PLACEHOLDER_VALUES = {
    "",
    "TBD",
    "NOT_RUN",
    "NOT-RUN",
    "NONE",
    "NULL",
    "UNKNOWN",
    "N/A",
    "NA",
    "NONE_RESOLVED",
    "PLACEHOLDER",
}

# F-02: the schema keyword subset this walker implements. Anything else found in the
# schema fails closed (the contract is narrowed honestly, not silently ignored).
SUPPORTED_SCHEMA_KEYWORDS = {
    "$ref", "$defs", "type", "enum", "const", "oneOf", "if", "then", "else",
    "required", "properties", "additionalProperties", "items", "minItems",
    "minLength", "pattern",
}
ANNOTATION_SCHEMA_KEYWORDS = {
    "$schema", "$id", "title", "description", "$comment",
    "examples", "default", "deprecated",
}
ALLOWED_SCHEMA_KEYWORDS = SUPPORTED_SCHEMA_KEYWORDS | ANNOTATION_SCHEMA_KEYWORDS


# --------------------------------------------------------------------------- #
# YAML parsing - one deterministic parser contract (F-03)
# --------------------------------------------------------------------------- #
# Parser decision record (W2):
# - This validator is an offline verification gate (component), so it must keep a
#   dependency-free fallback for environments where PyYAML is unavailable.
# - yaml.safe_load() is not used directly because the gate requires duplicate mapping
#   keys to be rejected instead of silently taking the last value.
# - PyYAML's implicit timestamp resolver is disabled so date/time-looking evidence
#   remains a string; validation must not depend on locale/timezone datetime coercion.
# - The bundled parser intentionally accepts only a narrow mapping/list/flow subset.
#   Unsupported or structurally ambiguous syntax is rejected rather than guessed.
# - Parser errors are terminal for the selected parser. A PyYAML syntax error is never
#   retried through the fallback, because fallback-after-error would widen acceptance.
# - Full-string security identifiers are checked with fullmatch / schema \\Z anchors;
#   'YAML11_BOOLEANS = {
    "yes": True, "Yes": True, "YES": True,
    "no": False, "No": False, "NO": False,
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "on": True, "On": True, "ON": True,
    "off": False, "Off": False, "OFF": False,
}
YAML11_NULLS = {"", "~", "null", "Null", "NULL"}

_STRICT_YAML_CACHE: dict[str, type[Any]] = {}


def _split_flow(s: str) -> list[str]:
    """Split a single-line flow collection body on top-level commas.

    The fallback parser rejects unbalanced delimiters and unterminated quotes instead
    of returning a partially interpreted value.
    """
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    depth = 0
    escaped = False
    for ch in s:
        if quote is not None:
            buf.append(ch)
            if quote == '"' and ch == "\\" and not escaped:
                escaped = True
                continue
            if ch == quote and not escaped:
                quote = None
            escaped = False
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced closing delimiter in flow collection")
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if quote is not None:
        raise ValueError("unterminated quote in flow collection")
    if depth != 0:
        raise ValueError("unbalanced delimiter in flow collection")
    if buf:
        parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def _split_flow_pair(pair: str) -> tuple[str, str]:
    """Split one flow-mapping entry at its first top-level colon."""
    quote: str | None = None
    depth = 0
    escaped = False
    for index, ch in enumerate(pair):
        if quote is not None:
            if quote == '"' and ch == "\\" and not escaped:
                escaped = True
                continue
            if ch == quote and not escaped:
                quote = None
            escaped = False
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced closing delimiter in flow mapping")
        elif ch == ":" and depth == 0:
            key = pair[:index].strip().strip("'\"")
            value = pair[index + 1 :].strip()
            if not key or re.fullmatch(r"[A-Za-z0-9_]+", key) is None:
                raise ValueError(f"unsupported flow mapping key: {key!r}")
            return key, value
    raise ValueError(f"flow mapping entry has no top-level colon: {pair!r}")


def _parse_scalar(tok: str) -> Any:
    tok = tok.strip()
    if tok in YAML11_NULLS:
        return None
    if tok in YAML11_BOOLEANS:
        return YAML11_BOOLEANS[tok]
    if tok.startswith("[") and tok.endswith("]"):
        return [_parse_scalar(x) for x in _split_flow(tok[1:-1])]
    if tok.startswith("{") and tok.endswith("}"):
        out: dict[str, Any] = {}
        for pair in _split_flow(tok[1:-1]):
            key, val = _split_flow_pair(pair)
            if key in out:
                raise ValueError(f"duplicate key in flow mapping: {key!r}")
            out[key] = _parse_scalar(val)
        return out
    if tok.startswith(("[", "{")) or tok.endswith(("]", "}")):
        raise ValueError(f"malformed flow scalar: {tok!r}")
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    if tok.startswith(("'", '"')) or tok.endswith(("'", '"')):
        raise ValueError(f"unterminated quoted scalar: {tok!r}")
    if re.fullmatch(r"[-+]?[0-9]+", tok):
        return int(tok)
    # floats (with a dot or exponent, so plain ints are handled above first)
    if re.fullmatch(r"[-+]?(?:[0-9]+\.[0-9]+|\.[0-9]+)(?:[eE][-+]?[0-9]+)?", tok) \
            or re.fullmatch(r"[-+]?[0-9]+[eE][-+]?[0-9]+", tok):
        return float(tok)
    return tok


def _strip_comment(line: str) -> str:
    # YAML rule: '#' starts a comment only at line start or after whitespace
    # (outside quotes), so unquoted values containing '#' survive intact.
    out: list[str] = []
    quote: str | None = None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _minimal_yaml(text: str) -> Any:
    """Block-style YAML subset: nested maps, lists of maps/scalars, space indentation.

    Contract parity with the strict PyYAML loader (F-03): YAML 1.1 booleans
    (yes/no/on/off/true/false in PyYAML's exact casing set), the same null set, and
    duplicate-key rejection in block mappings AND flow mappings.
    """
    lines: list[tuple[int, str]] = []
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

    def parse_block(min_indent: int) -> Any:
        nonlocal pos
        if pos >= len(lines):
            return None
        indent, content = lines[pos]
        if content.startswith("- "):
            return parse_list(indent)
        return parse_map(indent) if indent >= min_indent else None

    def parse_map(cur_indent: int) -> dict[str, Any]:
        nonlocal pos
        result: dict[str, Any] = {}
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
            if key in result:
                raise ValueError(f"duplicate YAML mapping key: {key!r}")
            pos += 1
            if rest == "":
                if pos < len(lines) and lines[pos][0] > cur_indent:
                    result[key] = parse_block(cur_indent + 1)
                else:
                    result[key] = None
            else:
                result[key] = _parse_scalar(rest)
        return result

    def parse_list(cur_indent: int) -> list[Any]:
        nonlocal pos
        result: list[Any] = []
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
    if pos != len(lines):
        raise ValueError(f"unparsed YAML content remains at line index {pos}")
    return doc if doc is not None else {}


def _strict_yaml_loader() -> type[Any]:
    """Build (once) the single PyYAML authority loader. Strict contract on top of
    SafeLoader semantics: (a) duplicate mapping keys raise ValueError, (b) implicit
    timestamps are kept as strings (no locale/timezone-dependent datetime objects)."""
    if _STRICT_YAML_CACHE.get("loader") is not None:
        return _STRICT_YAML_CACHE["loader"]
    import yaml

    class StrictSafeLoader(yaml.SafeLoader):
        pass

    ts_tag = "tag:yaml.org,2002:timestamp"
    StrictSafeLoader.yaml_implicit_resolvers = {
        prefix: [(tag, regexp) for (tag, regexp) in resolvers if tag != ts_tag]
        for prefix, resolvers in StrictSafeLoader.yaml_implicit_resolvers.items()
    }

    def _construct_mapping_no_duplicates(
        loader: Any, node: Any, deep: bool = False
    ) -> dict[Any, Any]:
        loader.flatten_mapping(node)  # keep merge-key ('<<') support
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    f"unhashable mapping key: {key_node.value!r}",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise ValueError(
                    f"duplicate YAML mapping key: {key!r} "
                    f"(line {key_node.start_mark.line + 1})"
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping_no_duplicates,
    )
    _STRICT_YAML_CACHE["loader"] = StrictSafeLoader
    return StrictSafeLoader


def strict_yaml_load(text: str) -> Any:
    """The PyYAML-side parser contract (F-03). Raises ValueError on duplicate keys."""
    import yaml

    return yaml.load(text, Loader=_strict_yaml_loader())


def _json_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k!r}")
        result[k] = v
    return result


def load_plan(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text, object_pairs_hook=_json_no_duplicates)
    try:
        import yaml  # noqa: F401
    except ImportError:
        # stdlib-only fallback: the bundled block-style-subset parser, same contract
        return _minimal_yaml(text)
    # PyYAML is available -- it is the single authority. A parse error (including a
    # duplicate key) is a real error, never a reason to retry with the other parser.
    return strict_yaml_load(text)


def parser_identity(suffix: str = "") -> str:
    """Name+version of the parser this environment resolves to (F-03)."""
    if suffix.lower() == ".json":
        return f"json/stdlib (python {python_version()}; duplicate keys rejected)"
    try:
        import yaml
    except ImportError:
        return (
            "bundled-minimal-yaml/1 (PyYAML absent; block-style subset, "
            "corpus-equivalent contract, duplicate keys rejected)"
        )
    return (
        f"pyyaml/{getattr(yaml, '__version__', 'unknown')} strict-safe-loader "
        f"(duplicate keys rejected; timestamps kept as strings)"
    )


def python_version() -> str:
    return sys.version.split()[0]


def load_schema() -> dict[str, Any]:
    """Load the sibling schema file; C10 enforces whatever it declares."""
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "prework-plan.schema.json"
    return cast(dict[str, Any], json.loads(schema_path.read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def _type_ok(value: Any, types: str | list[str]) -> bool:
    if not isinstance(types, list):
        types = [types]
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


def _conformance_walk(
    value: Any,
    schema: dict[str, Any],
    path: str,
    fails: list[str],
    root: dict[str, Any] | None = None,
    depth: int = 0,
) -> None:
    """C10: enforce the schema's declared keyword subset (F-02): required keys,
    additionalProperties=false, local $ref targets, enum, const, oneOf, leaf types
    (incl. union types), minLength, minItems, pattern, and if/then. Unsupported
    keywords never reach this walk: validate() pre-scans the schema and fails closed
    on them."""
    if depth > 24:  # bounded: a schema this deep is a schema bug, not a plan bug
        fails.append(f"FAIL: C10 - {path}: schema nesting exceeds the walk bound")
        return
    if not isinstance(schema, dict) or not schema:
        return
    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(root, dict) and isinstance(ref, str) and ref.startswith("#/"):
            target = root
            for part in ref[2:].split("/"):
                target = target.get(part) if isinstance(target, dict) else None
            if target is None:
                fails.append(f"FAIL: C10 - {path}: unresolvable schema $ref {ref!r}")
                return
            _conformance_walk(value, target, path, fails, root, depth + 1)
            return
        fails.append(f"FAIL: C10 - {path}: non-local schema $ref {ref!r} is not enforced")
        return
    if "oneOf" in schema:
        branches = schema["oneOf"]
        matched = 0
        if isinstance(branches, list):
            for branch in branches:
                probe: list[str] = []
                if isinstance(branch, dict):
                    _conformance_walk(value, branch, f"{path}(oneOf)", probe, root, depth + 1)
                    if not probe:
                        matched += 1
        if matched != 1:
            fails.append(
                f"FAIL: C10 - {path}: value {value!r} matches {matched} oneOf branches "
                f"(exactly 1 required)"
            )
    if "const" in schema:
        c = schema["const"]
        if not (value == c and isinstance(value, bool) == isinstance(c, bool)):
            fails.append(f"FAIL: C10 - {path}: value {value!r} != const {c!r}")
    if "enum" in schema and value not in schema["enum"]:
        fails.append(
            f"FAIL: C10 - {path}: value {value!r} is not one of the schema enum "
            f"{schema['enum']!r}"
        )
    if "type" in schema and not _type_ok(value, schema["type"]):
        fails.append(
            f"FAIL: C10 - {path}: value {value!r} does not match declared type "
            f"{schema['type']!r}"
        )
        return
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            fails.append(
                f"FAIL: C10 - {path}: string shorter than declared minLength "
                f"{schema['minLength']}: {value!r}"
            )
        if "pattern" in schema:
            try:
                if re.search(schema["pattern"], value) is None:
                    fails.append(
                        f"FAIL: C10 - {path}: value {value!r} does not match schema "
                        f"pattern {schema['pattern']!r}"
                    )
            except re.error as exc:
                fails.append(
                    f"FAIL: C10 - {path}: schema pattern {schema['pattern']!r} is not a "
                    f"valid regex ({exc}) - fail closed"
                )
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            fails.append(
                f"FAIL: C10 - {path}: list shorter than declared minItems "
                f"{schema['minItems']}"
            )
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                _conformance_walk(item, items, f"{path}[{i}]", fails, root, depth + 1)
    if isinstance(value, dict) and (
        schema.get("type") == "object" or "properties" in schema or "required" in schema
    ):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                fails.append(f"FAIL: C10 - {path}: required key missing per schema: {req}")
        if schema.get("additionalProperties") is False:
            for key in sorted(value):
                if key not in props:
                    fails.append(
                        f"FAIL: C10 - {path}: key {key!r} is not declared in the schema "
                        f"(additionalProperties=false)"
                    )
        for key, sub in props.items():
            if key in value:
                _conformance_walk(value[key], sub, f"{path}.{key}", fails, root, depth + 1)
    # if / then / else
    if "if" in schema:
        probe: list[str] = []
        if isinstance(schema["if"], dict):
            _conformance_walk(value, schema["if"], f"{path}(if)", probe, root, depth + 1)
        if not probe:
            if "then" in schema and isinstance(schema["then"], dict):
                _conformance_walk(value, schema["then"], f"{path}(then)", fails, root, depth + 1)
        elif "else" in schema and isinstance(schema["else"], dict):
            _conformance_walk(value, schema["else"], f"{path}(else)", fails, root, depth + 1)


def _scan_schema_keywords(
    schema: Any,
    path: str,
    fails: list[str],
    root: dict[str, Any] | None = None,
) -> None:
    """F-02 fail-closed half: any schema keyword outside the enforced subset is an
    error, never a silent no-op. Run once over the whole schema tree before walking
    the plan."""
    if not isinstance(schema, dict):
        return
    if root is None:
        root = schema
    for key in schema:
        if key not in ALLOWED_SCHEMA_KEYWORDS:
            fails.append(
                f"FAIL: C10 - schema keyword {key!r} at {path} is outside the enforced "
                f"subset - fail closed (validator implements: "
                f"{sorted(SUPPORTED_SCHEMA_KEYWORDS)})"
            )
    for key in ("if", "then", "else"):
        if key in schema:
            _scan_schema_keywords(schema[key], f"{path}.{key}", fails, root)
    if isinstance(schema.get("oneOf"), list):
        for i, branch in enumerate(schema["oneOf"]):
            _scan_schema_keywords(branch, f"{path}.oneOf[{i}]", fails, root)
    props = schema.get("properties")
    if isinstance(props, dict):
        for k, v in props.items():
            _scan_schema_keywords(v, f"{path}.properties.{k}", fails, root)
    if isinstance(schema.get("items"), dict):
        _scan_schema_keywords(schema["items"], f"{path}.items", fails, root)
    if isinstance(schema.get("additionalProperties"), dict):
        _scan_schema_keywords(schema["additionalProperties"], f"{path}.additionalProperties", fails, root)
    if isinstance(schema.get("$defs"), dict):
        for k, v in schema["$defs"].items():
            _scan_schema_keywords(v, f"{path}.$defs.{k}", fails, root)
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/") and isinstance(root, dict):
        target = root
        for part in ref[2:].split("/"):
            target = target.get(part) if isinstance(target, dict) else None
        if isinstance(target, dict):
            _scan_schema_keywords(target, f"{path}$ref:{ref}", fails, root)


def _is_placeholder(v: Any) -> bool:
    return not isinstance(v, str) or v.strip().upper() in PLACEHOLDER_VALUES


def validate(plan: Any, schema: dict[str, Any] | None = None) -> list[str]:
    fails: list[str] = []

    def fail(cid: str, detail: str) -> None:
        fails.append(f"FAIL: {cid} - {detail}")

    if not isinstance(plan, dict):
        return ["FAIL: C9 - top-level document is not a mapping"]

    # C9 - required top-level keys present
    for key in (
        "work_unit", "actor", "generated_at", "baseline_id", "starting_candidate",
        "provenance", "starting_point_readback", "requirements", "review", "forecast",
    ):
        if key not in plan or plan[key] in (None, ""):
            fail("C9", f"missing or empty top-level key: {key}")

    # C10 - conformance to the published schema (v7.1, F-02). A None schema argument
    # means the library caller did not pass one: self-load it here so the C10 contract
    # holds for validate(plan) too. A schema that cannot be loaded, or that declares
    # keywords outside the enforced subset, is a fail-closed event, never a silent skip.
    if schema is None:
        try:
            schema = load_schema()
        except Exception as exc:  # noqa: BLE001
            fail("C10", f"schema could not be loaded: {exc}")
            schema = None
    if schema is not None:
        scan: list[str] = []
        _scan_schema_keywords(schema, "schema", scan, root=schema)
        fails.extend(scan)
        _conformance_walk(plan, schema, "plan", fails, root=schema)

    sc = plan.get("starting_candidate")

    # C1 - exactly one starting candidate, 64-hex sha256 (fullmatch), baseline_id present
    if not isinstance(sc, dict):
        fail("C1", "starting_candidate is not a mapping (exactly one required)")
    else:
        if not isinstance(sc.get("sha256"), str) or not HEX64.fullmatch(sc.get("sha256", "")):
            fail("C1", f"starting_candidate.sha256 is not 64 lowercase hex: {sc.get('sha256')!r}")
        if sc.get("type") not in ("commit", "tree", "rev", "doc"):
            fail("C1", f"starting_candidate.type invalid: {sc.get('type')!r}")
        if not sc.get("ref") or not isinstance(sc.get("ref"), str):
            fail("C1", "starting_candidate.ref is empty")
    if not plan.get("baseline_id"):
        fail("C1", "baseline_id is empty")

    # C2 - requirement ids unique and well-formed (fullmatch)
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
        if not isinstance(rid, str) or not REQ_ID.fullmatch(rid):
            fail("C2", f"requirements[{i}].id not fully matching R-[0-9]+ (trailing "
                       f"characters, incl. newlines, are rejected): {rid!r}")
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

    # C4 - unreachable requirement needs a capability decision; accept-as-open names
    # the honest end cell
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        if r.get("reachable") is False:
            dec = r.get("capability_decision")
            if dec not in CAP_DECISIONS:
                fail("C4", f"{rid}: reachable=false but capability_decision is {dec!r}")
            elif dec == "accept-as-open":
                end = r.get("accept_as_open_end_state")
                if not isinstance(end, str) or not end.strip():
                    fail("C4", f"{rid}: accept-as-open but accept_as_open_end_state is empty")
                elif not CELL_IN_TEXT.search(end):
                    fail("C4", f"{rid}: accept-as-open must name the honest end cell "
                               f"(E[1-5]/R[0-2]) in accept_as_open_end_state: {end!r}")
        elif r.get("reachable") is not True:
            fail("C4", f"{rid}: reachable must be an explicit boolean, got {r.get('reachable')!r}")

    # C5 - drift must be reconciled and rebound to the plan's baseline
    prov = plan.get("provenance")
    drift = isinstance(prov, dict) and prov.get("drift_at_start") is True
    if not isinstance(prov, dict):
        fail("C5", "provenance missing or not a mapping")
    else:
        drift_flag = prov.get("drift_at_start")
        if drift_flag is True:
            rec = prov.get("reconciliation")
            if not isinstance(rec, dict) or not rec:
                fail("C5", "drift_at_start=true but reconciliation block is missing or empty")
            else:
                if rec.get("action") not in ("reconcile", "accept"):
                    fail("C5", f"reconciliation.action invalid: {rec.get('action')!r}")
                if rec.get("rebound") is not True:
                    fail("C5", "reconciliation.rebound must be true (three live pointers may not be carried past rebind)")
                if not rec.get("new_baseline_id"):
                    fail("C5", "reconciliation.new_baseline_id is missing or empty (drift must resolve to one named base)")
                elif rec.get("new_baseline_id") != plan.get("baseline_id"):
                    fail("C5", f"reconciliation.new_baseline_id ({rec.get('new_baseline_id')!r}) != baseline_id ({plan.get('baseline_id')!r})")
        elif drift_flag is not False:
            fail("C5", f"provenance.drift_at_start must be an explicit boolean, got {drift_flag!r}")

    # C6 - any R2 target requires PROVEN review independence (F-04 / REPRO-03):
    # more than the self-attested distinct flag.
    review = plan.get("review")
    if not isinstance(review, dict):
        fail("C6", "review missing or not a mapping")
        review = {}
    if review.get("independence_target") == "R2":
        any_r2_target = True
    if any_r2_target:
        if review.get("author_reviewer_distinct") is not True:
            fail("C6", "an R2 target exists but review.author_reviewer_distinct is not true")
        if _is_placeholder(review.get("reviewer_id")):
            fail("C6", "an R2 target exists but review.reviewer_id is missing or a "
                       "placeholder (actual reviewer identity is required)")
        if _is_placeholder(review.get("route_id")):
            fail("C6", f"an R2 target exists but review.route_id is missing or a "
                       f"placeholder ({review.get('route_id')!r}); NOT_RUN is not an R2 "
                       f"route - same-lineage review is R1 by default")
        if _is_placeholder(review.get("bundle_path")):
            fail("C6", f"an R2 target exists but review.bundle_path is missing or a "
                       f"placeholder ({review.get('bundle_path')!r})")
        receipt = review.get("receipt")
        if not isinstance(receipt, dict):
            fail("C6", "an R2 target exists but review.receipt (review receipt pointer: "
                       "path + sha256) is missing")
        else:
            if _is_placeholder(receipt.get("path")):
                fail("C6", f"review.receipt.path is missing or a placeholder ({receipt.get('path')!r})")
            if not isinstance(receipt.get("sha256"), str) or not HEX64.fullmatch(receipt.get("sha256", "")):
                fail("C6", f"review.receipt.sha256 must be the 64-hex hash of the receipt "
                           f"artifact, got {receipt.get('sha256')!r} (NONE_RESOLVED is not a receipt)")
        if _is_placeholder(review.get("result_ref")):
            fail("C6", "an R2 target exists but review.result_ref (bound result "
                       "reference) is missing or a placeholder")

    # C7 - synced artifact needs a retention reason
    for i, a in enumerate(plan.get("artifact_hygiene") or []):
        if not isinstance(a, dict):
            fail("C7", f"artifact_hygiene[{i}] is not a mapping")
            continue
        if a.get("location") == "synced" and not a.get("retention_reason"):
            fail("C7", f"artifact_hygiene[{i}] ({a.get('artifact')!r}) is synced with no retention_reason")
        elif a.get("location") not in ("host-local", "synced"):
            fail("C7", f"artifact_hygiene[{i}].location invalid: {a.get('location')!r}")

    # C8 - forecast cell well-formed (fullmatch)
    fc = plan.get("forecast")
    if not isinstance(fc, dict):
        fail("C8", "forecast missing or not a mapping")
    else:
        cell = fc.get("best_reachable_cell")
        if not isinstance(cell, str) or not CELL.fullmatch(cell):
            fail("C8", f"forecast.best_reachable_cell not fully matching E[1-5]/R[0-2]: {cell!r}")
        for fld in ("dispositions", "raise_with_caller"):
            if not isinstance(fc.get(fld), list):
                fail("C8", f"forecast.{fld} must be a list")

    # C14 - forecast semantics (F-01 / REPRO-01/02)
    if isinstance(fc, dict) and isinstance(fc.get("dispositions"), list):
        disps = fc["dispositions"]
        for d in disps:
            if not (isinstance(d, str) and d in DISPOSITION_VOCABULARY):
                fail("C14", f"forecast.dispositions contains a value outside the "
                            f"published closed vocabulary {sorted(DISPOSITION_VOCABULARY)}: {d!r}")
        open_rows = [r.get("id", "?") for r in reqs
                     if isinstance(r, dict) and r.get("reachable") is False]
        open_decisions = [r.get("id", "?") for r in reqs
                          if isinstance(r, dict) and r.get("capability_decision") == "accept-as-open"]
        if "CANDIDATE_READY" in disps:
            if len(disps) > 1:
                fail("C14", "CANDIDATE_READY is exclusive - it cannot be listed alongside other dispositions")
            if open_rows:
                fail("C14", f"forecast claims CANDIDATE_READY but requirement(s) {open_rows} "
                            f"are reachable=false - the plan cannot be CANDIDATE_READY")
            if open_decisions:
                fail("C14", f"forecast claims CANDIDATE_READY but requirement(s) {open_decisions} "
                            f"carry an open (accept-as-open) capability decision")
            if drift:
                fail("C14", "forecast claims CANDIDATE_READY but provenance.drift_at_start=true - "
                            "reconciled start drift remains a disclosed disposition "
                            "(PROVENANCE_DRIFT_AT_START)")
        if drift and "PROVENANCE_DRIFT_AT_START" not in disps:
            fail("C14", "provenance.drift_at_start=true but forecast.dispositions does not "
                        "disclose PROVENANCE_DRIFT_AT_START - reconciled start drift is a "
                        "disclosed disposition and an empty disposition list is not accepted")

    # C11 - evidence_outputs (v1.1, optional section): each declared output must
    # name an immutable write mechanism (the H-A rule: a script that writes its
    # own evidence must never be able to overwrite an earlier run's artifact
    # within the unit).
    for i, eo in enumerate(plan.get("evidence_outputs") or []):
        if not isinstance(eo, dict):
            fail("C11", f"evidence_outputs[{i}] is not a mapping")
            continue
        if not eo.get("artifact") or not isinstance(eo.get("artifact"), str):
            fail("C11", f"evidence_outputs[{i}].artifact missing or empty")
        if not eo.get("writer") or not isinstance(eo.get("writer"), str):
            fail("C11", f"evidence_outputs[{i}].writer missing or empty")
        if eo.get("immutability") not in IMMUTABILITY_MECHANISMS:
            fail("C11", f"evidence_outputs[{i}].immutability must be one of {sorted(IMMUTABILITY_MECHANISMS)}, got {eo.get('immutability')!r}")

    # C12 - control_copies (v1.1, optional section): a pristine copy is a
    # verified-then-frozen witness (the H-B rule). It must carry a pin, be
    # verified before use, and if any execution is allowed inside it after
    # verification, a recreation procedure must be named.
    for i, cc in enumerate(plan.get("control_copies") or []):
        if not isinstance(cc, dict):
            fail("C12", f"control_copies[{i}] is not a mapping")
            continue
        if not cc.get("path") or not isinstance(cc.get("path"), str):
            fail("C12", f"control_copies[{i}].path missing or empty")
        if not isinstance(cc.get("pin_sha256"), str) or not HEX64.fullmatch(cc.get("pin_sha256", "")):
            fail("C12", f"control_copies[{i}].pin_sha256 is not 64 lowercase hex")
        if cc.get("verified_before_use") is not True:
            fail("C12", f"control_copies[{i}] must be verified_before_use=true (a control copy that was not verified first is not a control copy)")
        if cc.get("execution_allowed_after_verification") is True and not cc.get("recreation_procedure"):
            fail("C12", f"control_copies[{i}] allows execution after verification but names no recreation_procedure")

    # C13 - requirements[].coverage (v1.1, optional section): the H-C rule. A
    # coverage item names what is reviewed and the artifact that will demonstrate
    # the review reached it; an item with no demonstrable artifact is declared
    # accept-as-open at plan time, never silently dropped.
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        cov = r.get("coverage")
        if cov is None:
            continue
        if not isinstance(cov, list):
            fail("C13", f"{rid}: coverage must be a list when present")
            continue
        cov_seen = set()
        for j, item in enumerate(cov):
            if not isinstance(item, dict):
                fail("C13", f"{rid}: coverage[{j}] is not a mapping")
                continue
            for fld in ("item", "demonstration", "target"):
                if not item.get(fld) or not isinstance(item.get(fld), str):
                    fail("C13", f"{rid}: coverage[{j}].{fld} missing or empty")
            it = item.get("item")
            if isinstance(it, str):
                if it in cov_seen:
                    fail("C13", f"{rid}: duplicate coverage item: {it}")
                cov_seen.add(it)

    # C15 - starting-point readback (F-05 / REPRO-07): the provenance pointers must
    # bind to the actual candidate.
    sbr = plan.get("starting_point_readback")
    if not isinstance(sbr, dict):
        fail("C15", "starting_point_readback missing or not a mapping (the plan must "
                    "bind its pointers to the actual candidate: candidate path + hash "
                    "+ HEAD/tree state or an explicit non-git declaration)")
    else:
        cpath = sbr.get("candidate_path")
        if _is_placeholder(cpath):
            fail("C15", f"starting_point_readback.candidate_path is missing or a placeholder ({cpath!r})")
        csha = sbr.get("candidate_sha256")
        if not isinstance(csha, str) or not HEX64.fullmatch(csha):
            fail("C15", f"starting_point_readback.candidate_sha256 is not 64 lowercase hex: {csha!r}")
        elif isinstance(sc, dict) and sc.get("sha256") != csha:
            fail("C15", "starting_point_readback.candidate_sha256 does not equal "
                        "starting_candidate.sha256 - the readback does not bind to the "
                        "declared candidate")
        if isinstance(sc, dict) and sc.get("type") == "doc" and isinstance(cpath, str) \
                and cpath.replace("\\", "/") != str(sc.get("ref", "")).replace("\\", "/"):
            fail("C15", "starting_point_readback.candidate_path does not equal "
                        "starting_candidate.ref (a doc candidate binds by path + hash)")
        if sbr.get("points_at_candidate") is not True:
            fail("C15", f"starting_point_readback.points_at_candidate must be true, got "
                        f"{sbr.get('points_at_candidate')!r} (a readback that does not "
                        f"confirm the candidate is drift: re-run step 1)")
        gs = sbr.get("git_state")
        if not isinstance(gs, dict):
            fail("C15", "starting_point_readback.git_state missing (git HEAD/tree state "
                        "or an explicit non-git declaration is required)")
        elif gs.get("kind") == "git":
            if _is_placeholder(gs.get("head")):
                fail("C15", f"starting_point_readback.git_state.head is missing or a placeholder ({gs.get('head')!r})")
            if not isinstance(gs.get("clean"), bool):
                fail("C15", f"starting_point_readback.git_state.clean must be an explicit boolean (dirty status), got {gs.get('clean')!r}")
            if "branch" in gs and gs.get("branch") is not None and not isinstance(gs.get("branch"), str):
                fail("C15", f"starting_point_readback.git_state.branch must be a string or null, got {gs.get('branch')!r}")
        elif gs.get("kind") == "non-git":
            if _is_placeholder(gs.get("declaration")):
                fail("C15", f"starting_point_readback.git_state.declaration is missing or "
                            f"a placeholder ({gs.get('declaration')!r}) - an explicit "
                            f"non-git declaration is required")
        else:
            fail("C15", f"starting_point_readback.git_state.kind must be 'git' or 'non-git', got {gs.get('kind')!r}")

    return fails


def main(argv: Sequence[str] | None = None) -> int:
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

    # F-03: record the parser identity and Python version with every run.
    print(f"parser: {parser_identity(args.plan.suffix)}")
    print(f"python: {python_version()}")

    try:
        schema = load_schema()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: C10 - schema could not be loaded: {exc}")
        return 1

    fails = validate(plan, schema)
    if fails:
        for line in fails:
            print(line)
        print(f"\n{len(fails)} check(s) failed.")
        return 1
    print("OK: pre-work plan is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
 is not used because it can match before a trailing newline.
#
# YAML 1.1 boolean set, exactly as PyYAML's implicit resolver maps it.
YAML11_BOOLEANS = {
    "yes": True, "Yes": True, "YES": True,
    "no": False, "No": False, "NO": False,
    "true": True, "True": True, "TRUE": True,
    "false": False, "False": False, "FALSE": False,
    "on": True, "On": True, "ON": True,
    "off": False, "Off": False, "OFF": False,
}
YAML11_NULLS = {"", "~", "null", "Null", "NULL"}

_STRICT_YAML_CACHE: dict = {}


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
    if tok in YAML11_NULLS:
        return None
    if tok in YAML11_BOOLEANS:
        return YAML11_BOOLEANS[tok]
    if tok.startswith("[") and tok.endswith("]"):
        return [_parse_scalar(x) for x in _split_flow(tok[1:-1])]
    if tok.startswith("{") and tok.endswith("}"):
        out: dict = {}
        for pair in _split_flow(tok[1:-1]):
            key, _, val = pair.partition(":")
            key = key.strip().strip("'\"")
            if key in out:
                raise ValueError(f"duplicate key in flow mapping: {key!r}")
            out[key] = _parse_scalar(val.strip())
        return out
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("'", '"'):
        return tok[1:-1]
    if re.fullmatch(r"[-+]?[0-9]+", tok):
        return int(tok)
    # floats (with a dot or exponent, so plain ints are handled above first)
    if re.fullmatch(r"[-+]?(?:[0-9]+\.[0-9]+|\.[0-9]+)(?:[eE][-+]?[0-9]+)?", tok) \
            or re.fullmatch(r"[-+]?[0-9]+[eE][-+]?[0-9]+", tok):
        return float(tok)
    return tok


def _strip_comment(line: str) -> str:
    # YAML rule: '#' starts a comment only at line start or after whitespace
    # (outside quotes), so unquoted values containing '#' survive intact.
    out: list[str] = []
    quote = None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _minimal_yaml(text: str):
    """Block-style YAML subset: nested maps, lists of maps/scalars, 2-space indent.

    Contract parity with the strict PyYAML loader (F-03): YAML 1.1 booleans
    (yes/no/on/off/true/false in PyYAML's exact casing set), the same null set, and
    duplicate-key rejection in block mappings AND flow mappings.
    """
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
        result: dict = {}
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
            if key in result:
                raise ValueError(f"duplicate YAML mapping key: {key!r}")
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
        result: list = []
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


def _strict_yaml_loader():
    """Build (once) the single PyYAML authority loader. Strict contract on top of
    SafeLoader semantics: (a) duplicate mapping keys raise ValueError, (b) implicit
    timestamps are kept as strings (no locale/timezone-dependent datetime objects)."""
    if _STRICT_YAML_CACHE.get("loader") is not None:
        return _STRICT_YAML_CACHE["loader"]
    import yaml

    class StrictSafeLoader(yaml.SafeLoader):  # type: ignore[name-defined]
        pass

    ts_tag = "tag:yaml.org,2002:timestamp"
    StrictSafeLoader.yaml_implicit_resolvers = {
        prefix: [(tag, regexp) for (tag, regexp) in resolvers if tag != ts_tag]
        for prefix, resolvers in StrictSafeLoader.yaml_implicit_resolvers.items()
    }

    def _construct_mapping_no_duplicates(loader, node, deep=False):
        loader.flatten_mapping(node)  # keep merge-key ('<<') support
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                hash(key)
            except TypeError as exc:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    f"unhashable mapping key: {key_node.value!r}",
                    key_node.start_mark,
                ) from exc
            if key in mapping:
                raise ValueError(
                    f"duplicate YAML mapping key: {key!r} "
                    f"(line {key_node.start_mark.line + 1})"
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    StrictSafeLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_mapping_no_duplicates,
    )
    _STRICT_YAML_CACHE["loader"] = StrictSafeLoader
    return StrictSafeLoader


def strict_yaml_load(text: str):
    """The PyYAML-side parser contract (F-03). Raises ValueError on duplicate keys."""
    import yaml

    return yaml.load(text, Loader=_strict_yaml_loader())


def _json_no_duplicates(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError(f"duplicate JSON key: {k!r}")
        result[k] = v
    return result


def load_plan(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text, object_pairs_hook=_json_no_duplicates)
    try:
        import yaml  # noqa: F401
    except ImportError:
        # stdlib-only fallback: the bundled block-style-subset parser, same contract
        return _minimal_yaml(text)
    # PyYAML is available -- it is the single authority. A parse error (including a
    # duplicate key) is a real error, never a reason to retry with the other parser.
    return strict_yaml_load(text)


def parser_identity(suffix: str = "") -> str:
    """Name+version of the parser this environment resolves to (F-03)."""
    if suffix.lower() == ".json":
        return f"json/stdlib (python {python_version()}; duplicate keys rejected)"
    try:
        import yaml
    except ImportError:
        return (
            "bundled-minimal-yaml/1 (PyYAML absent; block-style subset, "
            "corpus-equivalent contract, duplicate keys rejected)"
        )
    return (
        f"pyyaml/{getattr(yaml, '__version__', 'unknown')} strict-safe-loader "
        f"(duplicate keys rejected; timestamps kept as strings)"
    )


def python_version() -> str:
    return sys.version.split()[0]


def load_schema() -> dict:
    """Load the sibling schema file; C10 enforces whatever it declares."""
    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "prework-plan.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def _type_ok(value, types) -> bool:
    if not isinstance(types, list):
        types = [types]
    for t in types:
        if t == "object" and isinstance(value, dict):
            return True
        if t == "array" and isinstance(value, list):
            return True
        if t == "string" and isinstance(value, str):
            return True
        if t == "boolean" and isinstance(value, bool):
            return True
        if t == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if t == "null" and value is None:
            return True
    return False


def _conformance_walk(value, schema: dict, path: str, fails: list[str],
                      root: dict | None = None, depth: int = 0) -> None:
    """C10: enforce the schema's declared keyword subset (F-02): required keys,
    additionalProperties=false, local $ref targets, enum, const, oneOf, leaf types
    (incl. union types), minLength, minItems, pattern, and if/then. Unsupported
    keywords never reach this walk: validate() pre-scans the schema and fails closed
    on them."""
    if depth > 24:  # bounded: a schema this deep is a schema bug, not a plan bug
        fails.append(f"FAIL: C10 - {path}: schema nesting exceeds the walk bound")
        return
    if not isinstance(schema, dict) or not schema:
        return
    if "$ref" in schema:
        ref = schema["$ref"]
        if isinstance(root, dict) and isinstance(ref, str) and ref.startswith("#/"):
            target = root
            for part in ref[2:].split("/"):
                target = target.get(part) if isinstance(target, dict) else None
            if target is None:
                fails.append(f"FAIL: C10 - {path}: unresolvable schema $ref {ref!r}")
                return
            _conformance_walk(value, target, path, fails, root, depth + 1)
            return
        fails.append(f"FAIL: C10 - {path}: non-local schema $ref {ref!r} is not enforced")
        return
    if "oneOf" in schema:
        branches = schema["oneOf"]
        matched = 0
        if isinstance(branches, list):
            for branch in branches:
                probe: list[str] = []
                if isinstance(branch, dict):
                    _conformance_walk(value, branch, f"{path}(oneOf)", probe, root, depth + 1)
                    if not probe:
                        matched += 1
        if matched != 1:
            fails.append(
                f"FAIL: C10 - {path}: value {value!r} matches {matched} oneOf branches "
                f"(exactly 1 required)"
            )
    if "const" in schema:
        c = schema["const"]
        if not (value == c and isinstance(value, bool) == isinstance(c, bool)):
            fails.append(f"FAIL: C10 - {path}: value {value!r} != const {c!r}")
    if "enum" in schema and value not in schema["enum"]:
        fails.append(
            f"FAIL: C10 - {path}: value {value!r} is not one of the schema enum "
            f"{schema['enum']!r}"
        )
    if "type" in schema and not _type_ok(value, schema["type"]):
        fails.append(
            f"FAIL: C10 - {path}: value {value!r} does not match declared type "
            f"{schema['type']!r}"
        )
        return
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            fails.append(
                f"FAIL: C10 - {path}: string shorter than declared minLength "
                f"{schema['minLength']}: {value!r}"
            )
        if "pattern" in schema:
            try:
                if re.search(schema["pattern"], value) is None:
                    fails.append(
                        f"FAIL: C10 - {path}: value {value!r} does not match schema "
                        f"pattern {schema['pattern']!r}"
                    )
            except re.error as exc:
                fails.append(
                    f"FAIL: C10 - {path}: schema pattern {schema['pattern']!r} is not a "
                    f"valid regex ({exc}) - fail closed"
                )
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            fails.append(
                f"FAIL: C10 - {path}: list shorter than declared minItems "
                f"{schema['minItems']}"
            )
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                _conformance_walk(item, items, f"{path}[{i}]", fails, root, depth + 1)
    if isinstance(value, dict) and (
        schema.get("type") == "object" or "properties" in schema or "required" in schema
    ):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                fails.append(f"FAIL: C10 - {path}: required key missing per schema: {req}")
        if schema.get("additionalProperties") is False:
            for key in sorted(value):
                if key not in props:
                    fails.append(
                        f"FAIL: C10 - {path}: key {key!r} is not declared in the schema "
                        f"(additionalProperties=false)"
                    )
        for key, sub in props.items():
            if key in value:
                _conformance_walk(value[key], sub, f"{path}.{key}", fails, root, depth + 1)
    # if / then / else
    if "if" in schema:
        probe: list[str] = []
        if isinstance(schema["if"], dict):
            _conformance_walk(value, schema["if"], f"{path}(if)", probe, root, depth + 1)
        if not probe:
            if "then" in schema and isinstance(schema["then"], dict):
                _conformance_walk(value, schema["then"], f"{path}(then)", fails, root, depth + 1)
        elif "else" in schema and isinstance(schema["else"], dict):
            _conformance_walk(value, schema["else"], f"{path}(else)", fails, root, depth + 1)


def _scan_schema_keywords(schema, path: str, fails: list[str], root: dict | None = None) -> None:
    """F-02 fail-closed half: any schema keyword outside the enforced subset is an
    error, never a silent no-op. Run once over the whole schema tree before walking
    the plan."""
    if not isinstance(schema, dict):
        return
    if root is None:
        root = schema
    for key in schema:
        if key not in ALLOWED_SCHEMA_KEYWORDS:
            fails.append(
                f"FAIL: C10 - schema keyword {key!r} at {path} is outside the enforced "
                f"subset - fail closed (validator implements: "
                f"{sorted(SUPPORTED_SCHEMA_KEYWORDS)})"
            )
    for key in ("if", "then", "else"):
        if key in schema:
            _scan_schema_keywords(schema[key], f"{path}.{key}", fails, root)
    if isinstance(schema.get("oneOf"), list):
        for i, branch in enumerate(schema["oneOf"]):
            _scan_schema_keywords(branch, f"{path}.oneOf[{i}]", fails, root)
    props = schema.get("properties")
    if isinstance(props, dict):
        for k, v in props.items():
            _scan_schema_keywords(v, f"{path}.properties.{k}", fails, root)
    if isinstance(schema.get("items"), dict):
        _scan_schema_keywords(schema["items"], f"{path}.items", fails, root)
    if isinstance(schema.get("additionalProperties"), dict):
        _scan_schema_keywords(schema["additionalProperties"], f"{path}.additionalProperties", fails, root)
    if isinstance(schema.get("$defs"), dict):
        for k, v in schema["$defs"].items():
            _scan_schema_keywords(v, f"{path}.$defs.{k}", fails, root)
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/") and isinstance(root, dict):
        target = root
        for part in ref[2:].split("/"):
            target = target.get(part) if isinstance(target, dict) else None
        if isinstance(target, dict):
            _scan_schema_keywords(target, f"{path}$ref:{ref}", fails, root)


def _is_placeholder(v) -> bool:
    return not isinstance(v, str) or v.strip().upper() in PLACEHOLDER_VALUES


def validate(plan, schema: dict | None = None) -> list[str]:
    fails: list[str] = []

    def fail(cid: str, detail: str):
        fails.append(f"FAIL: {cid} - {detail}")

    if not isinstance(plan, dict):
        return ["FAIL: C9 - top-level document is not a mapping"]

    # C9 - required top-level keys present
    for key in (
        "work_unit", "actor", "generated_at", "baseline_id", "starting_candidate",
        "provenance", "starting_point_readback", "requirements", "review", "forecast",
    ):
        if key not in plan or plan[key] in (None, ""):
            fail("C9", f"missing or empty top-level key: {key}")

    # C10 - conformance to the published schema (v7.1, F-02). A None schema argument
    # means the library caller did not pass one: self-load it here so the C10 contract
    # holds for validate(plan) too. A schema that cannot be loaded, or that declares
    # keywords outside the enforced subset, is a fail-closed event, never a silent skip.
    if schema is None:
        try:
            schema = load_schema()
        except Exception as exc:  # noqa: BLE001
            fail("C10", f"schema could not be loaded: {exc}")
            schema = None
    if schema is not None:
        scan: list[str] = []
        _scan_schema_keywords(schema, "schema", scan, root=schema)
        fails.extend(scan)
        _conformance_walk(plan, schema, "plan", fails, root=schema)

    sc = plan.get("starting_candidate")

    # C1 - exactly one starting candidate, 64-hex sha256 (fullmatch), baseline_id present
    if not isinstance(sc, dict):
        fail("C1", "starting_candidate is not a mapping (exactly one required)")
    else:
        if not isinstance(sc.get("sha256"), str) or not HEX64.fullmatch(sc.get("sha256", "")):
            fail("C1", f"starting_candidate.sha256 is not 64 lowercase hex: {sc.get('sha256')!r}")
        if sc.get("type") not in ("commit", "tree", "rev", "doc"):
            fail("C1", f"starting_candidate.type invalid: {sc.get('type')!r}")
        if not sc.get("ref") or not isinstance(sc.get("ref"), str):
            fail("C1", "starting_candidate.ref is empty")
    if not plan.get("baseline_id"):
        fail("C1", "baseline_id is empty")

    # C2 - requirement ids unique and well-formed (fullmatch)
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
        if not isinstance(rid, str) or not REQ_ID.fullmatch(rid):
            fail("C2", f"requirements[{i}].id not fully matching R-[0-9]+ (trailing "
                       f"characters, incl. newlines, are rejected): {rid!r}")
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

    # C4 - unreachable requirement needs a capability decision; accept-as-open names
    # the honest end cell
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        if r.get("reachable") is False:
            dec = r.get("capability_decision")
            if dec not in CAP_DECISIONS:
                fail("C4", f"{rid}: reachable=false but capability_decision is {dec!r}")
            elif dec == "accept-as-open":
                end = r.get("accept_as_open_end_state")
                if not isinstance(end, str) or not end.strip():
                    fail("C4", f"{rid}: accept-as-open but accept_as_open_end_state is empty")
                elif not CELL_IN_TEXT.search(end):
                    fail("C4", f"{rid}: accept-as-open must name the honest end cell "
                               f"(E[1-5]/R[0-2]) in accept_as_open_end_state: {end!r}")
        elif r.get("reachable") is not True:
            fail("C4", f"{rid}: reachable must be an explicit boolean, got {r.get('reachable')!r}")

    # C5 - drift must be reconciled and rebound to the plan's baseline
    prov = plan.get("provenance")
    drift = isinstance(prov, dict) and prov.get("drift_at_start") is True
    if not isinstance(prov, dict):
        fail("C5", "provenance missing or not a mapping")
    else:
        drift_flag = prov.get("drift_at_start")
        if drift_flag is True:
            rec = prov.get("reconciliation")
            if not isinstance(rec, dict) or not rec:
                fail("C5", "drift_at_start=true but reconciliation block is missing or empty")
            else:
                if rec.get("action") not in ("reconcile", "accept"):
                    fail("C5", f"reconciliation.action invalid: {rec.get('action')!r}")
                if rec.get("rebound") is not True:
                    fail("C5", "reconciliation.rebound must be true (three live pointers may not be carried past rebind)")
                if not rec.get("new_baseline_id"):
                    fail("C5", "reconciliation.new_baseline_id is missing or empty (drift must resolve to one named base)")
                elif rec.get("new_baseline_id") != plan.get("baseline_id"):
                    fail("C5", f"reconciliation.new_baseline_id ({rec.get('new_baseline_id')!r}) != baseline_id ({plan.get('baseline_id')!r})")
        elif drift_flag is not False:
            fail("C5", f"provenance.drift_at_start must be an explicit boolean, got {drift_flag!r}")

    # C6 - any R2 target requires PROVEN review independence (F-04 / REPRO-03):
    # more than the self-attested distinct flag.
    review = plan.get("review")
    if not isinstance(review, dict):
        fail("C6", "review missing or not a mapping")
        review = {}
    if review.get("independence_target") == "R2":
        any_r2_target = True
    if any_r2_target:
        if review.get("author_reviewer_distinct") is not True:
            fail("C6", "an R2 target exists but review.author_reviewer_distinct is not true")
        if _is_placeholder(review.get("reviewer_id")):
            fail("C6", "an R2 target exists but review.reviewer_id is missing or a "
                       "placeholder (actual reviewer identity is required)")
        if _is_placeholder(review.get("route_id")):
            fail("C6", f"an R2 target exists but review.route_id is missing or a "
                       f"placeholder ({review.get('route_id')!r}); NOT_RUN is not an R2 "
                       f"route - same-lineage review is R1 by default")
        if _is_placeholder(review.get("bundle_path")):
            fail("C6", f"an R2 target exists but review.bundle_path is missing or a "
                       f"placeholder ({review.get('bundle_path')!r})")
        receipt = review.get("receipt")
        if not isinstance(receipt, dict):
            fail("C6", "an R2 target exists but review.receipt (review receipt pointer: "
                       "path + sha256) is missing")
        else:
            if _is_placeholder(receipt.get("path")):
                fail("C6", f"review.receipt.path is missing or a placeholder ({receipt.get('path')!r})")
            if not isinstance(receipt.get("sha256"), str) or not HEX64.fullmatch(receipt.get("sha256", "")):
                fail("C6", f"review.receipt.sha256 must be the 64-hex hash of the receipt "
                           f"artifact, got {receipt.get('sha256')!r} (NONE_RESOLVED is not a receipt)")
        if _is_placeholder(review.get("result_ref")):
            fail("C6", "an R2 target exists but review.result_ref (bound result "
                       "reference) is missing or a placeholder")

    # C7 - synced artifact needs a retention reason
    for i, a in enumerate(plan.get("artifact_hygiene") or []):
        if not isinstance(a, dict):
            fail("C7", f"artifact_hygiene[{i}] is not a mapping")
            continue
        if a.get("location") == "synced" and not a.get("retention_reason"):
            fail("C7", f"artifact_hygiene[{i}] ({a.get('artifact')!r}) is synced with no retention_reason")
        elif a.get("location") not in ("host-local", "synced"):
            fail("C7", f"artifact_hygiene[{i}].location invalid: {a.get('location')!r}")

    # C8 - forecast cell well-formed (fullmatch)
    fc = plan.get("forecast")
    if not isinstance(fc, dict):
        fail("C8", "forecast missing or not a mapping")
    else:
        cell = fc.get("best_reachable_cell")
        if not isinstance(cell, str) or not CELL.fullmatch(cell):
            fail("C8", f"forecast.best_reachable_cell not fully matching E[1-5]/R[0-2]: {cell!r}")
        for fld in ("dispositions", "raise_with_caller"):
            if not isinstance(fc.get(fld), list):
                fail("C8", f"forecast.{fld} must be a list")

    # C14 - forecast semantics (F-01 / REPRO-01/02)
    if isinstance(fc, dict) and isinstance(fc.get("dispositions"), list):
        disps = fc["dispositions"]
        for d in disps:
            if not (isinstance(d, str) and d in DISPOSITION_VOCABULARY):
                fail("C14", f"forecast.dispositions contains a value outside the "
                            f"published closed vocabulary {sorted(DISPOSITION_VOCABULARY)}: {d!r}")
        open_rows = [r.get("id", "?") for r in reqs
                     if isinstance(r, dict) and r.get("reachable") is False]
        open_decisions = [r.get("id", "?") for r in reqs
                          if isinstance(r, dict) and r.get("capability_decision") == "accept-as-open"]
        if "CANDIDATE_READY" in disps:
            if len(disps) > 1:
                fail("C14", "CANDIDATE_READY is exclusive - it cannot be listed alongside other dispositions")
            if open_rows:
                fail("C14", f"forecast claims CANDIDATE_READY but requirement(s) {open_rows} "
                            f"are reachable=false - the plan cannot be CANDIDATE_READY")
            if open_decisions:
                fail("C14", f"forecast claims CANDIDATE_READY but requirement(s) {open_decisions} "
                            f"carry an open (accept-as-open) capability decision")
            if drift:
                fail("C14", "forecast claims CANDIDATE_READY but provenance.drift_at_start=true - "
                            "reconciled start drift remains a disclosed disposition "
                            "(PROVENANCE_DRIFT_AT_START)")
        if drift and "PROVENANCE_DRIFT_AT_START" not in disps:
            fail("C14", "provenance.drift_at_start=true but forecast.dispositions does not "
                        "disclose PROVENANCE_DRIFT_AT_START - reconciled start drift is a "
                        "disclosed disposition and an empty disposition list is not accepted")

    # C11 - evidence_outputs (v1.1, optional section): each declared output must
    # name an immutable write mechanism (the H-A rule: a script that writes its
    # own evidence must never be able to overwrite an earlier run's artifact
    # within the unit).
    for i, eo in enumerate(plan.get("evidence_outputs") or []):
        if not isinstance(eo, dict):
            fail("C11", f"evidence_outputs[{i}] is not a mapping")
            continue
        if not eo.get("artifact") or not isinstance(eo.get("artifact"), str):
            fail("C11", f"evidence_outputs[{i}].artifact missing or empty")
        if not eo.get("writer") or not isinstance(eo.get("writer"), str):
            fail("C11", f"evidence_outputs[{i}].writer missing or empty")
        if eo.get("immutability") not in IMMUTABILITY_MECHANISMS:
            fail("C11", f"evidence_outputs[{i}].immutability must be one of {sorted(IMMUTABILITY_MECHANISMS)}, got {eo.get('immutability')!r}")

    # C12 - control_copies (v1.1, optional section): a pristine copy is a
    # verified-then-frozen witness (the H-B rule). It must carry a pin, be
    # verified before use, and if any execution is allowed inside it after
    # verification, a recreation procedure must be named.
    for i, cc in enumerate(plan.get("control_copies") or []):
        if not isinstance(cc, dict):
            fail("C12", f"control_copies[{i}] is not a mapping")
            continue
        if not cc.get("path") or not isinstance(cc.get("path"), str):
            fail("C12", f"control_copies[{i}].path missing or empty")
        if not isinstance(cc.get("pin_sha256"), str) or not HEX64.fullmatch(cc.get("pin_sha256", "")):
            fail("C12", f"control_copies[{i}].pin_sha256 is not 64 lowercase hex")
        if cc.get("verified_before_use") is not True:
            fail("C12", f"control_copies[{i}] must be verified_before_use=true (a control copy that was not verified first is not a control copy)")
        if cc.get("execution_allowed_after_verification") is True and not cc.get("recreation_procedure"):
            fail("C12", f"control_copies[{i}] allows execution after verification but names no recreation_procedure")

    # C13 - requirements[].coverage (v1.1, optional section): the H-C rule. A
    # coverage item names what is reviewed and the artifact that will demonstrate
    # the review reached it; an item with no demonstrable artifact is declared
    # accept-as-open at plan time, never silently dropped.
    for r in reqs:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        cov = r.get("coverage")
        if cov is None:
            continue
        if not isinstance(cov, list):
            fail("C13", f"{rid}: coverage must be a list when present")
            continue
        cov_seen = set()
        for j, item in enumerate(cov):
            if not isinstance(item, dict):
                fail("C13", f"{rid}: coverage[{j}] is not a mapping")
                continue
            for fld in ("item", "demonstration", "target"):
                if not item.get(fld) or not isinstance(item.get(fld), str):
                    fail("C13", f"{rid}: coverage[{j}].{fld} missing or empty")
            it = item.get("item")
            if isinstance(it, str):
                if it in cov_seen:
                    fail("C13", f"{rid}: duplicate coverage item: {it}")
                cov_seen.add(it)

    # C15 - starting-point readback (F-05 / REPRO-07): the provenance pointers must
    # bind to the actual candidate.
    sbr = plan.get("starting_point_readback")
    if not isinstance(sbr, dict):
        fail("C15", "starting_point_readback missing or not a mapping (the plan must "
                    "bind its pointers to the actual candidate: candidate path + hash "
                    "+ HEAD/tree state or an explicit non-git declaration)")
    else:
        cpath = sbr.get("candidate_path")
        if _is_placeholder(cpath):
            fail("C15", f"starting_point_readback.candidate_path is missing or a placeholder ({cpath!r})")
        csha = sbr.get("candidate_sha256")
        if not isinstance(csha, str) or not HEX64.fullmatch(csha):
            fail("C15", f"starting_point_readback.candidate_sha256 is not 64 lowercase hex: {csha!r}")
        elif isinstance(sc, dict) and sc.get("sha256") != csha:
            fail("C15", "starting_point_readback.candidate_sha256 does not equal "
                        "starting_candidate.sha256 - the readback does not bind to the "
                        "declared candidate")
        if isinstance(sc, dict) and sc.get("type") == "doc" and isinstance(cpath, str) \
                and cpath.replace("\\", "/") != str(sc.get("ref", "")).replace("\\", "/"):
            fail("C15", "starting_point_readback.candidate_path does not equal "
                        "starting_candidate.ref (a doc candidate binds by path + hash)")
        if sbr.get("points_at_candidate") is not True:
            fail("C15", f"starting_point_readback.points_at_candidate must be true, got "
                        f"{sbr.get('points_at_candidate')!r} (a readback that does not "
                        f"confirm the candidate is drift: re-run step 1)")
        gs = sbr.get("git_state")
        if not isinstance(gs, dict):
            fail("C15", "starting_point_readback.git_state missing (git HEAD/tree state "
                        "or an explicit non-git declaration is required)")
        elif gs.get("kind") == "git":
            if _is_placeholder(gs.get("head")):
                fail("C15", f"starting_point_readback.git_state.head is missing or a placeholder ({gs.get('head')!r})")
            if not isinstance(gs.get("clean"), bool):
                fail("C15", f"starting_point_readback.git_state.clean must be an explicit boolean (dirty status), got {gs.get('clean')!r}")
            if "branch" in gs and gs.get("branch") is not None and not isinstance(gs.get("branch"), str):
                fail("C15", f"starting_point_readback.git_state.branch must be a string or null, got {gs.get('branch')!r}")
        elif gs.get("kind") == "non-git":
            if _is_placeholder(gs.get("declaration")):
                fail("C15", f"starting_point_readback.git_state.declaration is missing or "
                            f"a placeholder ({gs.get('declaration')!r}) - an explicit "
                            f"non-git declaration is required")
        else:
            fail("C15", f"starting_point_readback.git_state.kind must be 'git' or 'non-git', got {gs.get('kind')!r}")

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

    # F-03: record the parser identity and Python version with every run.
    print(f"parser: {parser_identity(args.plan.suffix)}")
    print(f"python: {python_version()}")

    try:
        schema = load_schema()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: C10 - schema could not be loaded: {exc}")
        return 1

    fails = validate(plan, schema)
    if fails:
        for line in fails:
            print(line)
        print(f"\n{len(fails)} check(s) failed.")
        return 1
    print("OK: pre-work plan is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
