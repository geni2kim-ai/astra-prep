# V7.1 header notice -- historical-v7 text marker (R62, per 260920-1C008)

Status: candidate-line remediation record, non-final, 2G-authored bundle metadata.

1C008 found that the two files below still open with stale v7-era header lines
(the v7 relay path, the v7 SKILL.md hash 9e5d15ed..., and the 2026-09-10 staging
date). They are marked here as HISTORICAL v7 TEXT rather than edited in place,
because both files are hash-cited in CANDIDATE_HASHES.json as part of the
reviewed 25-file payload whose aggregate
035662c4d64dc86e8f00924e01cd9f7f2949062b1f1db06605867d6f5a3c62bb is the reviewed
invariant; editing them would break the reviewed-aggregate proof. Editing them
in place remains available to 1C/USER if the pin decision prefers it (rollback:
re-copy the two files from the drafts candidate).

- ASTRA_PREP_USAGE.md  (sha256 f834fb5ea2ba5ee437cc16f774604c16e13fb43e28556a301e4a2de5891c6469) - HISTORICAL v7 text; header lines name the v7 path, the v7 SKILL.md hash, and the 2026-09-10 staging date.
- README_RELAY.md      (sha256 b4b3fea1c636bf351e126f5e43728022ea6f4d71491757574869a6551905fc07, updated 2026-09-22 -- see CANDIDATE_HASHES.json reconciliation_20260922_1C; the file also received an unrelated single-line GOV-MIG-001 path correction, `0.AI_Maestro_Shared` -> `0.AI_Maestro`, since this notice was first written) - HISTORICAL v7 text; same stale header lines.

The v7.1 authority for this directory is SKILL.md, sha256
c35b8929bc88f6cb76d695340c2ee03e660b6a78e09de42840683085bb63f29b
(the value 1C008 records 1C recomputed at this canonical path), with
scripts/validate_prework.py as the v7.1 validator and
CANDIDATE_HASHES.json (landed here 2026-09-20 per 1C008) as the manifest a
reader needs to recompute the aggregate independently. The pinned v7 at
astra_prep_20260910/ (SKILL.md 9e5d15ed...) remains the pinned reference until
the 1C notice lands.
