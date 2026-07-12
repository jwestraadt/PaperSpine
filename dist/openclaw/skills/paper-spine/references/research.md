# Research Stage

This file is the canonical stage playbook for the paper-spine orchestrator.

## Purpose

Learn the target scene, index local references, study strong examples, map SOTA
gaps, and produce user-confirmable motivation options. Research must complete
before the user confirms the controlling motivation.

## Literature Retrieval Priority Protocol

1. **Literature MCP tools (preferred).** If the host has MCP servers matching
   `cnki`, `ieee`, `arxiv`, `semantic scholar`, `scholar`, `pubmed`, `crossref`,
   `wos`, `web of science`, or `scopus`, use them first. Record the source
   channel in `source_index.md` as `MCP-CNKI`, `MCP-IEEE`, `MCP-PubMed`, etc.
2. **Host WebSearch / browsing tools (fallback).**
3. **Local files (always available).**
4. **local_first rule:** when `reference_mode=local_first` or `specified_paths`,
   local index must be built first; MCP/web may supplement only.
5. **MCP is an enhancement, not a dependency.** Do not error or ask the user to
   install MCP when none is available.

## Tier Rules

- `flash`: 3 target-scene examples + 3 recent high-quality field/SOTA examples.
- `pro`: 6 target-scene examples + 6 recent high-quality field/SOTA examples.

## Scene Reference Files

The "scene reference file" used by the sub-agents below is selected by the
configured `scene` (note the underscore→hyphen conversion for `report_review`):

| `scene` | Scene reference file |
|---|---|
| `journal` | `references/scenario-journal.md` |
| `conference` | `references/scenario-conference.md` |
| `report_review` | `references/scenario-report-review.md` |
| `competition` | `references/scenario-competition.md` |

When the target is a **named journal or conference venue**, additionally apply
`references/target-journal-research.md` and save
`target_journal_research.md` — the logic-transfer audit consumes it. For
`competition` and `report_review` scenes, apply
`references/task-genre-research.md` for genre learning beyond the scene
checklist (its output is `genre_research.md`).

## Stage 1 — Index Local References

Create `paper_rewriting_output/reference_materials/source_index.md`:

| Source ID | Type | Title/Name | Origin/URL/Path | Why Included | Local File/Note | Used For |
|---|---|---|---|---|---|---|

Use `scripts/reference_inventory.py`:
```bash
python scripts/reference_inventory.py . --output-dir paper_rewriting_output --mode local_first
```

Ingestion rules:

- `reference_mode` semantics: `local_first` scans the default folders
  (`materials_dir`, `reference_materials/`, `references/`, `literature/`,
  `papers/`) before any web/MCP collection; `specified_paths` indexes only
  `reference_paths`; `web` may skip local indexing when no local files exist.
- Source IDs are stable (`REF001`, `REF002`, …) — later stages cite them.
- Local references can support literature context, citation expansion, style
  learning, and background claims. Do **not** treat them as user evidence for
  this paper's results.
- Never bypass paywalls or login restrictions to obtain a source.

## Stage 2 — Three Parallel Specialist Sub-Agents

Launch all three simultaneously. Each agent gets only its own context. Role
cards with per-agent goals and limits: `agents/research-scene.md`,
`agents/research-exemplar.md`, `agents/research-sota.md`.

### Agent A: Scene Analyst → `research_dossier.md`

Context: `scene`, `target_name`, `official_urls`, `source_index.md`, scene reference file.

Sections: Venue Requirements, Review Criteria, Accepted Paper Patterns, Constraints for This Paper.

### Agent B: Exemplar Learner → `exemplar_learning_dossier.md`

Context: `tier`, `source_index.md`, scene reference path.

Sections: Exemplar Inventory table, Structural Patterns, Rhetorical Patterns, Language Patterns.

Full dossier schema, reading procedure, and the optional
`paragraph_function_templates.md` / `result_narrative_templates.md` outputs
(used by the rewrite matrix and logic-transfer audit):
`references/exemplar-learning-dossier.md`.

### Agent C: SOTA Mapper → `sota_gap_map.md`

Context: `tier`, `source_index.md`, `user_motivation` (if set).

Table: Candidate Contribution | What SOTA Already Does | User Evidence | Real Gap | Claim Strength | Risk. Plus Gap Summary.

## Stage 3 — Merge

Produce `style_profile.md`, `motivation_options_after_research.md`, and
`source_map.md`. For the full `style_profile.md` schema, corpus metrics
(`scripts/style_metrics.py`), and deep style imitation, read
`references/style-learning-workflow.md`. `source_map.md` lives at the root of
`paper_rewriting_output/` and maps the user's own materials to the manuscript:
one table row per user source (draft section, figure, table, dataset, note)
stating which planned sections and claims it can support. User materials only —
external examples belong in `source_index.md`, never in `source_map.md`.

Research ends with `motivation_options_after_research.md`. Do **not** stop for
user confirmation here and do not write `confirmed_motivation.md` — that is
Stage 4 (Motivation Confirmation), which runs after the citation support bank
is built. The orchestrator presents the options and blocks there.

## Required Outputs

- `source_map.md`
- `reference_materials/source_index.md`
- `research_dossier.md`
- `exemplar_learning_dossier.md`
- `style_profile.md`
- `sota_gap_map.md`
- `motivation_options_after_research.md`

(`confirmed_motivation.md` is Stage 4's artifact, written only after the user
chooses, revises, or writes their own motivation.)
