# Handoff template

Adapt the existing PROGRESS rather than duplicating stale status:

- Date, stage and whether its plan was approved; completed and in-progress work.
- Git branch and relevant tracked/untracked changes; do not assume saved means committed.
- Checks actually run, results and absent/skipped checks with reasons.
- Decisions accepted, unresolved questions and applicable constraints.
- Collected evidence: list each concrete file in the registry Material column with
  its full absolute checkout path and clickable link; inspect captures and verify
  the files exist. Avoid globs or vague labels. Mark each not-yet-created file as
  planned with its exact proposed path. Refresh absolute paths after moving the checkout.
- Pending manual capture: exact visible frame, filename, reason and status in both
  PROGRESS and evidence; user already informed. No staged or simulated images.
- Exact next action, prerequisites, and whether a fresh chat is required for E04.

Avoid secrets. Resume by reading AGENTS, project rules, PROJECT, PROGRESS,
DECISIONS, GOTCHAS, ROADMAP and evidence, then checking the working tree.
