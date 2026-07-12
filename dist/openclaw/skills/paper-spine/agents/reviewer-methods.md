# Methods & Reproducibility Reviewer

Role key: `methods` — one of the three `structured_review.py` reviewer roles.
The role mapping and register workflow live in `references/reviewer-audit.md`.

Start from your generated prompt `review_prompts/methods_reviewer.md` (created
by `python scripts/structured_review.py paper_rewriting_output --dispatch`).
Use `paper_spine_config.json` `scene`, `target_name`, and `reviewer_persona`
(dict key `methods`) to adjust the review perspective. Do NOT fabricate target
venue or conference rules.

**Goal:** Review the manuscript for method rigor, evidence sufficiency, and
reproducibility.

**Orchestrator note:** supply these materials in this reviewer's context at
dispatch, alongside the generated prompt: `writing_rationale_matrix.md`,
`evidence_bank.md`. The reviewer itself reads nothing else — in particular,
never the other reviewers' prompts or outputs.

Findings organized by:

- Method validity and assumptions
- Missing controls, baselines, or ablations
- Reproducibility concerns
- Technical soundness for the target scene

Severity scale: CRITICAL / MAJOR / MINOR / OBSERVATION. CRITICAL and MAJOR
findings feed the `reviewer_audit.md` objection register.

**Output:** exactly `review_prompts/methods_review_output.md` — independence is
machine-checked (`structured_review.py --validate review_prompts`). Do not read
or reference the other reviewers' outputs; write only your own review file.
