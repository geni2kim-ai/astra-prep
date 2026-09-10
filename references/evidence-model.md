# Evidence model -- two independent axes

astra-prep scores every planned-evidence target on **two axes that do not substitute for
each other**: how the evidence was produced (`E`), and who vouches for it (`R`).

## Why two axes

The old single 1-6 "ran-versus-read ladder" ended at `L6 Independent Review`. That put
independence on the same scale as runtime execution, which produces two wrong readings:

- An independent reviewer who only **read the source** scored `L6` -- higher than a
  device runtime test (`L4`) -- despite exercising nothing.
- An author who ran a **real field-integration test** could be pushed down to `L1`
  because "a self-run test is not independent" -- despite the code actually running end
  to end.

Independence and evidence-strength are orthogonal. Separating them makes both legible.

## Evidence Level (E)

| level | name | what it means | not this |
|---|---|---|---|
| `E1` | Static | source read, static analysis, lint, diff inspection | "the string is gone" is not proof of layout |
| `E2` | Deterministic Test | unit / host test; repeatable; no live dependency | a mocked provider is still `E2`, not `E5` |
| `E3` | Build | compiles / packages / assembles (binary, bundle, image, package) | a green build is not runtime behaviour |
| `E4` | Runtime | executed in a real runtime -- emulator, device, browser, live service process; behaviour observed | a screenshot with no interaction is weak `E4`; note it |
| `E5` | Field / Integration | real external provider, real peer, real movement/data; end-to-end smoke | one happy-path call is `E5` for that path only |

`E` is per **claim**, not per work unit. Different requirements in the same unit reach
different `E`.

## Review Independence (R)

| level | name | who | test |
|---|---|---|---|
| `R0` | Self / author | whoever wrote or modified the thing under review | did this actor touch the source? then `R0` |
| `R1` | Separate reviewer | a different person/agent with shared context or stake -- same team, same task, same lineage, was in the room | different identity, but not disinterested |
| `R2` | Independent external | no stake in the outcome, no prior context, did **not** author or modify the source | could this reviewer be surprised by the result? |

A "static review" by a participant is `E1/R0` or `E1/R1` -- never `R2`. Filing it as
independent evidence is the failure this axis prevents.

## Cells

Write a target as `E<n>/R<m>`. Examples:

| cell | reading |
|---|---|
| `E1/R0` | author read the source. Baseline. |
| `E2/R0` | author ran deterministic tests. |
| `E4/R0` | author ran it in a real runtime and watched it work. |
| `E1/R2` | independent reviewer read the source. Independent, but nothing ran. |
| `E4/R2` | ran in a real runtime **and** independently reviewed. Strong. |
| `E5/R1` | end-to-end smoke, reviewed by a teammate. Strong evidence, shared-stake review. |

Neither axis pulls the other. `E4/R0` and `E1/R2` are both incomplete, in different
ways, and the plan should say which.

## Planning rules

- Every requirement row has a **target cell**. "Best effort" is not a target.
- Do not plan to present a lower cell as a higher one on **either** axis.
- If the actor cannot reach the target cell, step 4 of the workflow forces a decision:
  acquire / rescope / accept-as-open. `accept-as-open` names the honest end cell, e.g.
  "target `E4/R2`, will end `E1/R0`".
- `R2` in any target requires the review route planned in step 5 and, in the sidecar,
  `review.author_reviewer_distinct = true`. The validator rejects an `R2` target without
  it.

## Legacy back-map (for un-migrated consumers)

A closeout audit or report still on the 1-6 ladder translates as:

| legacy | 2D |
|---|---|
| `L1` | `E1` |
| `L2` | `E2` |
| `L3` | `E3` |
| `L4` | `E4` |
| `L5` | `E5` |
| `L6` | any `E` with `R2` |
| `STATIC_ONLY` | `E1`, any `R` |
| `RUNTIME_NOT_RUN` | target `E4`+ not reached |
| `INDEPENDENT_REVIEW_NOT_RUN` | `R2` target not reached |

## Closeout linkage

The pre-work matrix is the closeout audit's matrix. At closeout each row is marked with
the cell **actually reached** and compared to the forecast cell:

- forecast `E4/R2`, reached `E4/R0` -> finding on the `R` axis (independent review not
  run).
- forecast `E4/R2`, reached `E1/R2` -> finding on the `E` axis (runtime not run).
- forecast `E1/R0` accepted-as-open, reached `E1/R0` -> not a finding; it matches the
  declared plan.
