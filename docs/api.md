# MiniWiki REST API

Interactive OpenAPI documentation is available locally at `/docs`; the schema
is available at `/openapi.json`. The default Compose service is bound to `127.0.0.1`. Authentication uses
server-side PostgreSQL sessions and cookies. Guests cannot read wiki content;
there is no self-registration. The initial admin creates other accounts.

Successful responses use JSON by default. `DELETE` returns an empty `204`
response, and export returns a ZIP attachment.
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
  "author_full_name": null,
  "last_editor_id": null,
  "last_editor_full_name": null,
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
New pages record the authenticated creator in `author_id` and initial editor
in `last_editor_id`. Authenticated saves (including tags/visibility) update the
last editor and timestamp while preserving the creator. Read responses include
`author_full_name` and `last_editor_full_name`; legacy/imported records can have
null attribution. Editor fields cannot be supplied by clients. The `public` tag controls reader visibility. `is_public`
is a compatibility representation of that tag. Setting only `is_public` adds
or removes the tag; setting only `tags` derives visibility from the tag. When
both are supplied, inconsistent values return `422`. Adding `public` through
the boolean alias still respects the maximum of 20 tags.

Markdown rendering is server-side and shared by the article view and preview
endpoint. The sanitizer preserves headings, lists, tables, code, links and
remote images with absolute `http`/`https` URLs. It removes scripts, SVG,
event-handler attributes, and dangerous URL schemes. Images are referenced by
URL. Export preserves those URLs in the Markdown source.

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
| `GET /api/export` | `200` | Download all wiki pages as a ZIP attachment. Admin only. |
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

## Authentication and permissions

| Operation | Guest | Reader | Editor | Admin |
|---|---|---|---|---|
| Read/list/search/tags/tree | `401` | Public-tagged pages only | All pages | All pages |
| Create/update/delete/preview | `401` | `403` | Allowed | Allowed |
| Manage users | `401` | `403` | `403` | Allowed |
| Export all pages | `401` | `403` | `403` | Allowed |

A private or missing article returns the same `404` to a reader, by id or
path. Counts, pagination, search, tags, tree and breadcrumbs use the same
visibility scope before deriving results. A virtual branch may reveal the
path segment required to reach a visible descendant, but never the hidden
ancestor title or link. The home page and HTML article routes redirect guests
to `/login`.
The public tag does not enable guest access.

The agreed session lifetime is eight hours with an absolute server expiry.
Session identifiers are random and stored hashed, as are CSRF tokens.
The session cookie is HttpOnly and SameSite=Lax; HTTPS deployments must enable
Secure cookies. Logout revokes the server record. Password/role changes,
deactivation and deletion revoke that user's sessions.

All cookie-authenticated state-changing requests, including login, logout and
Markdown preview, require an `X-CSRF-Token` matching the issued session.
First call `GET /api/auth/csrf` and retain both cookies. Send its `csrf_token`
in the header for `POST /api/auth/login` with JSON `username` and `password`.
A successful login rotates the cookies and token: call the CSRF endpoint
again before subsequent mutations. `GET /api/auth/me` returns the current
identity; `POST /api/auth/logout` returns `204`. Invalid CSRF returns `403`.
Do not put tokens or credentials in URLs or save them in shared logs.

```http
POST /api/auth/login
Content-Type: application/json
X-CSRF-Token: <token returned by the CSRF endpoint>
Cookie: <cookies retained by your HTTP client>

{"username": "<your username>", "password": "<your password>"}
```

## Export

`GET /api/export` uses the admin's session cookie and takes no parameters or
request body. It is read-only. A successful response contains a binary
`application/zip` body with `Content-Disposition: attachment; filename="miniwiki-export.zip"`
and `Cache-Control: no-store`. The archive includes public and private pages.

ZIP entry names are relative. `/docs/nlp` maps to `docs/nlp.md`, and
`/docs/nlp/topic` maps to `docs/nlp/topic.md`. Each UTF-8 file begins with
YAML front matter delimited by `---` lines. The fields are `title` (string)
and `tags` (list of strings). The stored Markdown follows the closing delimiter
and its newline byte for byte. An empty wiki yields a valid empty ZIP.

The API returns `401` for guests and `403` for readers and editors. If a stored
path is invalid or multiple entries would have the same name, the response is
`409` with a generic JSON error and no archive. The **Скачать ZIP** link uses
`GET /export`, which redirects guests to `/login` and returns `403` for readers
and editors. Entry names preserve the page path exactly. Windows extractors may
reject reserved file or directory names such as `con` and `nul`.

## User administration

Only active admins can access `/api/users` and the `/users` screen. There is
no self-registration. User responses contain `id`, `username`, `first_name`, `last_name`,
`full_name`, `role` and `is_active`; passwords and hashes are never returned.

| Method and path | Success | Body and behavior |
|---|---:|---|
| `GET /api/users` | `200` | List accounts ordered by username. |
| `POST /api/users` | `201` | `username`, `first_name`, `last_name`, `password`, `role` (`admin`, `editor`, `reader`); creates an active account. |
| `PATCH /api/users/{user_id}` | `200` | Change `first_name`, `last_name`, `role`, `is_active` and/or `password`; username is immutable. |
| `DELETE /api/users/{user_id}` | `204` | Remove the account; its articles remain, with creator/editor links to this account cleared. |

First and last names are required, trimmed, 1–100 characters each, and cannot
be null or contain only whitespace. Admins edit these fields; changing only
a name does not revoke sessions.

New usernames are trimmed and casefolded, 1–64 characters after normalization: letters, numbers,
underscore, dot or hyphen. Login matches normalized usernames; existing mixed-case accounts retain their
stored names while sharing the same collision checks. If legacy data already
contains conflicting case variants, login requires the exact stored spelling;
new accounts cannot introduce such conflicts. Passwords must
contain 12–256 characters and are stored with Argon2. The admin supplies the
initial credentials to the intended user; this app does not send them.

Duplicate usernames return `409`; missing users return `404`. Empty patches,
unknown fields, invalid roles and invalid passwords return `422`. The final
active admin cannot be deleted, disabled or demoted (`409`), including
concurrent mutations. Password resets, role changes, deactivation and deletion
revoke the target user's sessions. The next request requires login again.
An admin changing their own password or role must also sign in again.
Mutations use the same CSRF header flow as article operations.
