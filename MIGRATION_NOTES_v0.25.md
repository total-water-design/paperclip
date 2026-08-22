# Total Water Design Suite v0.25 Alpha — Migration Notes

## Database

The hosted Suite is designed for PostgreSQL 16 with SQLAlchemy + psycopg 3. SQLite remains supported for isolated/local testing.

v0.25 adds metadata/telemetry structures additively. Do **not** reset the production database.

Before deploying to a PostgreSQL-backed installation, create a verified backup, for example:

```bash
sudo -u postgres pg_dump -Fc totalwaterdesign > /var/backups/totalrodesign/totalwaterdesign_pre_v025.dump
```

Also back up:

```text
/etc/totalrodesign/totalrodesign.env
/opt/totalrodesign/app
```

## New/additive data concepts

- User Country (`country_code`, canonical display name)
- Project Country at ProjectFamily level
- telemetry sessions/events
- resource samples
- transactional email notification log

Legacy users/projects without Country must remain valid. Do not infer a country.

## Python dependencies

New hosted requirements include:

```text
psycopg[binary]>=3.3,<4
numpy>=1.26,<3
```

## Environment configuration

The sample environment uses PostgreSQL as the recommended hosted configuration. Existing production secrets should be preserved rather than replaced by the example file.

Founder email configuration uses:

```text
TWDS_FOUNDER_NAME
TWDS_FOUNDER_TITLE
TWDS_FOUNDER_EMAIL
```

## Project compatibility

The independent visible project numbering scheme remains authoritative:

```text
TROD-N-R
TBIO-N-R
TZLD-N-R
...
```

Cross-application lineage is represented through the internal project family/source-revision relationship and must not be inferred from matching visible numbers.
