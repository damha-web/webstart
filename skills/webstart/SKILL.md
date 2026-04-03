---
name: webstart
description: |
  1인 웹 에이전시 AI 에이전트 시스템 자동 세팅.
  새 프로젝트 폴더에서 /webstart를 실행하면
  13개 에이전트(제작 8개 + 검수 5개) 시스템에 맞는
  CLAUDE.md, 템플릿 파일, 폴더 구조를 자동으로 생성합니다.
  인수(args)로 프로젝트 이름과 기술 스택을 지정할 수 있습니다.
  예: /webstart my-client nextjs
      /webstart my-client php
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - AskUserQuestion
---

## 에이전시 에이전트 시스템 세팅

다음 단계로 현재 작업 디렉토리에 1인 웹 에이전시 AI 에이전트 시스템을 세팅합니다.

### Step 1 — 인수 파싱 및 확인

args에서 프로젝트 이름과 스택을 파싱합니다.
- 첫 번째 인수: 프로젝트 이름 (없으면 현재 폴더명 사용)
- 두 번째 인수: 스택 선택 (`nextjs` | `php`) — 기본값 `nextjs`

인수가 없으면 AskUserQuestion으로 아래 두 가지를 질문합니다:
1. 프로젝트 이름 (영문, 예: kim-interior)
2. 기술 스택 (nextjs / php / 미정)

### Step 2 — 폴더 구조 생성

현재 디렉토리 아래에 다음 구조를 생성합니다:

```
{project-name}/
├── CLAUDE.md                  ← 프로젝트 전역 에이전트 규칙
├── _agency/
│   ├── client-brief.md        ← 클라이언트 브리프 입력 템플릿 (webstart 생성)
│   ├── status.json            ← 파이프라인 상태 원본 (webstart 생성, 각 스킬 업데이트)
│   ├── status.md              ← 사람이 읽는 상태 뷰 (status.json 기준으로 갱신)
│   ├── sitemap.md             ← /pm 산출물
│   ├── design-system.md       ← /design 산출물
│   ├── contract.md            ← /contract 산출물
│   ├── api-spec.md            ← /be 산출물
│   ├── qa-report.md           ← /qa-check 산출물
│   └── handover.md            ← /devops 납품 문서
├── research.md                ← 구현 전 분석 (FE/BE 공용)
└── plan.md                    ← 구현 계획 (FE/BE 공용)
```

### Step 3 — CLAUDE.md 생성

선택한 스택에 맞게 CLAUDE.md를 생성합니다.

**nextjs 스택 CLAUDE.md 내용:**

```markdown
# {project-name} — 프로젝트 에이전트 규칙

## 글로벌 규칙
- 모든 답변은 한국어로 작성 (코드·파일명·기술용어는 영어 유지)
- 한자 사용 금지
- 코드는 서론 없이 즉시 복사 가능한 완성형으로 제공
- TypeScript strict 모드, any/unknown 타입 사용 금지
- console.log 디버깅 코드 프로덕션에 남기지 않기
- 하드코딩된 시크릿/API 키 금지 (.env.local 사용)

## 기술 스택
- 프레임워크: Next.js 14 (App Router)
- 언어: TypeScript
- 스타일링: Tailwind CSS + shadcn/ui
- 백엔드/DB: Supabase (PostgreSQL + Auth + Storage)
- 배포: Vercel (기본) / Fly.io / Synology NAS
- 결제: 토스페이먼츠

## 에이전트 역할 가이드

### PM (/pm)
클라이언트 요구사항 분석, 사이트맵, 페르소나, 견적서 작성.
산출물은 _agency/sitemap.md에 저장.

### 디자이너 (/design)
와이어프레임, 디자인 시스템(컬러·타이포·컴포넌트) 정의.
산출물은 _agency/design-system.md에 저장.

### Contract (/contract)
FE/BE 병렬 개발 전 API 엔드포인트, ERD, 공유 타입 확정.
산출물은 _agency/contract.md에 저장.

### 프론트엔드 (/fe)
디자인 시스템 기반 반응형 UI 컴포넌트 작성.
구현 전 research.md → plan.md 순서로 작성 후 진행.
모바일 first (sm → md → lg), Lighthouse 90+ 목표.

### 백엔드 (/be)
ERD 설계, API 명세서 작성, Supabase RLS 설정.
산출물은 _agency/api-spec.md에 저장.
모든 입력값 zod로 서버사이드 validation.

### QA (/qa-check)
기능 테스트 시나리오 작성, QA 리포트 생성.
산출물은 _agency/qa-report.md에 저장.
Critical 버그 0개 달성 전 배포 금지.

### DevOps (/devops)
Dockerfile, GitHub Actions 워크플로우, 환경변수 목록 제공.
NAS 배포 시 ~/.claude/nas-hosting-guide.md 준수.

## 파이프라인 순서
1. /pm → 기획·견적 → 클라이언트 승인
2. /design → 디자인 시스템
3. /contract → API 계약 확정
4. /fe + /be 병렬 진행
5. /qa-check → QA 리포트 → 버그 수정
6. /devops → 배포
```

**php 스택 CLAUDE.md 내용 (php 선택 시):**

위와 동일하되 기술 스택 섹션만 다음으로 교체:

```markdown
## 기술 스택
- 프레임워크: Laravel 11 (API) / WordPress (CMS형)
- 언어: PHP 8.x + TypeScript (프론트)
- 스타일링: Tailwind CSS
- 데이터베이스: MySQL 8.x
- 배포: Fly.io (Docker) / Synology NAS
- 결제: 토스페이먼츠
```

### Step 4 — 템플릿 파일 생성

**_agency/client-brief.md:**

```markdown
# 클라이언트 브리프

> 이 파일을 채운 뒤 /pm 을 실행하세요.

## 기본 정보
- **업종:** 
- **회사명/브랜드명:** 
- **담당자:** 

## 프로젝트 목표
- **핵심 목표:** (예: 포트폴리오 전시 + 상담 문의 증가)
- **성공 기준:** (예: 월 문의 10건 이상)

## 타겟 고객
- **연령/성별:** 
- **지역:** 
- **관심사/고민:** 

## 예산 및 일정
- **예산 범위:** 
- **희망 완성일:** 
- **시간당 단가:** (예: 50,000원)

## 필수 기능 (해당 항목에 체크)
- [ ] 메인 홈페이지
- [ ] 포트폴리오/갤러리
- [ ] 서비스 소개
- [ ] 팀/회사 소개
- [ ] 블로그/뉴스
- [ ] 문의 폼
- [ ] 로그인/회원가입
- [ ] 관리자 페이지
- [ ] 결제 기능
- [ ] 다국어 지원
- [ ] 기타: 

## 보유 자료
- [ ] 로고 파일 보유
- [ ] 사진/이미지 보유
- [ ] 카피라이팅(텍스트) 보유
- [ ] 참고 사이트: 

## 추가 요청사항
```

**_agency/status.json:**

```json
{
  "version": "2.2",
  "updated_at": "-",
  "stages": {
    "pm": { "label": "PM", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/sitemap.md"] },
    "design": { "label": "Design", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/design-system.md"] },
    "contract": { "label": "Contract", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/contract.md"] },
    "fe": { "label": "FE", "status": "pending", "completed_at": null, "notes": "", "artifacts": [] },
    "be": { "label": "BE", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/api-spec.md"] },
    "qa": { "label": "QA", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/qa-report.md"] },
    "devops": { "label": "DevOps", "status": "pending", "completed_at": null, "notes": "", "artifacts": ["_agency/handover.md"] }
  }
}
```

**_agency/status.md:**

```markdown
# 프로젝트 파이프라인 상태

> 이 파일은 사람이 읽는 뷰입니다. 실제 게이트 판정과 업데이트는 _agency/status.json 기준으로 진행합니다.

| 단계 | 상태 | 완료일 | 비고 |
|------|------|--------|------|
| PM | ⏳ 대기 | - | - |
| Design | ⏳ 대기 | - | - |
| Contract | ⏳ 대기 | - | - |
| FE | ⏳ 대기 | - | - |
| BE | ⏳ 대기 | - | - |
| QA | ⏳ 대기 | - | - |
| DevOps | ⏳ 대기 | - | - |
```

### Step 5 — 완료 메시지 출력

생성된 파일 목록과 다음 실행 방법을 표로 출력합니다:

| 다음 단계 | 명령 |
|----------|------|
| 1. 클라이언트 정보 입력 | `_agency/client-brief.md` 파일을 편집 |
| 2. PM 기획 | `/pm` |
| 3. 디자인 시스템 | `/design` |
| 4. API 계약 확정 | `/contract` |
| 5. 개발 시작 | `/fe` 또는 `/be` (병렬 가능) |
| 6. QA | `/qa-check` |
| 7. 배포 | `/devops` |
