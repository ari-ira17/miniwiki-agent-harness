---
name: systematic-debugging
description: Investigate a reproducible MiniWiki bug, test failure, or unexpected behavior by tracing evidence, testing a hypothesis, and verifying a focused fix.
---

# Systematic debugging

Adapted from obra/superpowers systematic-debugging; modified for this project.
See [license](LICENSE.txt) and [notice](NOTICE.txt).

1. Read the exact error and relevant code and changes; reproduce safely and
   record the trigger and actual behavior. If reproduction is unavailable,
   gather evidence and report the limitation instead of claiming a cause.
2. Trace the failing data or control flow backwards across component boundaries;
   compare a working case. Avoid revealing secrets in diagnostics.
3. State one testable root-cause hypothesis and check it with the smallest safe
   experiment. If it fails, revise the hypothesis using the new evidence.
4. Add a focused regression check where appropriate, fix the cause, rerun it
   and the affected checks; report actual results. If the required environment
   or test does not exist, record the check as not run with the reason.

If repeated fixes uncover architectural coupling, stop stacking changes and
reassess the design with the user before expanding scope. Record real agent
mistakes and their verified fixes in `docs/ai/GOTCHAS.md` when applicable.
