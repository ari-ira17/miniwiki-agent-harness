---
name: webapp-testing
description: Test a running MiniWiki web interface in a browser when verifying UI behavior, navigation, permissions, or screenshots.
---

# Web application testing

Adapted from Anthropic's webapp-testing; modified for MiniWiki and Codex.
See [license](LICENSE.txt) and [notice](NOTICE.txt).

Check the actual application, environment and available browser before testing.
If the application, browser or required runtime is absent, report the check as
not run and what is needed; do not claim a pass. Do not install dependencies
or start external services without the necessary authorization.

For an existing local server, navigate to the relevant page, wait for a specific
rendered condition, inspect the actual DOM or screen, then use observed selectors
and perform the requested scenario. For dynamic pages avoid relying on the initial
HTML or fixed sleep. Use the project's Playwright setup when available and close
any browser started for the test. Verify results including appropriate roles and
negative paths, and report commands and observed outcomes.

For report evidence, follow `docs/rules/workflow.md`: capture the real available
screen, inspect readability and secrets, save to `docs/report/screenshots/`, and
register it in `docs/report/evidence.md`; if unavailable, immediately specify
the exact manual frame and filename and record the pending action in both the
registry and PROGRESS. Do not replace captures with mockups.
