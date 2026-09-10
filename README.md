# astra-prep

> **Pre-Work Evidence & Verification Planning Gate**  
> *Authoritative starting-point fixation, requirement-to-evidence matrix, and capability gap disclosure at hour 0.*

`astra-prep` is a node-agnostic pre-work planning skill designed for autonomous coding agents and multi-agent ecosystems. It enforces a strict planning discipline **before** touching source code, drafting packets, or compiling artifacts.

Instead of discovering provenance drift, missing runtime evidence, or overlooked edge cases at closeout, `astra-prep` surfaces these constraints at $t=0$.

---

## Key Concepts

1. **Fixing the Starting Point ($t=0$)**:
   - Explicitly locks the authoritative state pointer, handoff record, git worktree/branch, and the single starting candidate (commit SHA or document hash).
   - Detects PROVENANCE_DRIFT_AT_START before any change is made. If the handoff and source tree diverge, work is held until reconciled.

2. **Requirement-to-Evidence Matrix (6-Level Ran-vs-Read Ladder)**:
   Every requirement is mapped to a planned evidence target on the 6-level verification ladder:
   - **Level 1**: Source inspection / Static review
   - **Level 2**: Deterministic unit / host tests
   - **Level 3**: Build or package creation (e.g., APK assemble, binary compilation)
   - **Level 4**: Rendered interactive runtime (emulator, device, browser)
   - **Level 5**: Field / integration smoke (live APIs, external providers)
   - **Level 6**: Independent external review (adversarial audit gate)
   *Rule: A lower level is never claimed as a substitute for a higher level.*

3. **Selective Domain Pre-checks**:
   Pre-populates requirements with domain-specific edge cases:
   - date-time: Timezones, midnight/late-night boundary, rollover, rounding reversal.
   - 
ealtime: Idempotency, duplicate-request prevention, distinct states (live/stale/planned/
o-query).
   - ui: System bar boundaries, touch targets, contrast, loading/empty/error states, responsive widths.
   - handoff: Single immutable candidate set, updating handoff after the final mutation.
   - packet-governance: ASCII/no-BOM format, single write-site, finality-lint safety.
   - db-migration: Forward/rollback paths, idempotency, row-count expectations.

4. **Capability Gaps & Upfront Decisions**:
   For any target verification level the executing node cannot reach, it must explicitly decide:
   - `acquire`: Secure the necessary runtime/device/provider.
   - `rescope`: Adjust requirement scope with caller.
   - `accept-as-open`: Declare upfront that evidence will finish as STATIC_ONLY or RUNTIME_NOT_RUN.

5. **Symbiosis with `astra-shadow`**:
   - `astra-prep` authors the pre-work matrix at start.
   - `astra-shadow` audits the finished work at closeout against this exact matrix. Any item forecast as reachable that finishes NOT_RUN is flagged as an immediate finding.

---

## Repository Contents

| File | Purpose |
| :--- | :--- |
| [SKILL.md](./SKILL.md) | The core skill specification (frontmatter, node-parameterization, workflow, contracts) |
| [ASTRA_PREP_USAGE.md](./ASTRA_PREP_USAGE.md) | Comprehensive per-lineage usage guide, fixed output templates, and worked examples |
| [README_RELAY.md](./README_RELAY.md) | Relay staging provenance, revision history, and governance promotion gate criteria |
| [.gitignore](./.gitignore) | Clean repository filter preventing accidental leak of backups and temporary files |
| [.gitattributes](./.gitattributes) | Strict UTF-8 and LF line ending normalization rules |

---

## Quick Start & Pre-Work Plan Output Format

Before beginning a feature or multi-step work unit, produce the following concise plan:

`markdown
## Pre-work plan -- <work unit>

### 1. Bindings resolved
- node symbol:            <id>
- state pointer + hash:   <path> <sha256>  |  NONE_RESOLVED
- handoff + hash:         <path> <sha256>  |  NONE_RESOLVED
- node-registry source:   <path>
- work tree / branch:     <worktree> <branch>  |  NO_WORKTREE
- starting candidate:     <commit/tree/rev>  |  <doc path + sha256>
- test runner:            <exact command>  |  N/A
- review route:           <route_id> -> <probe> -> <permitted adapter/command> -> <receipt/status contract> -> <fallback>

### 2. Starting-point check
- clean  |  PROVENANCE_DRIFT_AT_START: <handoff X vs source Y vs state Z>

### 3. Requirement -> planned-evidence matrix
| req_id | requirement | Implementation Target | Module | Target Level (1-6) | Reachable? | Missing Capability |
|--------|-------------|-----------------------|--------|-------------------|------------|--------------------|

### 4. Domain pre-check rows added
- module <id>: <added requirement rows>

### 5. Capability gaps -- decision per gap
| req_id | gap | acquire / rescope / accept-as-open | Rationale |

### 6. Independent-review plan
- required? <yes/no>   route: <route_id>   bundle started? <yes/no, path>

### 7. Closeout-readiness forecast
- best reachable: CANDIDATE_READY  |  <RUNTIME_NOT_RUN / PROVENANCE_DRIFT_AT_START / CAPABILITY_GAP>
- raise with caller NOW: <items>
`

---

## Governance & Standards

- **File Encoding**: Strict UTF-8 without BOM, LF line endings.
- **Node-Agnostic Design**: Parameterized for diverse agent runtimes (Claude, Codex, GLM, etc.).
- **Authority Boundary**: Planning-only. Does not grant finality or deploy code autonomously.

---

*Maintained by the AI Maestro Engineering Team.*
