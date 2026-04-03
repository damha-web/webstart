# WebStart 시스템 검토 보고서

> 검토일: 2026-04-02
> 검토 범위: SETUP-GUIDE.md + skills/ 13개 스킬 파일 전체
> 작성: Claude Code (simplify 스킬)
> 2026-04-03 업데이트: 이 문서는 1차 검토 기록입니다.
> 현재 남은 이슈 판단과 우선순위는 [REVIEW-REPORT-V2.md](./REVIEW-REPORT-V2.md)를 기준으로 보세요.

---

> v2 — 2026-04-02: webstart 사용자 경로 오류 추가(M-0), C-1 근본 원인 보완, M-4 심각도 하향

## 요약

| 심각도 | 건수 |
|--------|------|
| Critical (동작 오류) | 3 |
| Major (기능 저하/불일치) | 5 |
| Minor (표현/문서 개선) | 6 |
| **합계** | **14** |

---

## Critical — 수정 필수 (동작 오류)

### C-1. Playwright 실행 모델과 설치 방식 불일치
**위치:** `skills/audit/SKILL.md` Step 0, `skills/audit-ux/SKILL.md` Step 2, `skills/audit-ia/SKILL.md` Step 3, `skills/audit-db/SKILL.md` Step 3

**표면 오류:** `audit/SKILL.md`는 존재하지 않는 플래그를 사용함.
```bash
# 동작 안 함 — playwright test에 -e 플래그 없음
npx playwright test --config=/dev/null -e "..."
```

**근본 원인:** 설치 방식과 실행 모델 불일치.  
SETUP-GUIDE.md는 Playwright를 글로벌 CLI로 설치하도록 안내함:
```bash
npm install -g playwright   # CLI만 전역 설치
```
그러나 `audit-ux`, `audit-ia`, `audit-db` 스킬이 사용하는 `node -e "const { chromium } = require('playwright')"` 방식은 `playwright`가 **로컬 node_modules에 설치된 npm 패키지**여야 동작함. 글로벌 CLI 설치만으로는 `require('playwright')`가 MODULE_NOT_FOUND로 실패함. 이 환경에서도 실제로 실패 확인됨.

**수정이 필요한 두 지점:**
1. `SETUP-GUIDE.md` — 글로벌 CLI 설치 외에 각 프로젝트에서 로컬 설치 필요 명시:
   ```bash
   cd {프로젝트-폴더}
   npm install playwright   # 로컬 설치 필요
   ```
   또는 `npx playwright` 실행 시 자동 다운로드를 활용하는 방식으로 스킬 통일
2. `audit/SKILL.md` Step 0 — 나머지 스킬과 동일한 `node -e` 방식으로 교체 (단, 위 설치 문제 해결 전제)

---

### C-2. `/qa` vs `/qa-check` 스킬명 혼재
**위치:** `skills/fe/SKILL.md` Step 8, `skills/be/SKILL.md` Step 9, `skills/devops/SKILL.md` Step 1

세 스킬 모두 다음 단계로 `/qa`를 안내하지만, 제작 파이프라인의 QA 스킬명은 `/qa-check`.
(`/qa`는 gstack 기반의 별도 브라우저 테스트 스킬임)

| 파일 | 현재 | 올바른 스킬 |
|------|------|-----------|
| fe/SKILL.md Step 8 완료 메시지 | `다음 단계: /qa` | `/qa-check` |
| be/SKILL.md Step 9 완료 메시지 | `다음 단계: /qa` | `/qa-check` |
| devops/SKILL.md Step 1 게이트 메시지 | `먼저 /qa 를 실행하고` | `/qa-check` |

---

### C-3. `--step=report` 옵션 미처리
**위치:** `skills/audit/SKILL.md` Step 0 옵션 처리, `skills/audit-db/SKILL.md` Step 10 완료 메시지

`audit-db` 완료 메시지에서 다음 단계로 `/audit --step=report` 실행을 안내하지만,
`audit/SKILL.md`의 옵션 처리에는 `--step=ux|ia|tech|db` 만 명시되어 있어
`--step=report`를 실행하면 어떤 동작도 트리거되지 않음.

**수정안 (둘 중 하나):**
- `audit/SKILL.md` Step 0 옵션에 `--step=report` 추가하여 Step 5~6 실행
- `audit-db` 완료 메시지를 `/audit --full` 또는 `Step 5~6는 /audit 재실행`으로 수정

---

## Major — 기능 저하/불일치

### M-0. webstart 생성 CLAUDE.md의 호출 방식과 파이프라인이 공식 흐름과 충돌
**위치:** `skills/webstart/SKILL.md` line 78, 105~110, 134, 183~185

webstart가 프로젝트에 생성하는 CLAUDE.md 템플릿과 완료 안내가 두 가지 핵심 오류를 포함함.

**오류 1 — 호출 방식 불일치 (`@` vs `/`)**

생성된 CLAUDE.md는 에이전트를 `@pm`, `@design`, `@fe`, `@be`, `@qa`, `@devops`로 호출하도록 안내.
그러나 이 시스템의 공식 호출 방식은 `/pm`, `/design` 등 slash command임.
`@` 방식은 Claude.ai의 Project Instructions 문법으로, Claude Code CLI 환경에서는 동작하지 않음.

영향 범위:
- CLAUDE.md `## 에이전트 역할 가이드` 섹션 전체 (line 78~110)
- `_agency/client-brief.md` 템플릿 (line 134: "이 파일을 채운 뒤 @pm 에게 전달하세요.")
- Step 5 완료 메시지 표 (line 183~185: `@pm`, `@design`, `@fe`, `@be`)

사용자가 webstart를 실행하면 이 안내대로 `@pm`을 입력해도 아무 스킬도 실행되지 않음.

**오류 2 — Contract 단계 누락**

생성된 CLAUDE.md의 `## 파이프라인 순서` (line 106~110):
```
1. @pm → 기획·견적
2. @design → 디자인 시스템
3. @fe + @be 병렬 진행   ← /contract 없이 바로 병렬 개발
4. @qa → QA 리포트
5. @devops → 배포
```

공식 파이프라인 (SETUP-GUIDE.md line 102):
```
/pm → /design → /contract → /fe + /be → /qa-check → /devops
```

`/contract`이 빠진 채로 FE/BE를 바로 시작하도록 안내하면 계약 미확정 상태로 병렬 개발이 진행됨.
`/qa-check` 대신 `@qa`로 표기된 것도 C-2와 동일한 스킬명 혼재.

**수정 범위:** webstart/SKILL.md Step 3 (CLAUDE.md 템플릿), Step 4 (client-brief.md 템플릿), Step 5 (완료 메시지)

---

### M-1. webstart 생성 폴더 구조에 `contract.md`, `status.md` 누락
**위치:** `skills/webstart/SKILL.md` Step 2

webstart가 생성하는 `_agency/` 구조에 `contract.md`와 `status.md`가 없음.
두 파일은 `/contract`, `/pm` 스킬이 처음 생성하지만, webstart 폴더 구조 명세에 없어
구조 문서로서 불완전하고 사용자 예측 가능성이 낮음.

**현재 webstart Step 2 구조:**
```
_agency/
├── client-brief.md
├── sitemap.md
├── design-system.md
├── api-spec.md
└── qa-report.md
```

**누락된 파일:**
- `_agency/contract.md` — `/contract` 스킬 생성
- `_agency/status.md` — `/pm` 스킬 최초 생성, 이후 각 스킬이 업데이트
- `_agency/handover.md` — `/devops` 스킬 생성

---

### M-2. `contract` 스킬의 PHP 스택 분기 없음
**위치:** `skills/contract/SKILL.md` Step 3

`contract` 스킬이 공유 타입을 TypeScript(`types/shared.ts`)로만 정의하는데,
PHP 스택 프로젝트에서는 TypeScript 공유 타입이 의미없음.
`fe`, `be`, `design` 스킬은 모두 `CLAUDE.md`에서 스택을 확인하고 분기하는데,
`contract`만 스택 확인 및 분기 로직이 없음.

**수정안:**
- Step 2 이후 `CLAUDE.md`에서 스택 확인 단계 추가
- PHP 스택이면 공유 타입 대신 OpenAPI 스펙 또는 PHP 타입 힌트 문서로 대체

---

### M-3. `fe` 스킬 부분 작업 완료 시 전체 FE 완료 표시
**위치:** `skills/fe/SKILL.md` Step 7

`/fe Hero섹션`처럼 args로 특정 컴포넌트만 구현해도 Step 7에서 `status.md`의 FE 단계를
✅ 완료로 업데이트함. 이 경우 `/qa-check`의 게이트(FE 완료 확인)를 너무 일찍 통과하게 됨.

`/be`도 동일한 구조 (Step 8에서 전체 완료 표시).

**수정안:**
- args가 있는 경우(부분 작업) status.md 업데이트 생략
- 완료 메시지에 "전체 FE 완료 시 `/qa-check` 실행" 안내 추가

---

### M-4. ~~`audit-db` 게이트에서 단계 번호/이름 혼용~~ → Minor로 재분류
**위치:** `skills/audit-db/SKILL.md` Step 1, `skills/audit-ia/SKILL.md` Step 1

"IA 단계(Step 2)", "UX 단계(Step 1)"처럼 단계 이름과 번호를 혼용.
이 스킬들은 LLM이 실행하므로 `_audit/status.md`를 자연어로 읽어 판단함.
실제로 번호를 파싱하는 코드가 없어 **기능 오류로 이어지는 실행 경로는 없음.**
status.md에 Step 번호 열이 없어 혼란을 줄 수는 있지만, 이는 문서 명확성 이슈에 해당.

→ **Minor m-7로 이동, 아래 참조**

---

## Minor — 표현/문서 개선

### m-1. SETUP-GUIDE.md Playwright 설명 모호
**위치:** `SETUP-GUIDE.md` line 50, 67

"Playwright (검수용)"으로만 표기. `/qa-check`도 잠재적으로 Playwright 활용 가능하고,
검수 파이프라인에 한정된 도구라는 인상을 줘 제작 파이프라인 사용자가 설치를 건너뛸 수 있음.

**수정안:** "(검수 파이프라인 필수, /qa 스킬 선택)"으로 구체화

---

### m-2. SETUP-GUIDE.md `/audit --step=ux` vs `/audit-ux` 중복 설명
**위치:** `SETUP-GUIDE.md` line 199~215

개별 단계 실행 방법으로 `/audit-ux` 직접 호출과 `/audit --step=ux` 두 방식이 나란히 설명됨.
두 방식의 차이(언제 어떤 걸 써야 하는지)가 없어 혼란을 줌.

**수정안:** 두 방식 중 권장 방식 명시, 또는 차이를 한 줄로 설명

---

### m-3. SETUP-GUIDE.md 설치 확인 시 cleanup 안내 없음
**위치:** `SETUP-GUIDE.md` line 87

```bash
/webstart test-project nextjs    # → 프로젝트 세팅 완료
```

설치 확인 목적으로 실행하면 `test-project/` 폴더와 여러 파일이 실제로 생성됨.
확인 후 삭제 방법(`rm -rf test-project/`) 안내가 없음.

---

### m-4. `design/SKILL.md` 타이포그래피 템플릿 불완전
**위치:** `skills/design/SKILL.md` Step 4 타이포그래피 표

```markdown
| H1 | ... | ... | ... | ... | 메인 제목 |
| H2~H6, Body, Caption 포함 |
```

H2~H6, Body, Caption 행이 한 줄로 묶인 주석 형태로 처리됨.
표 구조상 이 행은 렌더링이 깨짐. 각 레벨을 개별 행으로 명시해야 함.

---

### m-5. `qa-check/SKILL.md` 불필요한 Bash 도구 포함
**위치:** `skills/qa-check/SKILL.md` frontmatter

```yaml
allowed-tools:
  - Bash
```

스킬 본문에 Bash 명령이 없음. 코드 분석 기반 QA 체크리스트라 Bash가 필요 없는 구조.
불필요한 도구 허용은 최소 권한 원칙에 반함.

---

### m-6. `pm/SKILL.md` 단가 하드코딩

**위치:** `skills/pm/SKILL.md` Step 2 견적서 표 헤더

```markdown
| 단가(시간당 5만원) |
```

시간당 단가(5만원)가 고정값으로 하드코딩됨. 클라이언트나 프로젝트에 따라 단가가 다를 수 있음.
`client-brief.md` 템플릿에 시간당 단가 입력 필드를 추가하거나, pm 스킬 시작 시
AskUserQuestion으로 확인하는 방식이 더 유연함.

---

### m-7. `audit-db`/`audit-ia` 게이트 단계 번호/이름 혼용
**위치:** `skills/audit-db/SKILL.md` Step 1, `skills/audit-ia/SKILL.md` Step 1

"IA 단계(Step 2)", "UX 단계(Step 1)"처럼 단계 번호를 병기하지만 `_audit/status.md`에는 번호 열이 없음.
LLM이 읽는 자연어 지시이므로 기능 오류는 아니나, 문서 일관성 측면에서 번호 제거가 더 명확함.

---

## 파일별 이슈 요약

| 파일 | C | M | m |
|------|---|---|---|
| SETUP-GUIDE.md | - | - | 3 |
| skills/webstart/SKILL.md | - | 2 | - |
| skills/pm/SKILL.md | - | - | 1 |
| skills/design/SKILL.md | - | - | 1 |
| skills/contract/SKILL.md | - | 1 | - |
| skills/fe/SKILL.md | 1 | 1 | - |
| skills/be/SKILL.md | 1 | 1 | - |
| skills/qa-check/SKILL.md | - | - | 1 |
| skills/devops/SKILL.md | 1 | - | - |
| skills/audit/SKILL.md | 1 | - | - |
| skills/audit-ux/SKILL.md | 1 | - | - |
| skills/audit-ia/SKILL.md | 1 | - | 1 |
| skills/audit-tech/SKILL.md | - | - | - |
| skills/audit-db/SKILL.md | 1 | 1 | 1 |

---

## 권장 수정 순서

1. **M-0** webstart/SKILL.md — `@command` → `/command` 전면 수정 + Contract 단계 파이프라인 추가 (사용자가 시스템 진입 즉시 만나는 첫 번째 안내)
2. **C-1** Playwright 설치 방식 결정 후 SETUP-GUIDE.md와 전체 스킬 일관화 (글로벌 CLI vs 로컬 패키지)
3. **C-2** fe/be/devops의 `/qa` → `/qa-check` 일괄 수정
4. **C-3** `--step=report` 처리 추가 또는 audit-db 완료 메시지 수정
5. **M-1** webstart 폴더 구조 명세 보완
6. **M-2** contract 스킬 PHP 분기 추가
7. **M-3** fe/be 부분 작업 완료 처리 로직 개선
8. Minor 항목들은 시간 여유 시 처리
