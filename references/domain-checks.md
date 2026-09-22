# Domain pre-check modules

Load only the modules the request actually touches. Each adds requirement rows to the
step-2 matrix **now**, so the edge case is planned, not discovered late. These are shared
checklist sections, not a runtime plugin loader. If an ecosystem supplies an external
module, record its source, version, and hash.

Module IDs: `date-time`, `realtime`, `ui`, `handoff`, `packet-governance`,
`db-migration`, `source-lineage`, `evidence-hygiene`. The `evidence-hygiene` module
(evidence & artifact hygiene, below) applies to almost every unit. This list is the
authoritative module vocabulary and must stay identical to the `module` enum in
`schemas/prework-plan.schema.json` (the test suite asserts the agreement).

---

## `date-time` -- date / time input

Today-default; timezone; invalid + restored value; month/day and year rollover; minute
rounding; midnight and late-night boundary; whether a target can round to earlier than
`now` (e.g. 23:45 -> 00:00 with today's date, which a planner must then reject or roll
the date forward). Plan the future-target calculation as atomic at design time.

## `realtime` -- realtime / external data

Identifiers, region codes, timestamps come from authoritative data, not route text or
fabricated ids. Live / partial / stale / planned / unavailable / no-query states are
distinct. Request generations + cancellation stop stale publication. An active request
cannot be duplicated or silently replaced. Failure preserves the planned result and
offers a safe retry.

## `ui` -- UI change

First content begins at the intended system-bar boundary. Duplicate titles / helper
prose / empty cards removed without hiding errors or next actions. Related values share
a row/card when asked. Touch target, contrast, semantics, focus order, and
loading/disabled/empty/error/success states intact. Narrow and wide layouts both
considered -- not just the source's nominal dp values.

## `handoff` -- multi-agent / handoff

The final candidate will have one unambiguous commit/tree/test-profile/artifact set;
superseded candidates get labelled; the handoff/state is updated after the last
mutation, not before. One clean end-to-end verification run is the anchor -- a run whose
collector failed and was patched with a later XML-only scrape is not a clean run and is
not a test-count claim.

## `packet-governance` -- packet / index / governance doc

ASCII / no-BOM / title / sequence rules; the same-task index update if the governing
rule requires it; single write-site; finality-safe wording per your profile. A packet
entering the emit path carries no preview-only state, no "no packet emitted" /
draft-identity marker, and no body-vs-envelope contradiction -- historical-correction
wording lives under an explicit historical namespace only.

v7.1 adds two pre-checks. **Emit-text prescan:** if the ecosystem provides
emit-time linters, the planned packet body is scanned with them at plan time and
known-vocabulary collisions are substituted before the first emit attempt - a failed
emit discovered by the linter at closeout is wasted work the plan already paid for.
**Time-scoped mutable-state claims:** any claim whose evidence is mutable state (a
queue sweep, a running counter, a service check) records its as-of timestamp at
capture time and is re-checked immediately before the review dispatch; an unmarked
snapshot of moving state is a reproducibility debt.

## `db-migration` -- DB / migration

Forward + rollback path; idempotency; row-count expectation before and after;
auth/lease/owner gate named.

## `source-lineage` -- building on a frozen baseline

When the work builds on a frozen baseline (a peer's frozen reference, a required-frozen
inventory), reconcile the current tree against it now -- match count, per-path drift,
missing paths. An undocumented drift from a frozen baseline is
`PROVENANCE_DRIFT_AT_START`. For multi-day reconstruction with likely candidate churn,
name the freeze point and state that HEAD and the branch set do not move until the
consolidating record is issued.

---

## `evidence-hygiene` -- evidence & artifact hygiene

Plan now where each artifact the work will produce is written and how large it gets.

- **Location:** host-local vs a shared/synced tree. Anything written into a shared
  governance/workspace tree is declared with a retention reason. A rotating or
  self-duplicating artifact (a log, a per-run report set) written into a shared tree is
  a finding at hour 0, not at closeout.
- **One authoritative run kept:** name which verification run is the anchor; superseded
  runs are pruned or moved out of the shared tree, not left to accumulate.
- **No build output in the shared tree** without a stated reason: binaries, bundles,
  source tars, and any repo-metadata directory left inside an evidence folder.
- **Draft discipline:** one working version of a consolidating doc or matrix, superseded
  in place -- not N disagreeing draft files.
- **Immutable evidence outputs (v7.1):** a script or probe that writes its own
  evidence artifact writes to a path that is never overwritten within the unit -- a
  timestamped filename, a copy-before-rerun, or an append-only log. An in-place
  output path is a finding at hour 0: the second run destroys the first run's
  evidence by construction, and regenerating "before" evidence after the fact is a
  restoration exercise, not a measurement.
- **Control-copy lifecycle (v7.1):** a pristine/baseline control copy is pinned at
  creation, verified before use, and not executed against after its verification --
  or it is recreated and re-verified. A copy whose byte-purity a later check depends
  on must never be the place where tests run; generated caches and run artifacts
  contaminate exactly the property the copy exists to prove.
- **Coverage accounting (v7.1):** review-type requirements enumerate coverage items
  -- each artifact or claim to be reviewed, and the artifact that will demonstrate
  the review reached it. A coverage item whose demonstration cannot be produced is
  declared accept-as-open at plan time; at closeout, planned coverage is compared
  against demonstrated coverage and a silently dropped item is a finding.

Forecast row: `EVIDENCE_TREE_BLOAT_RISK` if the plan cannot keep the shared footprint
bounded.
