"""Attack regressions for the 1X review of 2026-09-19 (REPRO-01..07 / F-01..F-05, F-07).

Each test_reproNN reproduces the exact attack input the 1X review demonstrated against
the pre-remediation v7.1 candidate (see
AI_MAESTRO_2G_PACKET_ASTRA_PREP_REVIEW_20260919, REVIEW_2G_PACKETS_AND_ASTRA_PREP_V71_1X_20260919.json).
Every attack input here was ACCEPTED (exit 0, no failures) before the repair; after the
repair each one MUST FAIL validation (errors present / exit non-zero).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate_prework.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SCHEMA = REPO / "schemas" / "prework-plan.schema.json"
DOMAIN_CHECKS = REPO / "references" / "domain-checks.md"
SKILL = REPO / "SKILL.md"


def _load_validator_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("validate_prework", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _plan_copy() -> dict:
    return json.loads((FIXTURES / "valid_v71_full.json").read_text(encoding="utf-8"))


def _run_cli(plan_path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(plan_path)],
        capture_output=True,
        text=True,
    )


def _fails_for(plan: dict) -> list[str]:
    mod = _load_validator_module()
    return mod.validate(plan, mod.load_schema())


# --------------------------------------------------------------------------- #
# REPRO-01 -- F-01: forecast semantics not enforced
# --------------------------------------------------------------------------- #
def test_repro01_forecast_must_not_be_candidate_ready_for_open_rows(tmp_path):
    """1X review REPRO-01 / F-01: every requirement reachable=false with
    accept-as-open end states while the forecast claims CANDIDATE_READY was ACCEPTED
    pre-remediation. Post-remediation this must fail (C14)."""
    plan = _plan_copy()
    for r in plan["requirements"]:
        r["reachable"] = False
        r["capability_decision"] = "accept-as-open"
        r["accept_as_open_end_state"] = "target E2/R1, will end E1/R0"
    plan["forecast"]["dispositions"] = ["CANDIDATE_READY"]
    plan["forecast"]["raise_with_caller"] = []

    fails = _fails_for(plan)
    assert fails, "attack plan must not validate clean"
    assert any(f.startswith("FAIL: C14") for f in fails), fails

    # CLI-level: exit non-zero
    p = tmp_path / "attack_repro01.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    result = _run_cli(p)
    assert result.returncode != 0, result.stdout
    assert "FAIL: C14" in result.stdout


def test_repro01_unknown_forecast_disposition_is_rejected():
    """F-01 companion: the disposition vocabulary is closed; an unknown value must be
    rejected (schema enum via C10, and C14 as the belt-and-braces check)."""
    plan = _plan_copy()
    plan["forecast"]["dispositions"] = ["TOTALLY_FINE_TRUST_US"]
    fails = _fails_for(plan)
    assert fails, "unknown disposition must not validate clean"
    assert any("TOTALLY_FINE_TRUST_US" in f for f in fails), fails


# --------------------------------------------------------------------------- #
# REPRO-02 -- F-01: reconciled drift with no matching forecast disposition
# --------------------------------------------------------------------------- #
def test_repro02_drifted_start_requires_disclosed_provenance_disposition():
    """1X review REPRO-02 / F-01: drift_at_start=true with a valid reconciliation and
    an empty forecast disposition list was ACCEPTED pre-remediation. Drift policy is
    now explicit: reconciled start drift remains a disclosed disposition, so
    forecast.dispositions must contain PROVENANCE_DRIFT_AT_START (C14)."""
    mod = _load_validator_module()

    def drifted_plan(dispositions):
        plan = _plan_copy()
        plan["provenance"]["drift_at_start"] = True
        plan["provenance"]["reconciliation"] = {
            "action": "reconcile",
            "new_baseline_id": plan["baseline_id"],
            "rebound": True,
        }
        plan["forecast"]["dispositions"] = dispositions
        return plan

    for dispositions in ([], ["CANDIDATE_READY"]):
        plan = drifted_plan(dispositions)
        fails = mod.validate(plan, mod.load_schema())
        assert fails, f"drifted plan with dispositions={dispositions!r} must not validate clean"
        assert any(
            f.startswith("FAIL: C14") and "PROVENANCE_DRIFT_AT_START" in f for f in fails
        ), fails


# --------------------------------------------------------------------------- #
# REPRO-03 -- F-04: R2 with self-attested placeholders
# --------------------------------------------------------------------------- #
def test_repro03_r2_target_with_placeholder_route_and_bundle_is_rejected(tmp_path):
    """1X review REPRO-03 / F-04: an R2 target with author_reviewer_distinct=true,
    route_id=NOT_RUN and bundle_path=TBD was ACCEPTED pre-remediation. Post-remediation
    C6 requires reviewer identity, a non-placeholder route and bundle path, a receipt
    pointer with a 64-hex hash, and a bound result reference."""
    plan = _plan_copy()
    plan["requirements"][0]["target"]["review_independence"] = "R2"
    plan["review"] = {
        "required": True,
        "independence_target": "R2",
        "author_reviewer_distinct": True,
        "route_id": "NOT_RUN",
        "bundle_path": "TBD",
    }

    fails = _fails_for(plan)
    assert fails, "placeholder-R2 plan must not validate clean"
    c6 = [f for f in fails if f.startswith("FAIL: C6")]
    assert c6, fails
    assert any("route_id" in f for f in c6), c6
    assert any("bundle_path" in f for f in c6), c6
    assert any("reviewer_id" in f for f in c6), c6

    p = tmp_path / "attack_repro03.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    result = _run_cli(p)
    assert result.returncode != 0, result.stdout
    assert "FAIL: C6" in result.stdout


# --------------------------------------------------------------------------- #
# REPRO-04 -- F-02: schema leaf constraints / pointer constraints not enforced
# --------------------------------------------------------------------------- #
def test_repro04_wrong_leaf_types_and_invalid_pointer_hash_are_rejected():
    """1X review REPRO-04 / F-02: wrong leaf types (actor=123,
    starting_candidate.ref=123, requirements[0].text=123, provenance.handoff.path=123)
    and an invalid pointer hash (sha256='not-a-hash') were ACCEPTED pre-remediation
    because C10 ignored declared leaf type/pattern/oneOf constraints. Each mutation
    must now fail C10."""
    attacks = [
        ("actor type", lambda p: p.__setitem__("actor", 123)),
        ("starting_candidate.ref type", lambda p: p["starting_candidate"].__setitem__("ref", 123)),
        ("requirement text type", lambda p: p["requirements"][0].__setitem__("text", 123)),
        ("pointer path type", lambda p: p["provenance"]["handoff"].__setitem__("path", 123)),
        ("pointer sha256 shape", lambda p: p["provenance"]["handoff"].__setitem__("sha256", "not-a-hash")),
        ("minLength", lambda p: p["requirements"][0].__setitem__("implementation", "")),
    ]
    for label, mutate in attacks:
        plan = _plan_copy()
        mutate(plan)
        fails = _fails_for(plan)
        assert fails, f"attack ({label}) must not validate clean"
        assert any(f.startswith("FAIL: C10") for f in fails), (label, fails)


# --------------------------------------------------------------------------- #
# REPRO-05 -- F-02: trailing newlines accepted by $-anchored regexes
# --------------------------------------------------------------------------- #
def test_repro05_trailing_newline_on_hash_and_id_is_rejected():
    """1X review REPRO-05 / F-02: a 64-hex hash plus a trailing newline and an id plus
    a trailing newline were ACCEPTED pre-remediation (re.match with $). Post-remediation
    hash/ID matching is fullmatch / \\Z-anchored, so both are rejected."""
    mod = _load_validator_module()

    plan = _plan_copy()
    plan["starting_candidate"]["sha256"] = "a" * 64 + "\n"
    fails = mod.validate(plan, mod.load_schema())
    assert fails, "hash with trailing newline must not validate clean"
    assert any(f.startswith("FAIL: C1") or f.startswith("FAIL: C10") for f in fails), fails

    plan2 = _plan_copy()
    plan2["requirements"][0]["id"] = "R-999\n"
    fails2 = mod.validate(plan2, mod.load_schema())
    assert fails2, "id with trailing newline must not validate clean"
    assert any(f.startswith("FAIL: C2") or f.startswith("FAIL: C10") for f in fails2), fails2


def test_repro05_trailing_newline_attack_fixture_fails_via_cli():
    """The bundled attack fixture (hash + id both carrying trailing newlines) must
    fail validation via the CLI."""
    result = _run_cli(FIXTURES / "attack_repro05_trailing_newline.json")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "FAIL:" in result.stdout


# --------------------------------------------------------------------------- #
# REPRO-06 -- F-03: parser divergence + duplicate keys
# --------------------------------------------------------------------------- #
def test_repro06_duplicate_keys_rejected_in_both_parser_modes():
    """1X review REPRO-06 / F-03: duplicate YAML keys were accepted by BOTH parser
    paths (last value silently won). Post-remediation both modes must reject them."""
    mod = _load_validator_module()
    text = (FIXTURES / "attack_repro06_duplicate_keys.yaml").read_text(encoding="utf-8")

    # mode 1: bundled fallback parser
    with pytest.raises(ValueError, match="duplicate"):
        mod._minimal_yaml(text)

    # mode 2: PyYAML strict contract (skipped only if PyYAML is genuinely absent)
    try:
        import yaml  # noqa: F401
        have_yaml = True
    except ImportError:
        have_yaml = False
    if have_yaml:
        with pytest.raises(ValueError, match="duplicate"):
            mod.strict_yaml_load(text)


def test_repro06_duplicate_keys_attack_fixture_fails_via_cli():
    result = _run_cli(FIXTURES / "attack_repro06_duplicate_keys.yaml")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "duplicate" in (result.stdout + result.stderr).lower()


def test_repro06_yaml11_booleans_agree_in_both_modes():
    """1X review REPRO-06 / F-03: PyYAML and the fallback parser disagreed on YAML
    no/yes. Post-remediation the fallback implements PyYAML's YAML 1.1 boolean set
    exactly, and the whole scalar battery parses identically in both modes."""
    mod = _load_validator_module()
    battery = (
        "a: yes\n"
        "b: no\n"
        "c: on\n"
        "d: off\n"
        "e: true\n"
        "f: FALSE\n"
        "g: null\n"
        "h: ~\n"
        "i: 12\n"
        "j: 1.5\n"
        "k: \"quoted string\"\n"
        "l: [1, 2, three]\n"
        "m: {x: 1, y: two}\n"
        "t: 2026-09-19\n"
    )
    fallback = mod._minimal_yaml(battery)
    assert fallback["a"] is True and fallback["b"] is False
    assert fallback["c"] is True and fallback["d"] is False
    assert fallback["g"] is None and fallback["h"] is None
    try:
        import yaml  # noqa: F401
    except ImportError:
        pytest.skip("PyYAML absent - fallback is the single mode")
    strict = mod.strict_yaml_load(battery)
    assert strict == fallback, (strict, fallback)


def test_repro06_parser_identity_recorded_in_output():
    """F-03: the parser name+version must be recorded in the validation output."""
    result = _run_cli(FIXTURES / "valid_minimal.yaml")
    assert result.returncode == 0, result.stdout + result.stderr
    m = re.search(r"^parser: (.+)$", result.stdout, re.MULTILINE)
    assert m, f"no parser line in output: {result.stdout}"
    identity = m.group(1)
    assert ("pyyaml/" in identity) or ("bundled-minimal-yaml/" in identity), identity
    assert re.search(r"^python: \d+\.\d+", result.stdout, re.MULTILINE), result.stdout


def test_repro06_json_duplicate_keys_rejected():
    """F-03 contract extended to JSON: duplicate keys must not silently collapse."""
    mod = _load_validator_module()
    raw = '{"work_unit": "a", "work_unit": "b"}'
    import tempfile, os
    fd, tmpname = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(raw)
        with pytest.raises(ValueError, match="duplicate JSON key"):
            mod.load_plan(__import__("pathlib").Path(tmpname))
    finally:
        os.unlink(tmpname)


# --------------------------------------------------------------------------- #
# REPRO-07 -- F-05: starting-point verification
# --------------------------------------------------------------------------- #
def test_repro07_starting_point_readback_binds_plan_to_candidate(tmp_path):
    """1X review REPRO-07 / F-05: the validator never verified the source tree against
    the provenance pointers and the pointer schema had no field identifying the
    candidate. Post-remediation a required starting_point_readback block must be
    present, must carry the candidate hash (equal to starting_candidate.sha256),
    points_at_candidate=true, and a git or explicit non-git state."""
    # (a) missing readback -> C15 + C10
    plan = _plan_copy()
    del plan["starting_point_readback"]
    fails = _fails_for(plan)
    assert any(f.startswith("FAIL: C15") for f in fails), fails

    # (b) hash mismatch -> the readback does not bind to the declared candidate
    plan_b = _plan_copy()
    plan_b["starting_point_readback"]["candidate_sha256"] = "b" * 64
    fails_b = _fails_for(plan_b)
    assert any(f.startswith("FAIL: C15") and "does not equal" in f for f in fails_b), fails_b

    # (c) points_at_candidate=false -> drift, never a clean plan
    plan_c = _plan_copy()
    plan_c["starting_point_readback"]["points_at_candidate"] = False
    fails_c = _fails_for(plan_c)
    assert any(f.startswith("FAIL: C15") for f in fails_c), fails_c

    # (d) placeholder git head
    plan_d = _plan_copy()
    plan_d["starting_point_readback"]["git_state"] = {"kind": "git", "head": "TBD", "clean": True}
    fails_d = _fails_for(plan_d)
    assert any(f.startswith("FAIL: C15") and "head" in f for f in fails_d), fails_d

    # (e) non-git declaration must be explicit, not a placeholder
    plan_e = _plan_copy()
    plan_e["starting_point_readback"]["git_state"] = {"kind": "non-git", "declaration": "TBD"}
    fails_e = _fails_for(plan_e)
    assert any(f.startswith("FAIL: C15") and "declaration" in f for f in fails_e), fails_e

    p = tmp_path / "attack_repro07.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    result = _run_cli(p)
    assert result.returncode != 0, result.stdout
    assert "FAIL: C15" in result.stdout


# --------------------------------------------------------------------------- #
# F-07 -- domain module vocabulary agreement
# --------------------------------------------------------------------------- #
def test_module_vocabulary_agrees_between_schema_and_domain_checks():
    """F-07: the schema's module enum and the Module IDs list in
    references/domain-checks.md must agree exactly (evidence-hygiene was in the schema
    but missing from the doc)."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    schema_modules = {
        m for m in schema["properties"]["requirements"]["items"]["properties"]["module"]["enum"]
        if m is not None
    }
    text = DOMAIN_CHECKS.read_text(encoding="utf-8")
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Module IDs:"))
    paragraph = []
    for line in lines[start:]:
        if line.strip() == "":
            break
        paragraph.append(line)
    ids_text = " ".join(paragraph)
    # keep only the first sentence (the Module IDs list itself)
    ids_sentence = ids_text.split(". ")[0]
    doc_modules = set(re.findall(r"`([a-z0-9-]+)`", ids_sentence))
    assert "evidence-hygiene" in doc_modules, ids_sentence
    assert schema_modules == doc_modules, (schema_modules, doc_modules)


def test_forecast_vocabulary_documented_in_skill_md():
    """F-01 companion: every validator-known disposition word is documented in the
    core SKILL.md step-6 vocabulary."""
    mod = _load_validator_module()
    text = SKILL.read_text(encoding="utf-8")
    missing = sorted(w for w in mod.DISPOSITION_VOCABULARY if w not in text)
    assert not missing, f"dispositions not documented in SKILL.md: {missing}"
