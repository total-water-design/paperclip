# Suite Core Launch Policy Reconciliation — 2026-08-25

Repository: `total-water-design/total-water-design-suite`
Owner branch: `platform/suite-core`
Owner source milestone: `698df96b0a4031c52a18b2ccb2ec60e91de043ab`
Starting protected Alpha: `27c915f1804d37c4edfdb5d328bd8b85c2617cf7`
Last Suite Core milestone already represented in Alpha: `96bc9e470eaea56d29fd969a3317609ae3d12330`
Reconciliation branch: `reconcile/suite-core-launch-policy-698-alpha`

## Reconciliation policy

This is a selective Suite Core reconciliation. The owner branch and current Alpha are materially divergent, so the owner branch must not be merged wholesale. The net owner change from the last Core milestone already represented in Alpha (`96bc9e47...`) to the current Core source (`698df96b...`) is limited to five Core-owned paths:

1. `suite_catalog.py`
2. `templates/suite_dashboard.html`
3. `templates/suite_landing.html`
4. `tests/test_suite_dashboard_launch_policy.py`
5. `tests/test_suite_post_treatment_portfolio.py`

This ledger is the only additional reconciliation record.

## Functional reconciliation

### Declarative administrator-preview policy

`suite_catalog.py` now owns the administrator-preview policy through `ProductDefinition.admin_preview_enabled`.

The exact enabled set is:
- Total Bio Design
- Total ZLD Design
- Total Water Academy

The following products remain fail-closed for administrator preview:
- Total Pretreatment Design
- Total Post-Treatment Design
- Total Water Balance
- Total Water Economics
- Total Water Design — System Integration & Optimization
- Total RO Design uses its normal subscription/entitlement behavior rather than administrator preview.

The dashboard consumes this catalog metadata rather than a hard-coded product-ID list.

### Total Post-Treatment Design portfolio registration

Suite Core registers Total Post-Treatment Design only as portfolio metadata:
- product ID: `post_treatment`
- status: `in_development`
- route metadata: `/post-treatment/`
- neutral Suite-owned placeholder icon until dedicated artwork is approved
- no public tiers
- no administrator preview
- no specialist runtime import or registration
- no production launch control

This reconciliation does not import any source from `app/total-post-treatment-design` and does not declare that application deployed or launchable.

### Suite narrative

The public Suite story now includes post-treatment and finished-water conditioning while explicitly describing connected stream handoff as a capability the Suite is being built toward. It does not claim unvalidated cross-application integration.

## Current Alpha protections preserved

The current Alpha dashboard and landing shell remain authoritative for newer cross-suite/mobile work. The reconciliation preserves:
- viewport-fit mobile layout metadata
- theme and mobile-web-app metadata
- Apple web-app metadata
- Apple touch icon
- `manifest.webmanifest`
- `mobile.css`
- `mobile.js`
- the current Alpha administrator greeting

Only the owner launch-policy and Post-Treatment portfolio semantics were composed into those templates.

## Explicitly unchanged

This reconciliation does not change:
- `wsgi.py`
- `requirements.txt` / server dependency closure
- `auth.py` or database models/migrations
- deployment workflows or systemd/runtime hardening
- Total RO calculations or UI runtime
- CCRO runtime
- Batch RO runtime/payload
- Shared WaterStream
- Shared Water Chemistry
- Total Bio specialist source
- Total Water Academy specialist source
- Total ZLD specialist source
- Total Water Balance engine
- Total Water Economics engine

## Validation requirements

Before Alpha promotion the frozen candidate must prove:
- exact starting-Alpha identity and exact owner source identity;
- the functional diff is limited to the five Core paths plus this ledger;
- exact owner equality for `suite_catalog.py` and both owner regression files;
- current Alpha critical specialist/shared/runtime files remain byte-identical;
- current Alpha mobile/PWA shell remains present;
- Python/Jinja/owner regression tests pass;
- relevant existing Suite Core regressions pass;
- immutable Batch RO materialization succeeds before integrated WSGI startup;
- `/healthz`, `/ro`, and `/zld` remain healthy in the composed Suite;
- Academy routes, CCRO and Batch RO remain registered;
- Post-Treatment remains portfolio-only and fail-closed;
- protected Alpha remains unchanged throughout validation.

No AWS deployment is performed by this reconciliation. A successful validation may produce a protected Alpha promotion PR. Merging that promotion PR is a separate deployment-triggering action.
