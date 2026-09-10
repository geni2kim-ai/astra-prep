"""Tests for scripts/validate_prework.py and the core-first constraint on SKILL.md."""

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


def run_validator(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(FIXTURES / fixture)],
        capture_output=True,
        text=True,
    )


# --------------------------------------------------------------------------- #
# valid fixtures
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "fixture",
    ["valid_minimal.yaml", "valid_drift_rebound.yaml", "valid_flow_style.yaml"],
)
def test_valid_fixtures_pass(fixture):
    result = run_validator(fixture)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK:" in result.stdout


# --------------------------------------------------------------------------- #
# invalid fixtures - each must fail on its named check
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "fixture,check_id",
    [
        ("invalid_two_candidates.yaml", "C1"),
        ("invalid_drift_no_rebind.yaml", "C5"),
        ("invalid_r2_no_separation.yaml", "C6"),
        ("invalid_unreachable_no_decision.yaml", "C4"),
    ],
)
def test_invalid_fixtures_fail(fixture, check_id):
    result = run_validator(fixture)
    assert result.returncode == 1, f"expected exit 1, got {result.returncode}: {result.stdout}"
    assert f"FAIL: {check_id}" in result.stdout, result.stdout


def test_missing_file_is_exit_2():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(FIXTURES / "does_not_exist.yaml")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


# --------------------------------------------------------------------------- #
# schema is well-formed JSON, draft 2020-12
# --------------------------------------------------------------------------- #
def test_schema_is_well_formed():
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert doc["type"] == "object"
    assert "requirements" in doc["properties"]


# --------------------------------------------------------------------------- #
# core-first gate: SKILL.md carries no ecosystem-specific identifiers
# --------------------------------------------------------------------------- #
FORBIDDEN_IN_CORE = re.compile(
    r"\b1C\b|\b1X\b|\b2G\b|\b2X\b|\b3X\b|\b3H\b|\b1A\b|\b4C\b|\b4X\b|\b4G\b|\b2O\b"
    r"|bridge_redagent|bridge_spt|chatgpt_review_bridge|redagent|astra-shadow"
    r"|PC4|PC1|BETA_LOCAL|0\.Workspace|0\.AI_Maestro|ai[-_]maestro|Maestro"
    r"|finality.?lint|Synapse|Syncthing|dispatch_app|\.state\.json",
    re.IGNORECASE,
)

# The ONE allowed ecosystem reference: the pointer to the shipped example profile.
ALLOWED_CORE_MENTION = "profiles/ai-maestro.md"


def test_core_skill_has_no_ecosystem_identifiers():
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    scrubbed = text.replace(ALLOWED_CORE_MENTION, "<PROFILE_POINTER>")
    hits = sorted({m.group(0) for m in FORBIDDEN_IN_CORE.finditer(scrubbed)})
    assert not hits, f"SKILL.md core leaked ecosystem-specific identifiers: {hits}"


def test_allowed_profile_pointer_appears_exactly_where_expected():
    """The only ecosystem-flavoured token in the core is the profile pointer,
    and it must be present (the core is useless without it)."""
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert text.count(ALLOWED_CORE_MENTION) >= 1


def test_profile_exists_and_is_the_only_node_specific_file():
    assert (REPO / "profiles" / "ai-maestro.md").is_file()
    core = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert "profiles/ai-maestro.md" in core


# --------------------------------------------------------------------------- #
# the bundled minimal YAML parser must agree with PyYAML (stdlib-only path)
# --------------------------------------------------------------------------- #
def _load_validator_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("validate_prework", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    "fixture",
    [
        "valid_minimal.yaml",
        "valid_drift_rebound.yaml",
        "valid_flow_style.yaml",
        "invalid_two_candidates.yaml",
        "invalid_drift_no_rebind.yaml",
        "invalid_r2_no_separation.yaml",
        "invalid_unreachable_no_decision.yaml",
    ],
)
def test_minimal_yaml_matches_pyyaml(fixture):
    yaml = pytest.importorskip("yaml")
    mod = _load_validator_module()
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    assert mod._minimal_yaml(text) == yaml.safe_load(text)


def test_minimal_yaml_rejects_tab_indentation():
    mod = _load_validator_module()
    with pytest.raises(ValueError):
        mod._minimal_yaml("forecast:\n\tbest_reachable_cell: E1/R0\n")


def test_pyyaml_syntax_error_is_not_masked(tmp_path):
    """With PyYAML present, a real YAML syntax error must surface as exit 2,
    not be silently retried with the lenient hand parser."""
    pytest.importorskip("yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("work_unit: x\n  bad: indent\n:::\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(bad)], capture_output=True, text=True
    )
    assert result.returncode == 2, result.stdout + result.stderr


def test_minimal_parser_path_still_validates(monkeypatch):
    """Force the no-PyYAML branch and confirm a valid fixture still passes."""
    mod = _load_validator_module()
    real_import = __import__

    def blocked_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked_import)
    plan = mod.load_plan(FIXTURES / "valid_drift_rebound.yaml")
    assert mod.validate(plan) == []
