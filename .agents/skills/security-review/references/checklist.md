# Security review checklist

- Access: guest and all three roles through direct API, UI, search, tree, tags,
  preview and export. A reader sees only public pages, admin alone exports and
  manages users; protect the last active admin.
- Sessions: Argon2 passwords, server-side session lifecycle, cookie settings,
  CSRF on state-changing forms and logout. Never expose secrets in logs or images.
- Content: same server-side Markdown renderer and nh3 sanitization for display
  and preview; test script, event attributes and dangerous URL schemes.
- Storage: parameterized queries, validation, immutable ASCII paths, no cascading
  deletion of children; export paths cannot traverse outside the archive root.
- Evidence: trace the actual enforcement and relevant tests. Identify missing
  controls separately from requirements or tests that are not implemented yet.
