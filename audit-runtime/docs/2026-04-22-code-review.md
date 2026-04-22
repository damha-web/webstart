# audit-runtime 코드 검토 결과

> 검토일: 2026-04-22
> 범위: discovery.py, extractor.py, cli.py, test_runtime.py
> 검토자: Claude Code

## 한 줄 요약

작업의 기능적 완성도는 높으나, `mask_pii` 중복, `full_content` 무delay, discovery depth 처리에서 개선이 필요합니다.

---

## 1. 심각한 문제 (즉시 개선 필요)

### 1.1 `mask_pii` 함수 중복

**위치**: `cli.py:131-145` / `extractor.py:13-27`

**상황**:
- 동일한 함수가 두 파일에 독립적으로 정의됨
- 이메일, 전화, 카드번호, Bearer 토큰 마스킹 로직이 같음

**위험**:
- 향후 보안 요구사항 변경 시 한쪽만 수정될 가능성 높음
- PII 마스킹 수준이 파일마다 달라질 수 있음
- 유지보수 부채 증가

**권장**:
```
utils.py 또는 security.py를 만들고:
  def mask_pii(value: str) -> str: ...

cli.py, extractor.py에서:
  from webstart_audit.security import mask_pii
```

---

### 1.2 `--full-content` 실행 시 무제한 페이지 방문

**위치**: `cli.py:820-863` (full_content 블록)

**상황**:
```python
for page_data in pages:
    # ... 
    goto_with_retry(content_page, page_url, retry)
    # delay_ms 적용 안 함
```

**문제**:
1. 메인 크롤에서 이미 모든 페이지를 방문했는데, `full_content` 재활성화 시 다시 방문
2. 두 번째 루프에는 `delay_ms` 전혀 없음 → 서버에 연속 요청 폭주
3. 실제 운영 사이트에서 rate limiting 또는 차단 위험

**예시**:
```
webstart-audit crawl https://example.com --full-content --delay-ms=1000
→ 모든 페이지를 1초 간격으로 방문 (첫 크롤)
→ 모든 페이지를 0초 간격으로 다시 방문 (content 추출)
→ 서버 부하 2배
```

**권장**:
```python
# cli.py:825 근처에 delay 추가
if delay_ms:
    page.wait_for_timeout(delay_ms)
```

---

### 1.3 Discovery URL이 모두 depth=1로 주입

**위치**: `cli.py:637-644`

**상황**:
```python
if discover:
    disc = run_discovery(origin, robots_text)
    for disc_url in disc.urls:
        normed = normalize_url(disc_url)
        if normed and normed not in visited and same_origin(normed, origin):
            queue.append((normed, 1))  # ← 모두 depth=1
```

**문제**:
- 사이트맵에서 수집된 모든 URL(루트 포함)이 depth=1로 들어감
- `max_depth=1`로 실행할 때, depth 1 페이지의 자식(`depth=2`)은 탐색되지 않음
- 사용자 의도: "사이트맵으로 발견한 URL도 동일하게 탐색" → 결과: "발견 URL만 탐색 차단"

**예시**:
```
웹사이트 구조:
  / → /about → /about/team
  
robots.txt Sitemap: /sitemap.xml
사이트맵 콘텐츠: /about/team
discovery_urls = ["/about/team"]

max_depth=1 크롤:
  큐: [(root, 0), (about/team, 1)]
  
  root 방문 (depth 0):
    → 발견한 /about 추가 (depth=1)
    → depth < max_depth (0 < 1) ✓ 큐에 추가
  
  /about/team 방문 (depth 1):
    → 발견한 /about/team/member 추가 (depth=2)
    → depth < max_depth (1 < 1) ✗ 큐에 추가 안 함
```

**권장**:
```python
# discovery URL은 root와 동일하게 depth=0으로
queue.append((normed, 0))

# 또는 depth에 무관하게 처리하되, 사용자에게 명시
# (max_depth=1은 "root에서 출발한 1단계" 의미)
```

---

## 2. 개선 여지 (운영 중 보충)

### 2.1 `render_content_md` 테스트 없음

**위치**: `tests/test_runtime.py`

**상황**:
- `render_content_md` 함수는 frontmatter YAML + 본문 생성
- `mask_pii` 콜 포함
- 테스트 없음 (`# pragma: no cover`)

**권장**:
```python
def test_render_content_md_masks_pii_and_formats(self):
    content = {
        "bodyText": "Contact: user@example.com",
        "sections": [{"heading": "About", "text": "Phone: 01012345678"}],
        "images": [],
        "jsonLd": [],
        "og": {},
    }
    md = render_content_md(
        url="https://example.com/test",
        title="Test Page",
        depth=0,
        status=200,
        content=content,
        screenshot=None,
        screenshot_mobile=None,
        crawled_at="2026-04-22T10:00:00",
    )
    
    # 이메일 마스킹 확인
    self.assertIn("***@***.***", md)
    self.assertNotIn("user@example.com", md)
    
    # 전화번호 마스킹 확인
    self.assertIn("***-****-****", md)
    self.assertNotIn("01012345678", md)
    
    # frontmatter 있는지 확인
    self.assertIn("---", md)
    self.assertIn("url:", md)
```

---

### 2.2 `build_node` 재귀 깊이 한계

**위치**: `extractor.py:263-270`

**상황**:
```python
def build_node(url: str, children_map: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "url": url,
        "children": [build_node(child, children_map) for child in children_map.get(url, [])],
    }
```

**문제**:
- Python 기본 재귀 한도 1000
- 깊은 경로 사이트 (depth > 500) 또는 매우 계층화된 구조에서 `RecursionError`

**예시**:
```
URL 구조: / → /a → /a/b → /a/b/c → ... (500+ 레벨)
→ build_node() 호출 500+ 번
→ sys.getrecursionlimit() 기본값 1000 주변에서 실패 가능
```

**권장** (낮은 우선순위, 실제 발생 가능성 낮음):
```python
def build_node(url: str, children_map: dict[str, list[str]]) -> dict[str, Any]:
    stack = [(url, None)]
    result = {}
    
    while stack:
        current_url, parent_key = stack.pop()
        node = {"url": current_url, "children": []}
        result[current_url] = node
        
        for child_url in children_map.get(current_url, []):
            stack.append((child_url, current_url))
    
    # ... 트리 재구성
```

---

### 2.3 `_collect_sitemap_urls`가 DFS 구현

**위치**: `discovery.py:78`

**상황**:
```python
stack: list[tuple[str, int]] = [(root, 0) for root in roots]
while stack:
    sitemap_url, depth = stack.pop()  # ← DFS (LIFO)
    # ...
    stack.extend((child_url, depth + 1) for child_url in child_urls)
```

**문제**:
- `MAX_SITEMAP_URLS=2000` 제한에 도달할 때, 깊은 사이트맵이 먼저 수집될 수 있음
- 사용자 기대: 넓고 균형잡힌 수집 → 실제: 좁고 깊은 수집

**예시**:
```
사이트맵 구조:
  sitemap_index.xml
    ├─ sitemap-a.xml (100 URL)
    └─ sitemap-index-b.xml
        ├─ sitemap-b1.xml (200 URL)
        └─ sitemap-b2.xml (200 URL)

DFS 순서:
  1. sitemap-b2.xml → 200 URL 추가
  2. sitemap-b1.xml → 200 URL 추가
  3. MAX 도달 (400/2000)
  4. sitemap-a.xml은 수집 안 됨
```

**권장** (낮은 우선순위):
```python
from collections import deque

stack: deque[tuple[str, int]] = deque([(root, 0) for root in roots])
# ...
stack.appendleft((child_url, depth + 1))  # BFS
```

---

## 3. 긍정 평가

| 항목 | 상태 |
|------|------|
| `normalize_url` tracking param 제거 | ✅ 완성 |
| `load_robots_rules` 반환값 (rules, loaded, text) | ✅ 잘 설계됨 |
| `resolve_content_paths` 2-pass depth 감지 | ✅ 탄탄함 |
| `discover` sitemap/RSS 통합 | ✅ 동작 확인 |
| PII 마스킹 패턴 (이메일, 전화, 카드, Bearer) | ✅ 포괄적 |
| 기본값 유지 (`--discover`, `--full-content` off) | ✅ 호환성 고려 |
| 테스트 커버리지 (normalize, resolve, discover, build) | ✅ 핵심 로직 검증 |

---

## 4. 다음 단계

### 4.1 긴급 (이번 주)
- [ ] `mask_pii` 통합 (security.py)
- [ ] `--full-content` delay 추가
- [ ] discovery depth 처리 확인 (depth=0 vs depth=1)

### 4.2 운영 (다음 검증)
- [ ] `render_content_md` 테스트 추가
- [ ] 500+ 페이지 사이트에서 `build_node` 성능 테스트
- [ ] sitemap DFS → BFS 전환 고려

### 4.3 문서 (보고서 정리)
- [ ] `--discover` 동작 방식 문서화 (depth 처리)
- [ ] `--full-content` 서버 부하 가이드 추가
- [ ] PII 마스킹 규칙 명시

---

## 5. 총평

작업 자체는 **구조적으로 견고하고 기능적으로 완성도 높습니다.** 새로운 discovery와 full-content 파이프라인이 의도대로 동작하며, 기존 호환성도 잘 유지했습니다.

다만 **운영 단계에서 예상되는 문제점 3가지** (`mask_pii` 중복, full_content 무delay, discovery depth)는 지금 바로 손봐야 향후 유지보수와 사이트맥 실행에서 혼란이 없을 것 같습니다.

---

**예상 소요**: 긴급 항목 2-3시간, 전체 개선 반일
