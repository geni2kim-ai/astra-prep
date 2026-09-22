# astra-prep v7.1 CANDIDATE bundle -- 2G draft (2026-09-19, post-1X006 remediation)

```yaml
status: CANDIDATE_DRAFT_2G_ONLY__POST_1X006_REMEDIATION
author_node: 2G
work_unit: 20260919-2G-ASKILL-V71-R48 (remediation pass R54 / 20260919-2G-ASTRAPREP-R54-1X006-REMEDIATION)
base_version: v7 (pinned relay bundle, SKILL.md sha256 9e5d15eddb668b5f2c99a3a6df4843c35bba0a16c2aac33d02d21257e3ba2dfb)
review_driving_this_revision: AI_MAESTRO_2G_PACKET_ASTRA_PREP_REVIEW_20260919_1X (findings F-01..F-07, REPRO-01..07)
finality: non_final
decision_authority: none
promotion: 1C-owned per GOV-SKILL-001 (1X re-review -> 4G relay test -> 4X loader check -> 1C disposition -> USER gate)
```

This directory is a **candidate copy**, authored by node 2G. The pinned v7 relay
bundle at `Hub/skills/relay/astra_prep_20260910/` is untouched (re-verified by hash
after this remediation pass; see CANDIDATE_HASHES.json). Nothing here is approved,
adopted, or deployed; it is a proposal with working code and tests. Promotion is
**pending 1C/1X** (1X re-review of this remediation is required).

## What changed vs v7 (five deltas, born from R46/R47 + the simulation)

1. **C10 -- schema conformance now enforced (S-0 fix).** The v7 validator ran only its
   own hand-rolled checks (C1-C9) while the schema declared `additionalProperties:
   false`; a plan violating the published contract exited 0. v7.1 loads the sibling
   schema and walks every declared level: missing required keys and undeclared keys
   fail closed. Proof (same fixture, 2026-09-19): undeclared top-level key ->
   v7 exit 0, v7.1 exit 1 (`tests/fixtures/invalid_unknown_top_key.json`).
2. **C11 evidence_outputs (schema v1.1, optional).** Any self-writing probe/script
   must declare an immutable write mechanism: `timestamped-path`, `copy-before-rerun`,
   or `append-only`. Born from R47: a probe that overwrites its own output file
   destroyed the pre-fix evidence and forced a restoration exercise.
3. **C12 control_copies (schema v1.1, optional).** A pristine control copy must carry
   a sha256 pin, be `verified_before_use=true`, and name a `recreation_procedure` if
   any execution is allowed inside it after verification. Born from R47: a control
   copy was contaminated by its own pytest run, making the strict verification it
   existed to support unreproducible in place.
4. **C13 requirements[].coverage (schema v1.1, optional).** Review-type requirements
   enumerate coverage items with the artifact that will demonstrate each; a coverage
   item without a demonstrable artifact is declared accept-as-open at plan time.
   Born from R47-F8: claimed review coverage was not demonstrable at closeout.
5. **SKILL.md / domain-checks.md deltas** (core-first gate still green): the three
   hygiene rules above, an **emit-text prescan** pre-check (scan planned packet text
   with the ecosystem's emit-time linters at plan time - R46/R47 each paid two failed
   emit attempts to vocabulary collisions), and **time-scoped mutable-state claims**
   (as-of timestamps + pre-dispatch re-check - R44-F3/R46-F1 class).

## Post-1X006 remediation deltas (this revision, 2026-09-19)

Applied in response to the 1X review `AI_MAESTRO_2G_PACKET_ASTRA_PREP_REVIEW_20260919_1X`
(findings F-01..F-05, F-06, F-07; reproduced attacks REPRO-01..07). Full per-finding
dispositions: `R54_VALIDATOR_REPAIR_REPORT.md` in the remediation run folder
(`D:/Shared/0.Test_Room/0.AI_Maestro_client/20260919-2G-ASTRAPREP-R54-1X006-REMEDIATION/run1/`).

1. **C14 forecast semantics (F-01 / REPRO-01/02).** The forecast disposition
   vocabulary is a closed set (schema enum; unknown values rejected).
   `CANDIDATE_READY` is exclusive and forbidden when any requirement is
   `reachable=false`, carries an open (accept-as-open) capability decision, or when
   `drift_at_start=true`. **Drift policy is explicit:** reconciled start drift REMAINS
   a disclosed disposition -- `drift_at_start=true` requires a concrete reconciliation
   AND a non-empty `forecast.dispositions` containing `PROVENANCE_DRIFT_AT_START`.
   An accept-as-open row must name its honest end cell (`E[1-5]/R[0-2]`) in
   `accept_as_open_end_state` (C4).
2. **C10 full schema-keyword conformance (F-02 / REPRO-04/05).** C10 now enforces the
   schema's declared keyword subset: leaf types (incl. union types), `minLength`,
   `minItems`, `pattern` (all patterns fully anchored `^...\\Z`, so trailing newlines
   are rejected), `const`, `oneOf`, and `if`/`then`. Any schema keyword outside the
   enforced subset fails closed. Validator-side hash/ID regexes use `fullmatch`
   (`\Z`, not `$`). Pointer hashes are validated through a oneOf (64-hex or
   `NONE_RESOLVED`).
3. **One deterministic YAML parser contract (F-03 / REPRO-06).** PyYAML, when
   importable, is the single YAML authority, wrapped in a strict contract: duplicate
   mapping keys rejected, implicit timestamps kept as strings, YAML 1.1 booleans
   as-is. Without PyYAML the bundled block-style-subset parser applies the same
   contract for its accepted corpus (PyYAML's exact boolean set incl. yes/no/on/off,
   same null set, duplicate-key rejection in block and flow mappings). JSON duplicate
   keys are rejected too. Parser name+version and the Python version are printed with
   every validation run. The negative corpus runs in BOTH modes (tests).
4. **C6 review-independence evidence (F-04 / REPRO-03).** An R2 target now requires
   more than the self-attested `author_reviewer_distinct` boolean: a real
   `reviewer_id`, non-placeholder `route_id` and `bundle_path`, a `receipt` pointer
   whose sha256 is the hash of the receipt artifact, and a bound `result_ref`
   (placeholders TBD/NOT_RUN/NONE_RESOLVED/... are rejected). **Same-lineage review
   is R1 by default** -- documented in `references/evidence-model.md` and
   `profiles/ai-maestro.md`. Profile family table corrected: **1X runs the Codex
   bootstrap on PC1** and resolves the Codex Live row (an earlier revision wrongly
   listed 1X under Claude Live).
5. **C15 starting-point readback (F-05 / REPRO-07).** New REQUIRED sidecar section
   `starting_point_readback`: `candidate_path` + `candidate_sha256` (must equal
   `starting_candidate.sha256`; for doc candidates the path must also equal
   `starting_candidate.ref`), `points_at_candidate=true` (const), and a `git_state`
   block (kind=git with HEAD/branch/clean, or kind=non-git with an explicit
   declaration). The provenance pointers now bind to the actual candidate.
6. **F-07 module vocabulary.** `evidence-hygiene` added to the Module IDs list in
   `references/domain-checks.md`; a test asserts schema enum == domain-checks module
   IDs, and another asserts every disposition word is documented in SKILL.md.
7. **Bundle hygiene (F-06).** Test counts reconciled (35 collected pre-remediation,
   not 32; 50 after this remediation), `.pytest_cache/` and `__pycache__/` moved into
   `_quarantine/` (no deletions), and CANDIDATE_HASHES.json rebuilt as a FULL bundle
   manifest (every file, sha256) with an explicit exclusion rule and a bundle
   aggregate hash. The stale `README.md` file-table row in README_RELAY.md is
   annotated (that file is a GitHub-mirror artifact, absent from this bundle).

**Contract change notice:** the four valid fixtures (`valid_minimal.yaml`,
`valid_drift_rebound.yaml`, `valid_flow_style.yaml`, `valid_v71_full.json`) were
updated to the repaired contract (readback block added; the drifted-start fixture now
discloses `PROVENANCE_DRIFT_AT_START`; the R2 fixture carries reviewer identity,
receipt, and result reference). All eight pre-remediation invalid fixtures still fail
on their originally named checks.

## Validation status (all run 2026-09-19, Python 3.11.9, PyYAML 6.0.2, pytest 9.0.3)

- Candidate test suite: **50 passed** (35 collected pre-remediation: 27 v7-era
  parametrized/direct + 8 C10/C11-C13-era direct tests, unregressed; +15 new:
  test_repro01..test_repro07 attack regressions plus vocabulary-agreement and
  parser-contract tests). Command: scrubbed-env
  `python -B -m pytest tests/ -v -p no:cacheprovider`.
  Note: the exact form `python -S -B -m pytest` cannot import pytest in this
  environment (`-S` excludes site-packages, where pytest lives); `-S` IS used to run
  the validator itself in no-PyYAML fallback mode.
- Negative corpus (REPRO-01..07) all FAIL post-remediation, in BOTH parser modes
  where applicable (test_repro01..test_repro07 docstrings cite the 1X findings).
- Pinned v7 bundle re-hashed after the remediation: unchanged (see
  CANDIDATE_HASHES.json, section `pinned_v7_unchanged` / `pinned_v7_reverified`).

## Files

Same layout as v7 (SKILL.md core, one profile, references, schema, validator, tests +
fixtures) plus this README, `CANDIDATE_HASHES.json` (full manifest), and the attack
fixtures. Unchanged BY THIS REMEDIATION (hash-verified against the pre-remediation
candidate manifest): `SKILL.md` (note: the candidate SKILL.md is the v7.1 text and was
already different from the pinned v7 bytes before this pass),
`tests/test_validate_prework.py`, and the eight pre-remediation invalid fixtures.
Changed vs the pinned v7: `profiles/ai-maestro.md`, `references/evidence-model.md`,
`references/domain-checks.md`, `schemas/prework-plan.schema.json`,
`scripts/validate_prework.py`, the addenda in `README_RELAY.md` /
`ASTRA_PREP_USAGE.md`, and the fixtures. Cache artifacts live in `_quarantine/` and
are excluded from the manifest by the stated exclusion rule.
