# DESIGN.md 미반영 항목 구현 보고서

> 작성일: 2026-04-03
> 작업 근거: DESIGN.md (2026-02-20, Antigravity IDE용 웹사이트 리뉴얼 분석 설계)
> 작업 범위: DESIGN.md에 명시되어 있으나 WebStart audit-runtime에 미반영된 3개 기능 구현

---

## 1. 작업 배경

WebStart 프로젝트의 루트에 남아 있던 `DESIGN.md`는 Antigravity IDE 환경에서 작성된 웹사이트 분석 설계 문서다.
9개 Phase로 구성된 이 문서의 대부분은 이미 WebStart의 검수 파이프라인(`/audit` 스킬군)에 흡수되어 있었으나,
코드 레벨에서 확인한 결과 아래 3개 기능이 미구현 상태였다.

| # | 미반영 항목 | DESIGN.md 출처 | 적용 가치 |
|---|---|---|---|
| 1 | PC/Mobile 이중 뷰포트 스크린샷 캡처 | Phase 4 (콘텐츠 수집) | 높음 — 반응형 검증 필수 |
| 2 | Lighthouse 자동 성능 측정 | Phase 6 (인터랙티브 & 성능 분석) | 높음 — 객관적 점수 확보 |
| 3 | Color Thief 이미지 기반 팔레트 추출 | Phase 5 (디자인 시스템 분석) | 중간 — CSS 미사용 사이트 보완 |

참고: 초기 검토에서 "미반영"으로 분류했던 런타임 전역 객체 탐지(tech_scan L974-999)와 robots.txt 파싱(crawl L578-579)은 코드 확인 결과 이미 구현되어 있었다.

---

## 2. 변경 파일 목록

| 파일 | 변경 유형 | 변경 규모 |
|---|---|---|
| `audit-runtime/src/webstart_audit/cli.py` | 수정 | +98줄, -5줄 |
| `skills/audit-tech/SKILL.md` | 수정 | +13줄, -1줄 |
| `skills/audit-ux/SKILL.md` | 수정 | +6줄 |
| `DESIGN-REVIEW-REPORT.md` | 신규 | 보고서 (초기 검토 + 구현 후 정정) |
| `IMPLEMENTATION-REPORT.md` | 신규 | 이 파일 |
| `research.md` | 신규 | 사전 조사 기록 |
| `plan.md` | 신규 | 구현 계획 |

---

## 3. 구현 상세

### 3.1 PC/Mobile 이중 뷰포트 스크린샷 캡처

**사유:**
DESIGN.md Phase 4는 PC(1920px)와 Mobile(375px) 두 해상도로 스크린샷을 자동 캡처하도록 설계되어 있다.
기존 `crawl` 함수는 Playwright 기본 뷰포트(800x600)로 `full_page=True` 스크린샷을 한 번만 캡처하고 있어,
실제 데스크톱/모바일 레이아웃을 비교할 수 없었다.

**변경 내용:**

#### 3.1.1 뷰포트 상수 정의 (cli.py L587-588)

```python
PC_VIEWPORT = {"width": 1920, "height": 1080}
MOBILE_VIEWPORT = {"width": 375, "height": 812}
```

crawl 함수 내부에 PC와 Mobile 뷰포트 크기를 상수로 정의했다.
Mobile은 iPhone 13/14 기준 375x812를 채택했다.

#### 3.1.2 브라우저 초기 뷰포트를 PC로 설정 (cli.py L591)

```python
# 변경 전
page = browser.new_page()

# 변경 후
page = browser.new_page(viewport=PC_VIEWPORT)
```

기본 800x600 대신 1920x1080으로 페이지를 열어, 데스크톱 레이아웃 기준으로 데이터를 수집한다.
CSS 미디어 쿼리와 반응형 breakpoint가 데스크톱 기준으로 동작하므로 수집 데이터의 정확도가 올라간다.

#### 3.1.3 이중 스크린샷 캡처 루프 (cli.py L606-616)

```python
# 변경 전
screenshot_name = f"{len(pages)+1:03d}-{slugify_url(current_url)}.png"
screenshot_path = paths["screenshots"] / screenshot_name
page.screenshot(path=str(screenshot_path), full_page=True)

# 변경 후
slug = slugify_url(current_url)
page_num = f"{len(pages)+1:03d}"
screenshot_name = f"{page_num}-{slug}-pc.png"
screenshot_path = paths["screenshots"] / screenshot_name
page.screenshot(path=str(screenshot_path), full_page=True)

page.set_viewport_size(MOBILE_VIEWPORT)
page.wait_for_timeout(500)
mobile_screenshot_name = f"{page_num}-{slug}-mobile.png"
mobile_screenshot_path = paths["screenshots"] / mobile_screenshot_name
page.screenshot(path=str(mobile_screenshot_path), full_page=True)
page.set_viewport_size(PC_VIEWPORT)
```

각 페이지 방문 시:
1. PC 뷰포트(1920x1080)에서 full_page 스크린샷을 `*-pc.png`로 저장
2. 뷰포트를 Mobile(375x812)로 전환하고 500ms 대기 (CSS 재렌더링 여유)
3. Mobile full_page 스크린샷을 `*-mobile.png`로 저장
4. 뷰포트를 다시 PC로 복원하여 다음 페이지 수집에 영향 없도록 함
5. crawl summary의 `capturedScreenshots`는 페이지 수가 아니라 실제 저장한 스크린샷 파일 수를 기록한다

파일명에 `-pc`/`-mobile` 접미사를 붙여 서브폴더 분리 없이 구분한다.
서브폴더 방식 대비 기존 코드의 경로 참조 패턴 변경을 최소화할 수 있다.

#### 3.1.4 PageSnapshot 모델 확장 (cli.py L56)

```python
screenshot: str | None = None
screenshot_mobile: str | None = None  # 추가
```

기존 `screenshot` 필드를 유지하고 `screenshot_mobile` 필드를 추가했다.
`screenshot`의 타입을 str에서 dict로 변경하면 하위 호환성이 깨지므로, 별도 필드로 추가하는 방식을 선택했다.

#### 3.1.5 PageSnapshot 생성부에 mobile 경로 추가 (cli.py L650)

```python
screenshot_mobile=f"_audit/screenshots/{mobile_screenshot_name}",
```

#### 3.1.6 legacy scraped-data에 mobile 스크린샷 포함 (cli.py L732)

```python
"screenshot_mobile": page_data.get("screenshot_mobile"),
```

`scraped-data.json`의 pages 배열에도 mobile 스크린샷 경로를 포함하여,
ux-scan이나 에이전트가 legacy 데이터에서도 mobile 스크린샷을 참조할 수 있게 했다.

---

### 3.2 Lighthouse 자동 성능 측정

**사유:**
DESIGN.md Phase 6는 `npx lighthouse`로 객관적 성능 점수(Performance, Accessibility, Best Practices, SEO)를 측정하도록 설계되어 있다.
기존 `tech_scan`은 Navigation Timing API와 Core Web Vitals(LCP, CLS)를 Playwright로 직접 수집하고 있었으나,
Lighthouse가 제공하는 종합 점수와 상세 감사(audit) 항목은 포함하지 않았다.

**변경 내용:**

#### 3.2.1 `run_lighthouse` 헬퍼 함수 추가 (cli.py L945-993)

```python
def run_lighthouse(target_url: str, paths: dict[str, Path]) -> dict[str, float] | None:
```

독립 함수로 분리한 이유:
- tech_scan 함수의 복잡도를 높이지 않기 위해
- 실패 시 None을 반환하여 tech_scan의 나머지 흐름에 영향을 주지 않도록

동작 순서:
1. `shutil.which("npx")`로 npx 존재 여부 확인 — 없으면 경고 출력 후 None 반환
2. `subprocess.run`으로 `npx lighthouse {URL} --output=json --chrome-flags="--headless --no-sandbox" --quiet` 실행
3. timeout 120초 — 초과 시 경고 출력 후 None 반환
4. 종료 코드 비정상 시 경고 출력 후 None 반환
5. stdout의 JSON을 파싱하여 categories에서 4개 카테고리 점수 추출 (0~1 범위를 0~100으로 변환)
6. 전체 보고서를 `_audit/raw/lighthouse.json`에 저장
7. 점수 dict 반환

실패 경로가 5개(npx 없음, timeout, FileNotFoundError, 비정상 종료, JSON 파싱 실패)로 많은 이유:
Lighthouse는 외부 도구이므로 설치 상태, Node 버전, 네트워크 상태 등 다양한 이유로 실패할 수 있다.
모든 경우에 경고만 출력하고 tech_scan은 정상 완료되도록 하여, 핵심 기술 스캔이 Lighthouse 장애에 의존하지 않게 했다.

#### 3.2.2 tech_scan에서 lighthouse 호출 (cli.py L1149-1150)

```python
paths = ensure_audit_dirs(resolved)
lighthouse_scores = run_lighthouse(normalized_url, paths)
```

`ensure_audit_dirs` 호출을 lighthouse 실행 전으로 옮겼다 (기존에는 summary 생성 후에 호출).
lighthouse가 `_audit/raw/` 경로에 결과를 저장해야 하므로 디렉토리가 먼저 존재해야 한다.

#### 3.2.3 tech-summary.json에 lighthouse 키 추가 (cli.py L1160)

```python
"lighthouse": lighthouse_scores,
```

lighthouse_scores가 None이면 JSON에 `"lighthouse": null`로 저장된다.
에이전트가 이 값을 읽을 때 null 여부로 Lighthouse 실행 성공/실패를 판단할 수 있다.

#### 3.2.4 artifacts에 lighthouse.json 조건부 추가 (cli.py L1164-1166)

```python
artifacts = ["_audit/raw/tech-scan.json", "_audit/derived/tech-summary.json"]
if lighthouse_scores:
    artifacts.append("_audit/raw/lighthouse.json")
```

Lighthouse가 성공한 경우에만 산출물 목록에 포함하여, status.json에 존재하지 않는 파일이 기록되는 것을 방지한다.

---

### 3.3 Color Thief 이미지 기반 팔레트 추출

**사유:**
DESIGN.md Phase 5는 `colorthief` 라이브러리로 이미지에서 주요 색상을 추출하도록 설계되어 있다.
기존 `ux_scan`은 CSS computed style에서 추출한 색상(`palette`)만 제공하고 있어,
CSS 변수를 사용하지 않거나 이미지 중심인 사이트에서는 주요 색상을 놓칠 수 있었다.

**변경 내용:**

#### 3.3.1 이미지 팔레트 추출 로직 추가 (cli.py L832-847)

```python
image_palette: dict[str, list[int] | list[list[int]]] | None = None
if screenshot_samples:
    first_screenshot = resolved / screenshot_samples[0]
    if first_screenshot.exists():
        try:
            from colorthief import ColorThief

            ct = ColorThief(str(first_screenshot))
            dominant = list(ct.get_color(quality=1))
            top_colors_img = [list(c) for c in ct.get_palette(color_count=6, quality=1)]
            image_palette = {"dominant": dominant, "palette": top_colors_img}
        except ImportError:
            console.print("[yellow]colorthief 패키지가 없어 이미지 팔레트를 건너뜁니다.[/yellow]")
        except Exception as exc:
            console.print(f"[yellow]이미지 팔레트 추출 실패: {exc}[/yellow]")
```

동작 방식:
1. `screenshot_samples`(최대 4개 페이지의 스크린샷 경로)에서 첫 번째(홈페이지)를 선택
2. `colorthief.ColorThief`로 이미지를 열어 dominant color 1개 + 6색 팔레트를 추출
3. RGB 튜플을 list로 변환하여 JSON 직렬화 가능하게 함

colorthief를 선택 의존성(optional dependency)으로 처리한 이유:
- `try: from colorthief import ColorThief / except ImportError`로 감싸서, 패키지가 없어도 ux_scan이 정상 동작
- 이미지 팔레트는 CSS 팔레트의 보완 수단이므로, 필수 의존성으로 강제할 필요 없음
- audit-runtime의 설치 복잡도를 높이지 않음

#### 3.3.2 ux-summary.json에 imagePalette 키 추가 (cli.py L855)

```python
"imagePalette": image_palette,
```

출력 형식 예시:
```json
{
  "imagePalette": {
    "dominant": [41, 98, 168],
    "palette": [[41, 98, 168], [245, 245, 245], [32, 32, 32], [200, 60, 60], [120, 180, 80], [255, 200, 50]]
  }
}
```

colorthief가 없거나 실패하면 `"imagePalette": null`이 저장된다.

---

## 4. 스킬 문서 변경

### 4.1 `/audit-tech` SKILL.md

**변경 위치:** Step 5 (성능 진단) 섹션 상단

**추가 내용:** Lighthouse 점수 표 템플릿과 산출물 참조 안내

| 카테고리 | 점수 | 판정 |
|---------|------|------|
| Performance | ... | 양호(90+)/보통(50~89)/미달(<50) |
| Accessibility | ... | ... |
| Best Practices | ... | ... |
| SEO | ... | ... |

기존 "로딩 성능" 표 앞에 Lighthouse 표를 배치했다.
runtime이 npx를 찾지 못하면 이 표는 생략하도록 "(runtime이 자동 측정, npx 없으면 생략)" 안내를 포함했다.

기존 "로딩 성능" 표 제목에 "(Navigation Timing + Core Web Vitals)"를 추가하여,
Lighthouse 점수와 수집 방식이 다름을 명확히 했다.

### 4.2 `/audit-ux` SKILL.md

**변경 위치:** Step 3 (디자인 토큰 분석) 섹션 상단

**추가 내용:** 2개의 참고 블록

1. **이미지 팔레트 안내:** `ux-summary.json`에 CSS 기반 `palette`와 이미지 기반 `imagePalette` 두 가지가 있으며, `imagePalette`는 colorthief 설치 시에만 생성됨
2. **이중 뷰포트 스크린샷 안내:** `_audit/screenshots/`에서 `*-pc.png`, `*-mobile.png`로 구분하여 반응형 비교에 활용

---

## 5. 하위 호환성

| 항목 | 호환성 영향 | 대응 |
|---|---|---|
| 스크린샷 파일명 변경 (`*.png` → `*-pc.png`) | crawl 재실행 시 새 파일명 적용 | 기존 스크린샷은 그대로 유지되며, 새로운 crawl 실행 시 덮어쓰기 |
| PageSnapshot에 `screenshot_mobile` 필드 추가 | Pydantic BaseModel의 optional 필드 — 기존 데이터 역직렬화에 영향 없음 | `= None` 기본값 |
| ux-summary.json에 `imagePalette` 키 추가 | 기존 소비자가 없는 키를 무시하면 영향 없음 | null 허용 |
| tech-summary.json에 `lighthouse` 키 추가 | 동일 | null 허용 |
| SKILL.md 템플릿 변경 | 에이전트 프롬프트 변경 — 기존 보고서에는 영향 없음 | 다음 실행부터 적용 |

---

## 6. 선택 의존성

| 패키지 | 용도 | 필수 여부 | 미설치 시 동작 |
|---|---|---|---|
| `colorthief` | 이미지 팔레트 추출 | 선택 | 경고 메시지 출력, `imagePalette: null` |
| `lighthouse` (npx) | 성능 점수 측정 | 선택 | 경고 메시지 출력, `lighthouse: null` |

설치 방법:
```bash
pip install colorthief          # Python 패키지
npm install -g lighthouse       # 또는 npx가 자동 다운로드
```

---

## 7. 검증

| 검증 항목 | 결과 |
|---|---|
| Python 문법 검사 (`py_compile`) | 통과 |
| 런타임 임포트 검사 | httpx 등 런타임 의존성이 로컬에 없어 임포트 단계에서 중단 — 코드 자체의 문법/구조 오류는 아님 |
| 하위 호환성 검토 | 모든 새 필드가 optional, 기존 데이터 파싱에 영향 없음 |
