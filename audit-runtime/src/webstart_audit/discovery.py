from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx
from bs4 import BeautifulSoup

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ATOM_NS = "http://www.w3.org/2005/Atom"
FEED_TIMEOUT = 10.0
MAX_SITEMAP_DEPTH = 3
MAX_SITEMAP_URLS = 2000
MAX_FEED_LINKS = 3


@dataclass
class DiscoveryResult:
    urls: list[str] = field(default_factory=list)
    sitemap_count: int = 0
    rss_count: int = 0
    source_detail: dict[str, int] = field(default_factory=dict)


def discover(origin: str, robots_text: str | None = None) -> DiscoveryResult:
    """robots.txt, sitemap, feed 기반으로 seed URL 후보를 수집한다."""
    result = DiscoveryResult()
    seen: set[str] = set()

    robots_sitemaps = _extract_sitemap_urls_from_robots(robots_text or "", origin)
    if not robots_sitemaps:
        robots_sitemaps = [
            urljoin(origin, "/sitemap.xml"),
            urljoin(origin, "/sitemap_index.xml"),
        ]

    sitemap_urls = _collect_sitemap_urls(robots_sitemaps, origin)
    for url in sitemap_urls:
        if url not in seen:
            seen.add(url)
            result.urls.append(url)
    result.sitemap_count = len(sitemap_urls)

    feed_urls = _collect_feed_urls(origin)
    new_feed_urls = [url for url in feed_urls if url not in seen]
    result.urls.extend(new_feed_urls)
    seen.update(new_feed_urls)
    result.rss_count = len(feed_urls)

    result.source_detail = {
        "sitemap": result.sitemap_count,
        "rss": result.rss_count,
        "total_unique": len(result.urls),
    }
    return result


def _extract_sitemap_urls_from_robots(robots_text: str, origin: str) -> list[str]:
    urls: list[str] = []
    for raw_line in robots_text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() == "sitemap":
            sitemap_url = value.strip()
            if sitemap_url:
                urls.append(urljoin(origin, sitemap_url))
    return urls


def _collect_sitemap_urls(roots: list[str], origin: str) -> list[str]:
    """sitemap index를 BFS로 순회한다.

    DFS(LIFO)였을 때는 MAX_SITEMAP_URLS 제한에 도달했을 때 깊은 쪽에
    치우친 URL만 수집되는 편향이 있었다. BFS로 바꿔 상위 sitemap이 먼저
    소진되도록 한다.
    """
    urls: list[str] = []
    origin_netloc = urlparse(origin).netloc
    client = httpx.Client(timeout=FEED_TIMEOUT, follow_redirects=True)
    try:
        queue: deque[tuple[str, int]] = deque((root, 0) for root in roots)
        seen_sitemaps: set[str] = set()
        while queue:
            sitemap_url, depth = queue.popleft()
            if sitemap_url in seen_sitemaps or depth > MAX_SITEMAP_DEPTH:
                continue
            seen_sitemaps.add(sitemap_url)
            try:
                response = client.get(sitemap_url)
            except Exception:
                continue
            if response.status_code != 200 or not response.content:
                continue
            try:
                root_el = ET.fromstring(response.content)
            except ET.ParseError:
                continue

            tag = root_el.tag.split("}", 1)[-1]
            if tag == "sitemapindex":
                child_urls = [
                    loc.text.strip()
                    for sitemap_el in root_el.findall(f"{{{SITEMAP_NS}}}sitemap")
                    for loc in sitemap_el.findall(f"{{{SITEMAP_NS}}}loc")
                    if loc.text and loc.text.strip()
                ]
                for child_url in child_urls:
                    queue.append((child_url, depth + 1))
            elif tag == "urlset":
                for url_el in root_el.findall(f"{{{SITEMAP_NS}}}url"):
                    loc = url_el.find(f"{{{SITEMAP_NS}}}loc")
                    if loc is None or not loc.text:
                        continue
                    candidate = loc.text.strip()
                    if urlparse(candidate).netloc != origin_netloc:
                        continue
                    urls.append(candidate)
                    if len(urls) >= MAX_SITEMAP_URLS:
                        return urls
    finally:
        client.close()
    return urls


def _collect_feed_urls(origin: str) -> list[str]:
    urls: list[str] = []
    origin_netloc = urlparse(origin).netloc
    client = httpx.Client(timeout=FEED_TIMEOUT, follow_redirects=True)
    try:
        try:
            response = client.get(origin)
        except Exception:
            return []
        if response.status_code != 200 or not response.text.strip():
            return []

        soup = BeautifulSoup(response.text, "lxml")
        feed_links = []
        for link in soup.find_all("link", href=True):
            type_value = (link.get("type") or "").lower()
            rel_value = (link.get("rel") or [])
            if isinstance(rel_value, str):
                rel_value = [rel_value]
            rel_joined = " ".join(rel_value).lower()
            if "rss" in type_value or "atom" in type_value or "feed" in rel_joined:
                feed_links.append(urljoin(origin, link["href"]))
        if not feed_links:
            feed_links = [
                urljoin(origin, "/feed"),
                urljoin(origin, "/rss"),
                urljoin(origin, "/atom.xml"),
            ]

        for feed_url in feed_links[:MAX_FEED_LINKS]:
            if urlparse(feed_url).netloc != origin_netloc:
                continue
            try:
                feed_response = client.get(feed_url)
            except Exception:
                continue
            if feed_response.status_code != 200 or not feed_response.content:
                continue
            urls.extend(_extract_urls_from_feed(feed_response.content, origin_netloc))
    finally:
        client.close()
    return urls


def _extract_urls_from_feed(feed_xml: bytes, origin_netloc: str) -> list[str]:
    urls: list[str] = []
    try:
        root_el = ET.fromstring(feed_xml)
    except ET.ParseError:
        return urls

    tag = root_el.tag.split("}", 1)[-1]
    if tag == "rss":
        for item in root_el.findall(".//item"):
            link_el = item.find("link")
            if link_el is not None and link_el.text:
                candidate = link_el.text.strip()
                if urlparse(candidate).netloc == origin_netloc:
                    urls.append(candidate)
    else:
        for entry in root_el.findall(f".//{{{ATOM_NS}}}entry"):
            links = entry.findall(f"{{{ATOM_NS}}}link")
            chosen = None
            for link in links:
                rel = (link.get("rel") or "").lower()
                href = (link.get("href") or "").strip()
                if href and (rel in {"", "alternate"}):
                    chosen = href
                    break
            if not chosen and links:
                chosen = (links[0].get("href") or "").strip()
            if chosen and urlparse(chosen).netloc == origin_netloc:
                urls.append(chosen)
    return urls
