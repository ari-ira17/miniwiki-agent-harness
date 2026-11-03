---
name: session-handoff
description: Prepare a truthful MiniWiki session handoff or resume work from project memory and Git when a session ends or a new one starts.
---

# Session handoff

Before handoff, compare `git status` and actual files with PROJECT, PROGRESS,
DECISIONS, GOTCHAS, ROADMAP and `docs/report/evidence.md`. Use the
[handoff template](references/handoff-template.md) to update PROGRESS with
completed work, uncommitted state, tests and exact next action. Do not claim a
planned result, external action or unrun check happened. Save only agreed ADRs.

Capture available required screens yourself immediately, inspect readability and
secrets, save actual captures in `docs/report/screenshots/` and register each in
`docs/report/evidence.md` with date, contents, context and caption. If a screen
cannot be captured, immediately tell the user the exact frame and filename and
mark it `ожидается ручной снимок` in both PROGRESS and evidence. Never fabricate
screenshots; list saved and pending materials in the handoff.

On resumption, read project instructions and memory, inspect Git and actual files,
then continue only within the agreed scope. E04 is proven only by actual work in
a new chat reading the handoff; the current chat or a hypothetical transcript
does not count. Tell the user when a new chat is needed.
