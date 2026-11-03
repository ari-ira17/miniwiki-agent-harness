---
name: grill-with-docs
description: Stress-test a MiniWiki design or plan through focused questions and record user-agreed architectural decisions with alternatives and rationale.
---

# Design interview with project memory

Adapted from LinnetCodes/grill-me grill-with-docs, grilling and domain-modeling;
modified for this project. See [license](LICENSE.txt) and [notice](NOTICE.txt).

Read PROJECT, PROGRESS, DECISIONS, ROADMAP and relevant code first. Resolve facts
from the repository; do not re-ask decisions already accepted in an ADR. Identify
unresolved decisions, their dependencies and concrete edge cases. Ask a focused
question with a recommended option, wait for the user's answer, then follow its
dependencies; do not present guesses as decisions. Flag discrepancies with the
existing vocabulary or implementation and clarify them with the user.

Record only decisions actually agreed by the user in `docs/ai/DECISIONS.md`,
including context, alternatives, choice, reason and consequences. Existing ADRs
are changed only when the user agrees to a revision. Keep terminology concise
in existing project documents when needed; do not invent a new domain-model
folder. Before implementing a new stage, obtain the required plan approval.
If the task requires no interview or no decision has been agreed, make no ADR.
