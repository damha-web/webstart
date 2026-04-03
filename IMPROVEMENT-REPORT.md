# WebStart 시스템 개선 검토 보고서

> 작성일: 2026-04-02
> 검토 기준: SESSION-REPORT.md 이후 잔존 이슈 + 구조적 개선 제안

> 2026-04-03 업데이트:
> 이 문서는 "당시 검토 시점의 개선 제안 기록"입니다.
> 아래 I-1 ~ I-6 항목은 현재 저장소 기준으로 모두 반영 완료되었고,
> 더 이상 실제 미완료 작업 목록으로 보면 안 됩니다.
> 최신 상태는 `CHANGELOG.md`, `SETUP-GUIDE.md`, `README.md`, 각 `skills/*/SKILL.md`를 기준으로 확인하세요.

---

## 개요

SESSION-REPORT.md에서 14건을 수정한 뒤, 당시 시점에서 추가로 식별된 구조적 개선점 6건을 정리한 문서다.
현재는 이 문서의 제안이 대부분 실제 코드와 문서에 반영되었으므로,
"후속 작업 제안의 기록"으로 읽는 것이 맞다.

---

## 빠른 판단 요약

| # | 제목 | 유형 | 작업량 | 우선순위 |
|---|------|------|--------|----------|
| I-1 | CHANGELOG 설치 안내 오류 | 버그 (문서) | 소 | **즉시** |
| I-6 | webstart 소개 문구 미반영 | 버그 (문서) | 소 | 즉시 |
| I-2 | `--full` 자동화 경로 불완전 | 기능 결함 | 중 | 단기 |
| I-3 | 상태 관리 구조 취약 | 설계 부채 | 대 | 중기 |
| I-4 | install.sh 확장성 부족 | 설계 부채 | 소~중 | 중기 |
| I-5 | 문서 일관성 자동 검사 없음 | 운영 개선 | 중 | 중기 |

## 현재 상태 요약

| # | 현재 상태 | 반영 위치 |
|---|-----------|-----------|
| I-1 | 완료 | `CHANGELOG.md` v2.2 업그레이드 안내 |
| I-2 | 완료 | `skills/audit/SKILL.md` 기본 분석 목적 반영 |
| I-3 | 완료 | `_agency/status.json` 도입, `agency-ai-agent-plan.md`, 제작 스킬 전반 |
| I-4 | 완료 | `install.sh`의 `rsync` 기반 디렉터리 복사 |
| I-5 | 완료 | `scripts/lint-docs.sh` 추가 및 `install.sh` 자동 실행 |
| I-6 | 완료 | `skills/webstart/SKILL.md`, `README.md` 설명 갱신 |

---

## 상세 내용

---

### I-1. CHANGELOG 설치 안내가 현재 정책과 충돌 — 즉시 수정

**현재 상태:** 완료
([CHANGELOG.md](./CHANGELOG.md) v2.2 업그레이드 안내에 반영됨)

**위치:** [CHANGELOG.md:51-55](./CHANGELOG.md#L51)

**문제:**
v2.0→v2.1 업그레이드 안내에 여전히 전역 설치를 안내하고 있다.

```bash
# CHANGELOG.md line 51-55 현재 내용
npm install -g playwright
npx playwright install chromium
```

반면 SETUP-GUIDE.md (line 50, 67)와 SESSION-REPORT.md (C-1)에서는 이미 `_audit/` 폴더에 **자동 설치**하는 방식으로 정리됐다.

**왜 문제인가:**
기존 사용자가 업그레이드할 때 가장 먼저 보는 문서가 CHANGELOG다. 여기서 전역 설치하면, `require('./_audit/node_modules/playwright')` 경로를 찾지 못해 MODULE_NOT_FOUND가 발생한다. C-1에서 고친 근본 원인을 다시 재현하는 것이다.

**수정안:**

```markdown
# 변경 전 (CHANGELOG.md line 51-55)
1. **Playwright 설치 확인**
   ```bash
   npm install -g playwright
   npx playwright install chromium
   ```

# 변경 후
1. **Playwright 설치 확인**
   `/audit` 실행 시 `_audit/` 폴더에 자동 설치됩니다. 별도 설치 불필요.
   (직접 설치하려면: `cd _audit && npm install playwright && npx playwright install chromium`)
```

---

### I-2. `--full` 옵션이 "완전 자동"이 아님 — 단기 수정

**현재 상태:** 완료
([skills/audit/SKILL.md](./skills/audit/SKILL.md)에서 기본 분석 목적을
`기존 사이트 역설계 및 리뉴얼 기획 참고`로 고정)

**위치:**
- [SETUP-GUIDE.md:189-195](./SETUP-GUIDE.md#L189) — "Step 0~6 순차 자동 실행"
- [skills/audit/SKILL.md:39-57](./skills/audit/SKILL.md#L39) — target.md 템플릿

**문제:**
`--full` 실행 시에도 `target.md` 생성 과정에서 아래 항목이 포함된다.

```markdown
- **분석 목적:** (사용자에게 질문)
```

이 한 줄 때문에 Step 0에서 LLM이 AskUserQuestion을 호출하거나 잠시 멈출 가능성이 있다.
"무중단 자동 파이프라인"과 "중간 질의"가 같은 경로에 공존하는 것이다.

**현재 상태 정확히 말하면:**
- `--full` 플래그를 처리하는 분기는 있음 (SKILL.md Step 1~4 안내 부분)
- 그러나 Step 0의 target.md 생성은 플래그와 무관하게 동일하게 수행됨
- "분석 목적: (사용자에게 질문)" 항목은 LLM에게 힌트를 주는 형태라, `--full`에서도 질문할 수 있음

**수정 선택지 (중 하나 선택):**

| 방법 | 장점 | 단점 |
|------|------|------|
| A. `--purpose` 옵션 추가 | 의도 명확, CLI 표준 패턴 | 인터페이스 변경 |
| B. `--full`일 때 기본값("리뉴얼 기획 참고") 사용 | 뒤로 호환 | 목적이 모호할 수 있음 |
| C. target.md에서 질문 항목 제거 | 가장 단순 | 목적 정보 손실 |

추천: **B안** — `--full` 감지 시 분석 목적을 "기존 사이트 역설계 및 리뉴얼 기획 참고"로 기본 채움.

---

### I-3. 상태 관리가 Markdown 표 중심 — 중기 설계 결정

**현재 상태:** 완료
(`_agency/status.json`을 진실 원본으로 도입했고,
`_agency/status.md`는 보기용 뷰로 재정의됨)

**위치:**
- [agency-ai-agent-plan.md:42-107](./agency-ai-agent-plan.md#L42)
- [skills/audit/SKILL.md:118-132](./skills/audit/SKILL.md#L118)

**현재 구조:**
```markdown
# _agency/status.md 형태
| 단계 | 스킬 | 상태 | 완료일 |
|------|------|------|--------|
| 1. 기획 | /pm | ✅ 완료 | 2026-04-02 |
| 2. 디자인 | /design | ⏳ 대기 | - |
```

LLM이 이 표를 자연어로 읽어서 `✅` 여부를 판단하는 방식이다.

**실제 위험:**
지금까지는 단순한 선형 파이프라인이라 크게 문제없었다. 하지만 다음 상황에서 게이트가 오동작할 수 있다:

1. **부분 완료**: FE 일부만 구현했지만 `✅`로 표시되어 QA 게이트 통과 (SESSION-REPORT M-3에서 수정했지만, Markdown 표 방식 자체가 구조적으로 취약)
2. **병렬 작업 충돌**: FE/BE 동시 실행 시 두 세션이 status.md를 동시에 쓰면 표가 깨질 수 있음
3. **재실행 판단**: "이미 완료된 단계를 덮어써야 하는가"를 LLM이 자연어로 판단해야 함

**제안 방향:**
```json
// _agency/status.json (진실 원본)
{
  "version": "2.0",
  "updated": "2026-04-02",
  "stages": {
    "pm":       { "status": "done", "completed_at": "2026-04-02" },
    "design":   { "status": "pending" },
    "contract": { "status": "pending" },
    "fe":       { "status": "partial", "completed_steps": 2, "total_steps": 5 },
    "be":       { "status": "pending" },
    "qa":       { "status": "blocked", "reason": "fe_incomplete" },
    "devops":   { "status": "pending" }
  }
}
```

Markdown 표(`status.md`)는 JSON에서 자동 생성된 **읽기 전용 뷰**로 유지한다.

**결정 필요 사항:**
- 전환할 의향이 있는가? (있다면 모든 스킬의 status 읽기/쓰기 로직을 수정해야 함)
- 또는 현재 Markdown 방식을 유지하되, 게이트 판단 기준을 더 엄격하게 명시하는 선에서 개선할 것인가?

---

### I-4. install.sh가 SKILL.md 단일 파일만 복사 — 중기 수정

**현재 상태:** 완료
([install.sh](./install.sh)에서 `rsync` 기반 디렉터리 복사로 전환됨)

**위치:** [install.sh:29-35](./install.sh#L29)

**현재 코드:**
```bash
for skill_dir in "$SKILLS_SRC"/*/; do
  skill_name=$(basename "$skill_dir")
  dest="$SKILLS_DEST/$skill_name"
  mkdir -p "$dest"
  cp "$skill_dir/SKILL.md" "$dest/SKILL.md"  # ← SKILL.md만 복사
done
```

**문제:**
현재 스킬은 모두 `SKILL.md` 단일 파일이라 괜찮다. 하지만 앞으로 스킬이 아래를 참조하기 시작하면 설치가 깨진다:
- `skills/audit/templates/target.md.tpl`
- `skills/pm/references/rate-card.md`
- `skills/fe/scripts/scaffold.sh`

**수정안 (2가지):**

**A. 폴더 전체 복사 (즉시 적용 가능):**
```bash
# cp 한 줄을 rsync로 교체
rsync -a --exclude='._*' "$skill_dir" "$dest/"
```

**B. manifest 방식 (장기):**
각 스킬에 `manifest.yaml` 추가:
```yaml
# skills/audit/manifest.yaml
name: audit
files:
  - SKILL.md
  - templates/
```
install.sh는 manifest를 읽어 필요한 파일만 복사.

추천: **A안** 먼저 적용, 스킬 복잡도 증가 시 B안으로 전환.

---

### I-5. 문서 일관성 자동 검사 없음 — 중기 구축

**현재 상태:** 완료
([scripts/lint-docs.sh](./scripts/lint-docs.sh) 추가, [install.sh](./install.sh)에서 자동 실행)

**배경:**
이번 SESSION-REPORT.md가 보여주듯, `/qa` vs `/qa-check`, `@` vs `/`, Playwright 설치 모델 같은 문제는 대규모 수동 검토에서 잡혔다. 같은 종류의 오류가 반복 발생하고 있다.

**제안: `scripts/lint-docs.sh` 추가**

```bash
#!/bin/bash
# 문서 일관성 검사
set -e
ERRORS=0

# 1. 잘못된 slash command 참조 검사 (존재하지 않는 스킬명)
VALID_SKILLS="webstart pm design contract fe be qa-check devops audit audit-ux audit-ia audit-tech audit-db"
for skill in $VALID_SKILLS; do
  # 스킬 파일 존재 확인
  [ -f "skills/$skill/SKILL.md" ] || echo "[ERROR] skills/$skill/SKILL.md 없음"
done

# 2. CHANGELOG에 전역 playwright 설치 안내 잔존 여부
if grep -r "npm install -g playwright" CHANGELOG.md 2>/dev/null; then
  echo "[ERROR] CHANGELOG에 전역 playwright 설치 안내 발견"
  ERRORS=$((ERRORS+1))
fi

# 3. 스킬 파일에 @command 방식 잔존 여부
if grep -r "@pm\|@design\|@fe\|@be\|@qa\|@devops" skills/ 2>/dev/null; then
  echo "[ERROR] @command 방식 발견 (/ 방식으로 변경 필요)"
  ERRORS=$((ERRORS+1))
fi

# 4. /qa (잘못된 스킬명) 참조 여부
if grep -rn "next.*\/qa[^-]" skills/ 2>/dev/null; then
  echo "[ERROR] 존재하지 않는 /qa 참조 발견 (/qa-check 사용)"
  ERRORS=$((ERRORS+1))
fi

[ $ERRORS -eq 0 ] && echo "✅ 문서 일관성 검사 통과" || exit 1
```

이 스크립트를 `bash scripts/lint-docs.sh` 또는 `bash install.sh` 직후 자동 실행하는 방식으로 통합할 수 있다.

---

### I-6. webstart 소개 문구 미반영 — 즉시 수정

**현재 상태:** 완료
([skills/webstart/SKILL.md](./skills/webstart/SKILL.md) 및 [README.md](./README.md)에 반영)

**위치:** [skills/webstart/SKILL.md:4-7](./skills/webstart/SKILL.md#L4)

**현재 내용:**
```
description: |
  1인 웹 에이전시 AI 에이전트 시스템 자동 세팅.
  새 프로젝트 폴더에서 /webstart를 실행하면
  6개 에이전트(PM, 디자이너, FE, BE, QA, DevOps) 역할에 맞는
```

**문제:**
`6개 에이전트`는 v1.0 기준이다. 현재 시스템은 **제작 8개 + 검수 5개 = 13개 스킬**이다. 사용자가 `/webstart`를 처음 발견했을 때 보는 설명이라 첫인상에 영향을 주고, 검색·자동 완성에서도 불리하다.

**수정안:**
```markdown
description: |
  1인 웹 에이전시 AI 에이전트 시스템 자동 세팅.
  새 프로젝트 폴더에서 /webstart를 실행하면
  13개 에이전트(제작 8개 + 검수 5개) 시스템에 맞는
  CLAUDE.md, 템플릿 파일, 폴더 구조를 자동으로 생성합니다.
```

---

## 당시 수정 경로 추천

아래 내용은 **검토 당시**의 실행 제안 기록이다.
현재 저장소 기준으로는 이미 대부분 반영 완료된 항목이다.

### 즉시 (30분 이내, 당시 기준)

1. **I-1** — CHANGELOG.md line 51-55 수정 (3줄 교체)
2. **I-6** — skills/webstart/SKILL.md line 4-7 수정 (1줄 교체)

### 단기 (1~2시간, 당시 기준)

3. **I-4A** — install.sh의 `cp` → `rsync` 교체 (1줄 교체)
4. **I-2B** — audit/SKILL.md Step 0에서 `--full` 감지 시 분석 목적 기본값 채움

### 중기 (설계 결정 필요, 당시 기준)

5. **I-5** — `scripts/lint-docs.sh` 신규 작성 (약 40줄)
6. **I-3** — status.json 도입 여부 결정 후 전체 스킬 수정 (대형 작업)

---

## 파일별 영향 범위

아래 표도 **검토 당시 예상 범위**이며, 현재는 실제 반영 결과와 다를 수 있다.

| 파일 | 관련 이슈 | 수정량 |
|------|----------|--------|
| `CHANGELOG.md` | I-1 | 소 (5줄) |
| `skills/webstart/SKILL.md` | I-6 | 소 (1줄) |
| `install.sh` | I-4 | 소 (1줄) |
| `skills/audit/SKILL.md` | I-2 | 중 (Step 0 분기 추가) |
| `scripts/lint-docs.sh` | I-5 | 신규 (~40줄) |
| 전체 스킬 파일 (14개) | I-3 | 대 (설계 확정 후) |
