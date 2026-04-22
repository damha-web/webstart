from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webstart_audit import cli, extractor
from webstart_audit.discovery import discover
from webstart_audit.extractor import (
    build_sitemap_json,
    render_content_md,
    resolve_content_paths,
)
from webstart_audit.security import mask_pii


class FakeResponse:
    def __init__(self, *, status_code: int = 200, text: str = "", content: bytes | None = None):
        self.status_code = status_code
        self.text = text
        self.content = content if content is not None else text.encode("utf-8")


class FakeClient:
    def __init__(self, mapping: dict[str, FakeResponse]):
        self.mapping = mapping
        self.closed = False

    def get(self, url: str):
        if url not in self.mapping:
            raise AssertionError(f"unexpected URL: {url}")
        return self.mapping[url]

    def close(self):
        self.closed = True


class RuntimeTests(unittest.TestCase):
    def test_normalize_url_removes_tracking_and_fragment(self):
        normalized = cli.normalize_url(
            "https://example.com/about/?utm_source=newsletter&foo=1#team"
        )
        self.assertEqual(normalized, "https://example.com/about?foo=1")

    def test_resolve_content_paths_is_query_safe(self):
        paths = resolve_content_paths(
            [
                "https://example.com/",
                "https://example.com/about",
                "https://example.com/about/team",
                "https://example.com/search?q=1",
            ]
        )

        self.assertEqual(paths["https://example.com/"], Path("_audit/content/_index.md"))
        self.assertEqual(
            paths["https://example.com/about"],
            Path("_audit/content/about/_index.md"),
        )
        self.assertEqual(
            paths["https://example.com/about/team"],
            Path("_audit/content/about/team.md"),
        )
        self.assertTrue(str(paths["https://example.com/search?q=1"]).endswith("search__q-7de36096ee.md"))

    def test_load_robots_rules_returns_text_for_discovery(self):
        fake = FakeResponse(
            text="\n".join(
                [
                    "User-agent: *",
                    "Disallow: /private",
                    "Sitemap: /sitemap.xml",
                ]
            )
        )

        with patch("webstart_audit.cli.httpx.get", return_value=fake):
            rules, loaded, robots_text = cli.load_robots_rules("https://example.com")

        self.assertEqual(rules, ["/private"])
        self.assertTrue(loaded)
        self.assertIn("Sitemap: /sitemap.xml", robots_text)

    def test_discover_collects_sitemap_and_feed_urls(self):
        mapping = {
            "https://example.com": FakeResponse(
                text="""
                    <html>
                      <head>
                        <link rel="alternate" type="application/rss+xml" href="/feed.xml" />
                      </head>
                    </html>
                """
            ),
            "https://example.com/sitemap.xml": FakeResponse(
                content=(
                    """
                    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                      <url><loc>https://example.com/about</loc></url>
                      <url><loc>https://example.com/blog/post-1</loc></url>
                    </urlset>
                    """
                ).encode("utf-8")
            ),
            "https://example.com/feed.xml": FakeResponse(
                content=(
                    """
                    <rss><channel>
                      <item><link>https://example.com/news/alpha</link></item>
                    </channel></rss>
                    """
                ).encode("utf-8")
            ),
        }

        class ClientFactory:
            def __call__(self, *args, **kwargs):
                return FakeClient(mapping)

        with patch("webstart_audit.discovery.httpx.Client", ClientFactory()):
            result = discover("https://example.com", "Sitemap: /sitemap.xml")

        self.assertEqual(
            result.source_detail,
            {"sitemap": 2, "rss": 1, "total_unique": 3},
        )
        self.assertIn("https://example.com/about", result.urls)
        self.assertIn("https://example.com/blog/post-1", result.urls)
        self.assertIn("https://example.com/news/alpha", result.urls)

    def test_build_sitemap_json_builds_tree_and_writes_file(self):
        pages = [
            {"url": "https://example.com/", "title": "Home", "depth": 0},
            {"url": "https://example.com/about", "title": "About", "depth": 1},
            {"url": "https://example.com/about/team", "title": "Team", "depth": 2},
            {"url": "https://example.com/search?q=1", "title": "Search", "depth": 1},
        ]
        path_map = resolve_content_paths([page["url"] for page in pages])

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "_audit").mkdir()
            build_sitemap_json(
                pages,
                path_map,
                project_dir,
                root_url="https://example.com/",
            )

            payload = json.loads((project_dir / "_audit" / "sitemap.json").read_text())

        self.assertEqual(payload["root"], "https://example.com")
        self.assertEqual(payload["totalPages"], 4)
        self.assertEqual(payload["tree"]["url"], "https://example.com/")
        children = {child["url"]: child for child in payload["tree"]["children"]}
        self.assertIn("https://example.com/about", children)
        self.assertIn("https://example.com/search?q=1", children)
        self.assertEqual(
            children["https://example.com/search?q=1"]["contentFile"],
            "_audit/content/search__q-7de36096ee.md",
        )
        about_children = {
            child["url"]: child
            for child in children["https://example.com/about"]["children"]
        }
        self.assertIn("https://example.com/about/team", about_children)


    def test_mask_pii_is_single_source(self):
        self.assertIs(cli.mask_pii, mask_pii)
        self.assertIs(extractor.mask_pii, mask_pii)

    def test_render_content_md_masks_and_embeds_frontmatter(self):
        markdown = render_content_md(
            url="https://example.com/about",
            title="Contact user@example.com",
            depth=1,
            status=200,
            content={
                "bodyText": "Reach us at user@example.com or 010-1234-5678.",
                "sections": [
                    {
                        "heading": "Team",
                        "text": "Call 01012345678 or email hi@example.org.",
                    }
                ],
                "images": [
                    {
                        "src": "https://cdn.example.com/a.png",
                        "alt": "Ping user@example.com",
                        "width": 100,
                        "height": 80,
                    }
                ],
                "jsonLd": [{"@type": "Organization"}],
                "og": {"og:title": "Home"},
                "lang": "ko",
                "canonical": "https://example.com/about",
                "wordCount": 12,
            },
            screenshot="_audit/screenshots/001.png",
            screenshot_mobile="_audit/screenshots/001-m.png",
            crawled_at="2026-04-22T10:00:00",
        )

        self.assertTrue(markdown.startswith("---\n"))
        self.assertIn("url: \"https://example.com/about\"", markdown)
        self.assertIn("word_count: 12", markdown)
        self.assertIn("reading_time: 1", markdown)
        self.assertIn("***@***.***", markdown)
        self.assertNotIn("user@example.com", markdown)
        self.assertNotIn("hi@example.org", markdown)
        self.assertIn("***-****-****", markdown)
        self.assertNotIn("01012345678", markdown)
        self.assertNotIn("010-1234-5678", markdown)

    def test_build_sitemap_json_handles_deep_tree_without_recursion_error(self):
        depth = 1200
        pages = [{"url": "https://example.com/", "title": "root", "depth": 0}]
        path_parts: list[str] = []
        for idx in range(1, depth + 1):
            path_parts.append(f"level{idx}")
            pages.append(
                {
                    "url": "https://example.com/" + "/".join(path_parts),
                    "title": f"level {idx}",
                    "depth": idx,
                }
            )
        path_map = resolve_content_paths([page["url"] for page in pages])

        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            (project_dir / "_audit").mkdir()
            build_sitemap_json(
                pages,
                path_map,
                project_dir,
                root_url="https://example.com/",
            )
            payload = json.loads((project_dir / "_audit" / "sitemap.json").read_text())

        self.assertEqual(payload["totalPages"], depth + 1)
        node = payload["tree"]
        observed_depth = 0
        while node["children"]:
            self.assertEqual(len(node["children"]), 1)
            node = node["children"][0]
            observed_depth += 1
        self.assertEqual(observed_depth, depth)

    def test_collect_sitemap_urls_is_breadth_first(self):
        index_xml = (
            "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<sitemap><loc>https://example.com/a.xml</loc></sitemap>"
            "<sitemap><loc>https://example.com/nested-index.xml</loc></sitemap>"
            "</sitemapindex>"
        ).encode("utf-8")
        nested_index_xml = (
            "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<sitemap><loc>https://example.com/b.xml</loc></sitemap>"
            "</sitemapindex>"
        ).encode("utf-8")
        a_xml = (
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<url><loc>https://example.com/a-first</loc></url>"
            "</urlset>"
        ).encode("utf-8")
        b_xml = (
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<url><loc>https://example.com/b-deep</loc></url>"
            "</urlset>"
        ).encode("utf-8")

        mapping = {
            "https://example.com/sitemap.xml": FakeResponse(content=index_xml),
            "https://example.com/a.xml": FakeResponse(content=a_xml),
            "https://example.com/nested-index.xml": FakeResponse(content=nested_index_xml),
            "https://example.com/b.xml": FakeResponse(content=b_xml),
        }

        class ClientFactory:
            def __call__(self, *args, **kwargs):
                return FakeClient(mapping)

        with patch("webstart_audit.discovery.httpx.Client", ClientFactory()):
            result = discover(
                "https://example.com",
                "Sitemap: https://example.com/sitemap.xml",
            )

        a_index = result.urls.index("https://example.com/a-first")
        b_index = result.urls.index("https://example.com/b-deep")
        self.assertLess(a_index, b_index)

    def test_discover_seed_inserts_depth_zero(self):
        crawl_command = cli.crawl
        self.assertTrue(callable(crawl_command))
        source = Path(cli.__file__).read_text(encoding="utf-8")
        self.assertIn("queue.append((normed, 0))", source)
        self.assertNotIn("queue.append((normed, 1))", source)


if __name__ == "__main__":
    unittest.main()
