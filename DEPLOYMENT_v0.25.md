# Total Water Design Suite v0.25 Alpha — Deployment Notes

## Recommended production topology

```text
Internet
   ↓
Nginx / HTTPS
   ↓
Flask + Gunicorn (localhost)
   ↓
PostgreSQL 16 (localhost or future RDS)
```

Total Bio Design remains a separate localhost-only service where deployed and continues to use Suite authentication through the existing Nginx/Flask integration.

## Upgrade principle

Treat v0.25 as an in-place application-code upgrade over the current database. Never replace the production environment file or database with package defaults.

Recommended sequence:

1. Back up PostgreSQL with `pg_dump`.
2. Back up `/etc/totalrodesign/totalrodesign.env`.
3. Back up the current `/opt/totalrodesign/app` tree.
4. Build a candidate Python environment from `requirements-server.txt`.
5. Run template and runtime verification.
6. Stop the service only for the final code cutover.
7. Preserve the existing `TOTALRO_DATABASE_URL`, secret key, SMTP credentials and security settings.
8. Restart Gunicorn and validate Nginx/public health.

## PostgreSQL

The sample environment contains a placeholder PostgreSQL URL. Never deploy the placeholder password.

## Security

Preserve:

- Flask-Login sessions
- CSRF protection
- HTTPS
- `strict-origin-when-cross-origin` behavior for hosted specialist applications
- localhost-only internal services
- existing Nginx authentication gates
- administrator-only Metrics access

Do not expose PostgreSQL or specialist-app internal ports publicly.
