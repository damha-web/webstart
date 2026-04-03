# WebStart 변경 이력

## v2.2 — 2026-04-03 (상태 관리 강화 + 문서 릴리스 정리)

### 주요 변경

- 제작 파이프라인의 상태 원본을 `_agency/status.json`으로 승격
- `_agency/status.md`를 게이트 판정 파일이 아닌 사람이 읽는 뷰로 재정의
- `/fe`, `/be` 부분 작업 상태를 `partial`, `/qa-check` 차단 상태를 `blocked`로 명시
- `/pm`, `/design`, `/contract` 재실행 시 downstream 단계를 `pending`으로 되돌리는 규칙 추가
- `scripts/lint-docs.sh` 추가, 설치 직후 핵심 문서 회귀 자동 검사
- `audit-runtime/README.md`에 재설치, 수동 부트스트랩, 문제 해결 가이드 추가

### 문서/운영 개선

- `SETUP-GUIDE.md`를 v2.2 기준으로 갱신
- `agency-ai-agent-plan.md`를 `status.json` 기반 파이프라인 설계로 업데이트
- 내부 검토 문서(`IMPROVEMENT-REPORT.md`, `REVIEW-REPORT.md`, `REVIEW-REPORT-V2.md`, `SESSION-REPORT.md`, `AUDIT-AUTOMATION-V3.md`)를 repo 내부 참고 문서로 유지
- `install.sh`에서 문서 lint를 자동 실행하고, runtime/skill 복사 시 캐시 파일을 제외

### 파일 변경

| 파일 | 상태 |
|------|------|
| `install.sh` | 수정 (runtime 동기화, 문서 lint 자동 실행, 캐시 제외) |
| `scripts/lint-docs.sh` | 신규 |
| `SETUP-GUIDE.md` | 수정 (v2.2 가이드 반영) |
| `agency-ai-agent-plan.md` | 수정 (status.json 기반 상태 관리) |
| `skills/webstart/SKILL.md` | 수정 (13개 스킬 체계, status.json 템플릿) |
| `skills/pm/SKILL.md` | 수정 (status.json 원본 규칙) |
| `skills/design/SKILL.md` | 수정 (status.json 게이트/리셋 규칙) |
| `skills/contract/SKILL.md` | 수정 (status.json 게이트/리셋 규칙) |
| `skills/fe/SKILL.md` | 수정 (`partial` 상태 규칙) |
| `skills/be/SKILL.md` | 수정 (`partial` 상태 규칙) |
| `skills/qa-check/SKILL.md` | 수정 (`blocked` 상태 규칙) |
| `skills/devops/SKILL.md` | 수정 (status.json 게이트/완료 처리) |
| `audit-runtime/README.md` | 수정 (운영 가이드 보강) |

### 업그레이드 시 필수 작업

**v2.1 → v2.2 업데이트 사용자**

1. **스킬과 runtime 재설치**
   ```bash
   bash install.sh
   ```

2. **문서 lint 통과 확인**
   ```bash
   bash scripts/lint-docs.sh
   ```

3. **runtime 설치 확인**
   ```bash
   ~/.webstart/bin/webstart-audit doctor
   ```

4. **제작 파이프라인 상태 파일 확인**
   새 프로젝트부터는 `_agency/status.json`이 원본이다.

---

## v2.1 — 2026-04-02 (검수 파이프라인 추가)

### 신규 기능

**검수 에이전트 팀 (Agent 5~8)**

기존 웹사이트를 역설계하여 제작 팀에 인계하는 5개 스킬 추가.

| 스킬 | 역할 | 주요 기능 |
|------|------|----------|
| `/audit` | 오케스트레이터 | 대상 등록, Playwright 자동 수집, 종합 보고서, client-brief.md 변환 |
| `/audit-ux` | UI/UX 리서처 | 컬러/폰트/컴포넌트 추출, 접근성 검수 |
| `/audit-ia` | 정보 아키텍트 | 사이트맵 역추적, 사용자 여정, SEO 메타데이터 |
| `/audit-tech` | 기술 스택 진단 | 프레임워크 감지, CWV 측정, 서드파티 분석 |
| `/audit-db` | DB 유추 | API 증거 기반 ERD 역설계, 입력 게이트 판정 |

### 구조 변경

- 파이프라인 Step 0~6 체계 (기존 Step 1~5에서 확장)
- Step 0: 분석 대상 등록 (`_audit/target.md` 템플릿)
- Step 5: 종합 보고서 (`known gaps` 섹션 강제)
- Step 6: 제작 팀 인계 (`_agency/client-brief.md` 자동 생성)

### 공통 규칙 추가

- **신뢰도 분류 체계:** Confirmed / Likely / Hypothesis / Unknown
- **보안 정책:** PII 마스킹, 인증 정보 저장 금지, rate limit 준수
- **입력 게이트:** `/audit-db`에서 API 증거 유무에 따른 산출물 신뢰 등급 분류

### 파일 변경

| 파일 | 상태 |
|------|------|
| `skills/audit/SKILL.md` | 신규 |
| `skills/audit-ux/SKILL.md` | 신규 |
| `skills/audit-ia/SKILL.md` | 신규 |
| `skills/audit-tech/SKILL.md` | 신규 |
| `skills/audit-db/SKILL.md` | 신규 |
| `web-audit-agent-plan.md` | 신규 (v1.1) |
| `web-audit-agent-plan-review-report.md` | 신규 |
| `web-audit-agent-plan-revision-report.md` | 신규 |
| `install.sh` | 수정 (5개 스킬 안내 추가) |
| `SETUP-GUIDE.md` | 수정 (v2.1 전면 개정) |

### 업그레이드 시 필수 작업

**v2.0 → v2.1 업데이트 사용자**

1. **공용 audit runtime 설치 확인**
   `bash install.sh` 실행 시 `~/.webstart/bin/webstart-audit`와 Playwright Chromium이 함께 설치됩니다.
   설치 확인:
   ```bash
   ~/.webstart/bin/webstart-audit doctor
   ```

2. **스킬 재설치**
   ```bash
   bash install.sh
   ```

3. **Claude Code 재시작** (스킬 인식 필요)

4. **검수 파이프라인 테스트**
   ```bash
   /audit https://example.com  # 기본 동작 확인
   ```

### 알려진 제약사항

- 검수 파이프라인(`/audit*`)은 claude.ai 웹 Projects에서 지원하지 않습니다. CLI 전용입니다.
- audit runtime 또는 Playwright Chromium 설치가 없으면 검수 파이프라인이 실행되지 않습니다.

---

## v2.0 — 2026-04-02 (제작 파이프라인 v2)

### 주요 변경

- @mode 방식에서 독립 스킬 8개로 전환
- Contract Freeze 단계 추가 (`/contract`)
- 파이프라인 게이트 강제화 (`_agency/status.md` 자동 검증)
- PHP 스택 분기 지원
- 범위 변경 규칙 추가

### 스킬 목록 (8개)

| 스킬 | 역할 |
|------|------|
| `/webstart` | 프로젝트 초기 세팅 |
| `/pm` | 기획, 견적 |
| `/design` | 디자인 시스템 |
| `/contract` | API 계약 확정 |
| `/fe` | 프론트엔드 개발 |
| `/be` | 백엔드 개발 |
| `/qa-check` | QA 체크리스트 |
| `/devops` | 배포 설정 |

---

## v1.0 — 2026-04-02 (초기 버전)

- CLAUDE.md @mode 전환 방식
- 6개 에이전트 (PM, 디자이너, FE, BE, QA, DevOps)
