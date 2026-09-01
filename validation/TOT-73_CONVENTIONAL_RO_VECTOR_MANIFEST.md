# TOT-73 conventional BWRO/SWRO vector freeze

Status: **PENDING HUMAN APPROVAL — NOT CERTIFIABLE**

The machine-readable registry is [`TOT-73_CONVENTIONAL_RO_VECTOR_MANIFEST.json`](TOT-73_CONVENTIONAL_RO_VECTOR_MANIFEST.json). The two downloaded DuPont FilmTec product data sheets under [`sources/`](sources/) are the authority for every frozen value. The original fail-closed skeleton SHA-256 was `b74eeb74ce476b42c64257238f05a39d0d45f7d8bced30de8dafaec72b541c26`.

## Independent-source and anti-fitting controls

No TWDS solver output was used to derive, check, or adjust any expected value or tolerance. No Batch RO tolerance was reused. Manufacturer production variation and minimum rejection remain Layer A product-envelope criteria and never become Layer B solver tolerances.

| Product | Source | SHA-256 | Standard test point |
|---|---|---|---|
| BW30 PRO-400 | Form 45-D03742-en, Rev. 4, November 2024 | `1021bce0a5a8e84020d2e030a145667ec77ebe19039e3130a26f6bb486a81ba2` | 2,000 ppm NaCl; 225 psi (15.5 bar); 25 °C; pH 8; 15% recovery |
| SW30HRLE-400 | Form 45-D00967-en, Rev. 8, January 2026 | `a9cbf1641204b79629a27475d6046ab64f6f81bb58227623add05cc30f10ab9c` | 32,000 ppm NaCl; 5 ppm boron; 800 psi (55 bar); 25 °C; pH 8; 8% recovery |

The sheets do not state permeate backpressure, separate feed flow, concentration-polarization coefficient, or test-point element pressure drop. The manifest therefore explicitly fixes permeate backpressure and pressure-drop adjustment to zero for this comparison, applies no separate concentration-polarization adjustment, and derives feed flow solely from published permeate flow and recovery. These are vector conventions for approval, not new engineering equations.

## Layer A — published product envelope

BW30 PRO-400 publishes 11,000 gpd (42 m³/day), stabilized salt rejection 99.6%, minimum rejection 99.4%, and individual-element flow no more than 15% below nominal (35.7 m³/day lower bound). SW30HRLE-400 publishes 7,500 gpd (28.4 m³/day), stabilized boron rejection 92%, stabilized salt rejection 99.8%, minimum rejection 99.65%, and flow no more than 15% below nominal (24.14 m³/day lower bound). Neither current sheet states an upper flow bound. These envelopes are not numerical regression tolerances.

## Layer B — independent arithmetic

1. BW30 PRO-400: `42 / 24 = 1.75 m³/h`. At 15% recovery, `1.75 / 0.15 = 11.6666666667 m³/h` feed. Salt passage is `100 - 99.6 = 0.4%`; indicative permeate TDS is `2,000 × 0.004 = 8 mg/L`.
2. SW30HRLE-400: `28.4 / 24 = 1.18333333333 m³/h`. At 8% recovery, `1.18333333333 / 0.08 = 14.7916666667 m³/h` feed. Salt passage is `100 - 99.8 = 0.2%`; indicative permeate TDS is `32,000 × 0.002 = 64 mg/L`.

The compared quantities are manufacturer permeate flow and stabilized salt rejection. Each absolute tolerance is one-half of the sheet’s displayed least-significant unit; each relative tolerance is that same rounding interval divided by the expected value. A quantity passes when its absolute **or** relative error is within tolerance (the max(abs, rel) envelope). Comparison occurs at full precision before display rounding. All rules remain `NOT_APPROVED`.

## Catalog data-quality discrepancy

[`data/swro_membranes.json`](../data/swro_membranes.json) assigns SW30HRLE-400 the BW30 PRO-400/34 product URL. The correct authoritative source is the retrieved SW30HRLE-400 sheet at `https://www.dupont.com/content/dam/water/amer/us/en/water/public/documents/en/RO-FilmTec-SW30HRLE-400-PDS-45-D00967-en.pdf`. This task records but does not alter the separately owned catalog entry.

## Remaining gate

The manifest is structurally complete but intentionally has `status=PENDING_HUMAN_APPROVAL`, `immutable=false`, and `registry.approval_status=NOT_APPROVED`. Board approval must precede immutable approval metadata and any same-candidate-SHA TOT-67 rerun.

Approval uses the separate TOT-73_CONVENTIONAL_RO_APPROVAL.json record. It binds the unchanged complete-manifest SHA-256 to approved_by, approved_at, the approval interaction ID, and the candidate commit SHA, so no digest is stored inside the file it hashes. The verifier also hashes both referenced source PDFs and fails closed if either is absent or modified. Focused automated tests cover the pending draft, missing/modified sources, altered vectors or tolerances, and a valid detached approval.
