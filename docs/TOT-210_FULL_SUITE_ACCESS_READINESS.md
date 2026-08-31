# TOT-210 full-suite application access readiness

Reconciled base: `4cdbc3e26ac0a955c7a8693071196a8bc7598260` (protected Alpha branch baseline; deployment state not inferred).

| Suite surface | Catalog route | Readiness | Access after TOT-210 | Evidence basis |
|---|---|---|---|---|
| Total RO Design | `/ro` | Available | Active entitled users | Hosted Flask UI and calculation APIs; existing focused runtime/browser suites. |
| CCRO | Total RO process mode | Testable | Through Total RO entitlement | Registered by `ccro_runtime`; it is not a separate Suite product or entitlement. |
| Batch RO | Total RO process mode | Testable | Through Total RO entitlement | Registered by `batch_ro_runtime`; it is not a separate Suite product or entitlement. |
| Total Bio Design | `/apps/bio/` | Controlled Alpha preview | Administrators and active, currently entitled users | Deployed static specialist application plus Suite auth subrequest. |
| Total ZLD Design | `/zld/` | Controlled Alpha preview | Administrators and active, currently entitled users | Registered Flask blueprint with UI, health API, and guarded engineering APIs. |
| Total Water Academy | `/academy` | Controlled Alpha preview | Administrators and active, currently entitled users | Registered Flask blueprint with its own guarded UI/API and persisted progress. |
| Total Pretreatment Design | `/pretreatment` | Not functionally testable in this baseline | Unavailable | Catalog/status page only; no specialist application route is registered. |
| Total Post-Treatment Design | `/post-treatment/` | Not functionally testable in this baseline | Unavailable | Portfolio placeholder; no specialist application route is registered. |
| Total Water Balance | `/balance` | Engine only, no Suite application | Unavailable | Python engine exists, but no application UI/route is registered. |
| Total Water Economics | `/economics-suite` | Components only, no standalone Suite application | Unavailable | RO economics components exist, but no standalone Suite application route is registered. |
| System Integration & Optimization | `/integrate` | Not functionally testable in this baseline | Unavailable | Catalog/status page only; no specialist application route is registered. |

## Exact gates changed

- `auth.user_can_access_product`: catalog `admin_preview_enabled` now grants active administrators preview access and permits an active/current explicit entitlement for controlled testers.
- `auth.serialized_product_entitlements`: dashboard/API `accessible` uses the same release/readiness rule for Bio, ZLD, and Academy.
- A mere entitlement cannot bypass readiness: products that are neither `available` nor `admin_preview_enabled` remain denied.
- Product statuses and routes are unchanged. Preview products remain labeled **In Development**, not **Available**.

## Composed-runtime Chromium evidence

Executed against the production `wsgi` composition with a disposable SQLite database, real password-authenticated sessions, Chromium 1.62.0, and the production Bio auth subrequest. The Bio static-file route in this evidence host mirrors the nginx-owned `/apps/bio/` file mapping; authorization was still decided by the application endpoint and shared policy.

```text
admin dashboard 200 http://127.0.0.1:5210/suite
admin zld 200 Total ZLD Design — Engineering Preview
admin academy 200 Total Water Academy
admin bio 200 Total Bio Design — Biological Wastewater Treatment
admin bio-auth 204
authorized dashboard 200 http://127.0.0.1:5210/suite
authorized zld 200 Total ZLD Design — Engineering Preview
authorized academy 200 Total Water Academy
authorized bio 200 Total Bio Design — Biological Wastewater Treatment
authorized bio-auth 204
enabled-app uncaught console errors: []
denied /zld/ 200 http://127.0.0.1:5210/suite
denied /academy 403 http://127.0.0.1:5210/academy
```
