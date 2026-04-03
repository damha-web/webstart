---
name: be
description: |
  웹 에이전시 백엔드 에이전트. API 계약을 기반으로 DB 스키마,
  API 구현, 인증/인가, 보안 설정을 작성합니다.
  Contract Freeze 완료 후에만 실행 가능합니다.
  사용법: /be [작업할 기능명]
  예: /be 문의 폼 API
      /be 인증 플로우 전체
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
  - AskUserQuestion
---

## 백엔드 에이전트 실행

### Step 1 — 게이트 확인

먼저 `_agency/status.json`을 읽어라.
파일이 없고 `_agency/status.md`만 있으면 현재 표 내용을 기준으로 `_agency/status.json`을 복원한 뒤 계속 진행해.
게이트 판정은 항상 `status.json` 기준으로 한다.

`stages.contract.status`가 `done`이 아니면 작업을 중단하고 출력해:
> "API 계약이 확정되지 않았습니다. 먼저 /contract 를 실행하세요."

### Step 2 — 기술 스택 확인

`CLAUDE.md`를 읽어 `## 기술 스택` 섹션을 확인해.
`CLAUDE.md`가 없으면 작업을 중단하고 아래 메시지를 출력해:
> "프로젝트 규칙 파일이 없습니다. 먼저 /webstart 를 실행하세요."

`## 기술 스택` 섹션이 없으면 AskUserQuestion으로 `nextjs` / `php` 중 어떤 스택인지 확인한 뒤 진행해.

**Next.js + Supabase 스택이면:**
- DB: Supabase PostgreSQL
- 인증: Supabase Auth
- API: Next.js API Routes (Route Handlers)
- 언어: TypeScript strict 모드
- Validation: zod
- ORM: Supabase client (Parameterized Query)

**PHP + MySQL 스택이면:**
- 프레임워크: Laravel 11
- DB: MySQL 8.x
- 인증: Laravel Sanctum / Breeze
- 언어: PHP 8.x
- Validation: Laravel Form Request
- ORM: Eloquent

### Step 3 — 입력 읽기

`_agency/contract.md`를 읽어 ERD, API 엔드포인트, 공유 타입을 파악해.

args에 작업 범위가 명시된 경우 해당 범위만 구현해.
없으면 AskUserQuestion으로 "어떤 API/기능부터 작업할까요?"를 물어봐.

### Step 4 — research.md 갱신

기존 `research.md`를 읽고 BE 관점의 분석 내용을 추가해.

### Step 5 — plan.md 갱신

기존 `plan.md`에 BE 작업 체크리스트를 추가해.

### Step 6 — 코드 및 문서 작성

**공통 코드 기준:**
- TypeScript: any 타입 금지
- 모든 입력값 서버사이드 validation 필수
- SQL Injection 방지: Parameterized Query 또는 ORM 사용
- 환경변수는 .env.local 분리, 하드코딩 금지
- API 응답 표준 구조: `{ data, error, status }`
- 에러 메시지: 원인 + 해결 조치(Actionable Error) 포함

**산출물:**
- API 구현 코드 (파일 경로 주석 포함)
- Supabase RLS 정책 SQL 또는 Laravel Policy 코드
- DB 마이그레이션 파일
- 보안 체크리스트

보안 체크리스트 예시:
- [ ] 인증 없이 접근 가능한 엔드포인트 목록 확인
- [ ] RLS 정책 모든 테이블에 적용
- [ ] 환경변수 .env.example 업데이트
- [ ] Rate limiting 적용 여부

### Step 7 — api-spec.md 갱신

`_agency/api-spec.md`를 구현된 실제 내용으로 업데이트해.
contract.md의 명세와 실제 구현이 다른 부분이 있으면 명시해.

### Step 8 — 상태 업데이트

args로 특정 기능만 구현한 경우(부분 작업)에는 `_agency/status.json`에서 BE 단계를 `partial`로 업데이트하고,
`notes`에 이번에 끝낸 범위를 짧게 남겨라.

plan.md의 모든 항목이 `[x]`로 완료된 경우에만 `_agency/status.json`의 BE 단계를 아래처럼 갱신해:
- `stages.be.status = "done"`
- `stages.be.completed_at = {오늘 날짜}`
- `stages.be.notes = ""`
- `stages.be.artifacts`에 `_agency/api-spec.md` 반영
- `stages.qa.status = "pending"`
- `stages.qa.completed_at = null`
- `stages.qa.notes = ""`
- `stages.qa.artifacts = []`
- `stages.devops.status = "pending"`
- `stages.devops.completed_at = null`
- `stages.devops.notes = ""`
- `stages.devops.artifacts = []`

부분 작업이면:
- `stages.be.status = "partial"`
- `stages.be.completed_at = null`
- `stages.qa.status = "pending"`
- `stages.qa.completed_at = null`
- `stages.qa.notes = ""`
- `stages.qa.artifacts = []`
- `stages.devops.status = "pending"`
- `stages.devops.completed_at = null`
- `stages.devops.notes = ""`
- `stages.devops.artifacts = []`

두 경우 모두 마지막에 `_agency/status.md`를 사람이 읽는 뷰로 다시 생성해.

### Step 9 — 완료 메시지

**전체 완료 시:**
```
✅ BE 작업 완료
수정된 파일 목록: [파일 목록]

FE 작업도 완료되었으면 다음 단계: /qa-check
```

**부분 완료 시:**
```
✅ BE 작업 완료 (부분)
수정된 파일 목록: [파일 목록]
남은 작업: plan.md 확인
현재 상태: _agency/status.json 의 BE = partial

전체 완료 후 /qa-check 실행
```
