# Binary Brain Institute Management System (BB-IMS) — Documentation Index

Single home for all BB-IMS documentation. BB-IMS is a full-stack institute
management platform with a desktop client (CustomTkinter), a web dashboard
(React 19), a REST API (FastAPI), an ML risk-prediction pipeline (XGBoost +
SHAP), and full CI/CD.

**Start here:** [architecture.md](architecture.md) (system map) →
[folder_structure.md](folder_structure.md) (repo tree) →
[technical/TechSpec.md](technical/TechSpec.md) (build details).

## Structure

```
docs/
├── README.md                      ← this index
├── architecture.md                system architecture
├── folder_structure.md            repository + docs tree
├── module_dependency.md           dependency graph
├── package_overview.md            module inventory
├── startup_flow.md                boot + pipeline flow
├── community/
│   └── CONTRIBUTING.md            contribution guide
├── decisions/
│   ├── ADR-001-postgresql-production-database.md
│   ├── ADR-002-xgboost-over-polyfit.md
│   ├── ADR-003-celery-for-background-tasks.md
│   ├── ADR-004-timezone-aware-datetimes.md
│   ├── ADR-005-ml-model-promotion-gate.md
│   └── ADR-006-unified-jwt-auth.md
├── design/
│   ├── AppFlow.md                 app screens / states / flows
│   └── Design.md                  design decisions
├── product/
│   └── PRD.md                     product requirements
├── project/
│   ├── analysis_report.md         repo inventory & classification
│   ├── ImplementationPlan.md      implementation plan
│   ├── RiskRegister.md            risks & mitigations
│   ├── Rules.md                   engineering rules
│   └── Tracker.md                 status tracker
├── reference/
│   ├── Glossary.md                terminology
│   ├── legacy-docs-readme.md      legacy docs overview (pre-move index)
│   └── SECURITY_QA_REPORT.md      security QA record
├── technical/
│   ├── alerting.md                alerting / notifications setup
│   ├── API.md                     endpoint reference
│   ├── Deployment.md              deployment guide
│   ├── Schema.md                  data model
│   ├── SecurityAndCompliance.md   security baseline
│   ├── TechSpec.md                technical spec
│   └── Testing.md                 test strategy
├── migration/
│   ├── migration_summary.md       modernization record
│   ├── old_tree_to_new_tree.md    restructure before/after
│   └── file_move_ledger.md        file-move ledger
└── audit/
    ├── cleanup-audit-2026-08-13.md  previous cleanup audit
    └── cleanup-audit-2026-08-15.md  docs de-LLM-ification audit
```

## Guidance

| You want... | Read |
|---|---|
| How the system works end-to-end | [architecture.md](architecture.md) |
| Architecture decisions | [decisions/ADR-001-postgresql-production-database.md](decisions/ADR-001-postgresql-production-database.md) |
| API surface | [technical/API.md](technical/API.md) |
| Alerting setup | [technical/alerting.md](technical/alerting.md) |
| Deployment | [technical/Deployment.md](technical/Deployment.md) |
| Security QA | [reference/SECURITY_QA_REPORT.md](reference/SECURITY_QA_REPORT.md) |
| What's shipped / next | [project/Tracker.md](project/Tracker.md) |
| Risks & follow-ups | [project/RiskRegister.md](project/RiskRegister.md) |
