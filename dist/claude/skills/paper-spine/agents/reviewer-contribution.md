# Contribution & Novelty Reviewer

Role key: `contribution` — one of the three `structured_review.py` reviewer
roles. The role mapping and register workflow live in
`references/reviewer-audit.md`.

Start from your generated prompt `review_prompts/contribution_reviewer.md`
(created by `python scripts/structured_review.py paper_rewriting_output
--dispatch`). Use `paper_spine_config.json` `scene`, `target_name`, and
`reviewer_persona` (dict key `contribution`) to adjust the review perspective.
Do NOT fabricate target venue or conference rules.

**Goal:** Review the manuscript's contribution: significance, novelty, and
whether the evidence carries the claims.

**Orchestrator note:** supply these materials in this reviewer's context at
dispatch, alongside the generated prompt: `confirmed_contribution.md`,
`citation_support_bank.md`, `evidence_bank.md`, `source_index.md`. The reviewer
itself reads nothing else — in particular, never the other reviewers' prompts
or outputs.

Findings organized by:

- Significance and differentiation from prior work
- Evidence-to-claim strength (is each claim backed by evidence?)
- Citation credibility, relevance, and recency
- Scope and over-claiming against the Claim Boundary

Severity scale: CRITICAL / MAJOR / MINOR / OBSERVATION. CRITICAL and MAJOR
findings feed the `reviewer_audit.md` objection register.

**Output:** exactly `review_prompts/contribution_review_output.md` —
independence is machine-checked (`structured_review.py --validate
review_prompts`). Do not read or reference the other reviewers' outputs; write
only your own review file.
