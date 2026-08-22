# Total Water Design Suite v0.25 Alpha

**Release class:** Alpha / Engineering Preview  
**Suite version:** 0.25  
**Total RO Design application line:** 0.2

This source tree is the reconciled v0.25 engineering-platform update for the Total Water Design Suite and Total RO Design.

Highlights include:

- compact Suite landing/application portfolio;
- Water Quality → Plant Design workflow improvements;
- corrected acid-property presets;
- report osmotic/efficiency consistency and dynamic glossary;
- controlled User Country and Suite-wide Project Country;
- administrator Metrics/telemetry foundation;
- queued activation/access-expansion emails;
- PostgreSQL/psycopg 3 hosted architecture;
- generalized multi-pass RO flowsheet foundation;
- downstream-pass concentrate recycle to upstream HPP suction;
- conservative stream mixing and nonlinear recycle convergence;
- Jacobian-Free Newton-Krylov/GMRES support for difficult tear systems.

## Release status

The ordinary regression suite and the conventional two-pass/100%-P2-concentrate-recycle fixture pass. Advanced element-interface split-permeate hydraulics, arbitrary interstage recycle destinations and full ionic/Pitzer multi-pass recycle qualification remain explicitly experimental in this Alpha release.

Read before deployment:

- `RELEASE_NOTES_v0.25.md`
- `VALIDATION_v0.25.md`
- `MIGRATION_NOTES_v0.25.md`
- `DEPLOYMENT_v0.25.md`

## Server requirements

Install from:

```text
requirements-server.txt
```

PostgreSQL 16 is recommended for hosted multi-user deployments. SQLite remains useful for isolated/local testing.

## Windows package

`windows_launcher/` contains the lightweight Windows x64 Suite launcher source. The release package includes a Windows x64 launcher built to open the primary Suite domain at `https://totalwaterdesign.com/`.
