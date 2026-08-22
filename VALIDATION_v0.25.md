# Total Water Design Suite v0.25 Alpha — Validation Report

## Automated validation

Release-tree checks performed on 2026-08-21:

```text
Python compileall: PASS
JavaScript syntax (static/app.js): PASS
JavaScript syntax (static/report.js): PASS
JavaScript syntax (static/admin.js): PASS
Jinja template compilation: PASS — 23 templates
pytest: PASS — 50 passed, 2 skipped
```

Skipped tests:

1. Authenticated Flask runtime smoke test: skipped in the packaging environment because Flask/Flask-Login/Flask-SQLAlchemy/Flask-WTF were not installed in that packaging interpreter. Server requirements include these dependencies and the deployment installer creates an isolated server environment.
2. Historical v0.23 byte-baseline comparison: skipped because the historical baseline is intentionally not embedded in the source-only release.

## Two-pass / 100% Pass-2 concentrate recycle regression

### Configuration

```text
External feed                  1000.000 m3/h
External feed pressure         2.0 bar
External-feed TDS              1000 mg/L
Membrane                       DuPont FilmTec BW30XFRLE-400/34
Pass 1                         40 vessels × 7 elements
Pass 1 feed pressure           15 bar
Pass 1 permeate pressure       1 bar
Pass 2                         30 vessels × 7 elements
Pass 2 feed pressure           8 bar
Pass 2 permeate pressure       1 bar
Recycle                        100% P2 concentrate → P1 HPP suction
Tier                           Platinum
```

### Result

```text
Converged                      True
Outer iterations               7
Convergence method             anderson/damped
Final residual norm            1.4806912613751935e-07
Water closure                  -1.2686770105574396e-05 m3/h
Overall external recovery      0.18051697529501315

P1 HPP suction flow            1069.9592088268093 m3/h
P1 membrane feed flow          1069.9592088268093 m3/h
P1 permeate                    250.47617143505235 m3/h
P1 final concentrate           819.483037391757 m3/h
P1 HPP power                   483.1096118772571 kW

P2 suction/feed                250.47617143505235 m3/h
P2 permeate product            180.51697529501314 m3/h
P2 concentrate recycle         69.95919614003921 m3/h
P2 HPP power                   60.89751364620881 kW

Recycle TDS                    55.87139922294213 mg/L
Final product TDS              0.47655863341002874 mg/L
Final P1 reject TDS            1220.1765350203996 mg/L
```

Residual history:

```text
3.8535241761384054e-01
1.6961891878382230e-01
7.9864420362542520e-02
2.6192032106996306e-04
1.3707971836664997e-05
7.0358251106668016e-06
1.4806912613751935e-07
```

This fixture confirms the key hydraulic architecture requested for conventional double-pass RO: the Pass-1 HPP suction flow is external feed plus the converged Pass-2 concentrate recycle. The recycle is internal and is not counted as new external plant feed in overall recovery.

## What is not yet validated

The Alpha label remains because the following acceptance items need additional engineering qualification:

- full ionic/Pitzer chemistry through multi-pass recycle loops;
- element-interface split-partial permeate with independent zone backpressures;
- arbitrary interstage/crossing recycle destinations;
- open/gas-equilibrium mass-transfer junctions;
- high-recycle continuation/JFNK stress matrix;
- production-scale telemetry performance/cost rollups.

The code intentionally exposes these boundaries instead of masking them with approximations.
