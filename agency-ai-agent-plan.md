# 1인 웹사이트 제작 에이전시 AI 에이전트 시스템 계획서

> **버전:** v2.0  
> **작성일:** 2026-04-02  
> **변경 이력:** v1.0 → v2.0: @mode 방식에서 개별 스킬 방식으로 전환, Contract Freeze 추가, PHP 스택 분기 보완, 파이프라인 게이트 강제화

---

## 0. 글로벌 공통 규칙

모든 에이전트 스킬에 적용되는 기본 규칙.

| 항목 | 규칙 |
|------|------|
| **언어** | 한국어 답변, 한자 사용 금지, 기술 용어·파일명·코드는 영어 유지 |
| **출력 형식** | 단계별 설명, 결과물은 표·체크리스트 우선 |
| **코드 출력** | 서론 없이 즉시 복사 가능한 완성 코드 제공 |
| **코드 품질** | `any` / `unknown` 타입 사용 금지, TypeScript strict 모드 기준 |
| **보안** | OWASP Top 10 준수, 하드코딩 시크릿 금지 |
| **최소 변경 원칙** | 요청된 범위만 수정, 불필요한 리팩토링·주석 추가 금지 |
| **에러 처리** | 원인 + 해결을 위한 실행 가능한 조치(Actionable Error) 포함 |
| **단일 원본 원칙** | `_agency/` 파일이 원본. CLAUDE.md는 규칙만, 산출물은 `_agency/`에만 저장 |

---

## 1. 기본 기술 스택

| 레이어 | Next.js 스택 | PHP 스택 |
|--------|-------------|---------|
| **프레임워크** | Next.js 14 (App Router) | Laravel 11 / WordPress |
| **언어** | TypeScript | PHP 8.x + TypeScript (프론트) |
| **스타일링** | Tailwind CSS + shadcn/ui | Tailwind CSS |
| **DB/인증** | Supabase (PostgreSQL + Auth) | MySQL 8.x + Laravel Sanctum |
| **배포** | Vercel / Fly.io / NAS | Fly.io (Docker) / NAS |
| **결제** | 토스페이먼츠 | 토스페이먼츠 |
| **Validation** | zod | Laravel Form Request |

---

## 2. 에이전트 스킬 구성 (8개)

v1.0의 "CLAUDE.md @mode 전환" 방식에서 **각 에이전트를 독립 스킬**로 분리.
각 스킬은 이전 단계 완료 여부를 `_agency/status.md`에서 자동 검증하고,
산출물을 지정된 `_agency/` 파일에 저장합니다.

| 스킬 | 입력 | 출력 | 게이트 |
|------|------|------|--------|
| `/webstart` | 프로젝트명, 스택 | 폴더 구조 전체 | 없음 |
| `/pm` | `_agency/client-brief.md` | `_agency/sitemap.md` | 없음 (첫 단계) |
| `/design` | `_agency/sitemap.md` | `_agency/design-system.md` | PM 완료 |
| `/contract` | sitemap + design-system | `_agency/contract.md` | Design 완료 |
| `/fe` | design-system + contract | 코드 파일 | Contract 완료 |
| `/be` | `_agency/contract.md` | 코드 + `_agency/api-spec.md` | Contract 완료 |
| `/qa-check` | 코드 + contract | `_agency/qa-report.md` | FE + BE 완료 |
| `/devops` | 코드 + 스택 | 배포 설정 + `_agency/handover.md` | QA 완료 |

---

## 3. 파이프라인

### 전체 흐름

```
[/webstart 프로젝트명 스택]
         |
    [/pm]  ← client-brief.md 작성 후 실행
  페르소나·사이트맵·견적서 → _agency/sitemap.md
         |
    [/design]  ← PM 완료 게이트
  디자인 시스템 → _agency/design-system.md
         |
    [/contract]  ← Design 완료 게이트
  API 계약·ERD·공유타입 → _agency/contract.md
         |
    ┌────┴────┐  ← 병렬 (Contract 완료 후에만 허용)
  [/fe]     [/be]
  UI 코드   API + DB
    └────┬────┘
         |
    [/qa-check]  ← FE + BE 완료 게이트
  체크리스트·버그리포트 → _agency/qa-report.md
         |
  Critical 버그 있으면 → /fe 또는 /be 수정 → /qa-check 재실행
         |
    [/devops]  ← QA 완료 게이트
  배포 설정 + 납품 문서 → _agency/handover.md
         |
    [클라이언트 납품]
```

### 파이프라인 상태 추적

모든 스킬은 `_agency/status.md`를 읽고 씁니다.

```markdown
# 파이프라인 상태

| 단계 | 스킬 | 상태 | 완료일 |
|------|------|------|--------|
| 1. 기획 | /pm | ✅ 완료 | 2026-04-02 |
| 2. 디자인 | /design | ⏳ 대기 | - |
| 3. API 계약 | /contract | ⏳ 대기 | - |
| 4a. 프론트엔드 | /fe | ⏳ 대기 | - |
| 4b. 백엔드 | /be | ⏳ 대기 | - |
| 5. QA | /qa-check | ⏳ 대기 | - |
| 6. 배포 | /devops | ⏳ 대기 | - |
```

### 범위 변경 규칙 (Scope Change)

개발 중 요구사항이 변경되면:

1. **범위 변경 발견** → `/pm`에 변경 내용 전달하여 재승인
2. **Design 영향** → `/design` 재실행하여 디자인 시스템 갱신
3. **API 영향** → `/contract` 재실행하여 계약 갱신, FE/BE에 공지
4. **status.md의 범위 변경 이력**에 날짜·내용·영향 단계 기록

---

## 4. 프로젝트 폴더 구조

`/webstart` 실행 시 생성되는 구조:

```
{project-name}/
├── CLAUDE.md                   ← 스택별 에이전트 규칙 (단일 원본: _agency/)
├── _agency/
│   ├── client-brief.md         ← 사용자 작성 (입력)
│   ├── status.md               ← 파이프라인 진행 상태 (자동 관리)
│   ├── sitemap.md              ← /pm 산출물
│   ├── design-system.md        ← /design 산출물
│   ├── contract.md             ← /contract 산출물 (FE/BE 공통 계약)
│   ├── api-spec.md             ← /be 산출물 (실제 구현 기준)
│   ├── qa-report.md            ← /qa-check 산출물
│   └── handover.md             ← /devops 산출물 (납품 문서)
├── research.md                 ← /fe, /be 구현 전 분석
└── plan.md                     ← /fe, /be 구현 계획 (체크리스트)
```

---

## 5. 스킬 상세

### /webstart

- **역할:** 프로젝트 초기 세팅
- **인수:** `프로젝트명 스택(nextjs|php)`
- **생성물:** 위의 전체 폴더 구조
- **스택 분기:** CLAUDE.md 내용이 nextjs / php에 따라 다르게 생성

### /pm

- **역할:** 클라이언트 요구사항 분석, 사이트맵, 페르소나, 세일즈 카피, 견적서
- **게이트:** 없음 (첫 단계)
- **입력 없음 시:** 작업 중단 + client-brief.md 작성 안내

### /design

- **역할:** 와이어프레임, 디자인 시스템 (컬러/타이포/컴포넌트), 다크모드
- **게이트:** PM 완료
- **스택 인식:** CLAUDE.md 읽어 nextjs면 shadcn/ui 기준, php면 Tailwind 기준

### /contract *(v2.0 신규)*

- **역할:** FE/BE 병렬 개발 전 공통 계약 확정
- **게이트:** Design 완료
- **산출물:** ERD, API 엔드포인트, 공유 타입, 에러 코드, Out of Scope 목록
- **중요:** 이 단계 완료 전까지 /fe, /be 실행 차단

### /fe

- **역할:** 반응형 UI 코드 작성
- **게이트:** Contract 완료
- **스택 분기:**
  - nextjs: App Router, next/image, next/link, TypeScript
  - php: Laravel Blade / Alpine.js, Tailwind CSS
- **산출물 자동 저장:** research.md, plan.md 자동 관리

### /be

- **역할:** DB 스키마, API 구현, 인증/보안
- **게이트:** Contract 완료
- **스택 분기:**
  - nextjs: Supabase + API Routes + zod
  - php: Laravel + Eloquent + Form Request
- **산출물 자동 저장:** api-spec.md 갱신

### /qa-check

- **역할:** 기능/성능/접근성/보안 체크리스트 + 버그 리포트
- **게이트:** FE + BE 모두 완료
- **배포 승인 조건:** Critical 버그 0개
- **참고:** 실제 브라우저 자동 테스트는 별도로 `/qa` 스킬 사용 가능

### /devops

- **역할:** 배포 파이프라인, Dockerfile, GitHub Actions, 도메인/SSL, 납품 문서
- **게이트:** QA 완료
- **스택 분기:**
  - nextjs+Vercel: vercel.json + 환경변수 목록
  - nextjs+Fly.io/NAS: Dockerfile (standalone, 상대경로) + GitHub Actions
  - php: Dockerfile (PHP-FPM+Nginx) + GitHub Actions + 마이그레이션

---

## 6. 설치 방법

### 현재 컴퓨터

이미 설치되어 있음.

### 새 컴퓨터

```bash
git clone https://github.com/본인계정/webstart-agency.git
cd webstart-agency
bash install.sh
```

`install.sh`가 `skills/` 폴더의 모든 스킬을 `~/.claude/skills/`에 자동 복사합니다.

설치 확인:
```bash
# Claude Code 재시작 후 /webstart 입력 시 동작하면 성공
```

---

## 7. 사용 흐름 요약

```
1. 새 프로젝트 시작
   /webstart kim-interior nextjs

2. client-brief.md 작성 후
   /pm

3. /design

4. /contract

5. (병렬)
   /fe Hero섹션     /be 문의폼 API

6. /qa-check

7. /devops
```

---

## 8. v1.0 → v2.0 주요 변경 사항

| 항목 | v1.0 | v2.0 |
|------|------|------|
| 에이전트 구조 | CLAUDE.md @mode 전환 | 독립 스킬 8개 |
| 파이프라인 게이트 | 선언적 (강제 불가) | status.md 자동 검증 |
| FE/BE 병렬 조건 | Design 완료 후 | Contract 완료 후 |
| PHP 지원 | 텍스트만 변경 | 에이전트 행동 분기 |
| 산출물 저장 | 수동 | 각 스킬이 자동 저장 |
| 범위 변경 규칙 | 없음 | PM 재승인 → 계약 갱신 |
| 납품 문서 | 없음 | /devops가 handover.md 생성 |
| QA 기준 | Critical 버그 0개 | 기능+성능+a11y+보안+배포준비 체크리스트 |
