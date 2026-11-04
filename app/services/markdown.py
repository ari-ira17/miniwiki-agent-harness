"""One safe Markdown-to-HTML pipeline with a heading outline."""

import re
import secrets
import unicodedata
from html.parser import HTMLParser
from urllib.parse import urlsplit

import nh3
from markdown_it import MarkdownIt

MAX_MARKDOWN_LENGTH = 200_000
ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "img",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}
HEADING_TAGS = {f"h{level}" for level in range(1, 7)}


def _filter_attribute(allowed_ids: set[str]):
    def filter_attribute(tag: str, attribute: str, value: str) -> str | None:
        if attribute == "data-mw-anchor" and tag in HEADING_TAGS:
            return value if value in allowed_ids else None
        if attribute == "id":
            return None
        if attribute == "src" and tag == "img":
            try:
                parsed = urlsplit(value)
            except ValueError:
                return None
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
                return None
        return value

    return filter_attribute


def _heading_id(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    slug = re.sub(r"[^\w-]+", "-", normalized, flags=re.UNICODE).strip("-")
    return f"article-{slug or 'section'}"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def render_document(markdown: str) -> tuple[str, list[dict[str, int | str]]]:
    """Render sanitized HTML and return stable, unique Markdown heading anchors."""
    if len(markdown) > MAX_MARKDOWN_LENGTH:
        raise ValueError("Markdown exceeds the 200000 character limit.")
    parser = MarkdownIt("commonmark", {"html": True, "maxNesting": 20}).enable("table")
    tokens = parser.parse(markdown)
    used: set[str] = set()
    heading_rows: list[tuple[object, object, str, str]] = []
    allowed_markers: set[str] = set()
    nonce = secrets.token_urlsafe(12)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or index + 1 >= len(tokens):
            continue
        inline = tokens[index + 1]
        anchor_base = _heading_id(inline.content)
        anchor = anchor_base
        suffix = 2
        while anchor in used:
            anchor = f"{anchor_base}-{suffix}"
            suffix += 1
        used.add(anchor)
        marker = f"{nonce}-{len(heading_rows)}"
        allowed_markers.add(marker)
        token.attrSet("data-mw-anchor", marker)
        heading_rows.append((token, inline, anchor, marker))

    cleaner = nh3.Cleaner(
        tags=ALLOWED_TAGS,
        clean_content_tags={
            "embed",
            "iframe",
            "math",
            "object",
            "script",
            "style",
            "svg",
        },
        attributes={
            "a": {"href", "title"},
            "img": {"alt", "src", "title"},
            **{tag: {"data-mw-anchor"} for tag in HEADING_TAGS},
        },
        attribute_filter=_filter_attribute(allowed_markers),
        strip_comments=True,
        url_schemes=ALLOWED_URL_SCHEMES,
        url_relative="pass_through",
    )
    rendered = cleaner.clean(parser.renderer.render(tokens, parser.options, {}))
    for index, (_token, inline, anchor, marker) in enumerate(heading_rows):
        label_html = cleaner.clean(
            parser.renderer.renderInline(inline.children or [], parser.options, {})
        )
        extractor = _TextExtractor()
        extractor.feed(label_html)
        heading_rows[index] = (
            _token,
            inline,
            anchor,
            " ".join("".join(extractor.parts).split()),
        )
        rendered = rendered.replace(
            f'data-mw-anchor="{nonce}-{index}"', f'id="{anchor}"', 1
        )
    outline = [
        {"level": int(token.tag[1]), "title": label, "id": anchor}
        for token, _inline, anchor, label in heading_rows
    ]
    return rendered, outline


def render_markdown(markdown: str) -> str:
    """Render and sanitize Markdown; retained for preview compatibility."""
    return render_document(markdown)[0]
