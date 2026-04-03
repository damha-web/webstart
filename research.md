# Research: DESIGN.md 미반영 항목 구현

## 현재 코드 구조

### audit-runtime/src/webstart_audit/cli.py
- **crawl** (L557): BFS 크롤링, full_page 스크린샷 캡처 (단일 뷰포트, 브라우저 기본값)
  - L603-605: `page.screenshot(path=..., full_page=True)` - 뷰포트 설정 없이 기본 크기로만 캡처
  - screenshots 폴더: `_audit/screenshots/` (ensure_audit_dirs에서 생성)
  - PageSnapshot.screenshot 필드 존재 (L55)
- **ux_scan** (L757): pages.json에서 색상/폰트 집계, ux-summary.json 생성
  - CSS computed style 기반 색상만 수집 (이미지 팔레트 없음)
  - summary에 palette, typography, components 포함
- **tech_scan** (L915): 기술 스택 + 성능(Navigation Timing, CWV) 수집
  - L974-999: 런타임 전역 객체 탐지 (이미 구현됨)
  - L1000-1034: Navigation Timing + LCP/CLS 측정 (이미 구현됨)
  - Lighthouse 자동 측정은 **미구현**

### 의존성
- pyproject.toml 또는 requirements에 colorthief 없음
- Playwright는 이미 사용 중

## 구현 대상 3개

### 1. Mobile 뷰포트 스크린샷 (crawl 수정)
- 현재: 기본 뷰포트로 한 번만 캡처
- 목표: PC(1920x1080) + Mobile(375x812) 이중 캡처
- 영향: screenshots 폴더에 `{N}-{slug}-pc.png`, `{N}-{slug}-mobile.png` 생성
- PageSnapshot.screenshot을 dict로 변경하면 하위 호환성 깨짐 → 별도 필드 추가

### 2. Lighthouse 자동 측정 (tech_scan 수정)
- `npx lighthouse {URL} --output=json --chrome-flags="--headless"` 실행
- JSON 결과에서 performance, accessibility, best-practices, seo 점수 추출
- tech-summary.json에 lighthouse 키 추가
- npx가 없거나 실패 시 graceful skip

### 3. Color Thief 이미지 팔레트 (ux_scan 수정)
- 스크린샷 이미지에서 dominant color + palette 추출
- colorthief 패키지 의존성 추가 필요
- ux-summary.json에 imagePalette 키 추가
- colorthief 없으면 graceful skip
