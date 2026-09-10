# astra-prep -- 사용방법 (전 노드, Beta 포함)

```yaml
document_id: ASTRA-PREP-USAGE-20260910
skill: Hub/skills/relay/astra_prep_20260910/SKILL.md  (v6)
skill_sha256: 7b637653d78714f4643ab1304f136a67b91066a7cae959cc1b4aee9b20c2d949
status: candidate (relay/ ; approved/ 승격은 아래 6절 게이트)
author: 1C / Sol
finality: non_final
```

---

## 1. 한 줄

바운드된 작업을 **시작하기 전에** 실행하는 계획 게이트. 요구사항마다 어떤 증거가
필요한지, 이 노드가 그 증거를 만들 수 있는지, 못 만들면 무엇이 부족한지를 t=0에
확정한다. provenance 드리프트·도달 불가 런타임·누락 엣지케이스를 마무리가 아니라
착수 전에 드러낸다.

astra-shadow(마무리 감사)의 전방(前方) 절반. 같은 매트릭스를 착수 전에 채우고,
마무리에 astra-shadow가 실제값으로 대조한다.

---

## 2. 언제 쓰나 / 언제 안 쓰나

**쓴다**: feature 규모 또는 multi-step 작업, UI 변경, 실시간/데이터 통합, 다중 파일
수정, 핸드오프 이어받기, 다른 에이전트 산출물 검토, 거버넌스 문서/패킷 작성,
DB/마이그레이션, Beta→Live 이관 후보 준비.

**안 쓴다**: 한 줄 수정, 오타, 자명한 단일 파일 변경, 질문 답변만 하는 턴.

**중복 주의**: `bridge_spt`(외부 모델의 리스크·접근법 자문)와 다르다 — astra-prep은
좁고 로컬하며 *증거와 검증*을 계획한다. 전략 자문이 필요하면 `bridge_spt`를 먼저,
그다음 astra-prep. `redagent`/`bridge_redagent`는 astra-prep이 *경로로 계획*할 뿐
호출·대행하지 않는다.

---

## 3. 계열별 실행 방법

스킬 파일은 `D:\Shared\0.AI_Maestro_Shared\Hub\skills\relay\astra_prep_20260910\SKILL.md`
(전 노드가 Syncthing으로 읽음). 실행 = SKILL.md의 Workflow를 순서대로 따라 **pre-work
plan 문서**를 산출하는 것. 자동 툴이 아니다.

| 계열 | 호출 방식 |
|---|---|
| Claude Live (1C/1X/3H/1A) | `approved/`로 승격되면 `.claude/skills/astra-prep/`에서 `Skill` 툴로 `name` 호출. 그 전(relay 단계)에는 SKILL.md를 문서로 읽고 수동 적용. |
| Codex Live (2X/3X) | 승격 시 `.codex/skills/astra-prep/`(ID 규칙상 하이픈). `$astra-prep`. 그 전에는 문서 참조. |
| GLM Live (2G/2A) | 자기 스킬 로더 규칙으로 경로·해시 확인 후 문서로 적용. |
| Ollama (2O) | 문서로 적용. bindings 대부분 `NONE_RESOLVED`/`N/A`, 목표 레벨 L1~L2 + L6. |
| Beta (4C/4X/4A/4G) | `PC4_BETA_LOCAL_CANONICAL/skills/`에는 Hub 승격 후 4C가 배치(기존 `active_shared/` 1:1 미러 패턴). 그 전에는 relay SKILL.md를 **경로+해시로 명시 확인**해 문서로 적용. Codex 로더 규칙(4X)·GLM 로더 규칙(4G)으로 각자 확인. |

**공통 선행**: `SKILL.md` sha256이 위 `skill_sha256`과 일치하는지 확인. 불일치·부분
디코딩·BOM = 중지 조건. UTF-8로 명시적으로 읽는다(로케일 디코딩 실패는 검증 실패이지
한국어 트리거를 버리는 이유가 아니다).

---

## 4. 산출물 — pre-work plan (고정 양식)

짧게. 아래 순서:

```
## Pre-work plan -- <work unit>

### 1. Bindings resolved
- node symbol:            <id>
- state pointer + hash:   <path> <sha256>  |  NONE_RESOLVED
- handoff + hash:         <path> <sha256>  |  NONE_RESOLVED
- node-registry source:   <path>
- work tree / branch:     <worktree> <branch>  |  NO_WORKTREE
- starting candidate:     <commit/tree/rev>  |  <doc path + sha256>   (정확히 하나)
- test runner:            <exact command>  |  N/A
- review route:           <route_id> -> <probe> -> <permitted adapter/command> -> <receipt/status contract> -> <fallback>

### 2. Starting-point check
- clean  |  PROVENANCE_DRIFT_AT_START: <handoff X vs source Y vs state Z>

### 3. Requirement -> planned-evidence matrix
| req_id | requirement | 구현 위치(예상) | module | 목표 레벨(1-6) | 도달 가능? | 부족한 능력 |
|--------|-------------|-----------------|--------|----------------|-----------|-------------|

### 4. Domain pre-check rows added
- module <id>: <추가된 req 행들>   (frozen baseline이 있으면 `source-lineage` 대조: 일치 수 / per-path drift / missing)

### 5. Evidence and artifact hygiene
- 산출물별 기록 위치: host-local | synced (synced면 retention 사유)
- authoritative run 하나 지정; superseded run은 prune 또는 synced 밖으로
- synced 트리에 빌드 산출물(APK/번들/tar)/`.git` 없음; 통합 문서/매트릭스는 한 버전만
- synced footprint 예산: <bounded | EVIDENCE_TREE_BLOAT_RISK>

### 6. Capability gaps -- decision per gap
| req_id | gap | acquire / rescope / accept-as-open | 근거 |

### 7. Independent-review plan
- required? <yes/no>   level-6 독립? (소스를 만진 사람은 level 6 아님)   route: <route_id>   bundle started? <yes/no, 위치>

### 8. Closeout-readiness forecast
- best reachable: CANDIDATE_READY  |  <RUNTIME_NOT_RUN / PROVENANCE_DRIFT_AT_START /
  INDEPENDENT_REVIEW_NOT_RUN / TRANSPORT_UNVERIFIED / CAPABILITY_GAP /
  SCOPE_RENEGOTIATION_NEEDED / EVIDENCE_TREE_BLOAT_RISK>
- raise with caller NOW: <항목들>

(candidate-only / non-final / no-authority. 이 어휘를 패킷 본문·핸드오프 산문에 넣지 말 것.)
```

이 매트릭스를 마무리에 astra-shadow(또는 로컬 등가물)에 넘긴다. astra-shadow가 각 행을
PASS/STATIC_ONLY/NOT_RUN/UNVERIFIED로 대조하고 예보와 비교한다. 예보=도달 가능인데
실제=NOT_RUN인 행은 finding.

---

## 5. 워크된 예시

### 5.1 Claude Live -- 코드 작업 (ArriveBy UI + 실시간 조회, 사후 재구성)

```
### 1. Bindings
- node: (ArriveBy 담당)   state: 0.Workspace/Node/1X/.state.json
- handoff: 64581e92 / 83d04cba   work tree: arriveby worktree, HEAD 91ee1e29
- starting candidate: 불일치 -> 아래 2번
- test runner: gradle (JVM / Android Host / Android Unit)
- review route: redagent MID -> bridge_redagent -> NOT_RUN

### 2. Starting-point
PROVENANCE_DRIFT_AT_START: 핸드오프 64581e92 vs 소스 91ee1e29 (+16 commits). 착수 보류.

### 3. matrix (발췌)
| r1 | plan 헤더 제거·첫 화면 압축 | Phase8RouteInputScreen.kt | ui | L4 | 아니오 | adb/device |
| r2 | 월·일·시·30분 선택기, 최근접 30분 | Phase8...+TargetDatePickerTest | date-time | L2 | 예 | - |
| r3 | 안전 컨트롤+최근입력을 압축 레이아웃에 | Phase8... | ui | L4 | 아니오 | device |
| r4 | plan 탭 실시간 새로고침, 정직한 버스 ID | MainActivity, Kakao provider | realtime | L2~L5 | L2만 | live Kakao/TAGO smoke |
| r5 | 중복 새로고침 방지 | RouteTrafficRefresher | realtime | L2 | 예 | - |

### 4. domain rows
- date-time: r2에 23:44 / 23:45 / 23:59 / 자정복원 테스트 추가. "최근접 30분이 now보다 과거?"
  -> 23:45~23:59 -> 00:00 + 날짜=오늘 -> 플래너 거절. (설계 시점에 원자적 미래목표 계산으로)
- realtime: live/partial/stale/planned/unavailable/NO_QUERY 상태 구분, generation+cancel, 중복불가, 실패 시 planned 보존
- handoff: 최종 후보 단일 commit/tree/test-profile/artifact, 마지막 mutation 후 핸드오프 갱신 (= r6)

### 5. gaps
| r1,r3 | UI L4 device 없음 | accept-as-open | caller에 "RUNTIME_NOT_RUN, device 확보 시 후속" 고지 |
| r4 | live provider smoke | accept-as-open | bounded NO_QUERY를 의도된 fail-closed로 문서화 |

### 6. review
required yes. route redagent MID (있음). bundle 작업과 동시 조립.

### 7. forecast
best reachable: 코드 L2 완결 + 새 핸드오프 바인딩 + 독립검토 1회 + UI/live 명시적 OPEN.
CANDIDATE_READY 불가(device). raise NOW: (1) 핸드오프 드리프트 정리 여부 (2) device 없이 이 스코프로 갈지 (3) late-night rollover 포함 확인.
```

효과: astra-shadow가 사후에 blocks-close로 잡은 F1(드리프트)·F3(rollover)를 착수 전
requirement/보류 사유로 전환.

### 5.2 Beta -- 거버넌스 문서 작업 (4G 예: 기술검토 candidate 작성)

```
### 1. Bindings
- node: BETA:4G   state: memory/4G/active/4G_SESSION_BOOTSTRAP.md
- handoff: temp/4G_SESSION_HANDOFF_S5_20260909.md (sha ...)
- work tree: NO_WORKTREE (문서 검토)
- starting candidate: temp/4G_TECHNICAL_REVIEW_WORKPLAN_R3_20260909_R1.md + sha256
- test runner: py -3 -m pytest tests/ -q  (검토가 코드 주장 검증을 포함할 때만)
- review route: independent-subagent-glm Tier-1 -> chatgpt_review_bridge -> NOT_RUN   (bridge_* 금지)

### 2. Starting-point
clean (핸드오프·bootstrap·대상 workplan 해시 일치)

### 3. matrix
| g1 | R3가 R1 안전조항 5개 재현했는가 | R3 본문 vs R1 §안전 | packet-governance | L1 | 예 | - |
| g2 | rollback owner 명시됐는가 | R3 §G7/G10 | packet-governance | L1 | 예 | - |
| g3 | 병합 6요건 존재 | R3 vs Addendum 2 | packet-governance | L1 | 예 | - |
| g4 | 검토문 ASCII/제목/시퀀스 | 산출 문서 | packet-governance | L1 | 예 | - |

### 4. domain rows (packet-governance)
- same-task 인덱스 갱신 필요 여부, single write-site, finality-lint-safe 표현
- 문서만 되고 배선 안 된 규칙 = "design candidate" 표기

### 5. gaps
| - | 없음 (전부 L1 도달 가능) |

### 6. review
required yes (기술검토 산출물). route: independent-subagent-glm Tier-1.
bundle: 청구 + R1/R3 인용행 + 해시, 작업과 동시.

### 7. forecast
best reachable: RETURN_FOR_REWORK 또는 CONCUR candidate + Tier-1 receipt.
Live 효과 없음(live_effect=DENIED). CAPABILITY_GAP 없음(전 L1). 
raise NOW: 없음 -- 착수 가능.
```

효과: Beta 노드는 대부분 L1~L2 + L6 범위이므로 forecast가 깔끔하게 나온다. 이 스킬의
Beta 가치는 "정본 candidate가 하나인지, 인덱스 갱신이 필요한지, 검토 경로가 실제로
있는지"를 착수 전에 확정하는 것.

---

## 6. 배포·동기화·승격

```
relay/astra_prep_20260910/   (현재)
  -> 각 계열 loader 규칙으로 경로·해시 독립 확인
  -> 타 계열 독립검토 (Claude=1X, GLM=4G relay 테스트가 2G 블록 대행)
  -> 1C 처분
  -> USER 게이트
  -> Hub/skills/approved/astra_prep_20260910/
  -> Beta: skills/active_shared/astra_prep_20260910/  (4C가 기존 1:1 미러 패턴으로)
```

**approved/ 승격 전 필요 (세션 #5 CLOSEOUT 제약):**
1. 1X: v3/v4 변경요약 + author-bound immutable ref + v3→v4 diff + 해시 (v3 artifact 없으면 gap 명시)
2. 4G: relay 테스트 완료 → `temp/PC4_BETA_4G_ASTRA_PREP_RELAY_TEST_20260910_R1.md`
3. 4X: Codex loader/bindings + bounded Beta-local 확인
4. 1C: README provenance 블록 삽입 → UTF-8 재독취 → 새 candidate 리비전 공표
5. per-lineage loader 확인 (각 계열)
6. 1C 처분 + USER/Live-owner acceptance

그때까지: **해시일치 read-only relay candidate**. "전 노드 적용 / approved / Live 호환 /
배포 준비" 추론 금지. "1X가 테스트했으니 전 노드 가능"은 overreach.

---

## 7. 흔한 실수

- 다른 노드의 bindings 값을 복사 (state pointer, test runner 등). → 자기 노드에서 재확인.
- `NO_WORKTREE`/`NONE_RESOLVED`(정상 sentinel)를 `UNKNOWN`(중지)와 혼동.
- 목표 레벨을 실제로 도달할 것처럼 낙관 → 나중에 NOT_RUN. 착수 전에 정직하게.
- disposition 어휘(`CANDIDATE_READY` 등)를 패킷 본문/핸드오프에 붙여넣기 → finality-lint.
- 독립검토 번들을 마무리에 몰아서 조립 → transport 혼동. 작업과 동시에.
- Beta에서 L4~L5 미도달을 "실패"로 취급 → `live_effect=DENIED` 하의 정상. accept-as-open.
- 소스를 만진 워커/참가자의 검토를 level 6 독립 증거로 제출 → level 1로 표기.
- 증거를 synced 트리에 무제한 축적(중복 run, APK, `.git`) → 착수 전에 위치·예산 계획.
- collector가 실패한 run에 나중 XML 스크레이프를 이어붙여 test-count 주장 → clean end-to-end run 아님.
