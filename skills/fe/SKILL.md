---
name: fe
description: |
  웹 에이전시 프론트엔드 에이전트. 디자인 시스템과 API 계약을 기반으로
  반응형 UI 코드를 작성합니다. Contract Freeze 완료 후에만 실행 가능합니다.
  사용법: /fe [작업할 페이지 또는 컴포넌트명]
  예: /fe Hero섹션
      /fe 전체 메인페이지
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Bash
  - AskUserQuestion
---

## 프론트엔드 에이전트 실행

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

**Next.js 스택이면** 아래 규칙을 적용해:
- 프레임워크: Next.js 14 (App Router)
- 언어: TypeScript strict 모드, any/unknown 금지
- 스타일링: Tailwind CSS + shadcn/ui
- 이미지: next/image, 링크: next/link
- 파일 경로: `src/` 기준 App Router 구조

**PHP 스택이면** 아래 규칙을 적용해:
- 프레임워크: Laravel Blade / 순수 HTML + Tailwind
- 언어: TypeScript (프론트 JS), PHP는 BE 에이전트 담당
- 컴포넌트: Alpine.js 또는 Livewire로 인터랙션 처리
- 파일 경로: `resources/views/` 구조

### Step 3 — 입력 읽기

- `_agency/design-system.md` — 디자인 시스템, 와이어프레임
- `_agency/contract.md` — 공유 타입, API 엔드포인트 목록

args에 작업 범위가 명시된 경우 해당 범위만 구현해.
없으면 AskUserQuestion으로 "어떤 페이지/컴포넌트부터 작업할까요?"를 물어봐.

### Step 4 — research.md 작성

`research.md`를 열어 현재 프로젝트 상태를 기록해:
- 기존 코드가 있으면 구조 파악 후 기록
- 없으면 새 프로젝트임을 명시

### Step 5 — plan.md 작성

`plan.md`에 구현 계획을 작성해:
- 작업 단위별 체크리스트 (각 항목 `- [ ]` 형식)
- 완료 시 `- [x]`로 변경

### Step 6 — 코드 작성

**공통 코드 기준:**
- TypeScript: any 타입 금지, Props 타입 명시
- 반응형: 모바일 first (sm → md → lg)
- 접근성: 시맨틱 HTML, aria 속성, 키보드 네비게이션
- 상태: Loading / Error / Empty state 컴포넌트 포함
- 성능: Lighthouse 90+ 목표
- 파일 상단에 경로 주석 명시 (예: `// src/components/Hero.tsx`)
- 설치 필요 패키지가 있으면 `npm install` 명령어 함께 제공
- console.log 프로덕션 코드에 남기지 않기

각 컴포넌트 완성 후 plan.md에서 해당 항목을 `[x]`로 표시해.

### Step 7 — 상태 업데이트

args로 특정 컴포넌트/페이지만 구현한 경우(부분 작업)에는 `_agency/status.json`에서 FE 단계를 `partial`로 업데이트하고,
`notes`에 이번에 끝낸 범위를 짧게 남겨라.

plan.md의 모든 항목이 `[x]`로 완료된 경우에만 `_agency/status.json`의 FE 단계를 아래처럼 갱신해:
- `stages.fe.status = "done"`
- `stages.fe.completed_at = {오늘 날짜}`
- `stages.fe.notes = ""`
- `stages.qa.status = "pending"`
- `stages.qa.completed_at = null`
- `stages.qa.notes = ""`
- `stages.qa.artifacts = []`
- `stages.devops.status = "pending"`
- `stages.devops.completed_at = null`
- `stages.devops.notes = ""`
- `stages.devops.artifacts = []`

부분 작업이면:
- `stages.fe.status = "partial"`
- `stages.fe.completed_at = null`
- `stages.qa.status = "pending"`
- `stages.qa.completed_at = null`
- `stages.qa.notes = ""`
- `stages.qa.artifacts = []`
- `stages.devops.status = "pending"`
- `stages.devops.completed_at = null`
- `stages.devops.notes = ""`
- `stages.devops.artifacts = []`

두 경우 모두 마지막에 `_agency/status.md`를 사람이 읽는 뷰로 다시 생성해.

### Step 8 — 완료 메시지

**전체 완료 시:**
```
✅ FE 작업 완료
수정된 파일 목록: [파일 목록]

BE 작업도 완료되었으면 다음 단계: /qa-check
```

**부분 완료 시:**
```
✅ FE 작업 완료 (부분)
수정된 파일 목록: [파일 목록]
남은 작업: plan.md 확인
현재 상태: _agency/status.json 의 FE = partial

전체 완료 후 /qa-check 실행
```
