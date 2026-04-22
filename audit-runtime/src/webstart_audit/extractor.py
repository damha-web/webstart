from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from webstart_audit.security import mask_pii


def extract_content(page: Any) -> dict[str, Any]:
    """Playwright 페이지에서 구조화된 본문을 추출한다."""
    return page.evaluate(
        """
        () => {
            const main = document.querySelector('main, article, [role=main], .content, #content, #main');
            const root = main || document.body;

            const sections = Array.from(root.querySelectorAll('section, article'))
                .filter((section) => !section.closest('nav, header, footer'))
                .map((section) => ({
                    id: section.id || null,
                    heading: section.querySelector('h1,h2,h3,h4')?.textContent?.trim() || null,
                    text: section.innerText.trim(),
                    images: Array.from(section.querySelectorAll('img')).map((img) => ({
                        src: img.src,
                        alt: img.alt || null,
                        width: img.naturalWidth || null,
                        height: img.naturalHeight || null,
                    })),
                }));

            const bodyText = root.innerText.trim();

            const jsonLd = Array.from(
                document.querySelectorAll('script[type="application/ld+json"]')
            ).map((script) => {
                try {
                    return JSON.parse(script.textContent);
                } catch {
                    return null;
                }
            }).filter(Boolean);

            const og = {};
            document.querySelectorAll('meta[property^="og:"], meta[name^="og:"]').forEach((meta) => {
                const key = meta.getAttribute('property') || meta.getAttribute('name');
                og[key] = meta.content;
            });

            const seenSrc = new Set();
            const images = Array.from(document.querySelectorAll('img')).reduce((acc, img) => {
                if (img.src && !seenSrc.has(img.src)) {
                    seenSrc.add(img.src);
                    acc.push({
                        src: img.src,
                        alt: img.alt || null,
                        width: img.naturalWidth || null,
                        height: img.naturalHeight || null,
                        loading: img.loading || null,
                    });
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
                wordCount: bodyText.split(/\\s+/).filter(Boolean).length,
            };
        }
        """
    )


def url_to_content_path(url: str) -> Path:
    """URL을 _audit/content 하위의 안정적인 파일 경로로 바꾼다."""
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        path = "_index"
    segments = path.split("/")
    filename = segments[-1]
    if parsed.query:
        query_hash = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:10]
        filename = f"{filename}__q-{query_hash}"
    return Path("_audit/content") / "/".join(segments[:-1]) / f"{filename}.md"


def resolve_content_paths(all_urls: list[str]) -> dict[str, Path]:
    """2-pass로 부모/자식 관계를 반영한 최종 콘텐츠 경로를 계산한다."""
    path_map: dict[str, Path] = {}
    url_paths = {url: urlparse(url).path.strip("/") for url in all_urls}
    all_segments = {path for path in url_paths.values() if path}
    has_children: set[str] = set()

    for seg in all_segments:
        parts = seg.split("/")
        for index in range(1, len(parts)):
            has_children.add("/".join(parts[:index]))

    for url, seg in url_paths.items():
        if not seg:
            path_map[url] = Path("_audit/content/_index.md")
            continue
        if seg in has_children and not urlparse(url).query:
            path_map[url] = Path("_audit/content") / seg / "_index.md"
            continue
        path_map[url] = url_to_content_path(url)

    return path_map


def _yaml_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is None:
        return "null"
    if isinstance(value, (int, float, bool)):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(mask_pii(str(value)), ensure_ascii=False)


def _structured_data_types(json_ld: Any) -> list[str]:
    types: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            value = item.get("@type", "Unknown")
            if isinstance(value, list):
                for nested in value:
                    types.append(mask_pii(str(nested)))
            else:
                types.append(mask_pii(str(value)))
        elif isinstance(item, list):
            for nested in item:
                visit(nested)
        else:
            types.append("Unknown")

    visit(json_ld or [])
    return types


def render_content_md(
    *,
    url: str,
    title: str,
    depth: int,
    status: int | None,
    content: dict[str, Any],
    screenshot: str | None,
    screenshot_mobile: str | None,
    crawled_at: str,
) -> str:
    word_count = int(content.get("wordCount", 0) or 0)
    reading_time = max(1, (word_count + 199) // 200)
    canonical = content.get("canonical") or url
    lang = content.get("lang") or ""
    og = content.get("og") or {}

    sections_text = []
    for sec in content.get("sections") or []:
        heading = mask_pii(str(sec.get("heading") or "")).strip()
        text = mask_pii(str(sec.get("text") or "")).strip()
        if heading:
            sections_text.append(f"## {heading}\n{text}".rstrip())
        elif text:
            sections_text.append(text)

    images = content.get("images") or []
    images_table = ""
    if images:
        rows = "\n".join(
            f"| {mask_pii(str(img.get('src') or ''))} | {mask_pii(str(img.get('alt') or ''))} | {img.get('width') or ''} | {img.get('height') or ''} |"
            for img in images[:50]
        )
        images_table = (
            "\n## 이미지\n| src | alt | width | height |\n|-----|-----|-------|--------|\n"
            f"{rows}\n"
        )

    frontmatter = "\n".join(
        [
            "---",
            f"url: {_yaml_value(url)}",
            f"title: {_yaml_value(title)}",
            f"depth: {_yaml_value(depth)}",
            f"status: {_yaml_value(status if status is not None else 'unknown')}",
            f"canonical: {_yaml_value(canonical)}",
            f"lang: {_yaml_value(lang)}",
            f"og: {_yaml_value(og)}",
            f"structured_data: {_yaml_value(_structured_data_types(content.get('jsonLd')))}",
            f"screenshot: {_yaml_value(screenshot or '')}",
            f"screenshot_mobile: {_yaml_value(screenshot_mobile or '')}",
            f"crawled_at: {_yaml_value(crawled_at)}",
            f"word_count: {_yaml_value(word_count)}",
            f"reading_time: {_yaml_value(reading_time)}",
            "---",
        ]
    )

    body_parts = [f"# {mask_pii(title)}"]
    if sections_text:
        body_parts.append("\n\n".join(sections_text))
    else:
        body_parts.append(mask_pii(str(content.get("bodyText") or "")).strip())
    if images_table:
        body_parts.append(images_table.strip())

    return f"{frontmatter}\n\n" + "\n\n".join(part for part in body_parts if part) + "\n"


def build_sitemap_json(
    pages: list[dict[str, Any]],
    path_map: dict[str, Path],
    project_dir: Path,
    root_url: str,
) -> None:
    """URL 목록에서 트리 구조 sitemap.json을 생성한다."""
    if not pages:
        return

    url_meta = {page["url"]: page for page in pages}
    path_to_urls: dict[str, list[str]] = defaultdict(list)
    for page in pages:
        path = urlparse(page["url"]).path.rstrip("/") or "/"
        path_to_urls[path].append(page["url"])

    def pick_url_for_path(path: str) -> str | None:
        candidates = path_to_urls.get(path)
        if not candidates:
            return None
        for candidate in candidates:
            if not urlparse(candidate).query:
                return candidate
        return candidates[0]

    children_map: dict[str, list[str]] = defaultdict(list)
    for page in sorted(pages, key=lambda item: (item["depth"], item["url"])):
        url = page["url"]
        if url == root_url:
            continue
        path = urlparse(url).path.rstrip("/") or "/"
        clean_path = path.strip("/")
        parent_path = "/" + clean_path.rsplit("/", 1)[0] if "/" in clean_path else "/"
        parent_url = pick_url_for_path(parent_path) or root_url
        children_map[parent_url].append(url)

    # 재귀 대신 반복문으로 트리를 쌓는다. 경로 깊이가 Python 재귀 한도에
    # 근접해도 RecursionError가 발생하지 않도록 하기 위함이다.
    def make_node(url: str) -> dict[str, Any]:
        return {
            "url": url,
            "path": urlparse(url).path or "/",
            "title": url_meta[url]["title"],
            "depth": url_meta[url]["depth"],
            "contentFile": str(path_map[url]),
            "children": [],
        }

    nodes: dict[str, dict[str, Any]] = {root_url: make_node(root_url)}
    traversal_order: list[str] = [root_url]
    visited_tree: set[str] = {root_url}
    stack: list[str] = [root_url]
    while stack:
        current = stack.pop()
        for child in children_map.get(current, []):
            if child in visited_tree:
                continue
            visited_tree.add(child)
            nodes[child] = make_node(child)
            traversal_order.append(child)
            stack.append(child)

    for parent in traversal_order:
        parent_node = nodes[parent]
        for child in children_map.get(parent, []):
            child_node = nodes.get(child)
            if child_node is not None and child_node not in parent_node["children"]:
                parent_node["children"].append(child_node)

    payload = {
        "root": f"{urlparse(root_url).scheme}://{urlparse(root_url).netloc}",
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "totalPages": len(pages),
        "tree": nodes[root_url],
    }
    (project_dir / "_audit" / "sitemap.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
