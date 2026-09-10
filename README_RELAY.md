# astra-prep relay bundle — staged 2026-09-10

Staged by **1C** on direct USER instruction (2026-09-10): extract the work-improving
parts of the Codex-only `astra-shadow` skill, re-orient them to **pre-work** use, and
make them usable as an **all-node common skill**.

## What this is, and what it is not

- A **relay**, under `Hub/skills/relay/`, deliberately **not** `Hub/skills/approved/`.
  Cluster-wide standing is a USER-gated decision after 1C disposition. Nothing here has
  that standing yet.
- `SKILL.md` is a **candidate**. It has not had an independent cross-lineage review.
  Per the same flow as the `Maestro_claude` relay and `project_agent_commons_channel`:
  implement -> independent review (a different lineage: 1X for Claude side, 2G for GLM)
  -> 1C disposition -> USER gate -> `approved/`.

## Provenance

| Source | Detail |
|---|---|
| origin skill | `C:/Users/user/.codex/skills/astra-shadow/SKILL.md` (Codex-only, closeout audit) |
| 1C review of origin | `D:/Shared/0.Workspace/Node/1C/ASTRA_SHADOW_SKILL_REVIEW_FOR_COMMON_ADOPTION_1C_20260910.md` |
| pre-work simulation | `D:/Shared/0.Workspace/Node/1C/ASTRA_PREP_PREWORK_SIMULATION_1C_20260910.md` |
| usage guide | `./ASTRA_PREP_USAGE.md` |
| meeting-room session #5 minutes | `D:/Shared/0.AI_Maestro_Shared/src/dispatch_app/meeting_room/minutes/MEETING_20260910_sess5.md` |
| tunnel notice to Beta | `D:/Shared/0.AI_Maestro_tunnel/1C_TO_4C_4X_SESSION5_BETA_TO_LIVE_ALIGNMENT_20260910.md` |
| current SKILL.md sha256 | `9e5d15eddb668b5f2c99a3a6df4843c35bba0a16c2aac33d02d21257e3ba2dfb` (v7) |

If your computed digest does not match, do not use the file — report the mismatch.

**v7 is a directory bundle, not a single file.** The core `SKILL.md` is
ecosystem-agnostic; all AI_Maestro / Synapse bindings, routes, capped-capability notes,
and the finality-vocabulary rule now live in `profiles/ai-maestro.md`. `references/`,
`schemas/`, and `scripts/` carry the evidence model, the sidecar schema, and the
fail-closed validator. Hash-check every file in the bundle, not only `SKILL.md`.

### Exception context (why this skill did not go Beta-first)

The origin method (Astra / GPT6 working practice, captured as `astra-shadow`) was tested
only in the 1X environment. The normal Beta-first route (apply in Beta, then migrate to
Live) was not available for it, so the USER directed 1X to author it as an exception.
This means: 1X-only origin testing proves the tested 1X scope and its stated cases; it
does **not** prove Beta or every-lineage validation. The compensating post-creation
checks are the 4X read-only review, the 4G relay test, and each lineage's own loader
check (see "Before approved/ promotion" below).

### Revision history

| rev | actor / lineage | change summary | artifact / ref | SHA-256 (SKILL.md) | binding evidence |
|---|---|---|---|---|---|
| v1 | 1C / Claude | initial relay staging: extract + re-orient astra-shadow to pre-work, node-agnostic | this bundle, staged 2026-09-10 | `93d28808874b5480914f5606a01d14aac1a1e64e1fb4e1714a68eaa52948561d` | 1C review doc + simulation doc (above) |
| v2 | 1C / Claude | independent-review route split: Live=`bridge_redagent`, Beta=`chatgpt_review_bridge` (`bridge_*` forbidden by Beta policy) | 1C edit, 2026-09-10 | `24f905a55542ac6d3b3331265ffe7eae583acbdb911ddefeda91f42c6b9644a2` | this README (v2 line) |
| v3 | 1X / Claude | **1X-reported, change summary + immutable ref pending** | pending | `?` (v3 artifact not independently preserved -- transition v2->v4 cannot be reconstructed from hashes alone; recorded as a gap, not inferred) | pending 1X evidence |
| v4 | 1X / Claude | **1X-reported**: lineage binding hardening, route/transport contract fields, shadow-mapping section, UTF-8/no-BOM/LF loader contract, added dispositions (`TRANSPORT_UNVERIFIED`, `CAPABILITY_GAP`, `SCOPE_RENEGOTIATION_NEEDED`), stable `requirement_id`/module IDs | 1X edit, 2026-09-10 ~09:33 | `57ce1aed57b042c606195ed5a987d60c41bf641cee16134b63aaffd1bb5abaca` | pending 1X author-bound ref (readback of current bytes confirmed by 1C/4X/1X in session #5, ~post 156-161; authorship of the v2->v4 changes not yet independently bound) |
| v5 | 1C / Claude | review supplement: per-lineage binding starting-point table (incl. Beta), "Beta-node forecast is legitimately capped" note; usage guide authored separately | 1C edit, 2026-09-10 (post session #5) | `e89e714f22df54c0ad49ef0186bc6028809822666cb604d829c3a305fc34a82c` | this README (v5 line) + `ASTRA_PREP_USAGE.md` |
| v6 | 1C / Claude | evidence-integrity upgrade grounded in the 1X 2026-09-09 ArriveBy case (~20 findings): new step 3b "Evidence and artifact hygiene"; new `source-lineage` module + frozen-baseline reconciliation; `packet-governance` emit-provenance row (aligns with the 260910-1X308 guard spec); step 5 level-6 independence bar ("a review by anyone who touched the source is not independent"); handoff "one clean end-to-end run" rule; `EVIDENCE_TREE_BLOAT_RISK` disposition | 1C edit, 2026-09-10 (hourly tick) | `7b637653d78714f4643ab1304f136a67b91066a7cae959cc1b4aee9b20c2d949` | this README (v6 line) + `ASTRA_PREP_UPGRADE_ANALYSIS_FROM_1X_260909_1C_20260910.md` |
| v7 | 1C / Claude | **structural overhaul on USER review**: (1) the 1-6 ladder split into two independent axes -- Evidence Level `E1-E5` and Review Independence `R0-R2`, target written as a cell `E4/R2`; legacy back-map kept in `references/evidence-model.md`. (2) core `SKILL.md` made ecosystem-agnostic -- every node/route/path/vocabulary binding moved to `profiles/ai-maestro.md`; the only ecosystem token left in core is the profile pointer itself; grep gate in `tests/` (scrub-then-fail). (3) machine-readable sidecar `schemas/prework-plan.schema.json` + fail-closed `scripts/validate_prework.py` (checks C1-C9, stdlib only). (4) provenance flow hardened to `DRIFT -> RECONCILE/ACCEPT -> NEW BASELINE ID -> REBIND -> WORK`; validator C5 rejects unrebound drift. Closeout counterpart `astra-shadow` updated in the same pass. | 1C edit, 2026-09-10 | `9e5d15eddb668b5f2c99a3a6df4843c35bba0a16c2aac33d02d21257e3ba2dfb` | this README (v7 line) + plan `merry-kindling-galaxy.md` + USER review transcript 2026-09-10 |

**v3/v4 authorship stays `1X-reported / unverified`** until 1X supplies per-revision
change summaries and an author-bound immutable reference (review/receipt/commit). A
content hash proves current bytes, not who authored them. If the v3 artifact stays
unavailable, keep the v2->v4 transition labelled `source-reported`, do not infer it.

## What changed from astra-shadow (extraction + re-orientation)

Kept (the work-improving parts):
- evidence-layer separation -> provenance-drift detection
- requirement -> evidence -> verification-level -> result -> residual matrix
- the ran-versus-read distinction as **targets**, not post-hoc labels (v7: split into
  the `E1-E5` evidence axis and the `R0-R2` independence axis)
- reusable domain checklists (date/time, realtime data, UI states, multi-agent handoff)
- transport-as-separate-gate discipline for independent review
- candidate-only / non-authority framing; preserve superseded evidence

Dropped or changed (the blockers to common use, per the 1C review):
- **Codex-only packaging** -> lineage-neutral frontmatter with rich description + Korean
  triggers; a node-parameterization step so each lineage resolves its own bindings.
- **hard `$chatgpt-redagent` dependency** -> tiered route: same-lineage `redagent` MID
  -> policy-permitted route adapter (`bridge_redagent` or Beta's
  `chatgpt_review_bridge`) -> explicit `NOT_RUN`; each route now records its probe,
  command, receipt/status contract, and fallback. Codex-only Work Cloud variants stay
  gated to the calling lineage.
- **ArriveBy/Android-specific body** -> domain-agnostic core + pluggable modules
  (added: packet/index/governance, DB/migration).
- **closeout orientation** -> pre-work orientation. The matrix it produces is handed to
  `astra-shadow` at closeout, pre-filled.
- **finality-lint collisions** -> explicit rule: planning vocabulary stays out of packet
  bodies and handoff prose.

## Read the bindings table as a template, never as configuration

The node-parameterization table in `SKILL.md` shows the shape. Every node resolves its
own state pointer, canonical tree, worktree-or-not, test runner, and review route.
Copying another node's values is the failure mode.

## Relay-test in progress

2G (the natural GLM-lineage tester) is blocked, so the apply-test is routed to **4G**
(same GLM lineage, Beta node). Prompt: `D:/Shared/0.Workspace/Node/1C/PROMPT_TO_4G_ASTRA_PREP_RELAY_TEST_20260910.md`.
4G runs `astra-prep` at the start of its next bounded work unit, keeps the pre-work plan,
compares the forecast to the actual disposition at closeout, and reports GLM/Beta-node
friction to `temp/PC4_BETA_4G_ASTRA_PREP_RELAY_TEST_20260910_R1.md`.

## Before `approved/` promotion (session #5 CLOSEOUT constraints)

The relay stays a **hash-matched read-only candidate**. Do not infer "all-node applied",
"approved", "Live-compatible", or "deployment-ready" from it. "1X tested it, therefore
all nodes can use it" is a verification-level overreach.

Gate list for `Hub/skills/approved/`:

0. **core-first** — `SKILL.md` carries no ecosystem-specific bindings: no node ids, route
   names, host names, cluster paths, or `finality-lint`-style vocabulary. The single
   allowed ecosystem-flavoured token is the pointer to the shipped example profile
   (`profiles/ai-maestro.md`); the `tests/` grep gate enforces this (scrubbing that one
   token, then failing on any other). A reviewer with no AI_Maestro context can produce a
   valid pre-work plan from `SKILL.md` + `schemas/prework-plan.schema.json` alone. New
   shared skills are authored core-first / profile-second; this gate applies to every one.
1. **1X** — v3/v4 per-revision change summaries + author-bound immutable ref + v3->v4 diff + hashes (v3 gap explicit if the artifact is unavailable). **v7 re-review**: the 2D model, the core/profile split, and the validator are a structural change and need a fresh cross-lineage pass.
2. **4G** — relay test complete → `temp/PC4_BETA_4G_ASTRA_PREP_RELAY_TEST_20260910_R1.md`.
3. **4X** — Codex loader/bindings check + one bounded Beta-local use.
4. **1C** — fold 1X's evidence into the Revision history block → re-read the whole README as UTF-8 → keep the old hash historical → publish the new bytes/hash as a new candidate revision.
5. **each lineage** — its own loader/UTF-8/hash check + `python scripts/validate_prework.py` runs on that runtime.
6. **1C disposition + USER / Live-owner acceptance.**

Then: `approved/astra_prep_20260910/` → Beta `skills/active_shared/astra_prep_20260910/`
(4C, via the existing 1:1 mirror pattern).

## Files in this bundle

| File | Purpose |
|---|---|
| `SKILL.md` | the ecosystem-agnostic core (v7) — workflow, 2D evidence model, output contract |
| `profiles/ai-maestro.md` | the only node-specific file — lineage bindings, review routes, Beta cap note, non-final vocabulary rule |
| `references/evidence-model.md` | `E1–E5 × R0–R2` definitions, worked cells, legacy 1–6 back-map, closeout linkage |
| `references/domain-checks.md` | selective domain pre-check modules + evidence/artifact hygiene |
| `schemas/prework-plan.schema.json` | JSON Schema for the plan sidecar |
| `scripts/validate_prework.py` | fail-closed validator (Python stdlib only; checks C1–C9) |
| `tests/` | validator unit tests + fixtures + the core-first grep gate |
| `ASTRA_PREP_USAGE.md` | usage guide — per-lineage invocation, output template, worked examples, promotion gate |
| `README.md` | GitHub landing page (mirror only) |
| `README_RELAY.md` | this file — provenance, revision history, relay/promotion status |
