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

`_agency/status.md`를 읽어라.
Design 단계가 ✅ 완료 상태가 아니면 작업을 중단하고 출력해:
> "디자인 시스템이 완료되지 않았습니다. 먼저 /design 을 실행하세요."

### Step 2 — 입력 읽기

두 파일을 모두 읽어라:
- `_agency/sitemap.md` (기능 목록, 페르소나)
- `_agency/design-system.md` (화면 구조, 컴포넌트 목록)

### Step 3 — 계약 문서 작성

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

**3. 공유 타입 정의 (TypeScript)**

FE와 BE가 동일하게 사용할 타입을 코드로 작성:
```typescript
// types/shared.ts
export type ...
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
- 인증 방식 (Supabase Auth / 세션 / JWT)
- 토큰 갱신 규칙
- 미인증 접근 허용 엔드포인트 목록

**6. 범위 밖 기능 (Out of Scope)**
이번 프로젝트에서 구현하지 않는 기능을 명시해.
범위 변경이 생기면 /pm 재승인 후 이 문서를 갱신해야 함.

### Step 4 — 산출물 저장

작성한 내용 전체를 `_agency/contract.md`에 저장해.

### Step 5 — 상태 업데이트

`_agency/status.md`에서 Contract 단계를 ✅ 완료로 업데이트해.

### Step 6 — 완료 메시지

```
✅ Contract Freeze 완료
저장 위치: _agency/contract.md

이제 FE와 BE를 병렬로 진행할 수 있습니다:
- /fe  → 프론트엔드 개발 시작
- /be  → 백엔드 개발 시작
```
