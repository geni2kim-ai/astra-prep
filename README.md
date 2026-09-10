# astra-prep

> **Pre-Work Evidence & Verification Planning Gate**
> *Fix the starting point, plan every requirement's evidence on two independent axes, and disclose capability gaps at hour 0 — not at closeout.*

`astra-prep` is an ecosystem-agnostic pre-work planning skill for autonomous coding
agents and multi-agent systems. It enforces a planning discipline **before** touching
source, drafting documents, or compiling artifacts, so that provenance drift, missing
runtime evidence, and overlooked edge cases surface at *t=0* instead of at completion.

---

## Key concepts

### 1. Fix the starting point — `DRIFT → RECONCILE/ACCEPT → NEW BASELINE ID → REBIND → WORK`

Locks the authoritative state pointer, handoff, worktree/branch, and the **single**
starting candidate (commit SHA or document hash). If the handoff, state, and source tree
diverge, work is held: the drift is reconciled or the caller names a base, **one new
baseline id is minted**, the pointers are rebound to it, and only then does work start.
Carrying three divergent pointers past the rebind is itself a finding.

### 2. Two-axis evidence model

Every requirement is planned to a **cell** on two independent axes — never a single
"level".

| Evidence Level (what was done) | Review Independence (who vouches) |
| :--- | :--- |
| `E1` Static — source read / lint / diff | `R0` Self / author |
| `E2` Deterministic Test — unit / host, no live dep | `R1` Separate reviewer (shared context/stake) |
| `E3` Build — compile / package / assemble | `R2` Independent external (no stake, no prior context) |
| `E4` Runtime — real emulator / device / browser / service | |
| `E5` Field / Integration — real provider / peer / data | |

A target is written `E4/R2`, `E2/R0`, `E1/R1`, … The axes do not substitute for each
other: an author who ran a real integration test is `E5/R0` (not `E1`); an independent
reviewer who only read the source is `E1/R2` (not "level 6"). Full model and the legacy
1–6 back-map: [`references/evidence-model.md`](./references/evidence-model.md).

### 3. Selective domain pre-checks

Pre-populates requirements with domain edge cases — `date-time`, `realtime`, `ui`,
`handoff`, `packet-governance`, `db-migration`, `source-lineage`, plus evidence/artifact
hygiene. See [`references/domain-checks.md`](./references/domain-checks.md).

### 4. Capability gaps → upfront decisions

For any target cell the actor cannot reach: `acquire`, `rescope`, or `accept-as-open`
(which names the honest end cell, e.g. "target `E4/R2`, will end `E1/R0`").

### 5. Machine-readable contract + fail-closed validator

The plan has a YAML/JSON sidecar
([`schemas/prework-plan.schema.json`](./schemas/prework-plan.schema.json)) checked by
[`scripts/validate_prework.py`](./scripts/validate_prework.py) — stdlib only, no
third-party dependency. It **rejects** a plan that has more than one starting candidate,
a duplicate/malformed requirement id, a missing target cell, an unreachable requirement
with no capability decision, drift that was not rebound, an `R2` target with no proven
author/reviewer separation, or a shared artifact with no retention reason.

```bash
python scripts/validate_prework.py path/to/prework-plan.yaml
```

### 6. Ecosystem-agnostic core + profiles

`SKILL.md` names no concrete actor, path, route, or vocabulary — those live in a
**profile** ([`profiles/ai-maestro.md`](./profiles/ai-maestro.md) is the one shipped
here). Editing a profile does not change the workflow or the evidence model; the core is
edited once and every actor picks it up unchanged.

### 7. Symbiosis with a closeout audit

`astra-prep` authors the pre-work matrix at start; a closeout audit (`astra-shadow`)
fills the same rows with the `E/R` cell actually reached and flags any row that finished
lower than forecast on either axis.

---

## Repository layout

| Path | Purpose |
| :--- | :--- |
| [`SKILL.md`](./SKILL.md) | ecosystem-agnostic core — workflow, evidence model, output contract |
| [`profiles/ai-maestro.md`](./profiles/ai-maestro.md) | the one node-specific file — bindings, routes, capped-capability note, vocabulary rule |
| [`references/evidence-model.md`](./references/evidence-model.md) | `E1–E5 × R0–R2` definitions, worked cells, legacy 1–6 back-map |
| [`references/domain-checks.md`](./references/domain-checks.md) | selective domain pre-check modules + artifact hygiene |
| [`schemas/prework-plan.schema.json`](./schemas/prework-plan.schema.json) | JSON Schema for the plan sidecar |
| [`scripts/validate_prework.py`](./scripts/validate_prework.py) | fail-closed validator (Python stdlib only) |
| [`tests/`](./tests/) | validator tests + the core-first grep gate |
| [`ASTRA_PREP_USAGE.md`](./ASTRA_PREP_USAGE.md) | per-lineage usage guide, output template, worked examples |
| [`README_RELAY.md`](./README_RELAY.md) | relay staging provenance, revision history, promotion gate |

---

## Governance & standards

- **File encoding**: strict UTF-8 without BOM, LF line endings.
- **Ecosystem-agnostic core**: zero ecosystem-specific identifiers in `SKILL.md`
  (enforced by a grep gate in `tests/`).
- **Authority boundary**: planning-only. Does not grant finality or deploy code.

*Maintained by the AI Maestro Engineering Team.*
