---
name: astra-prep
description: >-
  Pre-work planning gate. Before starting a feature-sized or multi-step work unit,
  fix the authoritative starting point, turn every requirement into a planned-evidence
  target on two independent axes (evidence strength E1-E5 and review independence
  R0-R2), name the capability gaps now, and choose the independent-review route up
  front. Surfaces provenance drift, unreachable runtime evidence, missing edge-case
  tests, evidence-tree bloat, and mislabelled self-review at hour 0 instead of at
  closeout. Ecosystem-agnostic: the core carries no lineage, node, path, or route
  names; each ecosystem supplies a profile. Pairs with a closeout audit (astra-shadow)
  and complements external risk/approach advice. Korean triggers: 착수 전 계획 게이트,
  작업 시작 전 증거 계획, 요구사항 증거 매트릭스, provenance 드리프트 예방, 엣지케이스 사전 식별,
  런타임 증거 도달 가능성 점검, 증거 강도와 검토 독립성 분리, 자체검토 오분류 방지.
---

# astra-prep -- pre-work evidence & verification planning

Run this at the **start** of a bounded work unit, before editing source, drafting a
document, or building an artifact. It is the forward-looking half of the same checklist
a closeout audit runs at the end: instead of auditing claims after the fact, it decides
now what evidence the work will need, whether this actor can produce it, and what the
honest end-state will be.

## What it is / is not

- **Planning only. No authority.** It does not approve, gate, deploy, adopt, or grant
  finality, and it does not start the work. It produces a short pre-work plan the actor
  (and its caller) act on.
- **Complements, does not replace:**
  - External risk / approach advice -- astra-prep is narrower and local: it plans
    *evidence and verification*, not strategy.
  - The closeout audit -- astra-prep hands it a pre-filled matrix.
  - Adversarial closeout reviewers -- astra-prep records one as a planned route but
    never schedules, invokes, or impersonates it.
- **Non-final vocabulary.** The disposition words below are planning-local. If your
  ecosystem lints packet or handoff text for finality claims, keep these words out of
  that text and report them to the caller as plan notes instead (see your profile).

## 0. Load your ecosystem profile (do this first)

The core skill names no concrete actor, path, route, test runner, or vocabulary. Those
are **profile data**, kept in a separate file so the core is edited once and every actor
picks it up unchanged. Resolve them from your ecosystem's profile before step 1:

- This bundle ships one profile, `profiles/ai-maestro.md`. Use it if that is your
  ecosystem.
- Any other ecosystem supplies its own profile file of the same shape. If none exists
  yet, you are the first user -- resolve each binding below directly from your
  environment and record the source so a profile can be written.

A profile supplies: how to find this actor's state pointer and handoff, the test-runner
command, the independent-review route tiers (probe / adapter / receipt contract /
fallback), any capped-capability note for restricted actors, and the local
non-final-vocabulary rule. A profile never changes the workflow or the evidence model.

## Bindings to resolve (from the profile, per actor)

| Binding | Resolved value is |
|---|---|
| actor id | the running actor's own identifier |
| authoritative state pointer | this actor's state/cursor file + hash, or `NONE_RESOLVED` (no state file; caller context only) |
| authoritative handoff | this actor's latest handoff/continuity record + hash, or `NONE_RESOLVED` |
| work tree | worktree + branch if the work is code; else `NO_WORKTREE` (doc/config work) |
| starting candidate | the ONE commit/tree/rev (code) or doc path + sha256 (doc) the work builds on |
| test runner | the exact command this project uses, or `N/A` |
| independent-review route | first available tier for this actor from the profile: `route_id -> availability probe -> permitted adapter/command -> receipt/status contract -> fallback`, or `NOT_RUN` |

`NONE_RESOLVED`, `NO_WORKTREE`, and `N/A` are explicit resolved sentinels. Only `UNKNOWN`
or another unresolved value triggers the stop rule: an unresolved starting candidate or
state pointer is itself the first finding -- record it and stop.

A route name is not an executable call. Record the full `probe -> adapter -> receipt
contract -> fallback` chain from the profile. If no permitted adapter or probe is
available, record `NOT_RUN`; this planning skill does not invoke or schedule the
reviewer.

## Workflow

### 1. Fix the starting point -- DRIFT -> RECONCILE/ACCEPT -> NEW BASELINE -> REBIND -> WORK

Record the authoritative handoff/state pointer + hash, the work tree + branch, and the
request-versus-attachment split (text in the request is a requirement; marks in an image
are intent only unless the text also states the action).

Then check the three pointers -- handoff, state, source tree -- against each other:

1. **DRIFT.** If they point at different candidates, record `PROVENANCE_DRIFT_AT_START`
   with all three pointers. Do not begin.
2. **RECONCILE or ACCEPT.** Either reconcile to the true base, or have the caller
   explicitly name which base to use. "Caller accepts the drift" is not enough on its
   own -- it must resolve to one named base.
3. **NEW BASELINE ID.** Mint exactly one identifier for that base: a commit/tree/rev, or
   a doc path + sha256. This is the single `starting_candidate` and `baseline_id`.
4. **REBIND.** Update the handoff/state/tree pointers to the new baseline, or record
   that the stale pointers are explicitly retired. Carrying three live divergent pointers
   past this step is itself a finding.
5. **WORK** may begin only now.

If the base moves during the unit (new commit, rebuilt artifact), re-run this step -- the
plan is rebound to the new base or it is stale.

### 2. Requirement -> planned-evidence matrix (two independent axes)

For every requirement, one row:

`requirement -> where it will be implemented -> target E / target R -> can this actor
reach that cell? -> missing capability if not`

**Evidence Level (E) -- what will be done to produce the evidence:**

| | |
|---|---|
| `E1` Static | source read / static analysis / lint / diff inspection |
| `E2` Deterministic Test | unit / host test; repeatable; no live dependency |
| `E3` Build | compiles / packages / assembles (binary, bundle, image, package) |
| `E4` Runtime | executed in a real runtime -- emulator, device, browser, live service process; behaviour observed |
| `E5` Field / Integration | real external provider, real peer, real movement/data; end-to-end smoke |

**Review Independence (R) -- who vouches for the evidence:**

| | |
|---|---|
| `R0` Self / author | produced or reviewed by whoever wrote or modified the thing under review |
| `R1` Separate reviewer | a different person/agent, but shared context or stake (same team, same task) |
| `R2` Independent external | no stake in the outcome, no prior context; did not author or modify the source |

The two axes are **independent**. A high `E` implies nothing about `R`: an author who
ran a real field-integration test is `E5/R0`, not `E1`. A high `R` does not raise a low
`E`: an independent reviewer who only read the source is `E1/R2`. A worker's review of
code it changed is `R0` at whatever `E` it reached.

Write each target as a cell, e.g. `E4/R2`, `E2/R0`, `E1/R1`. Do not plan to present a
lower cell as a higher one on either axis. A removed string is not proof of layout; a
compiling module is not proof of behaviour; a passing build is not runtime; a teammate's
read is not an independent review.

The legacy 1-6 ladder maps as `L1..L5 -> E1..E5`, `L6 -> any E with R2`. See
`references/evidence-model.md`.

### 3. Expand requirements with domain pre-checks (selective modules)

Load only the modules the request actually touches, from `references/domain-checks.md`:
`date-time`, `realtime`, `ui`, `handoff`, `packet-governance`, `db-migration`,
`source-lineage`, plus **evidence & artifact hygiene** (where each artifact is written,
one authoritative run, no build output or repo metadata in a shared tree, one draft of a
consolidating doc). Each selected module adds requirement rows now so the edge case is
planned, not discovered late. If an ecosystem supplies an external module, record its
source, version, and hash.

### 4. Turn each unreachable cell into a decision

Per requirement whose target cell this actor cannot reach: choose one and record it --
**acquire** the capability (device, provider key, independent reviewer availability),
**rescope** the requirement, or **accept-as-open** and tell the caller the honest end
cell (e.g. "target `E4/R2`, will end `E1/R0`").

### 5. Independent-review plan

Decide now: does this work unit need an `R2` review? A review by anyone who authored or
modified the source under review is `R0`, not `R2` -- `R2` requires no stake and no prior
context. If yes:

- Pick the route tier from the profile. If the tier your ecosystem normally uses is
  unavailable, record the substitute tier now, not at closeout.
- Start assembling the portable, secret-screened evidence bundle **alongside** the work:
  stable request id, review round, transport attempt id, work unit, claims, artifact
  paths + hashes, commands, boundaries, soft spots. A bundle built during the work is
  complete; one scrambled at closeout is not.
- For an asynchronous external route, plan a separate transport observation: client
  correlation, actual reviewer id, server acknowledgement, exact-thread readback, bound
  final response, receipt, status. A client-only correlation is `NOT_RUN`.
- If no route is available, the plan already says the end-state carries
  `INDEPENDENT_REVIEW_NOT_RUN`.

### 6. Closeout-readiness forecast

Given the plan, state the best cell realistically reachable at closeout, and any
dispositions that will remain: `CANDIDATE_READY` (all target cells reachable), or one or
more of `RUNTIME_NOT_RUN`, `PROVENANCE_DRIFT_AT_START`, `INDEPENDENT_REVIEW_NOT_RUN`,
`TRANSPORT_UNVERIFIED`, `CAPABILITY_GAP`, `SCOPE_RENEGOTIATION_NEEDED`,
`EVIDENCE_TREE_BLOAT_RISK`.

If the forecast is anything other than `CANDIDATE_READY`, surface it to the caller / user
**before** starting, as scope items -- not as a surprise in the completion report.

## Output -- the pre-work plan

Two artifacts:

1. **A short prose plan** with these sections in order:
   1. bindings resolved (actor, state pointer + hash, handoff + hash, profile source,
      worktree/branch or `NO_WORKTREE`, starting candidate, test runner, review route)
   2. starting-point check result (clean, or `PROVENANCE_DRIFT_AT_START` -> the
      reconcile/accept decision -> new `baseline_id` -> rebind confirmation)
   3. requirement -> planned-evidence matrix (each row: `req_id`, requirement,
      implementation, module, target `E/R`, reachable?, missing capability)
   4. domain pre-check rows added (incl. `source-lineage` reconciliation if a frozen
      baseline applies)
   5. evidence & artifact hygiene: where each artifact is written (host-local / shared),
      the one authoritative run, the shared-footprint budget
   6. capability gaps + the acquire / rescope / accept-as-open decision for each
   7. independent-review plan (required? `R2` per the bar above? route? bundle started?)
   8. closeout-readiness forecast + anything to raise with the caller now

2. **A machine-readable sidecar** (`prework-plan.yaml` or `.json`) conforming to
   `schemas/prework-plan.schema.json`, validated by `scripts/validate_prework.py`. The
   validator is fail-closed: it rejects a plan with more than one starting candidate, a
   duplicate or malformed `req_id`, a missing target cell, an unreachable requirement
   with no capability decision, drift that was not rebound to a new baseline, an `R2`
   target with no proven author/reviewer separation, or a shared artifact with no
   retention reason.

Keep candidate-only / non-final / no-authority visible. Hand the matrix to the closeout
audit; it fills the same rows with actuals and issues the real result.

## Closeout linkage

- The plan's matrix IS the closeout audit's matrix. At closeout it marks each row with
  the `E/R` cell actually reached and compares to the forecast. A row forecast reachable
  that ended lower on either axis is a finding.
- Map `PROVENANCE_DRIFT_AT_START` to closeout `PROVENANCE_DRIFT`; `CAPABILITY_GAP` /
  `accept-as-open` to the actual `STATIC_ONLY` / `RUNTIME_NOT_RUN` / `UNVERIFIED` reason;
  `INDEPENDENT_REVIEW_NOT_RUN` and `TRANSPORT_UNVERIFIED` without collapsing them into a
  pass; `SCOPE_RENEGOTIATION_NEEDED` to `NEEDS_REWORK` or a newly scoped unit;
  `EVIDENCE_TREE_BLOAT_RISK` to the closeout evidence-footprint check. `CANDIDATE_READY`
  is a forecast, never an actual approval or closeout verdict.
- If work during the unit changed the starting candidate, re-run step 1 -- the plan is
  rebound to the new base or it is stale.

## File and loader contract

Bundle files are UTF-8, no-BOM, LF text. A loader or validator must read UTF-8
explicitly; a locale decoding failure is a validation failure, not a reason to drop the
Korean triggers or silently use a partial skill.

## Expected improvement (why run this before, not only after)

| Failure this prevents | Without astra-prep | With astra-prep |
|---|---|---|
| Provenance drift found at closeout, work discarded | discovered after hours of work | flagged at hour 0, one new baseline minted and rebound first |
| Requirement needed device/provider evidence the actor can't produce | "done" claim overstates | capability gap named up front; acquired, rescoped, or declared open |
| Edge case (late-night rollover, stale-request race) never tested | found in production or by an external reviewer | added as a requirement row before coding |
| Author's own review filed as independent evidence | mislabelled; caught in adversarial review | `R0` vs `R2` separated on its own axis up front |
| Runtime evidence and independent review conflated on one scale | "level 6" hides that nothing ran | `E` and `R` scored separately; `E1/R2` and `E4/R0` are both visible and distinct |
| Independent-review bundle incomplete / scrambled at the end | transport retries, hash mismatches | bundle assembled alongside the work |
| Completion report negotiates scope after the fact | caller surprised at "done, but..." | scope items raised before work starts |
| Evidence tree grows unbounded in a shared folder | found in a cleanup weeks later | artifact locations + one-run rule + shared budget planned at hour 0 |
