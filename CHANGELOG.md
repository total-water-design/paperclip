# Changelog

## Total Water Design Suite v0.25 Alpha — Engineering Platform Expansion

- Compacted the Suite landing page and preserved approved application branding.
- Moved membrane A/fouling and B/salt-passage controls out of Water Quality and retained them in Plant Design.
- Added automatic Water Chemistry → Plant Design navigation after successful chemistry calculation.
- Added complete HCl/H2SO4 preset switching with concentration/density/stoichiometric property profiles.
- Added authoritative osmotic-pressure and HPP efficiency fields for report/SEC consistency plus a dynamic report glossary.
- Added controlled User Country and Suite-wide Project Country metadata.
- Added administrator Metrics/telemetry infrastructure and queued activation/access-expansion transactional emails.
- Added PostgreSQL/psycopg 3 as the recommended hosted multi-user database architecture.
- Added generalized multi-pass flowsheet objects, downstream concentrate recycle to upstream HPP suction, conservative tear-state convergence, and JFNK/GMRES support.
- Added deterministic two-pass/100% P2-concentrate-recycle regression coverage.
- Preserved single-pass calculation paths and one common physics engine across subscription tiers.
- Split-partial permeate hydraulics and arbitrary interstage recycle destinations remain explicit Alpha limitations rather than being silently approximated.

## Total Water Design Suite v0.24 — Reconciled Release

### Branch reconciliation

- Retained the latest main-conversation code as the authoritative baseline.
- Used the v0.24 FIXED package strictly as a donor for administration, account workflow, IP monitoring, project debugging, authentication templates, deployment validation, and related tests.
- Avoided directory-level replacement and manually resolved shared-file conflicts in favor of the newer landing page, report generator, RO UI, project workflow, and calculations.
- Added regression gates proving protected engineering modules remain byte-identical to the authoritative baseline.

### User administration

- Replaced the stacked administration layout with a compact full-width SaaS-style table.
- Added user search across name, email, organization, and successful-login IP addresses.
- Added sortable columns and combined filters for status, role, and RO subscription tier.
- Added pending-account age, warning treatment, and direct approval/rejection actions.
- Added distinct IP count, last IP, and administrator-only IP-history inspection.
- Moved Add New User into a modal.
- Added product-specific enabled/tier controls to administrator-created accounts.
- Added rejection, suspension, cancellation, reactivation, reset, and access-management workflows.
- Added administrator self-protection and last-active-administrator safeguards.
- Preserved backend authorization for all administration routes.

### Authentication and email

- Preserved scrypt password hashing, Flask-Login sessions, CSRF, lockout/rate-limit logic, account approval, reset/setup tokens, and product entitlements.
- Preserved the corrected Jinja block endings across all authentication templates.
- Added a full-template compile release gate.
- Preserved Google Workspace SMTP configuration through protected environment variables.
- Improved SMTP fallback messages so browser users do not see server paths or raw SMTP exceptions.
- Retained protected `.eml` outbox fallback when delivery is unavailable.

### Project Library and administrator debugging

- Preserved the latest private Suite Project Library as the single project source of truth.
- Preserved Suite project families and product-origin revision identifiers such as `TROD-1-0`.
- Preserved authenticated online create/read/save/copy APIs and desktop fallback behavior.
- Added an administrator-only Project Database table with search, sort, filter, owner metadata, revision information, and read-only JSON inspection.
- Added an audit event whenever an administrator inspects a stored project snapshot.
- Did not introduce a second project database or overwrite the newer project workflow.

### Latest Total RO Design UI preserved

- Preserved compact Plant Design spacing and responsive numeric inputs.
- Preserved blank project-specific inputs and required-field guidance for new designs.
- Preserved reorganized Plant / Array Configuration, Hydraulic Conditions, and active stage cards.
- Preserved the compact All-Case Operating Summary.
- Preserved case-specific Performance, Water Chemistry, Tail Element Chemistry, and Detailed Elements results.
- Preserved Silver+ Auto Design gating and hidden Auto-only inputs for Entry/manual mode.
- Renamed the authenticated toolbar action to **Project Library**.

### Customer report preserved and validated

- Preserved the dedicated report-only template, immutable report snapshot, readiness validation, A4 layout, vector charts, stream table, warnings, and optional appendices.
- Preserved raw-feed and acid-adjusted-feed comparison.
- Preserved acid chemical, concentration, density, pure-acid dose, commercial-solution dose, consumption, alkalinity change, and counter-ion reporting.
- Preserved populated final-concentrate scaling and derived hydraulic values.
- Kept the incorrect process schematic removed; the Principal Process Streams table remains.
- Combined highest saturation and limiting mineral into one compact row to prevent physical PDF overflow.
- Added a dedicated acid-conditioning report validation case with correct four-page logical/physical pagination.

### Deployment

- Added automatic timestamped database and environment backups before installation.
- Builds and validates an isolated candidate environment before live cutover.
- Compiles Python and every Jinja template and runs the authenticated server smoke test before replacing live code.
- Preserves existing database, users, passwords, entitlements, projects, audit history, and environment secrets.
- Reloads Nginx and restarts an existing application service after validation.
- Rolls back application code and virtual environment if cutover fails.

### Engineering calculations

- No membrane, water-chemistry, osmotic-pressure, transport, pressure-drop, pump, ERD, SEC, optimizer, Hydraulic Envelope, economics, unit-conversion, solver-tolerance, or convergence equation was changed by the administration reconciliation.
- Protected engineering modules and solver files remain byte-identical to the authoritative latest baseline.
