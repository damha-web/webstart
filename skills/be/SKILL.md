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

`_agency/status.md`를 읽어라.
Contract 단계가 ✅ 완료 상태가 아니면 작업을 중단하고 출력해:
> "API 계약이 확정되지 않았습니다. 먼저 /contract 를 실행하세요."

### Step 2 — 기술 스택 확인

`CLAUDE.md`를 읽어 `## 기술 스택` 섹션을 확인해.

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

모든 작업 완료 시 `_agency/status.md`의 BE 단계를 ✅ 완료로 업데이트해.

### Step 9 — 완료 메시지

```
✅ BE 작업 완료
수정된 파일 목록: [파일 목록]

FE 작업도 완료되었으면 다음 단계: /qa
```
