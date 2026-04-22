from __future__ import annotations

import json
import platform
import re
from collections import Counter, deque
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
import typer
from pydantic import BaseModel
from rich.console import Console

from webstart_audit.security import mask_pii

app = typer.Typer(help="WebStart audit runtime CLI")
console = Console()

DEFAULT_PURPOSE = "기존 사이트 역설계 및 리뉴얼 기획 참고"
SENSITIVE_HEADERS = {"set-cookie", "authorization", "x-csrf-token", "cookie"}
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "ref",
        "source",
        "mc_cid",
        "mc_eid",
        "_ga",
    }
)
STAGE_META = [
    ("target", "0. 대상 등록", "/audit"),
    ("ux", "1. UX", "/audit-ux"),
    ("ia", "2. IA", "/audit-ia"),
    ("tech", "3. Tech", "/audit-tech"),
    ("db", "4. DB", "/audit-db"),
    ("report", "5. 종합 보고서", "/audit"),
    ("handover", "6. 제작팀 인계", "/audit"),
]
STATUS_LABELS = {
    "pending": "⏳ 대기",
    "in_progress": "🟡 진행 중",
    "done": "✅ 완료",
    "partial": "🟠 부분 완료",
    "blocked": "⛔ 차단",
}


class PageSnapshot(BaseModel):
    url: str
    title: str
    depth: int
    status: int | None
    head: str
    nav_links: list[dict[str, str]]
    all_links: list[dict[str, str]]
    scripts: list[str]
    styles: list[str]
    colors: list[dict[str, Any]]
    fonts: list[dict[str, Any]]
    forms: list[dict[str, Any]]
    meta: dict[str, Any]
    performance: dict[str, Any]
    screenshot: str | None = None
    screenshot_mobile: str | None = None


def ensure_audit_dirs(project_dir: Path) -> dict[str, Path]:
    audit_dir = project_dir / "_audit"
    paths = {
        "audit": audit_dir,
        "raw": audit_dir / "raw",
        "derived": audit_dir / "derived",
        "reports": audit_dir / "reports",
        "screenshots": audit_dir / "screenshots",
        "content": audit_dir / "content",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def normalize_url(raw_url: str, base: str | None = None) -> str | None:
    joined = urljoin(base or raw_url, raw_url)
    parsed = urlparse(joined)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.query:
        kept = sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key not in TRACKING_PARAMS
        )
        query = urlencode(kept, doseq=True)
    else:
        query = ""
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(parsed._replace(fragment="", query=query, path=path))


def slugify_url(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    base = parsed.path.strip("/") or "home"
    base = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-") or "home"
    if parsed.query:
        query = re.sub(r"[^a-zA-Z0-9_-]+", "-", parsed.query).strip("-")
        if query:
            base = f"{base}-{query}"
    return base[:80]


def dedupe_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for link in links:
        href = link.get("href", "").strip()
        if not href or href in seen:
            continue
        seen.add(href)
        result.append(link)
    return result


def load_robots_rules(origin: str) -> tuple[list[str], bool, str]:
    robots_url = urljoin(origin, "/robots.txt")
    try:
        response = httpx.get(robots_url, timeout=10.0, follow_redirects=True)
    except Exception:
        return [], False, ""

    if response.status_code != 200 or not response.text.strip():
        return [], False, ""

    rules: list[str] = []
    applies = False
    for raw_line in response.text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            applies = value in {"*", "webstartaudit", "webstart-audit"}
            continue
        if applies and key == "disallow" and value:
            rules.append(value)
    return rules, True, response.text


def is_allowed_by_robots(url: str, origin: str, disallow_rules: list[str]) -> bool:
    if not same_origin(url, origin):
        return True
    path = urlparse(url).path or "/"
    return not any(path.startswith(rule) for rule in disallow_rules if rule != "/")


def render_target_md(
    *,
    site_name: str,
    url: str,
    site_type: str = "미분류",
    purpose: str = DEFAULT_PURPOSE,
) -> str:
    return f"""# 분석 대상 정보

## 기본 정보
- **사이트명:** {site_name}
- **URL:** {url}
- **사이트 유형:** {site_type}
- **분석 목적:** {purpose}
- **고객 제공 권한:** 공개 페이지만

## 입력 데이터
- [x] URL 자동 수집 (webstart-audit runtime)
- [ ] 추가 데이터 (사용자 제공 시 체크)

## 특이사항
(분석 시 참고할 사항)
"""


def default_status_payload() -> dict[str, Any]:
    stages = {}
    for stage_id, label, skill in STAGE_META:
        stages[stage_id] = {
            "label": label,
            "skill": skill,
            "status": "pending",
            "completed_at": None,
            "notes": "",
            "artifacts": [],
        }
    return {
        "version": "1.0",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "stages": stages,
    }


def render_status_md_from_payload(payload: dict[str, Any]) -> str:
    rows = []
    for stage_id, _, _ in STAGE_META:
        stage = payload["stages"][stage_id]
        rows.append(
            "| {label} | {skill} | {status} | {completed_at} | {notes} |".format(
                label=stage["label"],
                skill=stage["skill"],
                status=STATUS_LABELS.get(stage["status"], stage["status"]),
                completed_at=stage["completed_at"] or "-",
                notes=stage["notes"] or "-",
            )
        )
    return "\n".join(
        [
            "# Audit Pipeline Status",
            "",
            "| 단계 | 스킬 | 상태 | 완료일 | 비고 |",
            "|------|------|------|--------|------|",
            *rows,
            "",
        ]
    )


def load_status_payload(project_dir: Path) -> dict[str, Any]:
    status_path = project_dir / "_audit" / "status.json"
    if status_path.exists():
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            if "stages" in payload:
                for stage_id, label, skill in STAGE_META:
                    payload["stages"].setdefault(
                        stage_id,
                        {
                            "label": label,
                            "skill": skill,
                            "status": "pending",
                            "completed_at": None,
                            "notes": "",
                            "artifacts": [],
                        },
                    )
                return payload
        except json.JSONDecodeError:
            pass
    return default_status_payload()


def save_status_payload(project_dir: Path, payload: dict[str, Any]) -> None:
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    audit_dir = project_dir / "_audit"
    write_json(audit_dir / "status.json", payload)
    (audit_dir / "status.md").write_text(
        render_status_md_from_payload(payload),
        encoding="utf-8",
    )


def mark_stage(
    project_dir: Path,
    stage_id: str,
    *,
    status: str,
    notes: str = "",
    artifacts: list[str] | None = None,
) -> None:
    payload = load_status_payload(project_dir)
    stage = payload["stages"][stage_id]
    stage["status"] = status
    stage["notes"] = notes
    stage["artifacts"] = artifacts or stage.get("artifacts", [])
    stage["completed_at"] = date.today().isoformat() if status == "done" else None
    save_status_payload(project_dir, payload)


def reset_downstream_stages(project_dir: Path, stage_id: str) -> None:
    payload = load_status_payload(project_dir)
    seen = False
    for current_stage, _, _ in STAGE_META:
        if current_stage == stage_id:
            seen = True
            continue
        if not seen:
            continue
        payload["stages"][current_stage]["status"] = "pending"
        payload["stages"][current_stage]["completed_at"] = None
        payload["stages"][current_stage]["notes"] = ""
        payload["stages"][current_stage]["artifacts"] = []
    save_status_payload(project_dir, payload)


def read_target_url(project_dir: Path) -> str | None:
    target_path = project_dir / "_audit" / "target.md"
    if not target_path.exists():
        return None

    match = re.search(
        r"^\- \*\*URL:\*\*\s+(?P<url>\S+)\s*$",
        target_path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group("url") if match else None


def read_target_name(project_dir: Path) -> str:
    target_path = project_dir / "_audit" / "target.md"
    if not target_path.exists():
        return "(제목 없음)"

    match = re.search(
        r"^\- \*\*사이트명:\*\*\s+(?P<name>.+?)\s*$",
        target_path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return match.group("name") if match else "(제목 없음)"


def load_crawl_urls(project_dir: Path, fallback_url: str) -> list[str]:
    crawl_path = project_dir / "_audit" / "raw" / "crawl-data.json"
    if not crawl_path.exists():
        return [fallback_url]

    try:
        payload = json.loads(crawl_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [fallback_url]

    urls = [page.get("url") for page in payload.get("pages", []) if page.get("url")]
    unique_urls = list(dict.fromkeys(urls))
    return unique_urls or [fallback_url]


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def filter_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in SENSITIVE_HEADERS
    }


def same_origin(url: str, origin: str) -> bool:
    return urlparse(url).netloc == urlparse(origin).netloc


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def rgb_to_hex(color_value: str) -> str:
    match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color_value)
    if not match:
        return color_value
    r, g, b = (int(match.group(i)) for i in range(1, 4))
    return f"#{r:02X}{g:02X}{b:02X}"


def collect_page_snapshot(page: Any, *, current_url: str, depth: int) -> dict[str, Any]:
    page.wait_for_load_state("networkidle")
    return page.evaluate(
        """
        ({ currentUrl, depth }) => {
          const pickText = (value) => (value || '').replace(/\\s+/g, ' ').trim();

          const colors = {};
          Array.from(document.querySelectorAll('*')).slice(0, 350).forEach((el) => {
            const style = getComputedStyle(el);
            ['color', 'backgroundColor', 'borderColor'].forEach((prop) => {
              const value = style[prop];
              if (!value || value === 'rgba(0, 0, 0, 0)' || value === 'transparent') return;
              colors[value] = (colors[value] || 0) + 1;
            });
          });

          const fonts = {};
          Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6,p,a,span,button,li,label'))
            .slice(0, 250)
            .forEach((el) => {
              const style = getComputedStyle(el);
              const key = [style.fontFamily, style.fontSize, style.fontWeight].join('|');
              if (!fonts[key]) {
                fonts[key] = {
                  family: style.fontFamily,
                  size: style.fontSize,
                  weight: style.fontWeight,
                  tag: el.tagName,
                  count: 0
                };
              }
              fonts[key].count += 1;
            });

          return {
            url: currentUrl,
            depth,
            title: document.title,
            head: document.head.innerHTML,
            navLinks: Array.from(document.querySelectorAll('nav a, header a, [role=navigation] a'))
              .map((a) => ({
                text: pickText(a.textContent),
                href: a.href || ''
              }))
              .filter((link) => link.href),
            allLinks: Array.from(document.querySelectorAll('a[href]'))
              .map((a) => ({
                text: pickText(a.textContent),
                href: a.href || '',
                parent: a.closest('nav,header,footer,main,aside,section')?.tagName || 'BODY'
              }))
              .filter((link) => link.href),
            scripts: Array.from(document.querySelectorAll('script[src]')).map((el) => el.src),
            styles: Array.from(document.querySelectorAll('link[rel=stylesheet]')).map((el) => el.href),
            colors: Object.entries(colors)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 25)
              .map(([value, count]) => ({ value, count })),
            fonts: Object.values(fonts)
              .sort((a, b) => b.count - a.count)
              .slice(0, 20),
            forms: Array.from(document.querySelectorAll('form')).map((form) => ({
              action: form.action || '',
              method: (form.method || 'get').toUpperCase(),
              fields: Array.from(form.querySelectorAll('input,select,textarea')).map((field) => ({
                name: field.name || field.id || '',
                type: field.type || field.tagName.toLowerCase(),
                required: !!field.required,
                placeholder: field.placeholder || ''
              }))
            })),
            meta: {
              description: document.querySelector('meta[name=description]')?.content || '',
              canonical: document.querySelector('link[rel=canonical]')?.href || '',
              h1: Array.from(document.querySelectorAll('h1')).map((el) => pickText(el.textContent)),
              h2: Array.from(document.querySelectorAll('h2')).map((el) => pickText(el.textContent))
            }
          };
        }
        """,
        {"currentUrl": current_url, "depth": depth},
    )


def goto_with_retry(page: Any, url: str, retry_count: int) -> Any:
    last_exc: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            return page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as exc:
            last_exc = exc
            if attempt < retry_count:
                page.wait_for_timeout(2000)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"failed to navigate to {url}")


def render_client_brief(
    *,
    brand_name: str,
    reference_url: str,
    site_type: str,
    key_goal: str,
    success_metric: str,
    features: list[str],
    additional_requests: list[str],
) -> str:
    feature_checks = [
        "메인 홈페이지",
        "포트폴리오/갤러리",
        "서비스 소개",
        "팀/회사 소개",
        "블로그/뉴스",
        "문의 폼",
        "로그인/회원가입",
        "관리자 페이지",
        "결제 기능",
        "다국어 지원",
    ]
    checked_lines = []
    for item in feature_checks:
        checked = "[x]" if item in features else "[ ]"
        checked_lines.append(f"- {checked} {item}")
    extra = [feature for feature in features if feature not in feature_checks]
    checked_lines.append(f"- [ ] 기타: {', '.join(extra)}" if extra else "- [ ] 기타: ")

    requests_text = "\n".join(f"- {request}" for request in additional_requests) or "- "
    return f"""# 클라이언트 브리프

> audit runtime이 검수 결과를 바탕으로 자동 생성한 초안입니다. /pm 실행 전 사람이 한 번 검토하세요.

## 기본 정보
- **업종:** {site_type}
- **회사명/브랜드명:** {brand_name}
- **담당자:** 

## 프로젝트 목표
- **핵심 목표:** {key_goal}
- **성공 기준:** {success_metric}

## 타겟 고객
- **연령/성별:** 
- **지역:** 
- **관심사/고민:** 

## 예산 및 일정
- **예산 범위:** 
- **희망 완성일:** 
- **시간당 단가:** 

## 필수 기능 (해당 항목에 체크)
{chr(10).join(checked_lines)}

## 보유 자료
- [ ] 로고 파일 보유
- [ ] 사진/이미지 보유
- [ ] 카피라이팅(텍스트) 보유
- [ ] 참고 사이트: {reference_url}

## 추가 요청사항
{requests_text}
"""


@app.command()
def doctor() -> None:
    """현재 런타임 설치 상태를 점검합니다."""

    try:
        import playwright  # noqa: F401

        playwright_status = "ok"
    except Exception as exc:  # pragma: no cover
        playwright_status = f"error: {exc}"

    console.print("[bold]WebStart Audit Runtime[/bold]")
    console.print(f"Python: {platform.python_version()}")
    console.print(f"Playwright: {playwright_status}")


@app.command()
def init(
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
) -> None:
    """프로젝트에 표준 _audit 폴더 구조와 기본 템플릿을 생성합니다."""

    resolved = project_dir.resolve()
    paths = ensure_audit_dirs(resolved)
    target_path = paths["audit"] / "target.md"

    if not target_path.exists():
        target_path.write_text(
            render_target_md(site_name="(수집 전)", url="https://example.com"),
            encoding="utf-8",
        )

    save_status_payload(resolved, load_status_payload(resolved))

    for label, path in paths.items():
        console.print(f"{label:12} {path}")


@app.command()
def crawl(
    url: str = typer.Argument(..., help="수집할 공개 URL"),
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
    max_pages: int = typer.Option(8, min=1, max=50, help="최대 수집 페이지 수"),
    max_depth: int = typer.Option(2, min=0, max=5, help="링크 탐색 깊이"),
    delay_ms: int = typer.Option(1000, min=0, max=10000, help="페이지 간 대기 시간(ms)"),
    discover: bool = typer.Option(False, help="sitemap/RSS 선행 수집"),
    full_content: bool = typer.Option(False, help="본문 콘텐츠 추출 및 content/ 미러링"),
    retry: int = typer.Option(2, min=0, max=5, help="실패 페이지 재시도 횟수"),
) -> None:
    """동일 origin 기준으로 다중 페이지 BFS 크롤링을 수행합니다."""

    from playwright.sync_api import sync_playwright

    resolved = project_dir.resolve()
    paths = ensure_audit_dirs(resolved)
    normalized_url = normalize_url(url)
    if not normalized_url:
        raise typer.BadParameter("유효한 http/https URL을 입력하세요.")

    init(project_dir=resolved)

    parsed = urlparse(normalized_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_rules, robots_loaded, robots_text = load_robots_rules(origin)
    queue: deque[tuple[str, int]] = deque([(normalized_url, 0)])
    visited: set[str] = set()
    pages: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    robots_blocked: list[str] = []
    aggregate_color_counter: Counter[str] = Counter()
    screenshot_count = 0
    discovery_report: dict[str, Any] | None = None

    PC_VIEWPORT = {"width": 1920, "height": 1080}
    MOBILE_VIEWPORT = {"width": 375, "height": 812}

    if discover:
        from webstart_audit.discovery import discover as run_discovery

        disc = run_discovery(origin, robots_text)
        queued_seed = {queued_url for queued_url, _ in queue}
        for disc_url in disc.urls:
            normed = normalize_url(disc_url)
            if (
                normed
                and normed not in visited
                and normed not in queued_seed
                and same_origin(normed, origin)
            ):
                # discovery로 찾은 URL은 root와 동등한 seed로 취급한다.
                # depth=0으로 넣어야 --max-depth=N 설정 시 자식 페이지 탐색이 기대대로 동작한다.
                queue.append((normed, 0))
                queued_seed.add(normed)
        discovery_report = {
            "origin": origin,
            "generatedAt": datetime.now().isoformat(timespec="seconds"),
            "sourceDetail": disc.source_detail,
            "urls": disc.urls,
        }
        write_json(paths["raw"] / "discovery-report.json", discovery_report)
        console.print(f"discovery: {disc.source_detail}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=PC_VIEWPORT)

        while queue and len(visited) < max_pages:
            current_url, depth = queue.popleft()
            if current_url in visited:
                continue
            if not is_allowed_by_robots(current_url, origin, robots_rules):
                robots_blocked.append(current_url)
                visited.add(current_url)
                continue

            try:
                response = goto_with_retry(page, current_url, retry)
                snapshot = collect_page_snapshot(page, current_url=current_url, depth=depth)
                slug = slugify_url(current_url)
                page_num = f"{len(pages)+1:03d}"
                screenshot_name = f"{page_num}-{slug}-pc.png"
                screenshot_path = paths["screenshots"] / screenshot_name
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshot_count += 1

                page.set_viewport_size(MOBILE_VIEWPORT)
                page.wait_for_timeout(500)
                mobile_screenshot_name = f"{page_num}-{slug}-mobile.png"
                mobile_screenshot_path = paths["screenshots"] / mobile_screenshot_name
                page.screenshot(path=str(mobile_screenshot_path), full_page=True)
                screenshot_count += 1
                page.set_viewport_size(PC_VIEWPORT)

                performance = page.evaluate(
                    """
                    () => {
                      const nav = performance.getEntriesByType('navigation')[0];
                      return {
                        domContentLoaded: Math.round(nav?.domContentLoadedEventEnd || 0),
                        loadComplete: Math.round(nav?.loadEventEnd || 0),
                        transferSize: Math.round(nav?.transferSize || 0),
                        domInteractive: Math.round(nav?.domInteractive || 0),
                      };
                    }
                    """
                )

                page_snapshot = PageSnapshot(
                    url=current_url,
                    title=snapshot["title"],
                    depth=depth,
                    status=response.status if response else None,
                    head=snapshot["head"],
                    nav_links=dedupe_links(snapshot["navLinks"]),
                    all_links=dedupe_links(snapshot["allLinks"]),
                    scripts=list(dict.fromkeys(snapshot["scripts"])),
                    styles=list(dict.fromkeys(snapshot["styles"])),
                    colors=snapshot["colors"],
                    fonts=snapshot["fonts"],
                    forms=snapshot["forms"],
                    meta=snapshot["meta"],
                    performance=performance,
                    screenshot=f"_audit/screenshots/{screenshot_name}",
                    screenshot_mobile=f"_audit/screenshots/{mobile_screenshot_name}",
                )
                pages.append(page_snapshot.model_dump())
                visited.add(current_url)

                for color in page_snapshot.colors:
                    aggregate_color_counter.update({color["value"]: int(color["count"])})

                queued_urls = {queued_url for queued_url, _ in queue}
                for link in page_snapshot.all_links:
                    href = normalize_url(link["href"], current_url)
                    if not href:
                        continue
                    edges.append({"from": current_url, "to": href, "parent": link.get("parent", "")})
                    if (
                        depth < max_depth
                        and same_origin(href, origin)
                        and is_allowed_by_robots(href, origin, robots_rules)
                        and href not in visited
                        and href not in queued_urls
                    ):
                        queue.append((href, depth + 1))
                        queued_urls.add(href)

                if delay_ms:
                    page.wait_for_timeout(delay_ms)
            except Exception as exc:  # pragma: no cover
                errors.append({"url": current_url, "error": str(exc)})
                visited.add(current_url)

        browser.close()

    unique_nav_links = dedupe_links(
        [link for page_data in pages for link in page_data["nav_links"]]
    )
    unique_scripts = list(dict.fromkeys(script for page_data in pages for script in page_data["scripts"]))
    unique_styles = list(dict.fromkeys(style for page_data in pages for style in page_data["styles"]))
    top_colors = [
        {"value": value, "count": count}
        for value, count in aggregate_color_counter.most_common(25)
    ]

    crawl_payload: dict[str, Any] = {
        "target": {
            "url": normalized_url,
            "origin": origin,
            "collectedAt": date.today().isoformat(),
            "maxPages": max_pages,
            "maxDepth": max_depth,
            "robotsLoaded": robots_loaded,
            "robotsDisallowRules": robots_rules,
        },
        "discovery": discovery_report,
        "pages": pages,
        "edges": edges,
        "errors": errors,
        "robotsBlocked": robots_blocked,
        "summary": {
            "visitedPages": len(pages),
            "uniqueScripts": len(unique_scripts),
            "uniqueStyles": len(unique_styles),
            "capturedScreenshots": screenshot_count,
            "robotsBlockedPages": len(robots_blocked),
            "discoveredUrls": discovery_report["sourceDetail"]["total_unique"] if discovery_report else 0,
            "fullContentEnabled": full_content,
            "contentMirrored": 0,
            "contentErrors": 0,
        },
    }

    # crawl-data.json 저장은 full_content 단계 이후로 미룬다.
    # 그래야 content 추출 중 발생한 에러도 errors 필드에 반영되고,
    # contentMirrored/contentErrors가 요약에 함께 기록된다.
    write_json(paths["derived"] / "pages.json", pages)
    write_json(paths["derived"] / "link-graph.json", edges)

    legacy_scraped_data = {
        "head": pages[0]["head"] if pages else "",
        "navLinks": unique_nav_links,
        "scripts": unique_scripts,
        "styles": unique_styles,
        "colors": [color["value"] for color in top_colors],
        "pages": [
            {
                "url": page_data["url"],
                "title": page_data["title"],
                "depth": page_data["depth"],
                "status": page_data["status"],
                "screenshot": page_data["screenshot"],
                "screenshot_mobile": page_data.get("screenshot_mobile"),
            }
            for page_data in pages
        ],
        "graph": edges,
    }
    write_json(paths["audit"] / "scraped-data.json", legacy_scraped_data)

    if pages:
        write_json(paths["raw"] / "site-snapshot.json", pages[0])
        (paths["audit"] / "target.md").write_text(
            render_target_md(
                site_name=pages[0]["title"] or "(제목 없음)",
                url=normalized_url,
                site_type="공개 웹사이트",
                purpose=DEFAULT_PURPOSE,
            ),
            encoding="utf-8",
        )

        if full_content:
            from webstart_audit.extractor import (
                build_sitemap_json,
                extract_content,
                resolve_content_paths,
                render_content_md,
            )

            all_urls = [page_data["url"] for page_data in pages]
            path_map = resolve_content_paths(all_urls)
            content_written = 0
            content_errors_before = len(errors)

            with sync_playwright() as content_playwright:
                content_browser = content_playwright.chromium.launch()
                content_page = content_browser.new_page(viewport=PC_VIEWPORT)
                try:
                    for index, page_data in enumerate(pages):
                        page_url = page_data["url"]
                        file_path = resolved / path_map[page_url]
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            goto_with_retry(content_page, page_url, retry)
                            content = extract_content(content_page)
                            markdown = render_content_md(
                                url=page_url,
                                title=page_data["title"],
                                depth=page_data["depth"],
                                status=page_data["status"],
                                content=content,
                                screenshot=page_data.get("screenshot"),
                                screenshot_mobile=page_data.get("screenshot_mobile"),
                                crawled_at=datetime.now().isoformat(timespec="seconds"),
                            )
                            file_path.write_text(markdown, encoding="utf-8")
                            content_written += 1
                        except Exception as exc:  # pragma: no cover
                            errors.append({"url": page_url, "error": f"content: {exc}"})
                        # 두 번째 방문 루프에도 delay_ms를 적용해야 rate limit 위험을 막는다.
                        if delay_ms and index < len(pages) - 1:
                            content_page.wait_for_timeout(delay_ms)
                finally:
                    content_browser.close()

            crawl_payload["summary"]["contentMirrored"] = content_written
            crawl_payload["summary"]["contentErrors"] = len(errors) - content_errors_before

            build_sitemap_json(pages, path_map, resolved, root_url=normalized_url)
            console.print(
                f"content mirrored: {content_written}, sitemap saved: {resolved / '_audit' / 'sitemap.json'}"
            )

    write_json(paths["raw"] / "crawl-data.json", crawl_payload)

    artifacts = [
        "_audit/target.md",
        "_audit/status.json",
        "_audit/status.md",
        "_audit/scraped-data.json",
        "_audit/raw/crawl-data.json",
    ]
    if discovery_report:
        artifacts.append("_audit/raw/discovery-report.json")
    if full_content and pages:
        artifacts.append("_audit/sitemap.json")
        artifacts.append("_audit/content/")

    mark_stage(
        resolved,
        "target",
        status="done",
        notes=f"{len(pages)}개 페이지 수집, robots 차단 {len(robots_blocked)}개",
        artifacts=artifacts,
    )
    reset_downstream_stages(resolved, "target")

    console.print(f"crawl saved: {paths['raw'] / 'crawl-data.json'}")
    console.print(f"pages collected: {len(pages)}")


@app.command("ux-scan")
def ux_scan(
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
) -> None:
    """crawl 결과를 기반으로 UX 요약 JSON을 생성합니다."""

    resolved = project_dir.resolve()
    paths = ensure_audit_dirs(resolved)
    pages: list[dict[str, Any]] = load_json(paths["derived"] / "pages.json", [])
    if not pages:
        raise typer.BadParameter("먼저 webstart-audit crawl 을 실행하세요.")

    color_counter: Counter[str] = Counter()
    font_counter: Counter[tuple[str, str, str]] = Counter()
    font_samples: dict[tuple[str, str, str], dict[str, Any]] = {}
    page_with_forms = 0
    page_with_nav = 0
    screenshot_samples: list[str] = []

    for page in pages:
        if page.get("forms"):
            page_with_forms += 1
        if page.get("nav_links"):
            page_with_nav += 1
        if page.get("screenshot") and len(screenshot_samples) < 4:
            screenshot_samples.append(page["screenshot"])

        for color in page.get("colors", []):
            color_counter.update({color["value"]: int(color["count"])})

        for font in page.get("fonts", []):
            key = (font["family"], font["size"], font["weight"])
            font_counter.update({key: int(font.get("count", 1))})
            font_samples[key] = font

    sorted_colors = color_counter.most_common(12)
    palette = []
    roles = ["Primary", "Secondary", "Accent", "Surface", "Muted"]
    for index, (value, count) in enumerate(sorted_colors):
        palette.append(
            {
                "role": roles[index] if index < len(roles) else f"Color {index + 1}",
                "value": value,
                "hex": rgb_to_hex(value),
                "count": count,
            }
        )

    top_fonts = []
    for key, count in font_counter.most_common(10):
        sample = font_samples[key]
        top_fonts.append(
            {
                "family": sample["family"],
                "size": sample["size"],
                "weight": sample["weight"],
                "sampleTag": sample["tag"],
                "count": count,
            }
        )

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

    summary = {
        "siteName": read_target_name(resolved),
        "url": read_target_url(resolved),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "pageCount": len(pages),
        "palette": palette,
        "imagePalette": image_palette,
        "typography": top_fonts,
        "components": {
            "navigationPages": page_with_nav,
            "formPages": page_with_forms,
            "screenshots": screenshot_samples,
        },
        "evidence": {
            "pagesFile": "_audit/derived/pages.json",
            "crawlFile": "_audit/raw/crawl-data.json",
        },
    }

    write_json(paths["derived"] / "ux-summary.json", summary)
    mark_stage(
        resolved,
        "ux",
        status="done",
        notes=f"{len(pages)}개 페이지 기반 요약",
        artifacts=["_audit/derived/ux-summary.json"],
    )
    console.print(f"ux summary saved: {paths['derived'] / 'ux-summary.json'}")


@app.command("ia-scan")
def ia_scan(
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
) -> None:
    """crawl 결과를 기반으로 IA 요약 JSON을 생성합니다."""

    resolved = project_dir.resolve()
    paths = ensure_audit_dirs(resolved)
    pages: list[dict[str, Any]] = load_json(paths["derived"] / "pages.json", [])
    if not pages:
        raise typer.BadParameter("먼저 webstart-audit crawl 을 실행하세요.")

    site_pages = [
        {
            "url": page["url"],
            "title": page.get("title", ""),
            "depth": page.get("depth", 0),
            "description": page.get("meta", {}).get("description", ""),
            "h1": page.get("meta", {}).get("h1", []),
        }
        for page in pages
    ]
    site_pages.sort(key=lambda item: (item["depth"], item["url"]))

    nav_counter: Counter[tuple[str, str]] = Counter()
    for page in pages:
        for link in page.get("nav_links", []):
            text = link.get("text", "").strip()
            href = link.get("href", "").strip()
            if text and href:
                nav_counter.update({(text, href): 1})

    top_nav = [
        {"text": text, "href": href, "count": count}
        for (text, href), count in nav_counter.most_common(12)
    ]

    summary = {
        "siteName": read_target_name(resolved),
        "url": read_target_url(resolved),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "pageCount": len(site_pages),
        "pages": site_pages,
        "mainNavigation": top_nav,
        "journeys": [
            {
                "name": "방문 → 핵심 정보 확인",
                "steps": min(max(len(top_nav[:3]), 1), 3),
                "assessment": "양호" if len(top_nav) >= 3 else "보통",
            }
        ],
        "evidence": {
            "pagesFile": "_audit/derived/pages.json",
            "graphFile": "_audit/derived/link-graph.json",
        },
    }

    write_json(paths["derived"] / "ia-summary.json", summary)
    mark_stage(
        resolved,
        "ia",
        status="done",
        notes=f"{len(site_pages)}개 페이지 구조화",
        artifacts=["_audit/derived/ia-summary.json"],
    )
    console.print(f"ia summary saved: {paths['derived'] / 'ia-summary.json'}")


def run_lighthouse(target_url: str, paths: dict[str, Path]) -> dict[str, float] | None:
    """npx lighthouse를 실행하여 카테고리 점수를 반환한다. 실패 시 None."""
    import shutil
    import subprocess

    if not shutil.which("npx"):
        console.print("[yellow]npx를 찾을 수 없어 Lighthouse를 건너뜁니다.[/yellow]")
        return None

    try:
        result = subprocess.run(
            [
                "npx", "lighthouse", target_url,
                "--output=json",
                "--chrome-flags=--headless --no-sandbox",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        console.print("[yellow]Lighthouse 실행 시간 초과 (120초). 건너뜁니다.[/yellow]")
        return None
    except FileNotFoundError:
        console.print("[yellow]npx 실행에 실패했습니다. Lighthouse를 건너뜁니다.[/yellow]")
        return None

    if result.returncode != 0:
        console.print(f"[yellow]Lighthouse 종료 코드 {result.returncode}. 건너뜁니다.[/yellow]")
        return None

    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        console.print("[yellow]Lighthouse 출력을 파싱할 수 없습니다. 건너뜁니다.[/yellow]")
        return None

    categories = report.get("categories", {})
    scores: dict[str, float] = {}
    for key in ("performance", "accessibility", "best-practices", "seo"):
        cat = categories.get(key)
        if cat and cat.get("score") is not None:
            scores[key] = round(cat["score"] * 100, 1)

    write_json(paths["raw"] / "lighthouse.json", report)
    console.print(f"lighthouse saved: {paths['raw'] / 'lighthouse.json'}")
    return scores


@app.command("tech-scan")
def tech_scan(
    url: str | None = typer.Argument(None, help="대상 URL. 생략 시 _audit/target.md에서 읽음"),
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
    max_pages: int = typer.Option(6, min=1, max=30, help="분석할 최대 페이지 수"),
    delay_ms: int = typer.Option(1000, min=0, max=10000, help="페이지 간 대기 시간(ms)"),
) -> None:
    """기술 스택과 네트워크 특성을 자동 수집합니다."""

    from playwright.sync_api import sync_playwright

    resolved = project_dir.resolve()
    effective_url = url or read_target_url(resolved)
    if not effective_url:
        raise typer.BadParameter("URL이 없고 _audit/target.md에서도 URL을 찾지 못했습니다.")

    normalized_url = normalize_url(effective_url)
    if not normalized_url:
        raise typer.BadParameter("유효한 http/https URL을 입력하세요.")

    page_urls = load_crawl_urls(resolved, normalized_url)[:max_pages]
    origin = f"{urlparse(normalized_url).scheme}://{urlparse(normalized_url).netloc}"

    requests: list[dict[str, Any]] = []
    page_results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        def on_response(response: Any) -> None:
            request = response.request
            try:
                headers = filter_headers(response.headers)
            except Exception:
                headers = {}

            size = 0
            try:
                size = len(response.body())
            except Exception:
                content_length = headers.get("content-length")
                if content_length and content_length.isdigit():
                    size = int(content_length)

            requests.append(
                {
                    "url": response.url[:300],
                    "type": request.resource_type,
                    "method": request.method,
                    "status": response.status,
                    "size": size,
                    "headers": headers,
                }
            )

        page.on("response", on_response)

        for current_url in page_urls:
            response = page.goto(current_url, wait_until="networkidle", timeout=30000)
            detection = page.evaluate(
                """
                () => {
                  const detected = [];
                  if (window.__NEXT_DATA__) detected.push({ name: 'Next.js', confidence: 'Confirmed', evidence: '__NEXT_DATA__ global' });
                  if (window.__NUXT__) detected.push({ name: 'Nuxt.js', confidence: 'Confirmed', evidence: '__NUXT__ global' });
                  if (document.querySelector('#__next') || document.querySelector('[data-reactroot]')) {
                    detected.push({ name: 'React', confidence: 'Confirmed', evidence: '#__next / data-reactroot' });
                  }
                  if (window.jQuery || window.$?.fn?.jquery) {
                    detected.push({ name: 'jQuery', confidence: 'Confirmed', evidence: 'jQuery global', version: window.jQuery?.fn?.jquery || '' });
                  }
                  if (document.querySelector('meta[name=generator][content*=WordPress]') || document.querySelector('[class*=wp-]')) {
                    detected.push({ name: 'WordPress', confidence: 'Confirmed', evidence: 'generator meta / wp-* class' });
                  }
                  const stylesheetHrefs = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map((el) => el.href);
                  if (stylesheetHrefs.some((href) => href.includes('tailwind'))) {
                    detected.push({ name: 'Tailwind CSS', confidence: 'Likely', evidence: 'stylesheet href' });
                  }
                  if (stylesheetHrefs.some((href) => href.includes('bootstrap'))) {
                    detected.push({ name: 'Bootstrap', confidence: 'Confirmed', evidence: 'stylesheet href' });
                  }
                  return detected;
                }
                """
            )
            perf = page.evaluate(
                """
                () => {
                  const nav = performance.getEntriesByType('navigation')[0];
                  return {
                    domContentLoaded: Math.round(nav?.domContentLoadedEventEnd || 0),
                    loadComplete: Math.round(nav?.loadEventEnd || 0),
                    transferSize: Math.round(nav?.transferSize || 0),
                    domInteractive: Math.round(nav?.domInteractive || 0),
                  };
                }
                """
            )
            cwv = page.evaluate(
                """
                () => new Promise((resolve) => {
                  const result = { lcp: null, cls: 0 };
                  try {
                    new PerformanceObserver((list) => {
                      const entries = list.getEntries();
                      const last = entries[entries.length - 1];
                      if (last) result.lcp = Math.round(last.startTime);
                    }).observe({ type: 'largest-contentful-paint', buffered: true });
                    new PerformanceObserver((list) => {
                      list.getEntries().forEach((entry) => {
                        if (!entry.hadRecentInput) result.cls += entry.value;
                      });
                    }).observe({ type: 'layout-shift', buffered: true });
                  } catch (error) {}
                  setTimeout(() => {
                    result.cls = Math.round(result.cls * 1000) / 1000;
                    resolve(result);
                  }, 1200);
                })
                """
            )

            page_results.append(
                {
                    "url": current_url,
                    "status": response.status if response else None,
                    "frameworks": detection,
                    "performance": perf,
                    "cwv": cwv,
                }
            )
            if delay_ms:
                page.wait_for_timeout(delay_ms)

        browser.close()

    frameworks = list(
        {
            (item["name"], item.get("version", ""), item["confidence"], item["evidence"]): item
            for page_result in page_results
            for item in page_result["frameworks"]
        }.values()
    )
    top_resources = sorted(requests, key=lambda item: item["size"], reverse=True)[:10]
    third_party = [
        item
        for item in top_resources
        if not same_origin(item["url"], origin) and item["type"] in {"script", "stylesheet", "image", "font"}
    ]
    main_document = next(
        (item for item in requests if item["type"] == "document" and same_origin(item["url"], origin)),
        None,
    )
    paths = ensure_audit_dirs(resolved)
    lighthouse_scores = run_lighthouse(normalized_url, paths)

    summary = {
        "frameworks": frameworks,
        "pageResults": page_results,
        "topResources": top_resources,
        "thirdParty": third_party,
        "serverHeaders": main_document["headers"] if main_document else {},
        "totalRequests": len(requests),
        "lighthouse": lighthouse_scores,
    }

    write_json(paths["raw"] / "tech-scan.json", {"requests": requests, **summary})
    write_json(paths["derived"] / "tech-summary.json", summary)

    artifacts = ["_audit/raw/tech-scan.json", "_audit/derived/tech-summary.json"]
    if lighthouse_scores:
        artifacts.append("_audit/raw/lighthouse.json")

    mark_stage(
        resolved,
        "tech",
        status="done",
        notes=f"{len(page_results)}개 페이지 기술 스캔",
        artifacts=artifacts,
    )
    console.print(f"tech scan saved: {paths['raw'] / 'tech-scan.json'}")


@app.command("api-scan")
def api_scan(
    url: str | None = typer.Argument(None, help="대상 URL. 생략 시 _audit/target.md에서 읽음"),
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
    max_pages: int = typer.Option(6, min=1, max=30, help="분석할 최대 페이지 수"),
    delay_ms: int = typer.Option(1000, min=0, max=10000, help="페이지 간 대기 시간(ms)"),
) -> None:
    """API 호출과 폼 데이터를 자동 수집합니다."""

    from playwright.sync_api import sync_playwright

    resolved = project_dir.resolve()
    effective_url = url or read_target_url(resolved)
    if not effective_url:
        raise typer.BadParameter("URL이 없고 _audit/target.md에서도 URL을 찾지 못했습니다.")

    normalized_url = normalize_url(effective_url)
    if not normalized_url:
        raise typer.BadParameter("유효한 http/https URL을 입력하세요.")

    page_urls = load_crawl_urls(resolved, normalized_url)[:max_pages]
    origin = f"{urlparse(normalized_url).scheme}://{urlparse(normalized_url).netloc}"

    api_calls: list[dict[str, Any]] = []
    forms_by_page: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        def on_response(response: Any) -> None:
            request = response.request
            if request.resource_type not in {"fetch", "xhr"}:
                return

            try:
                content_type = response.headers.get("content-type", "")
            except Exception:
                content_type = ""

            body_preview: str | None = None
            try:
                if "json" in content_type:
                    body_preview = mask_pii(response.text())
                    if len(body_preview) > 2000:
                        body_preview = body_preview[:2000] + "... (truncated)"
            except Exception:
                body_preview = None

            api_calls.append(
                {
                    "method": request.method,
                    "url": response.url[:300],
                    "status": response.status,
                    "resourceType": request.resource_type,
                    "contentType": content_type,
                    "sameOrigin": same_origin(response.url, origin),
                    "bodyPreview": body_preview,
                }
            )

        page.on("response", on_response)

        for current_url in page_urls:
            page.goto(current_url, wait_until="networkidle", timeout=30000)
            forms = page.evaluate(
                """
                () => Array.from(document.querySelectorAll('form')).map((form) => ({
                  action: form.action || '',
                  method: (form.method || 'get').toUpperCase(),
                  fields: Array.from(form.querySelectorAll('input,select,textarea')).map((field) => ({
                    name: field.name || field.id || '',
                    type: field.type || field.tagName.toLowerCase(),
                    required: !!field.required,
                    placeholder: field.placeholder || ''
                  }))
                }))
                """
            )
            forms_by_page.append({"url": current_url, "forms": forms})
            if delay_ms:
                page.wait_for_timeout(delay_ms)

        browser.close()

    own_api_calls = [call for call in api_calls if call["sameOrigin"]]
    summary = {
        "totalApiCalls": len(api_calls),
        "sameOriginApiCalls": len(own_api_calls),
        "apiCalls": api_calls,
        "formsByPage": forms_by_page,
    }

    paths = ensure_audit_dirs(resolved)
    write_json(paths["raw"] / "api-scan.json", summary)
    write_json(
        paths["derived"] / "api-summary.json",
        {
            "totalApiCalls": len(api_calls),
            "sameOriginApiCalls": len(own_api_calls),
            "uniqueEndpoints": list(dict.fromkeys(call["url"] for call in api_calls)),
            "formsByPage": forms_by_page,
        },
    )
    console.print(f"api scan saved: {paths['raw'] / 'api-scan.json'}")


@app.command("report-draft")
def report_draft(
    project_dir: Path = typer.Option(Path("."), help="대상 프로젝트 루트"),
) -> None:
    """derived JSON을 기반으로 종합 보고서와 client-brief 초안을 생성합니다."""

    resolved = project_dir.resolve()
    paths = ensure_audit_dirs(resolved)

    ux_summary = load_json(paths["derived"] / "ux-summary.json", {})
    ia_summary = load_json(paths["derived"] / "ia-summary.json", {})
    tech_summary = load_json(paths["derived"] / "tech-summary.json", {})
    api_summary = load_json(paths["derived"] / "api-summary.json", {})
    target_url = read_target_url(resolved) or "https://example.com"
    site_name = read_target_name(resolved)

    palette_lines = [
        f"- {item['role']}: {item['hex']} ({item['value']}, count {item['count']})"
        for item in ux_summary.get("palette", [])[:5]
    ] or ["- 추가 수집 필요"]
    typography_lines = [
        f"- {item['family']} / {item['size']} / {item['weight']}"
        for item in ux_summary.get("typography", [])[:4]
    ] or ["- 추가 수집 필요"]
    nav_lines = [
        f"- {item['text']} ({item['href']})"
        for item in ia_summary.get("mainNavigation", [])[:8]
    ] or ["- 추가 수집 필요"]
    framework_lines = [
        f"- {item['name']} ({item.get('confidence', 'Unknown')})"
        for item in tech_summary.get("frameworks", [])[:6]
    ] or ["- 추가 수집 필요"]
    api_lines = [
        f"- {urlparse(endpoint).path or endpoint}"
        for endpoint in api_summary.get("uniqueEndpoints", [])[:6]
    ] or ["- 추가 수집 필요"]

    known_gaps = []
    if not ux_summary:
        known_gaps.append("| UX summary | Unknown | ux-scan 미실행 | webstart-audit ux-scan 실행 |")
    if not ia_summary:
        known_gaps.append("| IA summary | Unknown | ia-scan 미실행 | webstart-audit ia-scan 실행 |")
    if not tech_summary:
        known_gaps.append("| Tech summary | Unknown | tech-scan 미실행 | webstart-audit tech-scan 실행 |")
    if api_summary.get("sameOriginApiCalls", 0) == 0:
        known_gaps.append("| API evidence | Hypothesis | 동일 origin API 호출 증거 부족 | 더 많은 사용자 여정 수집 또는 수동 데이터 제공 |")

    report_md = f"""# 웹사이트 검수 종합 보고서

> 분석 대상: {site_name} ({target_url})
> 분석일: {date.today().isoformat()}
> 분석 범위: 공개 페이지
> 생성 방식: webstart-audit report-draft

## 1. 분석 요약
- 수집된 페이지 수: {ia_summary.get('pageCount', ux_summary.get('pageCount', 0))}
- 주요 네비게이션 항목 수: {len(ia_summary.get('mainNavigation', []))}
- 감지된 프레임워크 수: {len(tech_summary.get('frameworks', []))}
- 동일 origin API 호출 수: {api_summary.get('sameOriginApiCalls', 0)}

## 2. 디자인 현황
### 컬러 팔레트
{chr(10).join(palette_lines)}

### 타이포그래피
{chr(10).join(typography_lines)}

## 3. 정보 구조
### 메인 네비게이션
{chr(10).join(nav_lines)}

## 4. 기술 스택
{chr(10).join(framework_lines)}

## 5. 데이터 구조
{chr(10).join(api_lines)}

## 6. 리뉴얼 권장사항
- 기존 핵심 동선을 유지하면서 주요 CTA를 더 명확하게 배치
- 현재 수집된 기술 스택과 동일 origin API 증거를 바탕으로 이전 범위를 우선 재현
- 추가 인터랙션이 필요한 페이지는 수동 검증 후 범위를 확정

## 7. Known Gaps
| 항목 | 상태 | 사유 | 후속 조치 |
|------|------|------|----------|
{chr(10).join(known_gaps) if known_gaps else '| 없음 | Confirmed | 자동 수집 기준 주요 공백 없음 | - |'}
"""

    report_path = paths["audit"] / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    features = []
    joined_text = " ".join(item.get("text", "") for item in ia_summary.get("mainNavigation", []))
    feature_map = {
        "문의": "문의 폼",
        "contact": "문의 폼",
        "portfolio": "포트폴리오/갤러리",
        "gallery": "포트폴리오/갤러리",
        "service": "서비스 소개",
        "about": "팀/회사 소개",
        "blog": "블로그/뉴스",
        "login": "로그인/회원가입",
        "signup": "로그인/회원가입",
        "admin": "관리자 페이지",
        "shop": "결제 기능",
        "product": "결제 기능",
    }
    lowered = joined_text.lower()
    for token, label in feature_map.items():
        if token in lowered and label not in features:
            features.append(label)
    if not features:
        features = ["메인 홈페이지", "서비스 소개", "문의 폼"]
    elif "메인 홈페이지" not in features:
        features.insert(0, "메인 홈페이지")

    additional_requests = [
        "Known Gaps 항목 검토 후 실제 요구사항으로 확정 필요",
        "자동 생성 초안이므로 /pm 실행 전 예산과 일정, 담당자 정보 보완 필요",
    ]
    if api_summary.get("sameOriginApiCalls", 0) == 0:
        additional_requests.insert(0, "⚠ 추정 — 실제 API 구조는 추가 검증 필요")

    agency_dir = resolved / "_agency"
    agency_dir.mkdir(exist_ok=True)
    brief_path = agency_dir / "client-brief.md"
    brief_path.write_text(
        render_client_brief(
            brand_name=site_name,
            reference_url=target_url,
            site_type="공개 웹사이트",
            key_goal="기존 사이트 구조를 유지하되 리뉴얼 품질과 전환 효율을 높이는 것",
            success_metric="주요 문의/전환 흐름을 더 짧고 명확하게 재구성",
            features=features,
            additional_requests=additional_requests,
        ),
        encoding="utf-8",
    )

    mark_stage(
        resolved,
        "report",
        status="done",
        notes="runtime 종합 보고서 초안 생성",
        artifacts=["_audit/report.md"],
    )
    mark_stage(
        resolved,
        "handover",
        status="done",
        notes="client-brief 초안 생성",
        artifacts=["_agency/client-brief.md"],
    )

    console.print(f"report draft saved: {report_path}")
    console.print(f"client brief saved: {brief_path}")


if __name__ == "__main__":
    app()
