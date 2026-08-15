# Design — BB-IMS: Design System & UX Principles

| Field | Value |
| --- | --- |
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Design Lead |
| Status | In Review |

---

## 1. Design Principles

1. **Efficiency first** — bulk actions and keyboard shortcuts for staff.
2. **Calm density** — tables lead; minimal chrome.
3. **Consistency** — same data same layout across desktop/web.
4. **Dark-friendly** — dark mode with CSS custom properties.
5. **Accessible** — WCAG AA, keyboard-first.

## 2. Brand & Visual Identity

- Voice: professional, institutional, reliable.
- Imagery: charts + data tables; institutional colors.

## 3. Color System

| Token | Hex | Usage | Contrast (AA) |
| --- | --- | --- | --- |
| bg | `#F8FAFC` | light bg | — |
| surface | `#FFFFFF` | cards | — |
| primary | `#2563EB` | CTAs | 5.9:1 |
| text | `#0F172A` | body | 15:1 |
| muted | `#64748B` | secondary | 4.9:1 |
| success | `#16A34A` | passed/fees paid | 5.1:1 |
| danger | `#DC2626` | at-risk/failed | 5.9:1 |
| warning | `#D97706` | borderline | 4.7:1 |

## 4. Typography Scale

| Token | Font | Size | Weight | Line-height | Usage |
| --- | --- | --- | --- | --- | --- |
| display | system sans | 28px | 700 | 1.2 | KPI numbers |
| heading | system sans | 20px | 600 | 1.3 | page titles |
| body | system sans | 14px | 400 | 1.5 | content |
| table | mono | 13px | 400 | 1.4 | data tables |
| label | system sans | 12px | 600 | 1.4 | labels |

## 5. Spacing & Grid

- Base 4px (4/8/12/16/24/32).
- Breakpoints: 640/768/1024/1280.

## 6. Component Library

**Data table** (core):

```
┌───┬───────────┬──────────┬────────┐
│ # │ Student   │ Attendance│ Fee %  │
├───┼───────────┼──────────┼────────┤
│ 1 │ A. Kumar  │ 92%      │ 85%    │
└───┴───────────┴──────────┴────────┘
states: loading skeleton, empty, error, paginated
```

**Risk card (SHAP):**

```
┌───────────────────────────┐
│ ⚠ HIGH RISK — Priya S.   │
│ AUROC 0.91 · SHAP top-3  │
│ 1. Attendance -0.42      │
│ 2. Fee arrears -0.31     │
└───────────────────────────┘
```

Other: sidebar nav, command palette (Cmd+K fuzzy), toast, modal, bulk-action bar, KPI card, leave calendar.

## 7. Iconography

- Desktop: tkinter native icons; Web: inline SVG library.

## 8. Accessibility

- WCAG 2.1 AA.
- Keyboard: full tab order, Cmd+K palette, focus rings.
- Risk never color-only.

## 9. Responsive

| Breakpoint | Rule |
| --- | --- |
| < 640 | Single column, drawer nav |
| ≥ 1024 | Sidebar + table layouts |

## 10. Motion

- 150ms hover, 200ms modals, 300ms transitions; reduced-motion honored.

## 11. Dark Mode

- CSS custom properties token mapping (both interfaces).

## 12. Related Documents

| Document | Relationship |
| --- | --- |
| [AppFlow.md](AppFlow.md) | Screens |
| [PRD.md](../product/PRD.md) | UX goals |
| [TechSpec.md](../technical/TechSpec.md) | UI stacks |
| [Schema.md](../technical/Schema.md) | Display data |
| [ImplementationPlan.md](../project/ImplementationPlan.md) | Tasks |
| [Tracker.md](../project/Tracker.md) | Status |
| [Rules.md](../project/Rules.md) | Standards |
| [API.md](../technical/API.md) | Contracts |
| [SecurityAndCompliance.md](../technical/SecurityAndCompliance.md) | Security |
| [Testing.md](../technical/Testing.md) | UI tests |
| [Deployment.md](../technical/Deployment.md) | Deploy |
| [Glossary.md](../reference/Glossary.md) | Vocabulary |
| [RiskRegister.md](../project/RiskRegister.md) | Risks |
