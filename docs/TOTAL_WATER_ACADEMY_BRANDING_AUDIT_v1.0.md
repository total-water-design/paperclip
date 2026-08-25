# Total Water Academy Branding Audit v1.0

**Branch:** `app/total-water-academy`  
**Audit target:** branding integration against Total Water Design Suite UI/UX Contract v1.0

## Result

Academy branding is ready for selective application reconciliation after validation. The Academy has a dedicated canonical icon and horizontal logo, preserves the authoritative Academy accent `#1A7F8E`, and uses the shared Suite application shell rather than introducing an independent shell.

## Contract checks

| Check | Status | Evidence / requirement |
| --- | --- | --- |
| Suite master identity remains authoritative | PASS | Academy continues to extend `templates/shared/application_shell.html`; no replacement master shell is introduced. |
| Dedicated application identity | PASS | Academy catalog and Academy render contexts use `total_water_academy_icon.svg`. |
| Product logo available | PASS | Catalog `logo_asset` points to `total_water_academy_logo.svg`. |
| Accent is catalog-driven and stable | PASS | Academy remains `#1A7F8E`; branding does not change specialist semantic states. |
| Theme architecture preserved | PASS | Academy uses shared `system/light/dark` behavior and Suite tokens. |
| Product name remains semantic text | PASS | Shared shell renders application name independently of artwork. |
| Color is not sole state carrier | PASS | Learning feedback continues to pair text/status language with visual treatment. |
| No authentication/billing fork | PASS | Branding change does not alter Suite Core entitlement, account or commercial services. |
| No specialist-engine modification | PASS | Branding change is UI/product identity only. |

## Asset consistency audit

The compact app icon is derived from the same emblem used in the horizontal logo. This avoids the earlier draft inconsistency where the standalone icon introduced a graduation-cap variant that was not present in the primary lockup.

The approved visual vocabulary is water + open book + process-flow/equipment cues. It supports the Academy objective: teach engineering by designing water-treatment systems in the Suite.

## Accessibility audit

- Academy accent `#1A7F8E` is approximately 4.70:1 against white, meeting WCAG AA contrast for ordinary text on white at the measured color pair.
- The shared shell keeps the application name as live text, so the logo is not the only accessible name.
- Logo files include accessible SVG title/description metadata, while normal page use should still provide context-appropriate `alt` behavior.
- Dark-theme text must continue to rely on Suite theme/token treatment where the base teal would not provide sufficient contrast on a dark surface.

## Reconciliation dependencies outside Academy ownership

These are **not** fixed by replacing Suite Core files from the Academy branch.

1. **Education portfolio grouping:** current `platform/suite-core` now includes an `education` / “Learning & Development” product group and explicitly mentions Total Water Academy. This dependency is resolved on the Suite Core branch, but the current `alpha` branch has not yet received that newer Suite Core landing/catalog architecture. Reconcile the validated Suite Core milestone first, or preserve equivalent current Alpha behavior while adding the Education group deliberately.
2. **Approved-student launch semantics:** the current Suite Core generic dashboard access calculation still treats generally launchable products as `available` (with a special Bio administrator preview). Academy has an explicit admin-approved pre-commercial student entitlement policy. Reconciliation must decide and test how an entitled approved student receives a launch control without making Academy generally public or bypassing release governance.
3. **Shared-shell prerequisite:** Academy templates extend `templates/shared/application_shell.html` and consume Suite Core UI tokens/components. Current `alpha` does not contain the full shared-shell prerequisite set visible on `platform/suite-core`; Academy must not be reconciled into an Alpha baseline that lacks those prerequisites.
4. If Suite Core later adopts a global branding-asset manifest or a different icon-size convention, Academy assets should be mapped there during reconciliation rather than duplicating Suite-owned logic.

## Merge/conflict risk

The Academy branch has diverged substantially from current `alpha` because it was developed from Suite Core history while Alpha continued receiving other specialist integrations. **Do not merge the branch wholesale.** Reconciliation must preserve current Alpha work and apply Academy-owned files/selective edits only.

Expected reconciliation touch points:

- `suite_catalog.py` — manually add/preserve the Academy product entry; do not replace the entire current Alpha catalog because parallel application routes/statuses may differ;
- `wsgi.py` — manually add Academy imports/registration to the current Alpha WSGI; never replace Alpha's chemistry, CCRO, mobile, ZLD, economics or metrics wiring with the Academy branch WSGI;
- `templates/suite_landing.html` / dashboard presentation — preserve the current target branch and add Academy education/launch behavior only where required;
- Academy-owned `academy.py`, `academy_content.py`, `academy_placement.py`, `templates/academy/**`, `static/academy.*`, Academy branding assets and Academy documentation/tests — predominantly additive;
- `.github/workflows/academy-validation.yml` — Academy-specific validation only.

No changes are required to specialist calculation engines, Shared Chemistry, WaterStream, RO, Bio, Pretreatment, ZLD or Water Economics for this branding milestone.
