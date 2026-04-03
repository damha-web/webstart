# 1인 웹 에이전시 AI 시스템 — 설치 및 사용 가이드

> 이 파일 하나로 새 컴퓨터에서 동일한 환경을 완전히 재현할 수 있습니다.
> 버전: v2.2 (제작 + 검수 파이프라인)
> 최종 업데이트: 2026-04-03

---

## 시스템 개요

1인 웹 에이전시를 위한 AI 에이전트 시스템. 두 개의 독립 파이프라인으로 구성.

```
[검수 파이프라인]                    [제작 파이프라인]
기존 사이트 분석·역설계             신규 사이트 기획·제작·배포

/audit → /audit-ux                 /webstart
       → /audit-ia                 /pm → /design → /contract
       → /audit-tech                              → /fe + /be
       → /audit-db                                → /qa-check
       → client-brief.md ──────→ /pm 인계          → /devops
```

**전체 스킬 목록 (13개)**

| 구분 | 스킬 | 역할 |
|------|------|------|
| 제작 | `/webstart` | 프로젝트 초기 세팅 |
| 제작 | `/pm` | 기획, 페르소나, 사이트맵, 견적서 |
| 제작 | `/design` | 디자인 시스템 (컬러, 타이포, 컴포넌트) |
| 제작 | `/contract` | API 계약 확정 (FE/BE 병렬 전) |
| 제작 | `/fe` | 프론트엔드 UI 코드 |
| 제작 | `/be` | 백엔드 API, DB 스키마 |
| 제작 | `/qa-check` | QA 체크리스트, 버그 리포트 |
| 제작 | `/devops` | 배포 설정, 납품 문서 |
| 검수 | `/audit` | 검수 오케스트레이터 |
| 검수 | `/audit-ux` | UI/UX 리서치 (컬러, 폰트, 컴포넌트) |
| 검수 | `/audit-ia` | 정보 구조 분석 (사이트맵, IA) |
| 검수 | `/audit-tech` | 기술 스택 진단 (프레임워크, 성능) |
| 검수 | `/audit-db` | 데이터 구조 유추 (ERD, API) |

---

## 사전 준비

| 항목 | 확인 방법 | 설치 명령 |
|------|----------|----------|
| Node.js 18+ | `node --version` | https://nodejs.org |
| Python 3.10+ (고급 검수 런타임) | `python3 --version` | https://python.org |
| Claude Code CLI | `claude --version` | `npm install -g @anthropic-ai/claude-code` |
| Playwright (검수 파이프라인 필수) | `~/.webstart/bin/webstart-audit doctor` | `install.sh`가 공용 audit runtime과 함께 설치 |
| Git | `git --version` | https://git-scm.com |

---

## 설치 방법

### 새 컴퓨터에 처음 설치

```bash
# 1. 저장소 클론
git clone https://github.com/본인계정/WebStart.git
cd WebStart

# 2. 스킬 설치 (13개 스킬을 ~/.claude/skills/에 복사)
bash install.sh

# 3. install.sh 는 공용 audit runtime(~/.webstart)도 함께 설치합니다.
#    건너뛰려면: bash install.sh --skip-audit-runtime

# 4. Playwright Chromium은 공용 audit runtime 설치 과정에서 함께 준비됩니다.

# 5. Claude Code 재시작
# Claude Code를 종료하고 다시 실행하면 스킬이 인식됩니다.
```

### 기존 설치 업데이트

```bash
cd WebStart
git pull
bash install.sh
```

### 설치 확인

```bash
# Claude Code 실행 후 아래 명령이 동작하면 성공
/webstart test-project nextjs    # → 프로젝트 세팅 완료 (확인 후 rm -rf test-project/ 로 삭제)
/audit https://example.com       # → 검수 대상 등록 및 Step 0 실행
~/.webstart/bin/webstart-audit doctor  # → 고급 검수 런타임 설치 확인
```

### 고급 검수 런타임 빠른 확인

```bash
~/.webstart/bin/webstart-audit init --project-dir .
~/.webstart/bin/webstart-audit crawl https://example.com --project-dir . --max-pages 8 --max-depth 2
~/.webstart/bin/webstart-audit ux-scan --project-dir .
~/.webstart/bin/webstart-audit ia-scan --project-dir .
~/.webstart/bin/webstart-audit tech-scan --project-dir .
~/.webstart/bin/webstart-audit api-scan --project-dir .
~/.webstart/bin/webstart-audit report-draft --project-dir .
```

---

## 사용법 A — 신규 사이트 제작 (제작 파이프라인)

### 전체 흐름

```
/webstart 프로젝트명 nextjs
    ↓
client-brief.md 작성
    ↓
/pm → /design → /contract → /fe + /be → /qa-check → /devops
```

### 단계별 사용법

**1. 프로젝트 생성**

```
/webstart kim-interior nextjs
```

프로젝트 폴더와 템플릿 파일이 자동 생성됩니다.
지원 스택: `nextjs` (기본) / `php`

**2. 클라이언트 브리프 작성**

생성된 `_agency/client-brief.md` 파일을 열어 클라이언트 정보를 채웁니다.
상태 파일은 `_agency/status.json`이 원본이며, `_agency/status.md`는 보기용으로 자동 갱신됩니다.

**3. PM 기획**

```
/pm
```

client-brief.md를 읽고 페르소나, 사이트맵, 세일즈 카피, 견적서를 `_agency/sitemap.md`에 저장합니다.

**4. 디자인**

```
/design
```

PM 기획안을 바탕으로 디자인 시스템을 `_agency/design-system.md`에 저장합니다.
게이트: PM 완료 필요

**5. API 계약 확정**

```
/contract
```

FE/BE 병렬 개발 전 공통 계약(ERD, API, 공유 타입)을 `_agency/contract.md`에 확정합니다.
게이트: Design 완료 필요

**6. FE/BE 병렬 개발**

```
/fe Hero 섹션 만들어줘
/be 문의폼 API 만들어줘
```

Contract 완료 후 병렬 실행 가능. 각각 `research.md` → `plan.md` → 코드 순서로 진행합니다.
부분 작업만 끝난 경우 `_agency/status.json`에는 `partial`로 기록되고, plan.md 전체 완료 시에만 `done`으로 올라갑니다.

**7. QA**

```
/qa-check
```

기능, 성능, 접근성, 보안 체크리스트와 버그 리포트를 `_agency/qa-report.md`에 저장합니다.
게이트: FE + BE 완료 필요. Critical 버그 0개 달성 전 배포 차단.

**8. 배포**

```
/devops
```

Dockerfile, GitHub Actions, 환경변수 목록, 납품 문서를 생성합니다.
게이트: QA 완료 필요

---

## 사용법 B — 기존 사이트 분석 (검수 파이프라인)

### 전체 흐름

```
/audit https://example.com
    ↓
/audit-ux → /audit-ia → /audit-tech → /audit-db
    ↓
종합 보고서 + client-brief.md 자동 생성
    ↓
/pm (제작 파이프라인으로 인계)
```

### 단계별 사용법

**1. 전체 자동 실행 (권장)**

```
/audit --full https://example.com
```

Step 0~6을 순차 자동 실행합니다. Playwright로 데이터를 자동 수집합니다.

**2. 개별 단계 실행 (권장)**

각 스킬을 순서대로 직접 실행합니다. 각 단계는 이전 단계 완료를 자동 확인합니다 (게이트 체크).

```
/audit https://example.com     # Step 0: 대상 등록 + 데이터 수집
/audit-ux                       # Step 1: UX 분석
/audit-ia                       # Step 2: IA 분석
/audit-tech                     # Step 3: 기술 분석
/audit-db                       # Step 4: DB 유추
/audit --step=report            # Step 5~6: 종합 보고서 + 제작팀 인계
```

**3. 특정 단계만 재실행**

이미 일부 단계를 완료한 상태에서 특정 단계만 다시 실행할 때 사용합니다:

```
/audit --step=ux https://example.com   # UX 분석만 재실행
/audit --step=tech https://example.com # 기술 분석만 재실행
/audit --step=report                   # 보고서만 재생성
```

### 산출물

```
_audit/
├── status.md        ← 진행 상태
├── target.md        ← 분석 대상 정보
├── status.json      ← 기계 판정용 상태 원본
├── scraped-data.json ← runtime 호환 수집 데이터
├── raw/
│   ├── crawl-data.json
│   ├── tech-scan.json
│   └── api-scan.json
├── derived/
│   ├── pages.json
│   ├── link-graph.json
│   ├── ux-summary.json
│   ├── ia-summary.json
│   ├── tech-summary.json
│   └── api-summary.json
├── ux-report.md     ← 디자인 토큰, 컴포넌트, 접근성
├── ia-report.md     ← 사이트맵, 사용자 여정, SEO
├── tech-report.md   ← 기술 스택, 성능, 서드파티
├── db-report.md     ← ERD, API 엔드포인트
└── report.md        ← 종합 보고서

_agency/
└── client-brief.md  ← 제작팀 인계용 (자동 생성)
```

### 제작 파이프라인 연계

검수 완료 후 제작 파이프라인으로 자연스럽게 이어집니다:

```
/audit --full https://example.com   # 기존 사이트 분석
                                     # → _agency/client-brief.md 자동 생성
/pm                                  # → client-brief.md 기반 기획 시작
/design                              # → 이후 일반 제작 흐름과 동일
```

추가 연계:
- `/contract` 실행 시 `_audit/db-report.md`의 ERD 초안을 참고 입력으로 활용 가능
- `/qa-check` 실행 시 `_audit/report.md`의 접근성/성능 이슈를 검증 항목에 포함 권장

### 제작 파이프라인 상태 파일

`_agency/status.json`이 게이트 판정용 단일 원본입니다.
`_agency/status.md`는 사람이 읽는 표 뷰이며, 각 스킬이 status.json을 기준으로 다시 생성합니다.

상태 값은 아래 네 가지를 사용합니다:
- `pending`: 아직 시작 전
- `partial`: 일부만 완료됨
- `done`: 완료
- `blocked`: 차단됨

---

## 신뢰도 체계 (검수 파이프라인)

검수 보고서의 모든 분석 항목에는 아래 신뢰도가 표기됩니다.

| 상태 | 의미 | 후속 조치 |
|------|------|----------|
| `Confirmed` | HTML/CSS/네트워크에서 직접 확인 | 그대로 사용 가능 |
| `Likely` | 복수 간접 근거 일치 | 대부분 신뢰 가능, 주의 사항 확인 |
| `Hypothesis` | 단일 근거 기반 추론 | 클라이언트 확인 필요 |
| `Unknown` | 증거 부족 | 반드시 추가 조사 필요 |

### 입력 게이트 (`/audit-db`)

`/audit-db`는 `/audit-tech`에서 수집한 API 호출 증거에 따라 산출물 품질이 달라집니다:

- **API 증거 충분** → 정상 분석 (Confirmed/Likely 항목 포함)
- **API 증거 부족/없음** → Hypothesis 한정 모드 (모든 항목 Hypothesis로 제한)

---

## 보안 정책 (검수 파이프라인)

외부 사이트 분석 시 준수해야 할 운영 원칙:

| 규칙 | 설명 |
|------|------|
| 공개 페이지 한정 | 로그인/결제/관리자 화면은 사용자 명시 승인 없이 분석 금지 |
| 인증 정보 미저장 | 쿠키, 세션 토큰, API 키 자동 필터 |
| PII 마스킹 | 이메일, 전화번호 자동 마스킹 후 저장 |
| Rate limit 준수 | 페이지 간 최소 1초 대기 |
| robots.txt 준수 | 대상 사이트 정책 위반 금지 |

---

## 폴더 구조

```
WebStart/
├── SETUP-GUIDE.md                ← 본 문서 (설치 및 사용 가이드)
├── CHANGELOG.md                  ← 버전별 변경 이력
├── agency-ai-agent-plan.md       ← 제작 파이프라인 설계 문서
├── web-audit-agent-plan.md       ← 검수 파이프라인 설계 문서
├── install.sh                    ← 자동 설치 스크립트
├── skills/
│   ├── webstart/SKILL.md         ← 프로젝트 초기 세팅
│   ├── pm/SKILL.md               ← 기획
│   ├── design/SKILL.md           ← 디자인
│   ├── contract/SKILL.md         ← API 계약
│   ├── fe/SKILL.md               ← 프론트엔드
│   ├── be/SKILL.md               ← 백엔드
│   ├── qa-check/SKILL.md         ← QA
│   ├── devops/SKILL.md           ← 배포
│   ├── audit/SKILL.md            ← 검수 오케스트레이터
│   ├── audit-ux/SKILL.md         ← UX 분석
│   ├── audit-ia/SKILL.md         ← IA 분석
│   ├── audit-tech/SKILL.md       ← 기술 분석
│   └── audit-db/SKILL.md         ← DB 유추
└── test-project/                 ← 테스트용 예제
```

---

## Claude.ai Projects 설정 (선택)

**제작 파이프라인만 지원**합니다. 검수 파이프라인(/audit, /audit-ux 등)은 Claude Code CLI 사용을 권장합니다.
claude.ai 웹에서 제작 파이프라인을 사용하려면 아래 Projects를 설정합니다.

### [PM] 기획 프로젝트

**Project Instructions:**
```
너는 10년 차 수석 웹 서비스 기획자이자 퍼포먼스 마케터야.

## 역할
1. 클라이언트 정보를 입력받으면 타겟 고객 페르소나를 3개 이내로 정의하고, 각 페르소나의 핵심 고민과 구매 동기를 분석해.
2. 전환율(CVR)을 높이는 세일즈 카피와 직관적인 사이트맵을 작성해.
3. 프로젝트 범위와 기능 목록을 기반으로 견적서와 제안서 초안을 표 형태로 작성해.

## 출력 기준
- 모든 기획안은 표와 체크리스트로 정리
- SEO 핵심 키워드 반드시 포함
- 견적은 기능별로 공수(시간)와 금액을 분리

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

### [Design] 디자인 프로젝트

**Project Instructions:**
```
너는 트렌드를 선도하는 시니어 UX/UI 디자이너야.

## 역할
1. 기획안을 바탕으로 페이지별 레이아웃을 텍스트로 상세히 묘사해.
2. 디자인 시스템을 표 형태로 제시해:
   - 컬러 팔레트 (Primary~Semantic) + HEX 코드
   - 타이포그래피 스케일 (H1~Caption)
   - 핵심 컴포넌트 상태 (Default, Hover, Disabled)
   - 간격 시스템 (4px 배수)
3. 다크모드 색상 쌍도 함께 정의해.

## 출력 기준
- 프론트엔드 개발자가 즉시 코딩 가능한 수준
- shadcn/ui + Tailwind CSS 변수 기준
- WCAG 2.1 AA 접근성 체크리스트 포함

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

### [FE] 프론트엔드 프로젝트

**Project Instructions:**
```
너는 시니어 프론트엔드 개발자야.
스택: Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui

## 코드 기준
- TypeScript strict, any 금지
- 모바일 first 반응형 (sm → md → lg)
- next/image, next/link 사용
- Lighthouse 90+ 목표

## 출력 기준
- 즉시 실행 가능한 완성 코드
- 파일 경로를 코드 상단 주석에 명시

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

### [BE] 백엔드 프로젝트

**Project Instructions:**
```
너는 시니어 백엔드 개발자이자 서버 아키텍트야.
스택: Supabase (PostgreSQL + Auth) + Next.js API Routes + TypeScript

## 역할
1. ERD를 표 형태로 설계
2. API 명세서 작성 (Endpoint, Method, Request, Response, Error)
3. Supabase RLS 정책과 인증 플로우 체크리스트 제공

## 코드 기준
- TypeScript strict, any 금지
- 모든 입력값 zod 서버사이드 validation
- API 응답 { data, error, status } 구조

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

### [QA] 테스트 프로젝트

**Project Instructions:**
```
너는 시니어 QA 엔지니어야.

## 테스트 기준
- 브라우저: Chrome, Safari, Firefox 최신
- 디바이스: Desktop (1920/1280px), Tablet (768px), Mobile (375/390px)
- 접근성: WCAG 2.1 AA
- 성능: Lighthouse 90+

## 출력 기준
- 테스트 항목, 기대/실제 결과, 통과/실패, 심각도 (Critical/Major/Minor)
- Critical 버그는 최상단 별도 섹션

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

### [DevOps] 배포 프로젝트

**Project Instructions:**
```
너는 DevOps 엔지니어야.
배포 환경: Vercel / Fly.io (Docker) / Synology NAS

## 역할
1. 배포 파이프라인 체크리스트 제공
2. Dockerfile, GitHub Actions, 환경변수 목록 완성형 제공
3. 도메인/SSL/CDN 설정 가이드

## 출력 기준
- 즉시 사용 가능한 설정 파일
- 롤백 방법 항상 함께 제공

## 글로벌 규칙
- 한국어 작성 (코드·기술용어는 영어 유지)
- 한자 사용 금지
```

---

## 문제 해결

### Playwright 관련

| 문제 | 해결 |
|------|------|
| `~/.webstart/bin/webstart-audit` 실행 안 됨 | `bash install.sh` 재실행 후 `~/.webstart/bin/webstart-audit doctor` 로 확인 |
| Chromium 다운로드 실패 | 네트워크 확인 후 재시도. 프록시 환경이면 `HTTPS_PROXY` 설정 |
| 스크래핑 타임아웃 | 대상 사이트 응답 느림. `_audit/target.md`에 수동 데이터 입력 후 진행 |

### 스킬 인식 안 됨

```bash
# 스킬 파일 위치 확인
ls ~/.claude/skills/

# 재설치
cd WebStart
bash install.sh

# Claude Code 완전 재시작
```

### 게이트 차단

각 스킬은 선행 단계 완료를 확인합니다. 차단 시:

```bash
# 상태 파일 확인
cat _agency/status.json # 제작 파이프라인 원본
cat _agency/status.md   # 제작 파이프라인 보기용
cat _audit/status.md    # 검수 파이프라인
```

선행 단계를 먼저 실행하면 해결됩니다.

---

## 참고 문서

| 문서 | 내용 |
|------|------|
| [agency-ai-agent-plan.md](./agency-ai-agent-plan.md) | 제작 파이프라인 설계 |
| [web-audit-agent-plan.md](./web-audit-agent-plan.md) | 검수 파이프라인 설계 |
| [CHANGELOG.md](./CHANGELOG.md) | 버전별 변경 이력 |
| [AUDIT-AUTOMATION-V3.md](./AUDIT-AUTOMATION-V3.md) | audit runtime 확장 설계 메모 |
| [IMPROVEMENT-REPORT.md](./IMPROVEMENT-REPORT.md) | 후속 개선점 정리 |
| [REVIEW-REPORT.md](./REVIEW-REPORT.md) | 1차 전수 검토 결과 |
| [REVIEW-REPORT-V2.md](./REVIEW-REPORT-V2.md) | 2차 전수 검토 결과 |
| [SESSION-REPORT.md](./SESSION-REPORT.md) | 세션 작업 기록 |

위 다섯 문서는 사용자 사용 설명서가 아니라 repo 내부 의사결정과 작업 기록용 문서로 유지합니다.
