# WebStart v2.2 심층 검토 보고서

> 검토일: 2026-04-03
> 검토 범위: 제작 스킬 8개 + 검수 스킬 5개 + 인프라(install.sh, lint-docs.sh, audit-runtime) + 전체 문서
> 기준 버전: v2.2
> 개정: v3 — 초판 오판 4건 수정(v2) + 피드백 반영하여 M-1/M-3/M-4 범위 축소 및 재분류(v3)

---

## 요약

| 심각도 | 건수 |
|--------|------|
| Critical | 1 |
| High | 3 |
| Medium | 5 |
| Low | 8 |
| **합계** | **17** |

---

## 정오표 (초판 대비 변경 사항)

| 초판 항목 | 조치 | 사유 |
|-----------|------|------|
| C-2. 검수 스킬 status.json 업데이트 부재 | Medium으로 재분류, 범위 축소 | audit-runtime의 `mark_stage()`가 crawl/ux-scan/ia-scan/tech-scan/report-draft에서 `_audit/status.json`을 갱신함 (`cli.py:678`, `777`, `845`, `1021`, `1277`). 실제 이슈는 audit-db와 일부 스킬 문구가 status.md 중심으로 남아 있는 것으로 한정 |
| C-3. `report-draft` 명령어 정의 미확인 | 삭제 | `cli.py:1138`에 `@app.command("report-draft")` 구현 존재. `cli.py:1277-1290`에서 report/handover stage를 `mark_stage()`로 갱신까지 수행. 완전한 오판 |
| H-1. 신뢰도 분류 체계 이원화 | 삭제 | `web-audit-agent-plan.md:36-42`에서 "신뢰도"(High/Medium/Low)와 "상태"(Confirmed/Likely/Hypothesis/Unknown)를 의도적 2축으로 분리 정의. 설계를 오독한 것 |
| M-4. PHP FE 디렉토리 구조 미명시 | 삭제 | `fe/SKILL.md:38-44`에 Next.js는 `src/`, PHP는 `resources/views/` 구조가 명시되어 있음 |
| M-1. `_agency/` 폴더 또는 CLAUDE.md 부재 | v3에서 범위 축소 | `_agency/status.json` 복원 설명과 PM의 client-brief 안내는 존재. 실제 빈틈은 CLAUDE.md 자체 부재 시 fallback 부족으로 한정 |
| M-3. status.json ↔ status.md 이모지 파싱 | v3에서 Low로 재분류 | 실제 파서 코드가 존재하는 구조가 아니라 문서 명확성 이슈에 가까움 |
| M-4. audit-db 및 일부 스킬 문구 불일치 | v3에서 범위 축소 | 일부 audit 스킬은 이미 runtime의 status.json 갱신을 명시. 실제 불일치는 audit-db/audit-tech의 완료 단계 문구로 한정 |

---

## Critical (동작 오류 가능)

### C-1. FE/BE 재실행 시 downstream(QA/DevOps) 리셋 누락

**위치:** `skills/fe/SKILL.md` Step 7, `skills/be/SKILL.md` Step 8

PM/Design/Contract는 재실행 시 하위 단계를 `pending`으로 리셋하지만, FE/BE는 자기 상태만 갱신한다.

**시나리오:** FE done → QA 실행 → FE 수정 후 재실행(done) → QA가 이전 결과로 남아 `/devops` 게이트를 통과

**수정안:** FE/BE가 `done` 전환 시 `stages.qa`, `stages.devops`를 `pending`으로 리셋하는 로직 추가

---

## High (기능 저하/불일치)

### H-1. robots.txt 준수 미구현

**위치:** `SETUP-GUIDE.md` 보안 정책, `web-audit-agent-plan.md`, `audit-runtime/` 코드

SETUP-GUIDE.md와 web-audit-agent-plan.md에서 robots.txt 준수를 요구하지만, 실제 audit-runtime 코드에 `Disallow` 지시자를 확인하는 로직이 없다.

**수정안:** audit-runtime crawl 단계에서 robots.txt 파싱 및 Disallow 경로 제외 로직 추가

---

### H-2. `--step=ux` 등 개별 단계 재실행 시 멱등성 미정의

**위치:** `skills/audit/SKILL.md` 옵션 처리 섹션

`/audit --step=ux` 실행 시 크롤링을 다시 하는지, 기존 데이터를 쓰는지, 보고서를 덮어쓰는지 명시되지 않았다.

**수정안:** 각 `--step` 옵션의 재실행 동작 명시 (기존 데이터 재사용 + 보고서 덮어쓰기가 합리적)

---

### H-3. install.sh에서 Node.js/Python 버전 미검증

**위치:** `install.sh` (Claude Code 존재만 확인, line 19~24)

SETUP-GUIDE에 명시된 Node.js 18+와 Python 3.10+ 요구사항을 install.sh가 검증하지 않는다.

**수정안:** install.sh 초반에 `node --version`, `python3 --version` 파싱 후 최소 버전 확인 추가

---

## Medium (엣지 케이스/견고성)

### M-1. CLAUDE.md 부재 시 fallback 부족

**위치:** `skills/design/SKILL.md` (line 21~35), `skills/fe/SKILL.md` (line 29~31), `skills/be/SKILL.md` (line 23~32), `skills/devops/SKILL.md` (line 21~30)

`_agency/status.json` 복원 안내와 PM의 client-brief 부재 안내는 존재하지만, CLAUDE.md 자체가 없을 때(예: `/webstart`를 거치지 않고 직접 `/design` 실행) 스택 분기에 필요한 정보를 얻을 수 없다.

**수정안:** 스택 읽기 단계에서 CLAUDE.md 부재 시 "/webstart를 먼저 실행하세요" 안내 추가

---

### M-2. CLAUDE.md에 "기술 스택" 섹션 없을 때 기본값 미정의

**위치:** Design, FE, BE, DevOps 스킬의 스택 분기 로직

스택 분기(NextJS vs PHP)에 의존하는 스킬 4개가 섹션 미발견 시 동작이 정의되지 않았다.

**수정안:** 섹션 미발견 시 기본값 `nextjs` 적용 또는 사용자에게 질문

---

### M-3. audit-db/audit-tech 완료 단계 문구에서 status.md 중심 표현 잔존

**위치:** `skills/audit-db/SKILL.md` (line 145~147), `skills/audit-tech/SKILL.md` (line 124~126)

audit-runtime은 `mark_stage()`로 `_audit/status.json`을 자동 갱신하고 (`cli.py:678`, `777`, `845`, `1021`, `1277`), 다른 audit 스킬은 이를 명시하고 있다. 그러나 audit-db와 audit-tech의 완료 단계는 아직 "status.md를 업데이트한다"는 표현만 남아 있어, status.json 기반 게이트와 불일치한다.

**수정안:** 해당 두 스킬의 완료 단계에 "runtime이 status.json을 자동 갱신한다"는 점을 명시하고, status.md 갱신 안내를 보조 설명으로 전환

---

### M-4. PII 마스킹 범위 제한적

**위치:** `audit-runtime/` 코드의 `mask_pii()` 함수

이메일과 한국 전화번호만 처리한다. 주민번호, 신용카드, API 키, 커스텀 인증 헤더 등 추가 패턴이 필요하다.

**수정안:** 정규식 패턴 확장 (주민번호, 카드번호, `x-api-key`/`authorization` 등)

---

### M-5. .gitignore에 Python 캐시 패턴 누락

**위치:** `.gitignore` (현재 3줄)

`__pycache__/`, `*.pyc`, `.venv/` 등이 없다. install.sh가 사후 정리하지만 개발 중 커밋 위험이 있다.

**수정안:**
```
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
.pytest_cache/
```

---

## Low (개선 기회)

### L-0. status.json ↔ status.md 복원 시 이모지 매핑 규칙 미명시

**위치:** 제작 파이프라인 스킬 전체의 게이트 체크 단계

status.json이 없고 status.md만 있을 때 복원한다고 하지만, 이모지 → 상태값 매핑(`✅ → done` 등)이 문서화되지 않았다. 실제 파서 코드가 존재하는 구조가 아니라 문서 명확성 이슈에 해당한다.

---

### L-1. PM 스킬에 "선행 조건 없음" 명시

**위치:** `skills/pm/SKILL.md` Step 1

PM은 첫 단계라 게이트가 없지만, 의도적 생략인지 실수인지 구분이 안 된다.

---

### L-2. FE/BE partial 완료 메시지에 상태 설명 부족

**위치:** `skills/fe/SKILL.md` Step 8, `skills/be/SKILL.md` Step 9

부분 완료 시 status.json이 `partial`로 기록되었다는 안내가 없어 사용자가 `/qa-check` 게이트 거부에 혼란 가능.

---

### L-3. QA 완료 메시지에 "FE와 BE 모두 done이어야 함" 명시 부족

**위치:** `skills/qa-check/SKILL.md` 완료 메시지

현재 "FE/BE 완료 확인" 수준이며, 둘 다 `done`(partial이 아닌)이어야 한다는 점이 강조되지 않았다.

---

### L-4. web-audit-agent-plan.md 버전 미동기화

**위치:** `web-audit-agent-plan.md` 헤더

v1.1 (2026-04-02)로 남아 있어 v2.2 시스템과 동기화되지 않았다.

---

### L-5. lint-docs.sh에 교차검증 부족

**위치:** `scripts/lint-docs.sh`

버전 일관성(CHANGELOG vs SETUP-GUIDE), 스킬 카운트 교차검증, git clone URL 검증이 없다.

---

### L-6. audit-db의 "API 증거 충분/부족" 판정 기준 모호

**위치:** `skills/audit-db/SKILL.md` Step 2

"API 호출 관련 증거"의 충분/부족 기준이 수치로 정의되지 않았다 (예: 3개 이상 엔드포인트 = 충분).

---

### L-7. 완성된 보고서 파일 예시 없음

**위치:** 각 audit 스킬

`ux-report.md`, `ia-report.md` 등의 완성본 예시가 없어 사용자가 기대 결과를 파악하기 어렵다.
