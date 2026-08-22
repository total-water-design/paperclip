# Total Water Design Suite v0.25 Alpha — Release Notes

**Release date:** 2026-08-21  
**Release class:** Alpha / Engineering Preview  
**Primary scope:** Total Water Design Suite + Total RO Design architectural expansion

## Release position

v0.25 is the first release in which Total RO Design begins moving from a single-application RO calculator toward the shared flowsheet architecture required by the Total Water Design Suite. It preserves the established single-pass/multistage RO engine while adding the foundations for multi-pass RO, downstream-concentrate recycle, Suite-wide project metadata, telemetry, and multi-user PostgreSQL deployment.

This is intentionally labeled **Alpha / Engineering Preview**. The validated conventional RO paths remain available, and the common two-pass second-pass-concentrate recycle topology has a deterministic regression fixture. Some of the most advanced topology features remain explicit experimental boundaries and are not represented as production-ready.

## Main UI and workflow changes

- Compacted the public Suite landing page so the application portfolio begins within/near the first desktop viewport.
- Reused the approved SUITE/PRE/BIO/RO/ZLD/BAL/ECO/SYS application branding.
- Kept UF, NF, IX and EDI within Total RO Design rather than creating independent Suite applications.
- Increased Water Quality information density.
- Removed membrane Flow/Fouling (A multiplier) and Salt Passage (B multiplier) controls from Water Quality; Plant Design remains their authoritative location.
- A successful Water Chemistry calculation now preserves the converged chemistry state and automatically opens Plant Design.
- Added controlled Project Country metadata to Suite project information.

## Acid-property presets

Acid selection now loads a complete property profile rather than changing only the chemical name.

Current validated defaults in the UI include:

- HCl: 32 wt%, density 1.16 kg/L, MW 36.46094 g/mol, 1 equivalent/mol.
- H2SO4: 93 wt%, density 1.83 kg/L, MW 98.07848 g/mol, 2 equivalents/mol.

Changing acid reloads the acid-specific defaults. The user may subsequently override concentration/density where permitted.

## Reporting

- Added authoritative feed osmotic pressure and final-concentrate osmotic pressure result fields.
- Added the actual HPP pump, motor and VFD efficiencies used by the energy calculation to the authoritative result state.
- Report tables use those calculated values rather than recreating the calculations.
- Missing values display **Not calculated** rather than an unexplained dash.
- Added a dynamic Acronyms & Glossary section that includes only abbreviations actually present in the rendered report.
- Added Project Country to report project metadata.

## Accounts, projects and administration

- Added controlled ISO-compatible Country metadata for users.
- Added independent Suite-wide Project Country metadata at the ProjectFamily level.
- Existing projects/users remain loadable without an invented country.
- Added administrator Metrics infrastructure for sessions, engineering events, resource samples, project/storage usage and time-series rollups.
- Added persistent transactional email notification records for account activation and access expansion.
- Founder identity is configurable; defaults are Jerry Ross-Sisniega, CEO and Founder, admin@totalrodesign.com.
- Preserved central Suite authentication, CSRF protection, IP tracking, roles and application entitlements.

## PostgreSQL / multi-user foundation

- PostgreSQL is the recommended hosted database for v0.25.
- `psycopg 3` is included in the server requirements.
- SQLite remains supported for isolated/local testing.
- Schema changes are additive and do not require destructive database recreation.
- Existing independent application-visible project numbering is preserved (`TROD-N-R`, `TBIO-N-R`, `TZLD-N-R`, etc.).

## Generalized RO flowsheet foundation

New first-class flowsheet objects include:

- Stream
- Junction
- Pass
- Stage
- Vessel
- Element
- Splitter
- RecycleLink
- SplitPermeateConfig
- Flowsheet

The generalized engine reuses the existing membrane and chemistry calculations instead of creating tier-specific physics engines.

### Pass limits

- Entry: up to 3 passes
- Silver: up to 8 passes
- Gold: up to 8 passes
- Platinum: up to 8 passes

Split-partial permeate is entitlement-gated Gold+.

### Downstream concentrate recycle

v0.25 supports the important conventional topology in which a downstream-pass concentrate is recycled to an upstream pass **HPP suction**. The upstream HPP therefore receives the converged mixture of external fresh feed plus recycle flow, and pump power uses the actual combined suction flow.

Overall recovery is calculated from exported product divided by external fresh feed; internal recycle does not count as new plant feed.

### Mixing chemistry

- pH is never treated as a conservative mixing variable.
- Conservative component states are mixed first.
- Chemistry is reconstructed through the existing chemistry interface.
- Tear streams use conservative states rather than pH/TDS shortcuts.

### Nonlinear convergence

The v0.25 solver foundation includes:

1. sequential modular initialization;
2. damped/Anderson-type recycle convergence for ordinary loops;
3. scaled Broyden/JFNK-ready residual architecture;
4. Jacobian-Free Newton-Krylov with GMRES support for difficult coupled systems;
5. explicit convergence residual/history and failure handling.

The solver does not return a non-converged final iterate as a successful engineering result.

## Deterministic two-pass recycle validation

A regression fixture exercises:

- 1,000 m3/h external feed;
- two RO passes;
- seven elements per vessel in both passes;
- 100% Pass 2 concentrate recycle to Pass 1 HPP suction;
- independent P1/P2 HPP duties;
- conservative water closure.

The current deterministic TDS-mode validation converges in 7 outer iterations with residual norm approximately `1.48e-7` and water closure approximately `-1.27e-5 m3/h`. See `VALIDATION_v0.25.md` for the detailed result.

## Known limitations / not yet accepted as production-ready

The following are deliberately **not** represented as completed features in this Alpha release:

1. **Element-interface split-partial permeate hydraulics.** The data model, entitlement gate and topology concept exist, but the local hydraulic solve intentionally raises `NotImplementedError` rather than silently approximating a blind-interconnector split as a post-solve flow split.
2. **Arbitrary interstage recycle destinations.** v0.25 supports pass HPP-suction recycle destinations. General interstage/crossing recycle destination UI/physics are still being completed.
3. **Full ionic/Pitzer multi-pass recycle qualification.** The conventional two-pass recycle regression currently validates the TDS-mode flowsheet foundation. Full chemistry recycle qualification still requires expanded engineering fixtures.
4. **Extreme tail-element cases.** An early aggressive full-chemistry/split fixture encountered tail-element nonconvergence. The release preserves that failure rather than forcing a numerically unjustified result.
5. **Open/gas-equilibrium junction mass-transfer model.** The architecture distinguishes open/closed junction intent, but the full gas mass-transfer boundary remains experimental.
6. **Visual arbitrary-topology flowsheet editor.** The generalized backend/API foundation exists; a complete drag-and-connect production UI is not yet included.
7. **Infrastructure telemetry depth.** Event/session/storage metrics are implemented; continuous low-overhead resource sampling and full HTTP latency/cost rollups remain an area for expansion.

## Compatibility

- Existing single-pass projects remain loadable.
- Existing projects without Project Country remain valid.
- Existing users without Country remain valid until updated.
- The project API and central Suite account architecture are preserved.
- No separate Entry/Silver/Gold/Platinum calculation engines were introduced.
