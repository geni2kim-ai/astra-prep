"""Deterministic mutation fuzzing for the strict YAML/JSON parser boundary.

The fuzzing is intentionally reproducible: a fixed seed generates many structurally
different inputs while each family has a documented accept/reject policy. The goal is
not broad YAML compatibility; this is an offline verification gate (component) with a
narrow, fail-closed fallback grammar.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import random
import string
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest

REPO = Path(__file__).resolve().parents[1]
VALIDATOR = REPO / "scripts" / "validate_prework.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
POLICY_FIXTURE = FIXTURES / "attack_parser_fuzz_cases.json"
VALID_PLAN = FIXTURES / "valid_v71_full.json"
SEED = 20261001


def _load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("validate_prework_fuzz", VALIDATOR)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pyyaml_error_type() -> type[BaseException]:
    yaml = pytest.importorskip("yaml")
    return yaml.YAMLError


def _decision(parser: Callable[[str], Any], text: str) -> tuple[str, Any | None]:
    """Return accept/reject while failing the test on an unexpected exception class."""
    yaml_error = _pyyaml_error_type()
    try:
        return "accept", parser(text)
    except (ValueError, yaml_error):
        return "reject", None
    except Exception as exc:  # pragma: no cover - this is the invariant under test
        pytest.fail(f"unhandled parser exception {type(exc).__name__}: {exc}")


def _random_key(rng: random.Random) -> str:
    alphabet = string.ascii_letters + string.digits + "_"
    return rng.choice(string.ascii_letters) + "".join(rng.choice(alphabet) for _ in range(11))


def test_attack_fixture_policy_matches_both_parser_modes() -> None:
    mod = _load_validator_module()
    fixture = json.loads(POLICY_FIXTURE.read_text(encoding="utf-8"))

    for case in fixture["cases"]:
        expected = case["expected"]
        minimal_decision, minimal_value = _decision(mod._minimal_yaml, case["text"])
        strict_decision, strict_value = _decision(mod.strict_yaml_load, case["text"])

        if expected == "reject":
            assert minimal_decision == "reject", case["id"]
            assert strict_decision == "reject", case["id"]
        else:
            assert expected == "accept_timestamp_string"
            assert minimal_decision == strict_decision == "accept", case["id"]
            key = case["key"]
            value = case["value"]
            assert minimal_value[key] == value and isinstance(minimal_value[key], str)
            assert strict_value[key] == value and isinstance(strict_value[key], str)


def test_fuzz_duplicate_mapping_keys_are_always_rejected() -> None:
    mod = _load_validator_module()
    rng = random.Random(SEED)

    for _ in range(200):
        key = _random_key(rng)
        first = rng.randint(-10_000, 10_000)
        second = rng.randint(-10_000, 10_000)
        block = f"{key}: {first}\n{key}: {second}\n"
        flow = f"root: {{{key}: {first}, {key}: {second}}}\n"
        for text in (block, flow):
            assert _decision(mod._minimal_yaml, text)[0] == "reject"
            assert _decision(mod.strict_yaml_load, text)[0] == "reject"


def test_fuzz_timestamp_scalars_remain_strings() -> None:
    mod = _load_validator_module()
    rng = random.Random(SEED + 1)

    for _ in range(200):
        year = rng.randint(2000, 2099)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        hour = rng.randint(0, 23)
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        stamp = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
        text = f"stamp: {stamp}\n"
        for parser in (mod._minimal_yaml, mod.strict_yaml_load):
            decision, value = _decision(parser, text)
            assert decision == "accept"
            assert value["stamp"] == stamp
            assert isinstance(value["stamp"], str)


def test_fuzz_malformed_flow_is_rejected_without_unhandled_exception() -> None:
    mod = _load_validator_module()
    rng = random.Random(SEED + 2)

    for _ in range(200):
        key = _random_key(rng)
        number = rng.randint(0, 9999)
        malformed = rng.choice(
            [
                f"{key}: [1, 2, {number}\n",
                f"{key}: {{x: 1, y: {number}\n",
                f"{key}: [1, {{x: {number}}}\n",
                f"{key}: \"unterminated-{number}\n",
            ]
        )
        assert _decision(mod._minimal_yaml, malformed)[0] == "reject"
        assert _decision(mod.strict_yaml_load, malformed)[0] == "reject"


def test_cli_fuzz_corpus_has_only_documented_exit_classes(tmp_path: Path) -> None:
    rng = random.Random(SEED + 3)

    for index in range(80):
        malformed = index % 2 == 0
        if malformed:
            text = f"alpha: [1, {rng.randint(0, 9999)}\n"
            expected = 2
        else:
            # Syntactically accepted, but deliberately not a valid pre-work plan.
            text = f"stamp: 2026-10-{rng.randint(1, 28):02d}\n"
            expected = 1

        path = tmp_path / f"fuzz-{index}.yaml"
        path.write_text(text, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        assert "Traceback" not in result.stderr


def test_fuzz_full_string_anchor_injections_are_rejected() -> None:
    mod = _load_validator_module()
    base = json.loads(VALID_PLAN.read_text(encoding="utf-8"))
    rng = random.Random(SEED + 4)
    alphabet = "0123456789abcdef"

    for _ in range(120):
        plan = copy.deepcopy(base)
        if rng.choice((True, False)):
            injected = "".join(rng.choice(alphabet) for _ in range(64)) + "\n"
            plan["starting_candidate"]["sha256"] = injected
            fails = mod.validate(plan, mod.load_schema())
            assert any(f.startswith(("FAIL: C1", "FAIL: C10")) for f in fails)
        else:
            injected = f"R-{rng.randint(1, 99999)}\n"
            plan["requirements"][0]["id"] = injected
            fails = mod.validate(plan, mod.load_schema())
            assert any(f.startswith(("FAIL: C2", "FAIL: C10")) for f in fails)
