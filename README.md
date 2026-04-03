# WebStart

1인 웹사이트 제작 에이전시를 위한 AI 에이전트 시스템입니다.

이 프로젝트는 두 가지 일을 합니다.

1. 새 웹사이트 제작 프로젝트를 빠르게 시작하게 해줍니다.
2. 기존 웹사이트를 분석해서, 리뉴얼용 기획 입력값으로 바꿔줍니다.

즉, "만드는 팀"과 "분석하는 팀"을 모두 갖춘 웹 에이전시 운영용 툴킷입니다.

---

## 한눈에 보기

- 총 13개 스킬로 구성됩니다.
- 제작 파이프라인 8개, 검수 파이프라인 5개입니다.
- Claude Code CLI 기준으로 설계되었습니다.
- 검수 파이프라인은 공용 `audit runtime`을 사용합니다.
- 설치는 기본적으로 `bash install.sh` 한 번으로 끝납니다.

---

## 이 프로젝트가 해결하는 문제

웹사이트 제작을 AI로 자동화하려고 하면 보통 세 가지가 먼저 꼬입니다.

1. 누가 어떤 순서로 일하는지 정리가 안 됩니다.
2. 기획 없이 디자인이나 개발부터 들어가서 결과물이 흔들립니다.
3. 기존 사이트 분석은 매번 사람 손으로 다시 해야 합니다.

WebStart는 이 문제를 파이프라인으로 해결합니다.

- 제작은 `/pm -> /design -> /contract -> /fe + /be -> /qa-check -> /devops`
- 검수는 `/audit -> /audit-ux -> /audit-ia -> /audit-tech -> /audit-db -> /audit --step=report`

중간 단계가 빠지면 다음 단계가 막히도록 설계되어 있습니다.

---

## 누가 쓰면 좋은가

- 1인 웹사이트 제작자
- 소규모 웹 에이전시
- 기존 사이트를 분석해서 리뉴얼 제안서를 만들어야 하는 사람
- Claude Code 기반으로 반복 작업을 줄이고 싶은 팀

---

## 전체 구조

### 1. 제작 파이프라인

새 프로젝트를 만들고 납품 가능한 상태까지 밀어주는 흐름입니다.

```text
/webstart
  -> /pm
  -> /design
  -> /contract
  -> /fe + /be
  -> /qa-check
  -> /devops
```

핵심 포인트:

- `/contract` 전에는 FE/BE 병렬 작업을 시작하지 않습니다.
- 제작 상태 원본은 `_agency/status.json`입니다.
- `_agency/status.md`는 사람이 읽는 뷰입니다.
- FE/BE는 부분 작업이면 `partial`, QA는 차단 상태면 `blocked`를 기록합니다.

### 2. 검수 파이프라인

기존 사이트를 분석해서 리뉴얼 기획 입력값으로 바꾸는 흐름입니다.

```text
/audit
  -> /audit-ux
  -> /audit-ia
  -> /audit-tech
  -> /audit-db
  -> report-draft
  -> _agency/client-brief.md 생성
```

핵심 포인트:

- 브라우저 수집과 정형 분석은 `audit runtime`이 담당합니다.
- 결과는 `_audit/` 아래에 저장됩니다.
- 마지막에는 제작 파이프라인 입력 파일인 `_agency/client-brief.md` 초안이 생성됩니다.

---

## 스킬 목록

### 제작 스킬 8개

| 스킬 | 역할 | 주요 산출물 |
|------|------|------------|
| `/webstart` | 프로젝트 초기 세팅 | 폴더 구조, `CLAUDE.md`, `_agency/*` 템플릿 |
| `/pm` | 기획, 페르소나, 사이트맵, 견적 | `_agency/sitemap.md` |
| `/design` | 디자인 시스템, 와이어프레임 | `_agency/design-system.md` |
| `/contract` | FE/BE 공통 계약 확정 | `_agency/contract.md` |
| `/fe` | 프론트엔드 구현 | 코드, `research.md`, `plan.md` |
| `/be` | 백엔드 구현, API 스펙 반영 | 코드, `_agency/api-spec.md` |
| `/qa-check` | 품질 점검, 버그 리포트 | `_agency/qa-report.md` |
| `/devops` | 배포 설정, 납품 문서 | `_agency/handover.md` |

### 검수 스킬 5개

| 스킬 | 역할 | 주요 산출물 |
|------|------|------------|
| `/audit` | 오케스트레이터, 대상 등록, 종합 보고서 | `_audit/target.md`, `_audit/report.md` |
| `/audit-ux` | UI/UX 분석 | `_audit/ux-report.md` |
| `/audit-ia` | 정보 구조 분석 | `_audit/ia-report.md` |
| `/audit-tech` | 기술 스택, 성능 진단 | `_audit/tech-report.md` |
| `/audit-db` | 데이터 구조 유추, API 증거 분석 | `_audit/db-report.md` |

---

## 설치 방법

### 요구 사항

- Node.js 18+
- Python 3.10+
- Git
- Claude Code CLI

확인 예시:

```bash
node --version
python3 --version
git --version
claude --version
```

### 처음 설치

```bash
git clone https://github.com/hyoukj-png/webstart.git
cd WebStart
bash install.sh
```

설치가 하는 일:

1. `skills/`를 `~/.claude/skills/`에 복사
2. `audit-runtime/`을 `~/.webstart/audit-runtime`에 동기화
3. Python venv 생성
4. `~/.webstart/bin/webstart-audit` 생성
5. Playwright Chromium 설치
6. 문서 일관성 검사 실행

runtime 설치를 잠시 건너뛰고 싶다면:

```bash
bash install.sh --skip-audit-runtime
```

### 설치 확인

```bash
~/.webstart/bin/webstart-audit doctor
bash scripts/lint-docs.sh
```

그리고 Claude Code를 재시작합니다.

---

## 빠른 시작

### A. 새 프로젝트 시작

```bash
/webstart kim-interior nextjs
```

이후 순서:

1. `_agency/client-brief.md` 작성
2. `/pm`
3. `/design`
4. `/contract`
5. `/fe`
6. `/be`
7. `/qa-check`
8. `/devops`

### B. 기존 사이트 분석 후 리뉴얼 시작

```bash
/audit --full https://example.com
```

이후 순서:

1. `_agency/client-brief.md` 자동 생성 확인
2. `/pm`
3. `/design`
4. 이후 제작 파이프라인 계속 진행

---

## 설치 후 실제 작업 예시

### 예시 1. 신규 제작 프로젝트

```bash
/webstart law-firm-site nextjs
/pm
/design
/contract
/fe 메인 페이지
/be 문의 API
/qa-check
/devops
```

### 예시 2. 기존 사이트 역설계

```bash
/audit https://example.com
/audit-ux
/audit-ia
/audit-tech
/audit-db
/audit --step=report
/pm
```

---

## 프로젝트 내부 파일 구조

### 루트 구조

```text
WebStart/
├── README.md
├── SETUP-GUIDE.md
├── CHANGELOG.md
├── agency-ai-agent-plan.md
├── web-audit-agent-plan.md
├── install.sh
├── skills/
├── scripts/
└── audit-runtime/
```

### 제작 프로젝트 생성 후 구조

```text
{project-name}/
├── CLAUDE.md
├── _agency/
│   ├── client-brief.md
│   ├── status.json
│   ├── status.md
│   ├── sitemap.md
│   ├── design-system.md
│   ├── contract.md
│   ├── api-spec.md
│   ├── qa-report.md
│   └── handover.md
├── research.md
└── plan.md
```

### `_agency/status.json`이 중요한 이유

제작 파이프라인의 실제 상태 원본입니다.

- 게이트 판정은 이 파일을 기준으로 합니다.
- `status.md`는 보기용으로 재생성됩니다.
- 상태 값은 `pending`, `partial`, `done`, `blocked`를 사용합니다.

예:

```json
{
  "stages": {
    "pm": { "status": "done" },
    "design": { "status": "done" },
    "contract": { "status": "done" },
    "fe": { "status": "partial", "notes": "Hero 섹션만 완료" },
    "be": { "status": "pending" },
    "qa": { "status": "blocked", "notes": "Critical 1개" }
  }
}
```

### 검수 산출물 구조

```text
_audit/
├── target.md
├── status.json
├── status.md
├── scraped-data.json
├── raw/
├── derived/
├── reports/
└── screenshots/
```

---

## `audit runtime`이란?

검수 파이프라인에서 실제 수집과 분석을 담당하는 실행 계층입니다.

Claude 스킬이 하는 일:

- 순서 제어
- 게이트 판정
- 보고서 작성

runtime이 하는 일:

- 브라우저 실행
- 링크 수집
- 페이지 스냅샷 생성
- 기술 스택 지문 수집
- API 응답 흔적 수집
- `_audit/` 구조화 데이터 생성

즉, 스킬은 "생각과 정리", runtime은 "실제 수집"을 담당합니다.

### runtime 명령

```bash
webstart-audit doctor
webstart-audit init --project-dir .
webstart-audit crawl https://example.com --project-dir .
webstart-audit ux-scan --project-dir .
webstart-audit ia-scan --project-dir .
webstart-audit tech-scan --project-dir .
webstart-audit api-scan --project-dir .
webstart-audit report-draft --project-dir .
```

PATH가 안 잡혀 있으면 절대경로로 실행합니다.

```bash
~/.webstart/bin/webstart-audit doctor
```

---

## 스택 지원 범위

### Next.js 스택

- Next.js 14 App Router
- TypeScript
- Tailwind CSS
- shadcn/ui
- Supabase
- Vercel / Fly.io / NAS

### PHP 스택

- Laravel 11 / WordPress
- PHP 8.x
- Tailwind CSS
- MySQL 8.x
- Laravel Sanctum
- Fly.io / NAS

---

## 운영 규칙

### 1. 무조건 순서대로 진행

- `/design` 전에 `/pm`
- `/contract` 전에 `/design`
- `/qa-check` 전에 `/fe`, `/be`
- `/devops` 전에 `/qa-check`

### 2. 재실행 시 downstream 리셋

예를 들어 `/design`을 다시 돌리면, 그 뒤 단계인 `contract`, `fe`, `be`, `qa`, `devops`는 다시 검토 대상이 됩니다.

이 규칙이 중요한 이유:

- 중간 산출물이 바뀌었는데 뒤 단계가 예전 결과를 믿으면 안 되기 때문입니다.

### 3. FE/BE는 부분 완료 허용

예:

- `/fe Hero 섹션`
- `/be 문의 API`

이런 경우 전체 완료가 아니라 `partial`로 기록됩니다.

### 4. QA는 배포 승인 게이트

Critical 버그가 있으면 `blocked`로 기록되고 `/devops`로 넘어가지 않습니다.

---

## Claude.ai Projects와의 관계

이 저장소는 기본적으로 Claude Code CLI 중심입니다.

- 제작 파이프라인은 Claude.ai Projects에 일부 이식 가능합니다.
- 검수 파이프라인은 CLI 사용을 권장합니다.
- 특히 `/audit*` 계열은 `audit runtime`이 필요해서 CLI 쪽이 맞습니다.

---

## 주요 문서 안내

| 파일 | 용도 |
|------|------|
| `README.md` | 프로젝트 전체 소개와 빠른 시작 |
| `SETUP-GUIDE.md` | 자세한 설치/사용 가이드 |
| `CHANGELOG.md` | 버전별 변경 이력 |
| `agency-ai-agent-plan.md` | 제작 파이프라인 설계 |
| `web-audit-agent-plan.md` | 검수 파이프라인 설계 |
| `audit-runtime/README.md` | runtime 운영 문서 |

내부 참고 문서:

| 파일 | 용도 |
|------|------|
| `IMPROVEMENT-REPORT.md` | 개선 후보 정리 |
| `REVIEW-REPORT.md` | 검토 결과 |
| `REVIEW-REPORT-V2.md` | 2차 검토 결과 |
| `SESSION-REPORT.md` | 작업 기록 |
| `AUDIT-AUTOMATION-V3.md` | audit runtime 확장 설계 메모 |

---

## 자주 막히는 지점

### `webstart-audit` 명령이 안 될 때

```bash
~/.webstart/bin/webstart-audit doctor
```

이게 되면 PATH 문제입니다.

### 설치 후 스킬이 안 보일 때

```bash
bash install.sh
```

그리고 Claude Code를 완전히 재시작합니다.

### QA가 안 열릴 때

대부분 `_agency/status.json`에서 FE 또는 BE가 아직 `done`이 아니기 때문입니다.

확인:

```bash
cat _agency/status.json
cat _agency/status.md
```

### 문서/스킬 설명이 서로 다르게 보일 때

```bash
bash scripts/lint-docs.sh
```

이 스크립트가 주요 회귀를 검사합니다.

---

## 추천 읽기 순서

처음 보는 사람이라면 아래 순서를 추천합니다.

1. 이 `README.md`
2. `SETUP-GUIDE.md`
3. `agency-ai-agent-plan.md`
4. `web-audit-agent-plan.md`
5. 필요 시 각 `skills/*/SKILL.md`

---

## 요약

WebStart는 "웹사이트를 만들기 위한 AI 작업 순서"와 "기존 웹사이트를 분석하는 AI 작업 순서"를 하나의 저장소에 정리한 프로젝트입니다.

중요한 포인트는 세 가지입니다.

1. 순서가 강제됩니다.
2. 산출물이 파일로 남습니다.
3. 검수 결과가 다시 제작 입력값으로 이어집니다.

설치 후 바로 시작하려면 이 두 줄이면 됩니다.

```bash
bash install.sh
/webstart my-project nextjs
```

기존 사이트부터 분석하려면:

```bash
bash install.sh
/audit --full https://example.com
```
