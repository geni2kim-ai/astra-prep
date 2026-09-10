# astra-prep profile -- AI_Maestro / Synapse

This is **profile data** for the generic `astra-prep` core. It supplies concrete
bindings, review routes, and vocabulary for the AI_Maestro / Synapse cluster. Editing
this file does not change the skill's workflow or evidence model -- only the values each
node resolves. One edit here reaches every node through the relay-path bundle mirror.

Every node resolves its **own** state pointer, tree, test runner, and review route.
Copying another node's values is the failure mode.

## Binding resolution by lineage (verify against the live node; do not copy blindly)

| Family / nodes | state pointer | handoff | test runner | review route (first available) |
|---|---|---|---|---|
| Claude Live (1C, 1X, 3H, 1A) | `0.Workspace/Node/<N>/.state.json` or `NONE_RESOLVED` | latest `<n>_*handoff*` memory file | project runner (pytest / gradle / etc.) | `redagent` MID subagent -> `bridge_redagent` -> `NOT_RUN` |
| Codex Live (2X, 3X) | node's `.codex` / project state | node's Codex handoff | project runner | `chatgpt-redagent` (Codex Work Cloud) -> `NOT_RUN` |
| GLM Live (2G, 2A) | `0.Workspace/Node/<N>/` state | node's GLM handoff | project runner | `redagent` MID subagent -> `bridge_redagent` -> `NOT_RUN` |
| Ollama (2O) | usually `NONE_RESOLVED` | node handoff or `NONE_RESOLVED` | `N/A` unless a runner is wired | `bridge_redagent` -> `NOT_RUN` |
| Beta (4C, 4X, 4A, 4G) | `PC4_BETA_LOCAL_CANONICAL/runtime/state/` or `memory/<N>/active/*_BOOTSTRAP.md` | `temp/<N>_SESSION_HANDOFF_*` | `py -3 -m pytest tests/ -q` | same-lineage independent subagent -> `chatgpt_review_bridge` -> `NOT_RUN` (never `bridge_*`) |

These are search hints, not configuration. Confirm each value against the live node.

## Review-route contract (per selected route)

Record `route_id -> availability probe -> permitted adapter/command -> receipt/status
contract -> fallback`. Notes:

- **Live Claude/GLM:** `redagent` MID subagent is the same-lineage tier; `bridge_redagent`
  is the permitted cross-lineage adapter; `NOT_RUN` if neither probes available.
- **Codex Live:** Codex Work Cloud `chatgpt-redagent`; Work Cloud variants stay gated to
  the calling lineage.
- **Beta nodes must use `chatgpt_review_bridge`** and must not substitute a forbidden
  `bridge_*` skill.
- For an asynchronous external route, the transport observation must carry client
  correlation, actual reviewer id, server acknowledgement, exact-thread readback, bound
  final response, receipt, and status. A client-only correlation is `NOT_RUN`.

## Beta-node forecast is legitimately capped

A Beta node runs under `live_effect=DENIED` with no device and no real external provider.
Evidence levels `E3`-`E5` for anything Live-facing are structurally unreachable from
Beta; `E1`-`E2` plus any `R` tier are its working range. Every Beta forecast that touches
Live behaviour legitimately carries `CAPABILITY_GAP` / `RUNTIME_NOT_RUN` for the upper
levels; record it as `accept-as-open` with the reason, not as a blocker or a skill
failure. The Beta value of this skill is catching provenance drift, missing edge-case
rows, and the review-route gap before work starts -- not reaching runtime levels it was
never allowed.

## Non-final vocabulary rule (Synapse finality-lint)

The skill's disposition words (`CANDIDATE_READY`, `RUNTIME_NOT_RUN`, `PROVENANCE_DRIFT_AT_START`,
`INDEPENDENT_REVIEW_NOT_RUN`, `TRANSPORT_UNVERIFIED`, `CAPABILITY_GAP`,
`SCOPE_RENEGOTIATION_NEEDED`, `EVIDENCE_TREE_BLOAT_RISK`) are planning-local. Keep them
**out of packet bodies and handoff prose** -- the Synapse `emit()` finality-lint blocks
whole words such as `approved`, `complete`, `final`, `passed`, `verified`, `done`, and
several phrase patterns. Report disposition words to the caller as plan notes only.
`packet_preflight.py` does not run finality-lint; `emit()` does.

## Authoritative in-cluster pin

The relay-path bundle at
`0.AI_Maestro_Shared/Hub/skills/relay/astra_prep_20260910/` is the authoritative
in-cluster artifact, hash-pinned by GOV-SKILL-001. The GitHub repo
`github.com/geni2kim-ai/astra-prep` is a published mirror for external visibility only,
not the source of record. Every node resolves and hash-checks against the relay path.

## Node-parameterization stop rule

If any binding resolves to `UNKNOWN` (not the explicit sentinels `NONE_RESOLVED` /
`NO_WORKTREE` / `N/A`), record it and stop -- an unresolved starting candidate or state
pointer is the first finding. Under a monitored pilot, record the `UNKNOWN` and proceed
with the rest of the plan rather than stalling the tick, per the governing notice.
