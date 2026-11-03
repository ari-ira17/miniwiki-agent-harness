---
name: add-wiki-endpoint
description: Plan or implement a MiniWiki API endpoint when adding or changing a wiki operation, its permissions, contract, and tests.
---

# Add a MiniWiki endpoint

Read the applicable project rules, accepted ADRs and current implementation.
For a proposed operation use [the endpoint contract checklist](references/endpoint-contract.md)
to describe inputs, responses, authorization and tests before changing code.
Separate agreed behavior from open decisions; ask about unresolved product choices.

After an implementation plan is approved, use the shared service and permission
checks for API and HTML; document the API and test success, validation and
permission failures. Run the checks required by the current stage and report
actual results. Do not invent routes or status codes as accepted contracts.

For a documentation-only demonstration, apply the checklist to a clearly labelled
hypothetical operation and report the draft without creating application files.
