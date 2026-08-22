# Total Water Design Suite v0.25 Alpha — Authenticated AWS Deployment

The current deployment guidance is maintained in the repository-root `DEPLOYMENT_v0.25.md` and `MIGRATION_NOTES_v0.25.md` files.

Key rules for an existing production installation:

- preserve `/etc/totalrodesign/totalrodesign.env`;
- preserve the PostgreSQL `totalwaterdesign` database;
- create a `pg_dump` backup before code cutover;
- install dependencies from `requirements-server.txt` into a candidate virtual environment;
- validate templates/runtime before replacing live code;
- keep Gunicorn and specialist applications localhost-only behind Nginx;
- do not disable CSRF or HTTPS security controls.

The installer in `deploy/install_ubuntu_24_04.sh` preserves an existing environment file. On a PostgreSQL production installation, create the database backup manually before running the installer because PostgreSQL backup credentials/policies are deployment-specific.
