---
name: contract
description: |
  웹 에이전시 Contract Freeze 에이전트.
  FE/BE 병렬 개발 전에 API 엔드포인트, 데이터 모델, 공유 타입을
  확정하고 _agency/contract.md에 저장합니다.
  이 단계 완료 후에만 /fe 와 /be 실행이 허용됩니다.
  사용법: /contract
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
---

## Contract Freeze 에이전트 실행

너는 FE와 BE가 충돌 없이 병렬 개발할 수 있도록 공통 계약을 확정하는 시니어 아키텍트야.

### Step 1 — 게이트 확인

먼저 `_agency/status.json`을 읽어라.
파일이 없고 `_agency/status.md`만 있으면 현재 표 내용을 기준으로 `_agency/status.json`을 복원한 뒤 계속 진행해.
게이트 판정은 항상 `status.json` 기준으로 한다.

`stages.design.status`가 `done`이 아니면 작업을 중단하고 출력해:
> "디자인 시스템이 완료되지 않았습니다. 먼저 /design 을 실행하세요."

### Step 2 — 기술 스택 확인

`CLAUDE.md`를 읽어 `## 기술 스택` 섹션을 확인해.
`CLAUDE.md`가 없으면 작업을 중단하고 아래 메시지를 출력해:
> "프로젝트 규칙 파일이 없습니다. 먼저 /webstart 를 실행하세요."

`## 기술 스택` 섹션이 없으면 AskUserQuestion으로 `nextjs` / `php` 중 어떤 스택인지 확인한 뒤 진행해.
이후 Step 3의 항목 3(타입 정의)을 스택에 맞게 작성한다.

### Step 3 — 입력 읽기

두 파일을 모두 읽어라:
- `_agency/sitemap.md` (기능 목록, 페르소나)
- `_agency/design-system.md` (화면 구조, 컴포넌트 목록)

### Step 4 — 계약 문서 작성

아래 항목을 모두 작성해:

**1. 데이터 모델 (ERD)**

각 엔티티를 표로 정의:

| 필드명 | 타입 | 필수 | 설명 |
|--------|------|------|------|
| id | uuid | Y | PK |
| ... | | | |

**2. API 엔드포인트 목록**

| Method | Endpoint | 설명 | 인증 필요 | Request Body | Response |
|--------|----------|------|----------|--------------|----------|
| GET | /api/... | | Y/N | | |

**3. 공유 타입 정의**

**Next.js 스택이면** TypeScript 타입으로 작성:
```typescript
// types/shared.ts
export type ...
```

**PHP 스택이면** OpenAPI 스펙(YAML)으로 작성:
```yaml
# openapi-types.yaml
components:
  schemas:
    EntityName:
      type: object
      properties:
        id:
          type: string
          format: uuid
```

**4. 상태 코드 및 에러 형식**

표준 에러 응답 구조:
```json
{
  "data": null,
  "error": { "code": "ERROR_CODE", "message": "설명" },
  "status": 400
}
```

에러 코드 목록 표로 정리.

**5. 인증 플로우**

**Next.js 스택이면:**
- 인증 방식: Supabase Auth
- 토큰 갱신 규칙
- 미인증 접근 허용 엔드포인트 목록

**PHP 스택이면:**
- 인증 방식: Laravel Sanctum (API 토큰) 또는 Breeze (세션)
- 미인증 접근 허용 라우트 목록 (routes/api.php 기준)

**6. 범위 밖 기능 (Out of Scope)**
이번 프로젝트에서 구현하지 않는 기능을 명시해.
범위 변경이 생기면 /pm 재승인 후 이 문서를 갱신해야 함.

### Step 5 — 산출물 저장

작성한 내용 전체를 `_agency/contract.md`에 저장해.

### Step 6 — 상태 업데이트

`_agency/status.json`에서 Contract 단계를 아래처럼 갱신해:
- `stages.contract.status = "done"`
- `stages.contract.completed_at = {오늘 날짜}`
- `stages.contract.artifacts`에 `_agency/contract.md` 반영
- downstream 단계(`fe`, `be`, `qa`, `devops`)는 모두 `pending`으로 재설정

이후 `_agency/status.md`를 사람이 읽는 뷰로 다시 생성해.

### Step 7 — 완료 메시지

```
✅ Contract Freeze 완료
저장 위치: _agency/contract.md

이제 FE와 BE를 병렬로 진행할 수 있습니다:
- /fe  → 프론트엔드 개발 시작
- /be  → 백엔드 개발 시작
```
