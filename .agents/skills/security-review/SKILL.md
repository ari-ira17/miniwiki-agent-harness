---
name: security-review
description: Review MiniWiki changes or proposed designs for security risks, authorization gaps, and evidence of effective safeguards.
---

# Review MiniWiki security

Read `docs/rules/security.md` and inspect the relevant actual files or design.
Use [the security review checklist](references/checklist.md) for the applicable
attack surfaces. Trace enforcement across API, services and UI; do not infer
security merely from a named package or hidden control.

Report actionable findings with file/line or precise design location, trigger,
impact and fix; distinguish verified behavior, untested assumptions and missing
implementation. Run safe, relevant checks if available and state their results.
When reviewing documentation before the application exists, identify future
verification work rather than claiming that the application is secure.
