# Plan: DESIGN.md 미반영 항목 구현

## 변경 파일
- `audit-runtime/src/webstart_audit/cli.py` — 핵심 런타임 수정
- `skills/audit-ux/SKILL.md` — imagePalette 언급 추가
- `skills/audit-tech/SKILL.md` — Lighthouse 점수 언급 추가
- `DESIGN-REVIEW-REPORT.md` — 부정확한 항목 정정

## Task 1: Mobile 뷰포트 스크린샷 이중 캡처

**파일:** cli.py crawl 함수 (L587~L666)

현재 `browser.new_page()`로 기본 뷰포트(800x600)에서 캡처한다.
PC(1920x1080)와 Mobile(375x812) 두 뷰포트로 각각 캡처하도록 변경.

**변경 내용:**
1. crawl 함수 내 Playwright 루프에서:
   - 기본 뷰포트를 PC(1920x1080)로 설정
   - 기존 스크린샷 촬영 후, 뷰포트를 Mobile(375x812)로 변경하여 추가 캡처
   - 파일명: `{N}-{slug}-pc.png`, `{N}-{slug}-mobile.png`
2. screenshots 폴더 구조: `_audit/screenshots/` 유지 (pc/, mobile/ 서브폴더 불필요 — 파일명으로 구분)
3. PageSnapshot.screenshot 필드: 기존 str → 유지하되, `screenshot_mobile` 필드 추가
4. crawl_payload.summary에 `capturedScreenshots` 갱신

## Task 2: Lighthouse 자동 측정

**파일:** cli.py tech_scan 함수 끝부분 (L1077~L1087)

tech_scan이 완료된 후, `npx lighthouse`를 subprocess로 실행.

**변경 내용:**
1. tech_scan 함수 끝에 `run_lighthouse(url, paths)` 헬퍼 호출 추가
2. 헬퍼 함수:
   ```python
   def run_lighthouse(url: str, paths: dict[str, Path]) -> dict[str, Any] | None:
       import subprocess
       result = subprocess.run(
           ["npx", "lighthouse", url, "--output=json", "--chrome-flags=--headless --no-sandbox", "--quiet"],
           capture_output=True, text=True, timeout=120
       )
       # JSON 파싱 → categories에서 score 추출
       # 실패 시 None 반환
   ```
3. 결과를 `_audit/raw/lighthouse.json` 저장
4. tech-summary.json에 `lighthouse` 키 추가 (performance, accessibility, bestPractices, seo 점수)
5. npx 없거나 timeout 시 경고 메시지만 출력, 스캔 자체는 성공 처리

## Task 3: Color Thief 이미지 팔레트

**파일:** cli.py ux_scan 함수 (L757~L843)

스크린샷 이미지에서 dominant color + palette 추출.

**변경 내용:**
1. ux_scan 함수 끝에 이미지 팔레트 추출 로직 추가
2. colorthief 임포트를 try/except로 감싸서 없으면 skip
3. 첫 번째 스크린샷(홈페이지)에서:
   - `get_color()` → dominant color
   - `get_palette(color_count=6)` → palette
4. ux-summary.json에 `imagePalette` 키 추가
5. colorthief 없으면 `imagePalette: null`

## Task 4: SKILL.md 업데이트

- `/audit-tech`: Step 5에 Lighthouse 점수 표 추가 안내
- `/audit-ux`: Step 3에 이미지 팔레트 보완 안내

## Task 5: DESIGN-REVIEW-REPORT.md 정정

- 런타임 전역 객체 탐지: "미반영" → "이미 구현됨" 수정
- robots.txt: "명시적이지 않다" → "이미 구현됨" 수정
- 실제 미반영 3개로 축소
