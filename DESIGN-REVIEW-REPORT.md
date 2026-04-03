# DESIGN.md 검토 보고서

> 작성일: 2026-04-03
> 대상: DESIGN.md (2026-02-20 작성, Antigravity IDE용 웹사이트 리뉴얼 분석 설계)
> 비교 대상: WebStart 현재 구조 (v2.2, Claude Code CLI 기반)

---

## 1. 요약

DESIGN.md는 2026-02-20에 Antigravity IDE(Windows) 환경에서 웹사이트를 분석하는 프로젝트로 설계되었다.
WebStart는 이후 Claude Code CLI 기반으로 발전하면서, DESIGN.md의 분석 기능을 **검수 파이프라인(audit)**으로 흡수했다.

결론: DESIGN.md의 핵심 아이디어는 이미 대부분 반영되어 있었고, 미반영 3개 항목을 이번에 구현 완료했다.

---

## 2. Phase별 대응 현황

| DESIGN.md Phase | WebStart 대응 | 상태 |
|---|---|---|
| Phase 0: 사전 준비 (Python/Playwright 설치) | `install.sh` + `audit-runtime` | **반영됨** |
| Phase 1: 사이트 접속 & 유효성 확인 | `/audit` Step 0 + robots.txt 파싱 | **반영됨** |
| Phase 2: 기술 스택 탐지 | `/audit-tech` (런타임 전역 객체 탐지 포함) | **반영됨** |
| Phase 3: 페이지 전체 탐색 | `/audit-ia` 스킬 (사이트맵 역추적, 메뉴 구조) | **반영됨** |
| Phase 4: 콘텐츠 수집 + 스크린샷 | crawl에서 PC/Mobile 이중 캡처 | **반영됨** (이번 구현) |
| Phase 5: 디자인 시스템 분석 | `/audit-ux` (CSS 팔레트 + 이미지 팔레트) | **반영됨** (이번 구현) |
| Phase 6: 인터랙티브 & 성능 분석 | `/audit-tech` (CWV + Lighthouse) | **반영됨** (이번 구현) |
| Phase 7: AI 종합 분석 | `/audit --step=report` | **반영됨** |
| Phase 8: 최종 리포트 | `/audit --step=report` (client-brief.md 생성) | **반영됨** |

---

## 3. 이번에 구현한 항목

### 3.1 PC/Mobile 스크린샷 이중 캡처

crawl 명령이 각 페이지를 PC(1920x1080)와 Mobile(375x812) 두 뷰포트로 캡처한다.
파일명은 `{N}-{slug}-pc.png`, `{N}-{slug}-mobile.png`으로 구분된다.

- **변경 파일:** `audit-runtime/src/webstart_audit/cli.py` (crawl 함수)
- **반영 스킬:** `/audit-ux` SKILL.md에 스크린샷 활용 안내 추가

### 3.2 Lighthouse 자동 측정

tech_scan 완료 후 `npx lighthouse`를 자동 실행하여 Performance, Accessibility, Best Practices, SEO 점수를 수집한다.
npx가 없거나 실행 실패 시 경고만 출력하고 스캔은 정상 완료 처리한다.

- **변경 파일:** `audit-runtime/src/webstart_audit/cli.py` (run_lighthouse 헬퍼 + tech_scan)
- **산출물:** `_audit/raw/lighthouse.json`, tech-summary.json의 `lighthouse` 키
- **반영 스킬:** `/audit-tech` SKILL.md Step 5에 Lighthouse 점수 표 추가

### 3.3 Color Thief 이미지 팔레트 추출

ux_scan이 홈페이지 스크린샷에서 dominant color + 6색 팔레트를 추출한다.
colorthief 패키지가 없으면 경고만 출력하고 건너뛴다.

- **변경 파일:** `audit-runtime/src/webstart_audit/cli.py` (ux_scan 함수)
- **산출물:** ux-summary.json의 `imagePalette` 키
- **반영 스킬:** `/audit-ux` SKILL.md Step 3에 이미지 팔레트 안내 추가

---

## 4. 기존에 이미 반영되어 있던 항목

초기 보고서에서 "미반영"으로 분류했으나, 코드 확인 결과 이미 구현되어 있었던 항목:

| 항목 | 구현 위치 | 비고 |
|---|---|---|
| 런타임 전역 객체 탐지 | cli.py tech_scan (L974-999) | `__NEXT_DATA__`, `__NUXT__`, React, jQuery, WordPress, Tailwind, Bootstrap |
| robots.txt 파싱 | cli.py crawl (L578-579) | `load_robots_rules` + `is_allowed_by_robots` |
| 스크린샷 캡처 (단일 뷰포트) | cli.py crawl (L603-605) | full_page 캡처 (이번에 이중 뷰포트로 확장) |

---

## 5. 적용 불필요한 항목

| DESIGN.md 항목 | 불필요 사유 |
|---|---|
| Antigravity IDE 도구 매핑 (`browser_subagent`, `view_file`) | WebStart는 Claude Code CLI 기반으로 별도 도구 체계 사용 |
| `h:\Research/` 경로 구조 | WebStart는 `_audit/` 폴더 구조를 사용 |
| `analyze_site.py` 통합 스크립트 | WebStart는 스킬 단위 분리 아키텍처 채택 |
| pytesseract OCR 제외 결정 | DESIGN.md에서도 이미 제외됨 |
| `.agent/workflows/` 워크플로우 파일 | Claude Code 스킬 시스템으로 대체됨 |

---

## 6. DESIGN.md 처리 권장

DESIGN.md의 모든 적용 가능 항목이 반영 완료되었다.
이 파일은 Antigravity IDE 시절의 설계 문서로, 현재 WebStart와 환경이 다르다.
**아카이브하거나 삭제**하는 것이 혼란 방지에 좋다.
