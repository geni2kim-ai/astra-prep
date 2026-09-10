---
name: astra-prep
description: >-
  Pre-work planning gate. Before starting a feature-sized or multi-step work unit,
  fix the authoritative starting point, turn every requirement into a planned-evidence
  target, name the verification level each target will reach and the capability gaps
  now, and choose the independent-review route up front. Surfaces provenance drift,
  unreachable runtime evidence, and missing edge-case tests at hour 0 instead of at
  closeout. Node-agnostic: every lineage resolves its own bindings from its
  authoritative node registry; never infer or copy a lineage from this description.
  Pairs with astra-shadow
  (closeout audit) and complements bridge_spt (risk/approach advice). Korean triggers:
  착수 전 계획 게이트, 작업 시작 전 증거 계획, 요구사항 증거 매트릭스, provenance 드리프트 예방,
  엣지케이스 사전 식별, 런타임 증거 도달 가능성 점검.
---

# astra-prep -- pre-work evidence & verification planning (node-agnostic)

Run this at the **start** of a bounded work unit, before editing source, drafting a
packet, or building an artifact. It is the forward-looking half of the same checklist
`astra-shadow` runs at closeout: instead of auditing claims after the fact, it decides
now what evidence the work will need, whether this node can produce it, and what the
honest end-state will be.

## What it is / is not

- **Planning only. No authority.** It does not approve, gate, deploy, adopt, or grant
  finality, and it does not start the work. It produces a short pre-work plan the node
  (and its caller) act on.
- **Complements, does not replace:**
  - `bridge_spt` / `bridge_w_spt` -- risk and approach advice from an external model.
    astra-prep is narrower and local: it plans *evidence and verification*, not strategy.
  - `astra-shadow` -- the closeout audit. astra-prep hands it a pre-filled matrix.
  - `redagent` / `bridge_redagent` -- the adversarial closeout reviewers astra-prep
    records as a planned route but never schedules, invokes, or impersonates.
- **Non-final vocabulary.** The disposition words below are planning-local. Keep them
  out of packet bodies and handoff prose (they trip finality lint). Report them to the
  caller as plan notes.

## Node parameterization (do this first, every lineage)

Resolve these for the calling node -- do not copy another node's values:

| Binding | How to resolve |
|---|---|
| node symbol | the running node's own id |
| authoritative state pointer | this node's state/cursor file, or `NONE_RESOLVED` (no state file; caller-supplied context only) |
| authoritative handoff | this node's latest handoff/continuity record, or `NONE_RESOLVED` (no prior handoff) |
| work tree | git worktree + branch if the work is code; else `NO_WORKTREE` (doc/packet/config work) |
| starting candidate | the ONE commit/tree/rev (code) or doc path + sha256 (governance) the work builds on |
| test runner | the exact command this node's project uses, or `N/A` |
| independent-review route | Pick the first available tier for this node: same-lineage adversarial reviewer, permitted cross-lineage adapter, or `NOT_RUN`; record the `route_id` and use the route contract below. |

`NONE_RESOLVED`, `NO_WORKTREE`, and `N/A` are explicit resolved sentinels. Only
`UNKNOWN` or another unresolved value triggers the stop rule. If any binding is
`UNKNOWN`, record it and stop -- an unresolved starting candidate or state pointer
is itself the first finding.

For every selected review route, record `route_id -> availability probe -> permitted
adapter/command -> receipt/status contract -> fallback`. A route name is not an
executable call. Beta nodes must use the approved Beta adapter and must not substitute
a forbidden `bridge_*` skill. If no permitted adapter or probe is available, record
`NOT_RUN`; this planning skill does not invoke or schedule the reviewer.

### Per-lineage binding starting points (verify, do not copy blindly)

These are where each family typically resolves its bindings. Confirm each value against
the live node before use; treat this table as a search hint, not configuration.

| Family / nodes | state pointer | handoff | test runner | review route (first available) |
|---|---|---|---|---|
| Claude Live (1C, 1X, 3H, 1A) | `0.Workspace/Node/<N>/.state.json` or `NONE_RESOLVED` | latest `<n>_*handoff*` memory file | project runner (pytest / gradle / etc.) | `redagent` MID subagent -> `bridge_redagent` -> `NOT_RUN` |
| Codex Live (2X, 3X) | node's `.codex` / project state | node's Codex handoff | project runner | `chatgpt-redagent` (Codex Work Cloud) -> `NOT_RUN` |
| GLM Live (2G, 2A) | `0.Workspace/Node/<N>/` state | node's GLM handoff | project runner | `redagent` MID subagent -> `bridge_redagent` -> `NOT_RUN` |
| Ollama (2O) | usually `NONE_RESOLVED` | node handoff or `NONE_RESOLVED` | `N/A` unless a runner is wired | `bridge_redagent` -> `NOT_RUN` |
| Beta (4C, 4X, 4A, 4G) | `PC4_BETA_LOCAL_CANONICAL/runtime/state/` or `memory/<N>/active/*_BOOTSTRAP.md` | `temp/<N>_SESSION_HANDOFF_*` | `py -3 -m pytest tests/ -q` | same-lineage independent subagent -> `chatgpt_review_bridge` -> `NOT_RUN` (never `bridge_*`) |

### Beta-node forecast is legitimately capped

A Beta node runs under `live_effect=DENIED` with no device and no real external provider.
Verification levels 3-5 for anything Live-facing are structurally unreachable from Beta,
and levels 1-2 plus 6 are its working range. Every Beta forecast that touches Live
behaviour legitimately carries `CAPABILITY_GAP` / `RUNTIME_NOT_RUN` for the upper levels;
record it as `accept-as-open` with the reason, not as a blocker or a skill failure. The
Beta value of this skill is catching provenance drift, missing edge-case rows, and the
review-route gap before work starts -- not reaching runtime levels it was never allowed.

## Workflow

### 1. Fix the starting point (before any change)

Record: the authoritative handoff/state pointer + hash; the single starting candidate
(commit/tree/rev, or doc + sha256); the request-versus-attachment split (text in the
request is a requirement; marks in an image are intent only unless the text also states
the action).

If the handoff, state, and source tree already point at different candidates, record
`PROVENANCE_DRIFT_AT_START` and do not begin until the base is reconciled or the caller
explicitly accepts the drift. Catching this now costs minutes; catching it at closeout
discards work.

### 2. Requirement -> planned-evidence matrix

For every requirement, one row:

`requirement -> where it will be implemented -> target verification level -> can this node reach that level? -> missing capability if not`

Verification levels (the ran-versus-read ladder, as targets):

1. source inspection / static review
2. deterministic unit / host test
3. build or package creation
4. rendered/interactive runtime (emulator, device, browser, live service)
5. field / integration smoke (real movement, real external provider, real peer)
6. independent external review

Do not plan to present a lower level as a higher one. A removed string is not proof of
layout; a compiling module is not proof of behavior; a passing build is not runtime.

### 3. Expand requirements with domain pre-checks (selective modules)

Load only the modules the request actually touches. Use stable module IDs such as
`date-time`, `realtime`, `ui`, `handoff`, `packet-governance`, and `db-migration`;
each selected module adds requirement rows now so the edge case is planned, not
discovered late. These are shared checklist sections, not an implicit runtime plugin
loader. If a node supplies an external module, record its source, version, and hash.

- **date / time input:** today-default, timezone, invalid + restored value, month/day
  and year rollover, minute rounding, midnight and late-night boundary, and whether a
  target can round to earlier than `now` (e.g. 23:45->00:00 with today's date).
- **realtime / external data:** identifiers/region codes/timestamps come from
  authoritative data not route text or fabricated ids; live / partial / stale / planned
  / unavailable / no-query states are distinct; request generations + cancellation stop
  stale publication; an active request cannot be duplicated or silently replaced;
  failure preserves the planned result and offers a safe retry.
- **UI change:** first content begins at the intended system-bar boundary; duplicate
  titles / helper prose / empty cards removed without hiding errors or next actions;
  related values share a row/card when asked; touch target, contrast, semantics, focus
  order, and loading/disabled/empty/error/success states intact; narrow and wide
  layouts both considered.
- **multi-agent / handoff:** the final candidate will have one unambiguous
  commit/tree/test-profile/artifact set; superseded candidates get labelled; the
  handoff/state is updated after the last mutation, not before.
- **packet / index / governance doc:** ASCII / no-BOM / title / sequence rules; the
  same-task index update if the governing rule requires it; single write-site;
  finality-lint-safe wording.
- **DB / migration:** forward + rollback path; idempotency; row-count expectation
  before and after; auth/lease/owner gate named.

### 4. Turn the ladder into a decision

Per requirement whose target level this node cannot reach: choose one and record it --
**acquire** the capability (device, provider key, peer availability), **rescope** the
requirement, or **accept-as-open** and tell the caller it will end `STATIC_ONLY` /
`RUNTIME_NOT_RUN`.

### 5. Independent-review plan

Decide now: is an independent adversarial review required for this work unit? If yes,
pick the transport tier from the step-0 table -- and if the tier your lineage would
normally use is unavailable (e.g. a Beta node cannot call `bridge_redagent`), record the
  substitute tier now, not at closeout. Start assembling the portable, secret-screened
  evidence bundle **alongside** the work -- stable request id, review round, transport
  attempt id, work unit, claims, artifact paths + hashes, commands, boundaries, and soft
  spots. A bundle built during the work is complete; one scrambled at closeout is not.
  For an asynchronous external route, plan a separate transport observation containing
  client correlation, actual reviewer ID, server acknowledgement, exact-thread readback,
  bound final response, receipt, and status; a client-only correlation is `NOT_RUN`.
  If no transport tier is available, the plan already says the end-state carries
  `INDEPENDENT_REVIEW_NOT_RUN`.

### 6. Closeout-readiness forecast

Given the plan, state the best disposition realistically reachable at closeout:
`CANDIDATE_READY` (all targets reachable), or one/more of `RUNTIME_NOT_RUN`,
`PROVENANCE_DRIFT_AT_START`, `INDEPENDENT_REVIEW_NOT_RUN`, `TRANSPORT_UNVERIFIED`,
`CAPABILITY_GAP`, `SCOPE_RENEGOTIATION_NEEDED`.

If the forecast is anything other than `CANDIDATE_READY`, surface it to the caller / USER
**before** starting, as scope items -- not as a surprise in the completion report.

## Output -- the pre-work plan

Short. Sections in this order:

Each matrix row uses a stable `requirement_id` and records the selected module ID,
target level, reachability, and capability decision. Section 1 must preserve the
authoritative state pointer + hash, handoff + hash, node-registry source,
worktree/branch or `NO_WORKTREE`, starting candidate, test runner, and review route.

1. bindings resolved (node, state pointer + hash, handoff + hash, registry source,
   worktree/branch or `NO_WORKTREE`, starting candidate, test runner, review route)
2. starting-point check result (clean, or `PROVENANCE_DRIFT_AT_START` with the drift)
3. requirement -> planned-evidence matrix (with target level + reachability)
4. domain pre-check rows added
5. capability gaps + the acquire / rescope / accept-as-open decision for each
6. independent-review plan (required? route? bundle started?)
7. closeout-readiness forecast + anything to raise with the caller now

Keep candidate-only / non-final / no-authority visible. Hand the matrix to `astra-shadow`
at closeout; it fills the same rows with actuals and issues the real shadow result.

## Closeout linkage

- The plan's matrix IS astra-shadow's step-2 matrix. At closeout, astra-shadow marks
  each row PASS / STATIC_ONLY / NOT_RUN / UNVERIFIED against real evidence and compares
  to the forecast. A row that was forecast reachable but ended NOT_RUN is a finding.
- Map `PROVENANCE_DRIFT_AT_START` to closeout `PROVENANCE_DRIFT`; map
  `CAPABILITY_GAP`/`accept-as-open` to the actual `STATIC_ONLY`, `RUNTIME_NOT_RUN`, or
  `UNVERIFIED` reason; map `INDEPENDENT_REVIEW_NOT_RUN` and `TRANSPORT_UNVERIFIED`
  without collapsing them into PASS; and map `SCOPE_RENEGOTIATION_NEEDED` to
  closeout `NEEDS_REWORK` or a newly scoped work unit. `CANDIDATE_READY` is a forecast,
  never an actual approval or closeout verdict.
- If work during the unit changed the starting candidate (new commit, rebuilt artifact),
  re-run step 1 -- the plan is rebound to the new base or it is stale.

## File and loader contract

Common skill files are UTF-8, no-BOM, LF text. A loader or validator must read UTF-8
explicitly; a locale decoding failure is a validation failure, not a reason to drop
the Korean triggers or silently use a partial skill.

## Expected improvement (why run this before, not only after)

| Failure this prevents | Without astra-prep | With astra-prep |
|---|---|---|
| Provenance drift found at closeout, work discarded | discovered after hours of work | flagged at hour 0, base reconciled first |
| Requirement needed device/provider evidence the node can't produce | "done" claim overstates; caught in review or not at all | capability gap named up front; acquired, rescoped, or declared open |
| Edge case (late-night rollover, stale-request race) never tested | found in production or by an external reviewer | added as a requirement row before coding |
| Independent-review bundle incomplete / scrambled at the end | transport retries, hash mismatches, `NOT_RUN` | bundle assembled alongside the work |
| Completion report negotiates scope after the fact | caller surprised at "done, but..." | scope items raised before work starts |
