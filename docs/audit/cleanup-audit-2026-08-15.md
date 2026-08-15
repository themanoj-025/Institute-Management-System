# Institute-Management-System — Documentation Folder Cleanup & De-LLM-ification Audit (2026-08-15)

## 1. Executive Summary

Scope: full `docs/` tree — root docs, `community/`, `decisions/` (ADR-001…006),
`design/`, `product/`, `project/`, `reference/` (incl. legacy-docs-readme,
SECURITY_QA_REPORT), `technical/` (incl. alerting), `migration/`, `audit/`.
Docs are specific to the actual system (XGBoost+SHAP pipeline, Celery, JWT
auth, real test counts: 348+ backend / 31+ frontend). Reads as human-curated.
One unreferenced doc flagged, not auto-removed.

## 2. Urgent: Leaked Secrets/Credentials Found

None.

## 3. LLM/AI Fingerprints Removed

None. The `alerting.md` "placeholder" match is a real config instruction
(webhook_configs must be configured before production), not filler.

## 4. Structural Changes

None.

## 5. Duplicate Content Consolidated

None. No identical files, no same-basename collisions.

## 6. Contradictions Found (manual review, not auto-resolved)

None.

## 7. Boilerplate/Template Cruft Removed

None.

## 8. Dead Links Fixed/Removed

None. Link scanner clean.

## 9. README / CONTRIBUTING / CONSTITUTION Review

No `docs/README.md` index. `reference/legacy-docs-readme.md` acts as an
outdated overview (see §14).

## 10. Security/Privacy Findings

None. `reference/SECURITY_QA_REPORT.md` is a genuine QA record.

## 11. Consistency Fixes Applied

None required.

## 12. Files Modified

- `docs/audit/cleanup-audit-2026-08-15.md` — added (this report)

## 13. Files/Folders Deleted

None.

## 14. Remaining Manual Review Items

1. **`docs/reference/legacy-docs-readme.md` (Tier 2)** — zero inbound links
   from other docs, and its title ("Documentation — …", "This directory
   contains ADRs…") reads like the old top-level index for the *pre-move*
   docs layout. However, it contains unique factual content (project overview,
   ADR table, deployment + test-status summary). Recommendation: either link
   it from an index as the historical overview, or remove it as superseded by
   the current suite. Not auto-deleted because it holds unique info.
2. **No docs index (Tier 2 recommendation)** — optional `docs/README.md`.

## 15. "Does This Still Look AI-Scaffolded?" Score

**97 / 100** — 100 baseline; −3 for the unreferenced legacy-docs-readme.md
needing an owner decision. Real ADRs with dates, real test counts, no
contradictions.
