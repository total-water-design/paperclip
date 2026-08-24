# Total Water Design Suite Application UI/UX Contract

**Contract version:** 1.0  
**Owner:** Suite Core (`platform/suite-core`)  
**Scope:** Common application shell, navigation, projects, calculation interaction, inputs, guidance, results, handoff, accessibility and responsive behavior.

## Purpose

Every Total Water Design Suite application remains a specialist engineering product, but users should not need to relearn basic interaction when they move between Pretreatment, Bio, RO, ZLD, Water Balance, Water Economics and System Integration.

The contract standardizes the common shell and behavior. It does **not** standardize specialist calculations, process content, icons or accent colors.

## 1. Common application shell

Every specialist application follows this conceptual hierarchy:

`Suite → Application → Project → Workspace → Inputs / Results`

The shell must expose:

- Total Water Design Suite master identity;
- application icon, name and version;
- **Part of the Total Water Design Suite** endorsement;
- predictable return-to-Suite control;
- common account controls;
- common project bar;
- application/workspace navigation in predictable regions;
- light/dark/system theme behavior;
- responsive collapse rules that preserve the same hierarchy.

Desktop header target is 64–72 px. On mobile the header may wrap, but Suite identity, application identity and return navigation remain visible.

The application accent may identify the active product, primary action and selected navigation state. Accent color must not be the only carrier of meaning.

## 2. Navigation contract

Primary hierarchy is always:

- **Suite** — dashboard / application switcher;
- **Application** — current specialist product;
- **Project** — identity and lifecycle controls;
- **Workspace** — engineering area;
- **Inputs / Results** — current work content.

Project vocabulary is standardized:

`New Project · Project Library · Save · Save As · Revision · Duplicate · Handoff · Report`

Contextual controls belong inside the current workspace rather than becoming competing global navigation.

## 3. Calculation workflow

Common engineering workflow:

`Inputs → Validate → Calculate → Converge → Results → Report`

| State | Customer label |
| --- | --- |
| idle | Calculate |
| validating | Validating… |
| calculating | Calculating… |
| converging | Converging… |
| converged | Converged |
| attention | Needs attention |
| failed | Calculation failed |
| stale | Recalculate |

A coupled calculation should have one primary **Calculate** action. Secondary calculation actions are allowed only for genuinely independent studies.

Customer messages must not expose stack traces, internal exceptions, proprietary algorithm names, hidden solver implementation details, AI/ChatGPT references or developer language.

## 4. Common input controls

Every control indicates its data origin.

| Origin | Standard treatment |
| --- | --- |
| User input | Neutral field with app-accent focus |
| Calculated value | Read-only treatment + Calculated marker |
| Database-selected value | Selection/read-only treatment + Database marker |
| Warning | Warning guidance adjacent to affected section |
| Constraint | Constraint marker + allowed range/engineering limit |

Rules:

- labels remain associated with controls;
- units are visible at the point of entry;
- required inputs use visual and programmatic indication;
- engineering limits are text/tooltips, never color only;
- disabled means unavailable; read-only means visible but not editable;
- advanced options are grouped and collapsed when not part of the normal path;
- display precision does not change calculation precision.

## 5. Guidance and severity system

All apps use the same five severities:

1. **Information** — neutral engineering context.
2. **Review** — assumption/result deserves engineering review.
3. **Warning** — constraint, feasibility or quality concern.
4. **Calculation error** — no usable calculation result.
5. **Critical/system error** — application/service problem outside normal engineering feasibility.

Every guidance card should answer:

- What happened?
- Why does it matter?
- What can the user do next?

## 6. Results architecture

Every application uses this hierarchy where applicable:

1. **System Summary** — major KPIs.
2. **Process / Pass / Unit Summary** — engineering performance.
3. **Detailed Results** — stage/unit/component detail.
4. **Warnings & Constraints**.
5. **Energy / Economics**.
6. **Water Chemistry**.

Applications may omit irrelevant sections but should not create a competing top-level hierarchy.

KPI cards use one label, value, unit and optional status. Tables use consistent units, decimal formatting and scroll/sticky-header behavior. Status chips use text plus color.

## 7. Common project behavior

Product IDs remain:

| Application | Prefix |
| --- | --- |
| Pretreatment | `TPRE` |
| Bio | `TBIO` |
| RO | `TROD` |
| ZLD | `TZLD` |
| Water Balance | `TWBAL` |
| Water Economics | `TWECO` |
| System Integration | `TWSYS` |

New Project, Save, Save As, Revision, Duplicate, Handoff and project identity must look and behave consistently. Unsaved work is visible and destructive navigation warns the user.

## 8. Common handoff experience

A handoff view shows:

- source application and source project/revision;
- receiving application;
- transferred water stream;
- lineage identifier where available;
- inherited values;
- inherited values that are editable;
- whether edits supersede lineage.

Inherited values must look different from fresh manual input.

## 9. Application personality

Current Suite catalog accents/icons remain authoritative. Specialist apps keep their accent and engineering content while typography, spacing, control geometry, navigation and interaction conventions remain Suite-standard.

## 10. Theme, accessibility and responsive behavior

Shared theme vocabulary is `system`, `light`, `dark`. One Suite preference key is used across specialist applications.

Minimum accessibility expectations:

- semantic buttons/links;
- visible keyboard focus;
- label/control association;
- `aria-live` for calculation state and material guidance updates;
- keyboard-operable menus/dialogs/disclosures;
- no essential meaning by color alone;
- mobile preserves Suite/Application/Project hierarchy;
- wide engineering tables scroll inside their region;
- practical touch targets around 40 px or larger.

## 11. Shared Suite Core component library

Suite Core owns:

- `templates/shared/application_shell.html`
- `templates/shared/suite_components.html`
- `static/suite_ui_tokens.css`
- `static/suite_application_shell.css`
- `static/suite_application_shell.js`

Specialist applications progressively extend/consume these pieces. Specialist branches retain ownership of their engines, process forms and calculation results.

## 12. Conformity audit — 2026-08-22

Audit basis: current `platform/suite-core`, `app/total-ro-design`, `app/total-bio-design` and `app/total-zld-design`.

| Standard | RO | Bio | ZLD | Required correction |
| --- | --- | --- | --- | --- |
| Suite master identity | Partial: Suite return + endorsement exist | Owning branch does not yet have a dedicated Bio shell; `index.html` still identifies as RO | Owning branch does not yet have a dedicated ZLD shell; `index.html` still identifies as RO | Adopt shared shell; preserve product accent/icon |
| Application identity | Good | UI inconsistency | UI inconsistency | Replace inherited RO title/icon/name with catalog-driven Bio/ZLD identity |
| Header/account controls | Mature but RO-specific | Inherited RO template | Inherited RO template | Move common structure to shared shell |
| Navigation hierarchy | Partial: rich RO sidebar but historical grouping does not fully map to common hierarchy | Not independently defined | Not independently defined | Map specialist workspaces to common hierarchy |
| Project controls | Partial: New, Library, Save and metadata exist; lifecycle controls are not one standard bar | Not independently defined | Not independently defined | Adopt shared project bar and wording |
| Theme behavior | Partial: RO has app-specific Light/Dark selector | Not independently defined | Not independently defined | Consume shared system/light/dark preference |
| Calculation workflow | Partial: Calculate exists; Run All is another major action and state vocabulary differs | Not independently defined | Not independently defined | Use common state vocabulary; keep secondary actions only when independent |
| Input origin styling | Good foundation: RO distinguishes setpoint/calculated fields | Not independently defined | Not independently defined | Align to User / Calculated / Database / Constraint vocabulary |
| Guidance/errors | Partial: warning/error styles exist but severity vocabulary is app-specific | Not independently defined | Not independently defined | Adopt common five-level guidance component |
| Results hierarchy | Partial: KPI/tables mature but section hierarchy is RO-specific | Not independently defined | Not independently defined | Map outputs to common results hierarchy |
| Report action | Present in more than one location | Not independently defined | Not independently defined | Keep one predictable primary Report action |
| Handoff experience | No common lineage card in application shell | Not independently defined | Not independently defined | Adopt shared handoff component |
| Accessibility | Partial: semantic controls common; custom menus/dialogs need app-level keyboard review | Same inherited concerns | Same inherited concerns | Validate keyboard/focus after migration |
| Responsive behavior | Extensive but RO-specific | Inherited RO behavior rather than Bio design | Inherited RO behavior rather than ZLD design | Adopt common shell breakpoints, retain specialist workspace responsiveness |

### Difference classification

- **Intentional engineering difference:** RO membrane/ERD workspaces, Bio biological process workspaces, ZLD concentration/crystallization workspaces.
- **Acceptable product accent difference:** catalog accent and product icon/logo.
- **UI inconsistency:** ad-hoc input origins, guidance severities, card geometry, project/account placement.
- **Navigation inconsistency:** per-app historical grouping without a shared Suite/Application/Project/Workspace frame.
- **Interaction inconsistency:** differing calculation state wording and competing primary-looking actions.
- **Accessibility issue to verify:** custom menu/dialog/disclosure keyboard behavior and focus.
- **Responsive-layout issue to verify:** specialist large tables and multi-column forms after shell migration.

## 13. Incremental implementation strategy

### Phase 1 — Suite Core

- freeze UI/UX Contract v1.0;
- provide common tokens, components, shell and behavior controller;
- validate without changing specialist calculations.

### Phase 2 — RO (`app/total-ro-design`)

- adapt mature RO UI to shared shell without calculation changes;
- map project controls into common project bar;
- map calculation states and guidance to common vocabulary;
- preserve RO workspaces and blue accent.

### Phase 3 — Bio (`app/total-bio-design`)

- replace inherited RO application identity/template with Bio-specific shell usage;
- use Bio accent/icon;
- implement Bio workspace navigation/results with common hierarchy.

### Phase 4 — ZLD (`app/total-zld-design`)

- replace inherited RO application identity/template with ZLD-specific shell usage;
- use ZLD accent/icon;
- implement concentration/crystallization navigation/results with common hierarchy.

### Phase 5 — remaining apps

Pretreatment, Water Balance, Water Economics and System Integration should start on the shared shell rather than creating another independent shell.

## Change-control rule

Changes to this contract are Suite Core responsibilities. Specialist exceptions must be justified by an engineering requirement, not only historical UI behavior.

Contract v1.0 intentionally does not rewrite specialist calculation code.
