# 크롤러 개선 기획안 v2

> 실제 `cli.py` 코드베이스 기반 작성. Gemini 초안의 방향성을 수용하되, 구현상 문제점을 수정.

---

## 핵심 결정 사항 (먼저 확정)

| 항목 | 결정 | 이유 |
|------|------|------|
| `crawl` vs `deep-crawl` | **`crawl` 단일 확장** | `ia-scan`, `ux-scan` 등이 `crawl` 결과를 직접 참조. 분기하면 하위 명령 전부 수정 필요 |
| async 전환 | **하지 않음** | sync Playwright 안정적. Discovery만 httpx sync로 처리 가능 |
| 파일 분리 | **3개 모듈** (`discovery.py`, `extractor.py`, cli.py 유지) | 각 200줄+ 예상, 단일 파일 유지는 유지보수 어려움 |
| 콘텐츠 파일 생성 시점 | **2-pass** (수집 완료 후 일괄 경로 결정) | 크롤 중 파일 이동 시 race condition 방지. query string까지 반영한 안정적 경로 키 필요 |

---

## 현재 코드 상태 파악

```
cli.py:557  crawl()        max_pages=8, max_depth=2
cli.py:73   normalize_url  fragment만 제거, 쿼리파라미터 미처리
cli.py:121  load_robots_rules  Disallow만 파싱, Sitemap: 미처리
cli.py:367  collect_page_snapshot  본문 텍스트 없음
```

**이미 사용 가능한 의존성:** `beautifulsoup4`, `lxml`, `httpx` (pyproject.toml 확인)
→ sitemap 파싱에 추가 패키지 불필요.

---

## 구현 순서 (의존성 기준)

```
1. URL 정규화 강화       ← 다른 모든 것의 전제조건
2. discovery.py 신규     ← URL 정규화 기반
3. crawl() 개선          ← discovery 결과를 opt-in seed로 사용
4. extractor.py 신규     ← crawl 개선 완료 후
5. content/ 미러링       ← extractor 기반, query-safe 경로 사용
6. sitemap.json 생성     ← content/ 미러링 완료 후, seed URL을 루트로 사용
```

---

## Phase 1: URL 정규화 강화 (`cli.py` 수정)

### 현황
```python
# cli.py:73 - fragment만 제거, 쿼리파라미터 살아있음
def normalize_url(raw_url: str, base: str | None = None) -> str | None:
    ...
    return urlunparse(parsed._replace(fragment=""))
```

### 변경
```python
TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid", "_ga",
})

def normalize_url(raw_url: str, base: str | None = None) -> str | None:
    joined = urljoin(base or raw_url, raw_url)
    parsed = urlparse(joined)
    if parsed.scheme not in {"http", "https"}:
        return None
    # 트래킹 파라미터 제거, 나머지 정렬(일관성 확보)
    if parsed.query:
        kept = sorted(
            (k, v) for k, v in parse_qsl(parsed.query)
            if k not in TRACKING_PARAMS
        )
        query = urlencode(kept)
    else:
        query = ""
    # 후행 슬래시 제거 (경로가 /만인 경우 제외)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(parsed._replace(fragment="", query=query, path=path))
```

**영향 범위:** `normalize_url`을 호출하는 모든 곳에 자동 적용됨.

**보완 포인트:** query string이 남는 URL은 path만으로 콘텐츠 파일명을 만들면 덮어쓰기 된다. `content/` 경로는 `normalize_url()` 결과를 기준으로 query-safe suffix 또는 hash를 포함해야 한다.

---

## Phase 2: `discovery.py` 신규 생성

**목적:** BFS 시작 전 URL Pool을 최대한 확보. robots.txt에서 이미 origin을 가져오므로 httpx 추가 요청 최소화.

```python
# audit-runtime/src/webstart_audit/discovery.py

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
FEED_TIMEOUT = 10.0
MAX_SITEMAP_URLS = 2000  # 사이트맵이 너무 큰 경우 방어


@dataclass
class DiscoveryResult:
    urls: list[str] = field(default_factory=list)       # 중복 제거된 전체 URL
    sitemap_count: int = 0
    rss_count: int = 0
    source_detail: dict[str, int] = field(default_factory=dict)


def discover(origin: str, robots_text: str | None = None) -> DiscoveryResult:
    """
    robots.txt → sitemap.xml → RSS 순으로 URL을 수집.
    실패해도 빈 결과 반환 (크롤 자체는 항상 진행).
    """
    result = DiscoveryResult()
    seen: set[str] = set()

    sitemap_roots = _extract_sitemap_urls_from_robots(robots_text or "")
    if not sitemap_roots:
        # 공통 경로 시도
        sitemap_roots = [urljoin(origin, "/sitemap.xml"), urljoin(origin, "/sitemap_index.xml")]

    sitemap_urls = _collect_sitemap_urls(sitemap_roots, origin)
    for url in sitemap_urls:
        if url not in seen:
            seen.add(url)
            result.urls.append(url)
    result.sitemap_count = len(sitemap_urls)

    rss_urls = _collect_rss_urls(origin)
    new_rss = [u for u in rss_urls if u not in seen]
    result.urls.extend(new_rss)
    seen.update(new_rss)
    result.rss_count = len(rss_urls)

    result.source_detail = {
        "sitemap": result.sitemap_count,
        "rss": result.rss_count,
        "total_unique": len(result.urls),
    }
    return result


def _extract_sitemap_urls_from_robots(robots_text: str) -> list[str]:
    urls = []
    for line in robots_text.splitlines():
        parts = line.split(":", 1)
        if len(parts) == 2 and parts[0].strip().lower() == "sitemap":
            url = parts[1].strip()
            if url.startswith("http"):
                urls.append(url)
    return urls


def _collect_sitemap_urls(roots: list[str], origin: str, _depth: int = 0) -> list[str]:
    """sitemap index → child sitemap → URL 재귀 파싱. 최대 depth=3."""
    if _depth > 3:
        return []
    urls: list[str] = []
    for root_url in roots:
        try:
            resp = httpx.get(root_url, timeout=FEED_TIMEOUT, follow_redirects=True)
            if resp.status_code != 200:
                continue
            content = resp.content
            # gzip 처리: httpx가 자동 디코딩
            root_el = ET.fromstring(content)
            tag = root_el.tag.split("}")[-1] if "}" in root_el.tag else root_el.tag

            if tag == "sitemapindex":
                child_urls = [
                    loc.text.strip()
                    for sitemap_el in root_el.findall(f"{{{SITEMAP_NS}}}sitemap")
                    for loc in sitemap_el.findall(f"{{{SITEMAP_NS}}}loc")
                    if loc.text
                ]
                urls.extend(_collect_sitemap_urls(child_urls, origin, _depth + 1))
            elif tag == "urlset":
                for url_el in root_el.findall(f"{{{SITEMAP_NS}}}url"):
                    loc = url_el.find(f"{{{SITEMAP_NS}}}loc")
                    if loc is not None and loc.text:
                        candidate = loc.text.strip()
                        if urlparse(candidate).netloc == urlparse(origin).netloc:
                            urls.append(candidate)
                        if len(urls) >= MAX_SITEMAP_URLS:
                            break
        except Exception:
            continue
    return urls


def _collect_rss_urls(origin: str) -> list[str]:
    """홈페이지에서 RSS/Atom 링크를 찾아 entry URL 수집."""
    urls: list[str] = []
    try:
        resp = httpx.get(origin, timeout=FEED_TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return []
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "lxml")
        feed_links = soup.find_all("link", type=lambda t: t and ("rss" in t or "atom" in t))
        for link in feed_links[:3]:
            feed_url = urljoin(origin, link.get("href", ""))
            if not feed_url:
                continue
            try:
                feed_resp = httpx.get(feed_url, timeout=FEED_TIMEOUT, follow_redirects=True)
                feed_root = ET.fromstring(feed_resp.content)
                # RSS 2.0
                for item in feed_root.findall(".//item/link"):
                    if item.text:
                        urls.append(item.text.strip())
                # Atom
                for entry in feed_root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                    link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                    if link_el is not None:
                        href = link_el.get("href", "")
                        if href:
                            urls.append(href)
            except Exception:
                continue
    except Exception:
        pass
    return urls
```

---

## Phase 3: `crawl()` 개선 (`cli.py` 수정)

### 시그니처 변경

```python
@app.command()
def crawl(
    url: str = typer.Argument(...),
    project_dir: Path = typer.Option(Path(".")),
    max_pages: int = typer.Option(8, min=1, max=50),
    max_depth: int = typer.Option(2, min=0, max=5),
    delay_ms: int = typer.Option(1000),
    discover: bool = typer.Option(False, help="sitemap/RSS 선행 수집"),
    full_content: bool = typer.Option(False, help="본문 콘텐츠 추출 및 content/ 미러링"),
    retry: int = typer.Option(2, min=0, max=5, help="실패 페이지 재시도 횟수"),
) -> None:
```

**`discover=False`, `full_content=False` 기본값인 이유:** 기존 파이프라인(`ux-scan` 등)의 동작을 깨지 않음. 명시적으로 opt-in.

### Discovery 통합

```python
# crawl() 내부 BFS 시작 전
robots_rules, robots_loaded, robots_text = load_robots_rules(origin)
if discover:
    from webstart_audit.discovery import discover as run_discovery
    disc = run_discovery(origin, robots_text)
    for disc_url in disc.urls:
        normed = normalize_url(disc_url)
        if normed and normed not in visited and same_origin(normed, origin):
            queue.append((normed, 1))  # depth=1 (sitemap URL은 홈 아래로 간주)
    console.print(f"discovery: {disc.source_detail}")
    write_json(
        paths["raw"] / "discovery-report.json",
        {
            "origin": origin,
            "generatedAt": date.today().isoformat(),
            "sourceDetail": disc.source_detail,
            "urls": disc.urls,
        },
    )
```

**보완 포인트:** `robots.txt`는 한 번만 가져오고, 그 결과를 `load_robots_rules()`와 `discover()`가 함께 써야 한다. 지금처럼 별도 호출을 두 번 만들면 요청만 늘고 행동은 같다. `load_robots_rules()`는 `rules`, `loaded`, `robots_text`를 함께 반환하도록 바꾸는 편이 안전하다.

### Retry 로직

```python
def goto_with_retry(page, url: str, retry_count: int) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as exc:
            last_exc = exc
            if attempt < retry_count:
                page.wait_for_timeout(2000)
    raise last_exc  # type: ignore[misc]
```

---

## Phase 4: `extractor.py` 신규 생성

**`full_content=True`일 때만 호출됨.**

```python
# audit-runtime/src/webstart_audit/extractor.py

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


def extract_content(page: Any) -> dict:
    """Playwright 페이지에서 구조화된 본문을 추출."""
    return page.evaluate("""
        () => {
            const main = document.querySelector('main, article, [role=main], .content, #content, #main');
            const root = main || document.body;

            // 섹션 구조화 (nav/header/footer 제외)
            const sections = Array.from(root.querySelectorAll('section, article'))
                .filter(s => !s.closest('nav, header, footer'))
                .map(s => ({
                    id: s.id || null,
                    heading: s.querySelector('h1,h2,h3,h4')?.textContent?.trim() || null,
                    text: s.innerText.trim(),  // 전문 (truncation 없음)
                    images: Array.from(s.querySelectorAll('img')).map(img => ({
                        src: img.src, alt: img.alt || null,
                        width: img.naturalWidth || null, height: img.naturalHeight || null,
                    }))
                }));

            // 전체 본문 (섹션 구분 없이)
            const bodyText = root.innerText.trim();

            // JSON-LD
            const jsonLd = Array.from(
                document.querySelectorAll('script[type="application/ld+json"]')
            ).map(s => { try { return JSON.parse(s.textContent); } catch { return null; } })
             .filter(Boolean);

            // Open Graph
            const og = {};
            document.querySelectorAll('meta[property^="og:"], meta[name^="og:"]').forEach(m => {
                const key = m.getAttribute('property') || m.getAttribute('name');
                og[key] = m.content;
            });

            // 전체 이미지 (중복 제거)
            const seenSrc = new Set();
            const images = Array.from(document.querySelectorAll('img')).reduce((acc, img) => {
                if (img.src && !seenSrc.has(img.src)) {
                    seenSrc.add(img.src);
                    acc.push({ src: img.src, alt: img.alt || null,
                                width: img.naturalWidth || null, height: img.naturalHeight || null,
                                loading: img.loading || null });
                }
                return acc;
            }, []);

            return {
                bodyText,
                sections,
                images,
                jsonLd,
                og,
                lang: document.documentElement.lang || null,
                canonical: document.querySelector('link[rel=canonical]')?.href || null,
                wordCount: bodyText.split(/\s+/).filter(Boolean).length,
            };
        }
    """)


def url_to_content_path(url: str) -> Path:
    """
    URL 경로를 _audit/content/ 하위 파일 경로로 변환.
    query string이 있는 URL은 덮어쓰기를 막기 위해 안정적인 suffix를 붙인다.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "_index"
    segments = path.split("/")
    filename = segments[-1]
    if parsed.query:
        import hashlib

        query_hash = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:10]
        filename = f"{filename}__q-{query_hash}"
    return Path("_audit/content") / "/".join(segments[:-1]) / f"{filename}.md"


def resolve_content_paths(all_urls: list[str]) -> dict[str, Path]:
    """
    2-pass: 전체 URL 목록을 받아 각 URL의 최종 파일 경로를 결정.
    부모 URL이 자식을 가지면 file.md → dir/_index.md로 승격.
    """
    # path string → 파일 경로 (초기: leaf)
    path_map: dict[str, Path] = {}
    # 각 URL의 path segment
    url_paths = {url: urlparse(url).path.strip("/") for url in all_urls}

    # 자식이 있는 경로 집합 확인
    all_segments = {p for p in url_paths.values() if p}
    has_children: set[str] = set()
    for seg in all_segments:
        parts = seg.split("/")
        for i in range(1, len(parts)):
            has_children.add("/".join(parts[:i]))

    for url, seg in url_paths.items():
        if not seg:
            path_map[url] = Path("_audit/content/_index.md")
        elif seg in has_children:
            if urlparse(url).query:
                path_map[url] = url_to_content_path(url)
            else:
                path_map[url] = Path("_audit/content") / seg / "_index.md"
        else:
            path_map[url] = url_to_content_path(url)

    return path_map


def render_content_md(
    *,
    url: str,
    title: str,
    depth: int,
    status: int | None,
    content: dict,
    screenshot: str | None,
    screenshot_mobile: str | None,
    crawled_at: str,
) -> str:
    word_count = content.get("wordCount", 0)
    reading_time = max(1, word_count // 200)
    canonical = content.get("canonical") or url
    lang = content.get("lang") or ""
    og = content.get("og") or {}

    og_lines = "\n".join(f"  {k}: \"{v}\"" for k, v in og.items()) if og else ""
    json_ld_types = [item.get("@type", "Unknown") for item in (content.get("jsonLd") or [])]

    sections_text = ""
    for sec in content.get("sections") or []:
        heading = sec.get("heading")
        text = (sec.get("text") or "").strip()
        if heading:
            sections_text += f"\n## {heading}\n{text}\n"
        elif text:
            sections_text += f"\n{text}\n"

    images = content.get("images") or []
    images_table = ""
    if images:
        rows = "\n".join(
            f"| {img['src']} | {img.get('alt') or ''} | {img.get('width') or ''} | {img.get('height') or ''} |"
            for img in images[:50]
        )
        images_table = f"\n## 이미지\n| src | alt | width | height |\n|-----|-----|-------|--------|\n{rows}\n"

    frontmatter = f"""---
url: {url}
title: "{title}"
depth: {depth}
status: {status or "unknown"}
canonical: {canonical}
lang: {lang}
{f"og:\n{og_lines}" if og_lines else "og: {}"}
structured_data: {json_ld_types}
screenshot: {screenshot or ""}
screenshot_mobile: {screenshot_mobile or ""}
crawled_at: "{crawled_at}"
word_count: {word_count}
reading_time: {reading_time}
---"""

    body = f"# {title}\n{sections_text or (content.get('bodyText') or '').strip()}{images_table}"
    return f"{frontmatter}\n\n{body}\n"
```

---

## Phase 5: Content 미러링 통합 (`crawl()` 완료 후)

```python
# crawl() 내 BFS 루프 종료 후, full_content=True인 경우
if full_content and pages:
    from datetime import datetime
    from webstart_audit.extractor import resolve_content_paths, render_content_md

    all_urls = [p["url"] for p in pages]
    path_map = resolve_content_paths(all_urls)

    with sync_playwright() as pw2:
        browser2 = pw2.chromium.launch()
        content_page = browser2.new_page(viewport={"width": 1920, "height": 1080})
        for page_data in pages:
            page_url = page_data["url"]
            file_path = resolved / path_map[page_url]
            file_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                content_page.goto(page_url, wait_until="networkidle", timeout=30000)
                content = extract_content(content_page)
                md = render_content_md(
                    url=page_url,
                    title=page_data["title"],
                    depth=page_data["depth"],
                    status=page_data["status"],
                    content=content,
                    screenshot=page_data.get("screenshot"),
                    screenshot_mobile=page_data.get("screenshot_mobile"),
                    crawled_at=datetime.now().isoformat(timespec="seconds"),
                )
                file_path.write_text(md, encoding="utf-8")
            except Exception:
                continue
        browser2.close()

    # sitemap.json 생성
    _build_sitemap_json(pages, path_map, resolved, root_url=normalized_url)
```

### `_build_sitemap_json` 구현

```python
def _build_sitemap_json(
    pages: list[dict],
    path_map: dict[str, Path],
    project_dir: Path,
    root_url: str,
) -> None:
    """URL 목록에서 트리 구조 sitemap.json을 생성."""
    from datetime import datetime

    url_meta = {p["url"]: p for p in pages}

    def build_node(url: str, children_map: dict[str, list[str]]) -> dict:
        children_urls = children_map.get(url, [])
        return {
            "url": url,
            "path": urlparse(url).path or "/",
            "title": url_meta[url]["title"],
            "depth": url_meta[url]["depth"],
            "contentFile": str(path_map[url]),
            "children": [build_node(c, children_map) for c in children_urls],
        }

    # parent-child 관계 구성 (seed URL 기준으로 경로 기반)
    children_map: dict[str, list[str]] = {}
    for page in sorted(pages, key=lambda p: p["depth"]):
        if page["url"] == root_url:
            continue
        page_path = urlparse(page["url"]).path.strip("/")
        segments = page_path.split("/")
        if len(segments) == 1:
            children_map.setdefault(root_url, []).append(page["url"])
        else:
            parent_path = "/" + "/".join(segments[:-1])
            parent_url = next(
                (p["url"] for p in pages if urlparse(p["url"]).path == parent_path),
                root_url,
            )
            if parent_url:
                children_map.setdefault(parent_url, []).append(page["url"])

    tree = build_node(root_url, children_map)
    payload = {
        "root": urlparse(pages[0]["url"]).scheme + "://" + urlparse(pages[0]["url"]).netloc if pages else "",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "totalPages": len(pages),
        "tree": tree,
    }
    write_json(project_dir / "_audit" / "sitemap.json", payload)
```

---

## 최종 산출물 구조

```
_audit/
├── target.md
├── scraped-data.json           # 기존 레거시 포맷 유지 (하위 호환)
├── sitemap.json                # NEW: 트리 구조 (full_content=True 시, seed URL 기준)
├── raw/
│   ├── crawl-data.json
│   └── discovery-report.json  # NEW: discover=True 시 저장
├── derived/
│   ├── pages.json
│   ├── link-graph.json
│   ├── ux-summary.json
│   └── ia-summary.json
├── content/                   # NEW: full_content=True 시, query-safe 파일명 사용
│   ├── _index.md              # /
│   ├── about/
│   │   ├── _index.md          # /about (자식이 있으므로 _index)
│   │   └── team.md            # /about/team
│   └── contact.md             # /contact
└── screenshots/
```

---

## 구현 우선순위

| 순위 | 항목 | 변경 파일 | 공수 |
|------|------|---------|------|
| **1** | URL 정규화 강화 (tracking params 제거) | `cli.py` | 소 |
| **2** | `load_robots_rules` → `Sitemap:` 파싱 추가, robots.txt 1회 로드 | `cli.py` | 소 |
| **3** | `discovery.py` 신규 | 신규 | 중 |
| **4** | `crawl()` `--discover` / `--full-content` 옵션 | `cli.py` | 소 |
| **5** | `crawl()` retry 로직 | `cli.py` | 소 |
| **6** | `extractor.py` 신규 + `resolve_content_paths` (query-safe) | 신규 | 중 |
| **7** | `crawl()` content/ 생성 | `cli.py` | 중 |
| **8** | `sitemap.json` 출력 + `discovery-report.json` 저장 | `cli.py` | 소 |

**1~5: 기존 파이프라인 영향 없이 즉시 배포 가능**  
**6~8: `--full-content` 플래그 뒤에 있으므로 opt-in, 기존 동작 불변**

---

## 하지 않는 것 (의도적 제외)

- **`deep-crawl` 명령 신설**: `--full-content` 플래그로 충분. CLI 분기는 혼란만 가중
- **async 전환**: sync Playwright 잘 동작. Discovery는 httpx sync로 처리 가능
- **SPA dynamic route 탐지**: 복잡도 대비 효과 낮음 (우선순위 원안 9번)
- **무한 스크롤 처리**: 기본값 제외, 후속 `--scroll` 플래그로 추후 추가
- **2000자 텍스트 truncation**: 제거. 전문 저장, 프리뷰 필요 시 별도 `preview` 필드 추가
