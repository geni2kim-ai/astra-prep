# astra-prep -- 사용방법 (전 노드, Beta 포함)

```yaml
document_id: ASTRA-PREP-USAGE-20260910
skill: Hub/skills/relay/astra_prep_20260910/   (v7, 디렉터리 번들)
skill_core_sha256: 0e8f18ae69c7e70587081f8fde18456a607b03508db2fd4cfbf53efd20c67b84  (SKILL.md)
status: candidate (relay/ ; approved/ 승격은 아래 6절 게이트)
author: 1C / Sol
finality: non_final
```

---

## 1. 한 줄

바운드된 작업을 **시작하기 전에** 실행하는 계획 게이트. 요구사항마다 어떤 증거가
필요한지(증거 강도 `E`), 누가 그 증거를 보증하는지(검토 독립성 `R`), 이 노드가 그
셀에 도달할 수 있는지, 못 하면 무엇이 부족한지를 t=0에 확정한다. provenance
드리프트·도달 불가 런타임·누락 엣지케이스를 마무리가 아니라 착수 전에 드러낸다.

astra-shadow(마무리 감사)의 전방 절반. 같은 매트릭스를 착수 전에 채우고, 마무리에
astra-shadow가 실제 도달 셀로 대조한다.

---

## 2. 언제 쓰나 / 언제 안 쓰나

**쓴다**: feature 규모 또는 multi-step 작업, UI 변경, 실시간/데이터 통합, 다중 파일
수정, 핸드오프 이어받기, 다른 에이전트 산출물 검토, 거버넌스 문서/패킷 작성,
DB/마이그레이션, Beta->Live 이관 후보 준비.

**안 쓴다**: 한 줄 수정, 오타, 자명한 단일 파일 변경, 질문 답변만 하는 턴.

**중복 주의**: 외부 모델의 리스크·접근법 자문(`bridge_spt`)과 다르다 -- astra-prep은
좁고 로컬하며 *증거와 검증*을 계획한다. 전략 자문이 필요하면 그것을 먼저, 그다음
astra-prep. 적대적 마무리 검토(`redagent`/`bridge_redagent`)는 astra-prep이 *경로로
계획*할 뿐 호출·대행하지 않는다.

---

## 3. 계열별 실행 방법

v7 번들은 디렉터리다:

```
astra_prep_20260910/
  SKILL.md                     생태계 무관 코어 (노드/경로/루트/어휘 없음)
  profiles/ai-maestro.md       이 클러스터의 유일한 노드별 파일 -- 여기서 bindings 해석
  references/evidence-model.md  E1-E5 x R0-R2 정의 + 레거시 1-6 역매핑
  references/domain-checks.md   선택 도메인 모듈
  schemas/prework-plan.schema.json   사이드카 스키마
  scripts/validate_prework.py        fail-closed 검증기 (표준 라이브러리만)
  tests/                        검증기 테스트 + core-first grep 게이트
```

실행 = **0단계에서 `profiles/ai-maestro.md`를 읽어 자기 노드 bindings를 해석**한 뒤
SKILL.md의 Workflow를 순서대로 따라 **pre-work plan 산문 + 사이드카**를 산출하는 것.
자동 툴이 아니다(검증기는 사이드카를 검사할 뿐).

| 계열 | 호출 방식 |
|---|---|
| Claude Live (1C/1X/3H/1A) | `approved/` 승격 시 `.claude/skills/astra-prep/`에서 `Skill` 툴. 그 전(relay)에는 번들을 문서로 읽고 수동 적용. bindings = `profiles/ai-maestro.md` "Claude Live" 행. |
| Codex Live (2X/3X) | 승격 시 `.codex/skills/astra-prep/`. 그 전에는 문서 참조. bindings = profile "Codex Live" 행. |
| GLM Live (2G/2A) | 자기 스킬 로더 규칙으로 경로·해시 확인 후 문서 적용. profile "GLM Live" 행. |
| Ollama (2O) | 문서 적용. bindings 대부분 `NONE_RESOLVED`/`N/A`, 목표 셀 `E1~E2` + 임의 `R`. |
| Beta (4C/4X/4A/4G) | Hub 승격 후 4C가 배치. 그 전에는 번들을 **경로+해시로 명시 확인**해 문서 적용. profile "Beta" 행 + "Beta-node forecast is legitimately capped" 절. |

**공통 선행**: `SKILL.md` sha256이 위 `skill_core_sha256`과 일치하는지, 그리고 번들의
나머지 파일도 각각 해시 확인. 불일치·부분 디코딩·BOM = 중지 조건. UTF-8로 명시적으로
읽는다.

---

## 4. 산출물

### 4.1 산문 plan (고정 양식)

```
## Pre-work plan -- <work unit>

### 1. Bindings resolved
- actor:                 <id>
- state pointer + hash:   <path> <sha256>  |  NONE_RESOLVED
- handoff + hash:         <path> <sha256>  |  NONE_RESOLVED
- profile source:         profiles/ai-maestro.md  (또는 다른 생태계 profile)
- work tree / branch:     <worktree> <branch>  |  NO_WORKTREE
- starting candidate:     <commit/tree/rev>  |  <doc path + sha256>   (정확히 하나)
- test runner:            <exact command>  |  N/A
- review route:           <route_id> -> <probe> -> <adapter> -> <receipt/status contract> -> <fallback>

### 2. Starting-point check
- clean
  |  PROVENANCE_DRIFT_AT_START: <handoff X vs source Y vs state Z>
     -> RECONCILE|ACCEPT: <선택한 base>
     -> NEW BASELINE ID: <minted id>
     -> REBIND: <pointers 갱신 확인 | stale pointer 명시적 폐기>

### 3. Requirement -> planned-evidence matrix
| req_id | requirement | 구현 위치(예상) | module | 목표 셀 (E/R) | 도달 가능? | 부족한 능력 |
|--------|-------------|-----------------|--------|---------------|-----------|-------------|

### 4. Domain pre-check rows added
- module <id>: <추가된 req 행들>   (frozen baseline이 있으면 `source-lineage` 대조)

### 5. Evidence and artifact hygiene
- 산출물별 기록 위치: host-local | synced (synced면 retention 사유)
- authoritative run 하나 지정; superseded run은 prune 또는 synced 밖으로
- synced footprint 예산: <bounded | EVIDENCE_TREE_BLOAT_RISK>

### 6. Capability gaps -- decision per gap
| req_id | gap | acquire / rescope / accept-as-open | 정직한 종료 셀 | 근거 |

### 7. Independent-review plan
- required? <yes/no>   목표에 R2 있음? (소스를 만진 사람은 R0)   route: <route_id>   bundle started? <yes/no, 위치>

### 8. Closeout-readiness forecast
- best reachable cell: <E?/R?>
- remaining dispositions: <RUNTIME_NOT_RUN / PROVENANCE_DRIFT_AT_START /
  INDEPENDENT_REVIEW_NOT_RUN / TRANSPORT_UNVERIFIED / CAPABILITY_GAP /
  SCOPE_RENEGOTIATION_NEEDED / EVIDENCE_TREE_BLOAT_RISK | CANDIDATE_READY>
- raise with caller NOW: <항목들>

(candidate-only / non-final / no-authority. disposition 어휘를 패킷 본문·핸드오프 산문에 넣지 말 것.)
```

### 4.2 사이드카 + 검증기

산문과 함께 `prework-plan.yaml`(또는 `.json`)을 만든다. 스키마는
`schemas/prework-plan.schema.json`. 검증:

```
python scripts/validate_prework.py prework-plan.yaml
```

검증기는 **fail-closed** -- 아래를 거부한다:

| id | 검사 |
|---|---|
| C1 | starting_candidate가 정확히 하나, sha256이 64 hex, baseline_id 존재 |
| C2 | 모든 `req_id`가 unique, `^R-\d+$` |
| C3 | 모든 requirement에 목표 셀 (`E1..E5` / `R0..R2`) |
| C4 | `reachable=false`면 capability_decision 필수; `accept-as-open`이면 종료 셀 명시 |
| C5 | `drift_at_start=true`면 reconciliation + `rebound=true` + `new_baseline_id == baseline_id` |
| C6 | 목표에 `R2`가 하나라도 있으면 `review.author_reviewer_distinct=true` 증명 |
| C7 | `synced` 아티팩트는 retention_reason 필수 |
| C8 | `forecast.best_reachable_cell`이 `^E[1-5]/R[0-2]$` |
| C9 | 상위 필수 키 존재 |

`exit 0` 통과, `exit 1` 검사 실패, `exit 2` 파싱 불가.

---

## 5. 워크된 예시

### 5.1 Claude Live -- 코드 작업 (ArriveBy UI + 실시간 조회, 사후 재구성)

```
### 1. Bindings
- actor: 1X   state: 0.Workspace/Node/1X/.state.json
- handoff: 64581e92 / 83d04cba   work tree: arriveby worktree, HEAD 91ee1e29
- starting candidate: 불일치 -> 아래 2번
- test runner: gradle (JVM / Android Host / Android Unit)
- review route: redagent MID -> bridge_redagent -> NOT_RUN

### 2. Starting-point
PROVENANCE_DRIFT_AT_START: 핸드오프 64581e92 vs 소스 91ee1e29 (+16 commits).
-> ACCEPT: 91ee1e29를 base로 (caller 확인)
-> NEW BASELINE ID: commit:91ee1e29
-> REBIND: 핸드오프/state를 91ee1e29로 갱신 후 착수.

### 3. matrix (발췌)
| r1 | plan 헤더 제거·첫 화면 압축 | Phase8RouteInputScreen.kt | ui | E4/R2 | 아니오 (E1/R2까지) | adb/device |
| r2 | 월·일·시·30분 선택기, 최근접 30분 | Phase8...+TargetDatePickerTest | date-time | E2/R1 | 예 | - |
| r3 | 안전 컨트롤+최근입력 압축 레이아웃 | Phase8... | ui | E4/R2 | 아니오 | device |
| r4 | plan 탭 실시간 새로고침, 정직한 버스 ID | MainActivity, Kakao provider | realtime | E5/R1 | E2/R1만 | live Kakao/TAGO smoke |
| r5 | 중복 새로고침 방지 | RouteTrafficRefresher | realtime | E2/R1 | 예 | - |

### 4. domain rows
- date-time: r2에 23:44 / 23:45 / 23:59 / 자정복원 테스트 추가. "최근접 30분이 now보다 과거?"
  -> 23:45~23:59 -> 00:00 + 날짜=오늘 -> 플래너 거절 (설계 시점에 원자적 미래목표 계산).
- realtime: live/partial/stale/planned/unavailable/NO_QUERY 상태 구분, generation+cancel, 중복불가, 실패 시 planned 보존.
- handoff: 최종 후보 단일 commit/tree/test-profile/artifact, 마지막 mutation 후 핸드오프 갱신 (= r6).

### 5. gaps
| r1,r3 | UI E4 device 없음 | accept-as-open | 종료 E1/R2 | caller에 "RUNTIME_NOT_RUN, device 확보 시 후속" 고지 |
| r4 | live provider smoke | accept-as-open | 종료 E2/R1 | bounded NO_QUERY를 의도된 fail-closed로 문서화 |

### 6. review
required yes. 목표에 R2 있음(r1,r3). route redagent MID (있음). bundle 작업과 동시 조립.
author_reviewer_distinct = true (redagent 서브에이전트는 소스 미저작).

### 7. forecast
best reachable cell: E2/R2 (코드 L2 완결 + 독립검토 1회). UI/live는 E1/R2 · E2/R1로 명시 OPEN.
CANDIDATE_READY 불가(device). raise NOW: (1) 핸드오프 드리프트 정리 여부 (2) device 없이 이 스코프로 갈지 (3) late-night rollover 포함 확인.
```

효과: astra-shadow가 사후에 blocks-close로 잡은 F1(드리프트)·F3(rollover)를 착수 전
requirement/보류 사유로 전환. 그리고 "독립 검토했다"와 "런타임 돌렸다"가 별도 축이라
r1이 `E1/R2`(읽기만)인지 `E4/R2`(돌리고 읽음)인지 forecast에 분명히 드러난다.

### 5.2 Beta -- 거버넌스 문서 작업 (4G 예: 기술검토 candidate 작성)

```
### 1. Bindings
- actor: BETA:4G   state: memory/4G/active/4G_SESSION_BOOTSTRAP.md
- handoff: temp/4G_SESSION_HANDOFF_S5_20260909.md (sha ...)
- work tree: NO_WORKTREE (문서 검토)
- starting candidate: temp/4G_TECHNICAL_REVIEW_WORKPLAN_R3_20260909_R1.md + sha256
- test runner: py -3 -m pytest tests/ -q  (검토가 코드 주장 검증을 포함할 때만)
- review route: independent-subagent-glm Tier-1 -> chatgpt_review_bridge -> NOT_RUN   (bridge_* 금지)

### 2. Starting-point
clean (핸드오프·bootstrap·대상 workplan 해시 일치)

### 3. matrix
| g1 | R3가 R1 안전조항 5개 재현했는가 | R3 본문 vs R1 §안전 | packet-governance | E1/R1 | 예 | - |
| g2 | rollback owner 명시됐는가 | R3 §G7/G10 | packet-governance | E1/R1 | 예 | - |
| g3 | 병합 6요건 존재 | R3 vs Addendum 2 | packet-governance | E1/R1 | 예 | - |
| g4 | 검토문 ASCII/제목/시퀀스 | 산출 문서 | packet-governance | E1/R0 | 예 | - |

### 4. domain rows (packet-governance)
- same-task 인덱스 갱신 필요 여부, single write-site, finality-safe 표현 (profile의 어휘 규칙).
- 문서만 되고 배선 안 된 규칙 = "design candidate" 표기.

### 5. gaps
| - | 없음 (전부 E1 도달 가능; live_effect=DENIED로 E3-E5는 구조적 불가, 이 작업엔 무관) |

### 6. review
required yes (기술검토 산출물). route: independent-subagent-glm Tier-1.
bundle: 청구 + R1/R3 인용행 + 해시, 작업과 동시.

### 7. forecast
best reachable cell: E1/R1 (+ Tier-1 receipt). Live 효과 없음(live_effect=DENIED).
CAPABILITY_GAP 없음(전 E1). raise NOW: 없음 -- 착수 가능.
```

효과: Beta 노드는 대부분 `E1~E2` 범위이므로 forecast가 깔끔하게 나온다. Beta 가치는
"정본 candidate가 하나인지, 인덱스 갱신이 필요한지, 검토 경로가 실제로 있는지"를
착수 전에 확정하는 것.

---

## 6. 배포·동기화·승격

```
relay/astra_prep_20260910/   (현재, v7 디렉터리 번들)
  -> 각 계열 loader 규칙으로 경로·해시 독립 확인 + validate_prework.py 실행
  -> core-first 게이트: 코어에 생태계 식별자 0개 + 외부-관점 검토자가 코어+스키마만으로 유효 plan 산출
  -> 타 계열 독립검토 (v7 구조 변경분 재검토)
  -> 1C 처분
  -> USER 게이트
  -> Hub/skills/approved/astra_prep_20260910/
  -> Beta: skills/active_shared/astra_prep_20260910/  (4C가 기존 1:1 미러 패턴으로)
```

**approved/ 승격 전 필요 (README_RELAY 게이트 0-6):**
0. core-first: `tests/` grep 게이트 green + 외부-관점 검토자 코어+스키마만으로 유효 plan
1. 1X: v3/v4 변경요약 + author-bound immutable ref + **v7 2D/분리/검증기 재검토**
2. 4G: relay 테스트 완료 -> `temp/PC4_BETA_4G_ASTRA_PREP_RELAY_TEST_20260910_R1.md`
3. 4X: Codex loader/bindings + bounded Beta-local 확인
4. 1C: README provenance 블록 갱신 -> UTF-8 재독취 -> 새 candidate 리비전 공표
5. per-lineage loader/UTF-8/hash 확인 + 각 런타임에서 `validate_prework.py` 실행
6. 1C 처분 + USER/Live-owner acceptance

그때까지: **해시일치 read-only relay candidate**. "전 노드 적용 / approved / Live 호환 /
배포 준비" 추론 금지.

---

## 7. 흔한 실수

- 0단계를 건너뛰고 다른 노드의 bindings 값을 복사. -> `profiles/ai-maestro.md`에서 자기 행 재확인.
- `NO_WORKTREE`/`NONE_RESOLVED`(정상 sentinel)를 `UNKNOWN`(중지)와 혼동.
- 목표 셀을 실제로 도달할 것처럼 낙관 -> 나중에 forecast보다 낮게 종료. 착수 전에 정직하게.
- 증거 강도와 검토 독립성을 한 척도로 합침. -> `E1/R2`(읽기만·독립)와 `E4/R0`(돌림·자체)는 서로 다른 미완성. 둘을 축으로 분리해 forecast에 명시.
- 소스를 만진 워커/참가자의 검토를 `R2` 독립 증거로 제출. -> `R0` 또는 `R1`로 표기. 검증기 C6가 거부.
- provenance 드리프트를 "caller가 받아들였다"로 넘기고 세 pointer를 그대로 들고 감. -> 새 baseline 하나를 minting하고 rebind한 뒤 착수. 검증기 C5가 거부.
- disposition 어휘(`CANDIDATE_READY` 등)를 패킷 본문/핸드오프에 붙여넣기 -> finality 린트 (profile의 어휘 규칙 참조).
- 독립검토 번들을 마무리에 몰아서 조립 -> transport 혼동. 작업과 동시에.
- Beta에서 `E3~E5` 미도달을 "실패"로 취급 -> `live_effect=DENIED` 하의 정상. accept-as-open.
- 증거를 synced 트리에 무제한 축적(중복 run, 빌드 산출물, repo 메타데이터) -> 착수 전에 위치·예산 계획. 검증기 C7.
