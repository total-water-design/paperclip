# Total Water Academy Brand Standard v1.0

**Owner:** `app/total-water-academy`  
**Suite contract:** `platform/suite-core/docs/UI_UX_CONTRACT_v1.0.md`  
**Application accent:** `#1A7F8E`

## Purpose

Total Water Academy is the educational application in the Total Water Design Suite. Its identity must communicate engineering education, water-treatment systems, applied learning and Suite membership without creating a competing master brand.

The Academy application remains inside the Suite hierarchy:

`Total Water Design Suite → Total Water Academy → Learning Journey → Level / Module → Activity`

The Suite master identity remains visible in the shared application shell. Academy branding identifies the active application only.

## Approved assets

| Asset | Repository path | Use |
| --- | --- | --- |
| Primary horizontal logo | `static/branding/suite/total_water_academy_logo.svg` | Product pages, approved marketing surfaces, documentation and future portfolio surfaces that support a full application lockup |
| Application icon | `static/branding/suite/total_water_academy_icon.svg` | Suite product card, application header identity, favicon and compact navigation |

The icon is derived from the same emblem used in the primary horizontal logo so the application has one canonical symbol at all sizes.

## Symbol meaning

The emblem combines:

- a water droplet and flowing-water bands — water treatment and water quality;
- an open book — engineering education and progressive learning;
- process-equipment / flow-path cues — learning by designing real treatment systems rather than consuming generic course content.

The symbol is not a separate professional certification seal and must not be presented as an accreditation mark.

## Color

### Authoritative application accent

`Academy Teal — #1A7F8E`

This remains the catalog/application accent and is supplied to the shared shell as `--twds-app-accent`.

### Supporting artwork colors

The logo artwork may use deep navy, aqua, white and tonal teal for visual depth. Supporting colors inside artwork do not create new Suite UI semantic colors. Application controls, severity states, accessibility behavior, backgrounds and typography continue to use Suite Core tokens.

For small text on light surfaces, `#1A7F8E` has approximately 4.70:1 contrast against white and may be used where Suite token behavior permits. In dark-theme contexts, use Suite theme tokens or a sufficiently light accessible treatment rather than assuming the same teal is readable on every dark surface.

## Typography

Academy does **not** define a separate application font family. Product UI inherits the Total Water Design Suite typography and control geometry from Suite Core. The logo wordmark is artwork and does not authorize a new UI font stack.

## Application-shell usage

The shared shell must show:

- Total Water Design Suite master identity;
- Total Water Academy icon, name and version;
- “Part of the Total Water Design Suite” treatment supplied by the Suite shell/contract;
- common account/project/theme behavior.

Do not replace the Suite master lockup with the Academy logo. The full Academy horizontal logo is a product lockup, not the master Suite identity.

## Accessibility and responsive rules

- Product name must remain available as text; do not rely on the logo image to communicate the application name.
- Decorative logo text does not replace semantic page headings.
- Never use teal alone to communicate pass/fail, warning, lock state or progress meaning.
- The application icon must remain recognizable without surrounding wordmark text.
- Compact/mobile navigation uses the icon plus semantic application name from the shared shell.

## Prohibited variants

Do not:

- recolor the Academy to another application’s accent;
- add independent login, billing or navigation branding;
- use the Academy symbol as a professional engineering seal;
- create alternate mascots or unrelated education marks;
- add unapproved website domains, accreditation claims or institutional affiliations to the logo;
- modify Suite Core typography or semantic colors merely to match logo artwork.

## Change control

Changes to the Academy product mark are owned by `app/total-water-academy`. Changes to the master Suite lockup, shared application shell, global UI tokens or Suite-wide brand hierarchy remain Suite Core responsibilities and must be reconciled through the appropriate owner.
