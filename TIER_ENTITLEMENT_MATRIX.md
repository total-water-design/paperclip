# Total RO Design v0.2 Hotfix 10 — Tier Entitlement Matrix

Total RO Design uses one calculation engine, one project format, and one source tree.
Subscription levels are cumulative:

**Entry ⊂ Silver ⊂ Gold ⊂ Platinum**

A higher tier adds workflow and automation. It does not substitute a different membrane,
chemistry, hydraulic, or mass-balance model.

## Entry — Free membrane projection

- Water Quality and complete feed-water definition.
- Manual 1–4 stage Plant Design.
- CCRO Design (Closed Circuit Reverse Osmosis), available after a valid Plant Design basis.
- Batch RO Design (Full Batch Reverse Osmosis), available after a valid Plant Design basis.
- Vendor-neutral membrane database.
- Different membrane manufacturers/models by stage.
- Element-position membrane recipes and hybrid designs.
- Stage-specific permeate backpressure and desired interstage boost.
- System, stage, and element-by-element membrane results.
- Basic current-tab projection report.
- One active case per project.
- Manual pump/energy efficiency inputs; no energy-recovery device.

CCRO and Batch RO are both process configurations within Total RO Design and are available to
**Entry, Silver, Gold, and Platinum**. They are not treated as ERD entitlements or as
Gold/Platinum-only optimization features. Availability is controlled by release maturity and
engineering/workflow readiness (a current Plant Design/water basis), not by subscription tier.

CCRO and Batch RO remain distinct process architectures. CCRO continuously introduces fresh
feed while concentrating a recirculating loop. Full Batch RO processes an initially charged
water inventory through a batch cycle without continuously mixing fresh feed into that
concentrating inventory.

## Silver — Professional manual design

Includes Entry, plus:

- Up to 10 independent cases.
- Hydraulic Envelope with four editable/stored conditions.
- Case comparison.
- VCMP pump database and VFD curve/duty selection.
- Full Engineering Report.

## Gold — Integrated RO plant design

Includes Silver, plus:

- Advance Design and warm-start Auto Design.
- Isobaric Chamber, Turbocharger, Interstage ERD, BiTurbo, DWEER, and Pelton workspaces,
  subject to Plant Design prerequisites and topology/engineering eligibility.
- Economics.

## Platinum — Advanced optimization and internal preview

Includes Gold, plus:

- Design Optimizer.
- Administrator-preview Scenario Matrix and Background Optimizer architecture.
- Future operations/normalization and portfolio capabilities.

Scenario Matrix, Background Optimizer, and operations/normalization remain marked
**internal** until their dedicated acceptance criteria are complete.

## Administrator preview

The desktop alpha defaults to an administrator context. Four controls at the
top of the engineering workspace emulate Entry, Silver, Gold, and Platinum. Administrators
may preview all four customer tiers without changing the licensed-account claim. Previewing
a tier:

- changes the effective entitlement for the current session;
- updates navigation, case limits, fields, and backend permissions;
- does not change the licensed account tier;
- does not store the preview tier in the project file;
- does not delete higher-tier inputs, cases, or results.

CCRO and Batch RO remain visible/available in every preview tier once their Plant Design
prerequisite is met.

## Availability rule

A module is available only when all relevant checks pass:

`tier entitlement AND release maturity AND workflow prerequisite AND engineering eligibility`

For CCRO and Batch RO, the tier-entitlement term is always satisfied for an account that has
access to Total RO Design; the remaining checks are release maturity and engineering/workflow
readiness.

For example, Gold entitlement alone does not make an interstage ERD available to a
one-stage Plant Design.
