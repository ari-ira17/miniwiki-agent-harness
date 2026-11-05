"""Role checks across direct API, search, tags, tree and HTML routes."""

from tests.conftest import login_as


def _create(client, path, title, tags=()):
    response = client.post(
        "/api/pages", json={"path": path, "title": title, "tags": list(tags)}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_guests_must_sign_in_for_articles_and_api(auth_client):
    assert auth_client.get("/api/pages").status_code == 401
    assert auth_client.get("/api/tags").status_code == 401
    assert auth_client.get("/api/navigation/tree").status_code == 401
    assert (
        auth_client.get("/wiki/private/page", follow_redirects=False).status_code == 303
    )
    assert (
        auth_client.get("/pages", follow_redirects=False).headers["location"]
        == "/login"
    )
    assert auth_client.get("/login").status_code == 200


def test_home_catalog_uses_only_role_visible_navigation(auth_client):
    login_as(auth_client, "test-admin")
    _create(auth_client, "/access/private", "Private tree title", ["internal"])
    _create(auth_client, "/access/public", "Public tree title", ["public"])
    _create(auth_client, "/disciplines/nlp", "Public course", ["public"])

    login_as(auth_client, "test-reader")
    home = auth_client.get("/")
    assert home.status_code == 200
    assert "Public tree title" in home.text
    assert "Private tree title" not in home.text
    assert (
        'data-tree-title="Бакалавриат" data-tree-kind="folder" aria-expanded="true"'
        in home.text
    )
    assert (
        'data-tree-title="3 курс" data-tree-kind="folder" aria-expanded="true"'
        in home.text
    )
    assert 'class="create-page-link"' not in home.text
    assert auth_client.get("/pages/new", follow_redirects=False).status_code == 403


def test_admin_and_editor_have_explicit_create_action(auth_client):
    for username in ("test-admin", "test-editor"):
        login_as(auth_client, username)
        home = auth_client.get("/")
        assert home.status_code == 200
        assert 'class="create-page-link" href="/pages/new"' in home.text
        editor = auth_client.get("/pages/new")
        assert editor.status_code == 200
        assert 'class="editor-page"' in editor.text
        assert (
            '<h1 class="editor-mode-title" id="editor-title">РЕДАКТОР MARKDOWN</h1>'
            in editor.text
        )
        assert (
            '<a class="editor-backlink" href="/pages">← К списку страниц</a>'
            in editor.text
        )
        assert 'aria-label="Редактор страницы"' not in editor.text
        assert 'class="toc-card"' not in editor.text
        editor_body = editor.text.split(
            '<main id="main-content" class="main-area">', 1
        )[1].split("</main>", 1)[0]
        assert "Новая страница" not in editor_body
        assert "Редактирование страницы" not in editor_body


def test_reader_only_sees_public_tag_across_read_channels_and_cannot_write(auth_client):
    login_as(auth_client, "test-admin")
    private = _create(auth_client, "/private/topic", "Secret title", ["classified"])
    public = _create(auth_client, "/public/topic", "Open title", ["public", "open"])
    public_child = _create(
        auth_client,
        "/private/topic/visible-child",
        "Visible child",
        ["public", "child-tag"],
    )

    login_as(auth_client, "test-reader")
    assert auth_client.get("/api/pages").json()["total"] == 2
    assert auth_client.get("/api/pages", params={"q": "Secret"}).json()["total"] == 0
    assert (
        auth_client.get("/api/pages", params={"tag": "classified"}).json()["total"] == 0
    )
    assert (
        auth_client.get("/api/pages", params={"q": "Open"}).json()["items"][0]["id"]
        == public["id"]
    )
    assert auth_client.get("/api/pages", params={"tag": "public"}).json()["total"] == 2
    assert auth_client.get("/api/tags").json() == ["child-tag", "open", "public"]
    tree = auth_client.get("/api/navigation/tree").json()
    assert [node["path"] for node in tree] == ["/private", "/public"]
    assert tree[0]["title"] == "private"
    assert tree[0]["children"][0]["title"] == "topic"
    assert tree[0]["children"][0]["children"][0]["path"] == public_child["path"]
    assert "Secret title" not in str(tree)
    assert auth_client.get(f"/api/pages/{private['id']}").status_code == 404
    assert auth_client.get(f"/api/pages/{public['id']}").status_code == 200
    assert (
        auth_client.get(
            "/api/pages/by-path", params={"path": private["path"]}
        ).status_code
        == 404
    )
    assert auth_client.get("/wiki/private/topic").status_code == 404
    assert "Secret title" not in auth_client.get("/pages").text
    assert auth_client.get("/pages/new", follow_redirects=False).status_code == 403

    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    assert (
        auth_client.post(
            "/api/pages", json={"path": "/reader-write", "title": "No"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        auth_client.patch(
            f"/api/pages/{public['id']}", json={"title": "No"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        auth_client.delete(f"/api/pages/{public['id']}", headers=headers).status_code
        == 403
    )
    assert (
        auth_client.post(
            "/api/markdown/preview", json={"markdown": "hi"}, headers=headers
        ).status_code
        == 403
    )


def test_editor_reads_private_and_can_edit_but_is_not_admin(auth_client):
    login_as(auth_client, "test-admin")
    private = _create(auth_client, "/editor/private", "Private")
    login_as(auth_client, "test-editor")
    assert auth_client.get(f"/api/pages/{private['id']}").status_code == 200
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    updated = auth_client.patch(
        f"/api/pages/{private['id']}",
        json={"title": "Edited"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.json()["author_id"] is not None


def test_page_tracks_creator_and_latest_editor(auth_client):
    login_as(auth_client, "test-admin")
    created = _create(auth_client, "/authorship", "Authorship", ["public"])
    assert created["author_full_name"] == "Test Admin"
    assert created["last_editor_full_name"] == "Test Admin"
    original_author_id = created["author_id"]
    original_editor_id = created["last_editor_id"]

    login_as(auth_client, "test-editor")
    edited = auth_client.patch(
        f"/api/pages/{created['id']}",
        json={"tags": ["public", "edited"]},
    )
    assert edited.status_code == 200
    assert edited.json()["author_id"] == original_author_id
    assert edited.json()["author_full_name"] == "Test Admin"
    assert edited.json()["last_editor_id"] != original_editor_id
    assert edited.json()["last_editor_full_name"] == "Test Editor"
    article = auth_client.get(f"/wiki{created['path']}")
    assert article.status_code == 200
    assert "Test Admin" not in article.text
    assert 'class="creator-attribution"' not in article.text
    assert 'class="last-editor-name">Test Editor</strong>' in article.text


def test_deleting_user_preserves_page_with_unknown_author_and_editor(auth_client):
    login_as(auth_client, "test-admin")
    created_user = auth_client.post(
        "/api/users",
        json={
            "username": "temporary-editor",
            "first_name": "Temporary",
            "last_name": "Editor",
            "password": "secure-initial-456",
            "role": "editor",
        },
    )
    assert created_user.status_code == 201

    login_as(auth_client, "temporary-editor", "secure-initial-456")
    page = _create(auth_client, "/unknown-editor", "Unknown editor")
    assert page["last_editor_full_name"] == "Temporary Editor"

    login_as(auth_client, "test-admin")
    deleted = auth_client.delete(f"/api/users/{created_user.json()['id']}")
    assert deleted.status_code == 204
    preserved = auth_client.get(f"/api/pages/{page['id']}")
    assert preserved.status_code == 200
    assert preserved.json()["author_id"] is None
    assert preserved.json()["author_full_name"] is None
    assert preserved.json()["last_editor_id"] is None
    assert preserved.json()["last_editor_full_name"] is None
