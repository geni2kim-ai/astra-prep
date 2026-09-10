# Domain pre-check modules

Load only the modules the request actually touches. Each adds requirement rows to the
step-2 matrix **now**, so the edge case is planned, not discovered late. These are shared
checklist sections, not a runtime plugin loader. If an ecosystem supplies an external
module, record its source, version, and hash.

Module IDs: `date-time`, `realtime`, `ui`, `handoff`, `packet-governance`,
`db-migration`, `source-lineage`. Plus **evidence & artifact hygiene**, which applies to
almost every unit.

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

## Evidence & artifact hygiene

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

Forecast row: `EVIDENCE_TREE_BLOAT_RISK` if the plan cannot keep the shared footprint
bounded.
