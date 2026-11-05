"""Markdown rendering, sanitization, preview and HTML route tests."""

import pytest
from fastapi.testclient import TestClient

from app.services.markdown import render_markdown


def test_markdown_preserves_common_content_and_remote_image() -> None:
    rendered = render_markdown(
        """# Heading

- first
- second

| Name | Value |
| --- | --- |
| unit | one |

```python
print("safe")
```

[Reference](https://example.org "title")

![diagram](https://example.org/diagram.png "Diagram")
"""
    )

    assert '<h1 id="article-heading">Heading</h1>' in rendered
    assert "<ul>" in rendered and "<li>first</li>" in rendered
    assert "<table>" in rendered and "<td>unit</td>" in rendered
    assert "<pre><code>" in rendered and 'print("safe")' in rendered
    assert (
        '<a href="https://example.org" title="title" rel="noopener noreferrer">'
        in rendered
    )
    assert (
        '<img src="https://example.org/diagram.png" alt="diagram" title="Diagram">'
        in rendered
    )


@pytest.mark.parametrize(
    "markdown",
    [
        "<script>alert(1)</script>",
        '<img src="x" onerror="alert(1)">',
        '<svg onload="alert(1)"><script>alert(1)</script></svg>',
        '<a href="javascript:alert(1)" onclick="alert(1)">unsafe</a>',
        "[unsafe](javascript:alert(1))",
        "[unsafe](data:text/html;base64,PHNjcmlwdD4=)",
        '<a href="java&#x73;cript:alert(1)">encoded</a>',
        "<script><img src=x onerror=alert(1)>",
        '<img src="http://[invalid" alt="bad">',
    ],
)
def test_renderer_removes_xss_and_unsafe_url_payloads(markdown: str) -> None:
    rendered = render_markdown(markdown).lower()

    assert "<script" not in rendered
    assert "<svg" not in rendered
    assert "onerror" not in rendered
    assert "onload" not in rendered
    assert "onclick" not in rendered
    assert 'href="javascript:' not in rendered
    assert "href='javascript:" not in rendered
    assert 'href="data:' not in rendered
    assert "href='data:" not in rendered


def test_image_urls_must_be_absolute_http_or_https() -> None:
    rendered = render_markdown(
        "![relative](images/chart.png)\n\n![web](//example.org/chart.png)"
        "\n\n![mail](mailto:charts@example.org)"
        "\n\n![safe](https://example.org/chart.png)"
    )
    assert 'src="images/chart.png"' not in rendered
    assert 'src="//example.org/chart.png"' not in rendered
    assert 'src="mailto:charts@example.org"' not in rendered
    assert 'src="https://example.org/chart.png"' in rendered


def test_preview_and_saved_article_share_the_same_renderer(
    wiki_client: TestClient,
) -> None:
    markdown = "# Same output\n\n<script>alert(1)</script>\n\n- safe"
    preview = wiki_client.post("/api/markdown/preview", json={"markdown": markdown})
    assert preview.status_code == 200
    assert preview.json()["html"] == render_markdown(markdown)

    created = wiki_client.post(
        "/api/pages",
        json={"path": "/docs/security", "title": "Security", "markdown": markdown},
    )
    assert created.status_code == 201
    article = wiki_client.get("/wiki/docs/security")
    assert article.status_code == 200
    assert '<h1 id="article-same-output">Same output</h1>' in article.text
    article_body = article.text.split(
        '<article class="article-card markdown-content"', 1
    )[1]
    article_body = article_body.split("</article>", 1)[0]
    assert "<script" not in article_body
    assert "alert(1)" not in article_body


def test_preview_rejects_unknown_fields_and_oversized_markdown(
    wiki_client: TestClient,
) -> None:
    client = wiki_client
    assert (
        client.post(
            "/api/markdown/preview", json={"markdown": "ok", "html": "<b>"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/markdown/preview", json={"markdown": "x" * 200_001}
        ).status_code
        == 422
    )


def test_editor_and_article_routes_render_from_shared_page_service(
    wiki_client: TestClient,
) -> None:
    client = wiki_client
    assert client.get("/pages").status_code == 200
    assert client.get("/pages/new").status_code == 200
    created = client.post(
        "/api/pages",
        json={"path": "/docs/ui", "title": "UI", "markdown": "## Article"},
    ).json()
    assert 'href="/wiki/docs/ui"' in client.get("/pages").text
    assert client.get(f"/pages/{created['id']}/edit").status_code == 200
    assert "Article" in client.get("/wiki/docs/ui").text
