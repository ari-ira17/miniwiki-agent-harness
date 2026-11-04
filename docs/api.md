# MiniWiki REST API

Interactive OpenAPI documentation is available locally at `/docs`; the schema
is available at `/openapi.json`. The service is currently a local development
prototype bound to `127.0.0.1`. Login, authorization and CSRF protection are
planned for stage 6; do not expose the current API to an untrusted network.

All endpoints use JSON except `DELETE`, which returns an empty `204` response.
Unknown JSON fields are rejected. Validation errors use FastAPI's `422`
response, missing pages return `404`, and duplicate paths return `409`.

## Page representation

```json
{
  "id": 1,
  "path": "/docs/nlp",
  "title": "NLP course",
  "markdown": "# Course notes",
  "is_public": false,
  "author_id": null,
  "created_at": "2026-11-04T12:00:00Z",
  "updated_at": "2026-11-04T12:00:00Z",
  "tags": ["nlp", "поиск"]
}
```

Paths are canonical and immutable: one leading slash, no trailing slash, and
lowercase ASCII slug segments containing letters, digits, and single internal
hyphens. Each segment is at most 64 characters and the full path at most 512.
Intermediate path branches need not have a page. Deleting a page does not
delete pages below it. Titles are trimmed and must contain 1–200 characters;
Markdown is limited to 200,000 characters. Tags are trimmed, Unicode NFC
normalized and casefolded for identity, stored in canonical lowercase form,
limited to 20 per page and 32 characters each. Commas and control characters
are rejected because the editor uses comma-separated input. New pages are
private by default.
The optional author remains null until authenticated editing is implemented.

Markdown rendering is server-side and shared by the article view and preview
endpoint. The sanitizer preserves headings, lists, tables, code, links and
remote images with absolute `http`/`https` URLs. It removes scripts, SVG,
event-handler attributes, and dangerous URL schemes. Images are referenced by
URL; uploads and local asset storage are outside this sprint. The planned
stage 7 export will preserve the Markdown URL without downloading image files;
export is not implemented yet.

## Endpoints

| Method and path | Success | Description |
|---|---:|---|
| `POST /api/pages` | `201` | Create a page. Body: `path`, `title`, optional `markdown`, optional `is_public`, optional `tags`. |
| `GET /api/pages?q=&tag=&limit=50&offset=0` | `200` | Search title/body by case-insensitive substring (`q` up to 200 chars), optionally filter by one exact tag (up to 32 chars). `%` and `_` are literal. Empty `q` lists all visible pages. `limit` is 1–100; `offset` is nonnegative. Returns `items`, `total`, `limit`, and `offset`. Invalid filters return `422`. |
| `GET /api/pages/by-path?path=/docs/nlp` | `200` | Read one page by its canonical path. |
| `GET /api/pages/{page_id}` | `200` | Read one page by numeric id. |
| `PATCH /api/pages/{page_id}` | `200` | Change `title`, `markdown`, `is_public`, and/or `tags`. Omitted tags are preserved; `tags: []` removes all tags. Path and unknown fields are rejected. Empty patches are invalid. |
| `GET /api/tags` | `200` | List tags attached to pages visible to the current principal. |
| `GET /api/navigation/tree` | `200` | Return nested visible pages and virtual branches. A node has `path`, `title`, nullable `page_id`, and `children`. |
| `DELETE /api/pages/{page_id}` | `204` | Delete only the selected page. |
| `POST /api/markdown/preview` | `200` | Render and sanitize `{ "markdown": "..." }`; returns `{ "html": "...", "outline": [{"level": 2, "title": "Section", "id": "article-section"}] }`. Heading IDs use an `article-` prefix and are unique and stable. Maximum 200,000 characters. |

Create example:

```http
POST /api/pages
Content-Type: application/json
```

```json
{
  "path": "/docs/nlp",
  "title": "NLP course",
  "markdown": "# Course notes",
  "tags": ["nlp", "course"]
}
```

No authentication or role checks exist yet; the service remains local only.
Read, search, tag and tree operations use one injectable page-visibility scope.
It currently permits all pages in this prototype. Stage 6 will derive the
scope from the principal and verify the role matrix across every channel.
