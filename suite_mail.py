"""Central transactional email service for Total Water Design Suite.

This module provides one delivery/audit path for Suite-owned transactional
messages. It intentionally reuses the existing SMTP delivery function and
``EmailNotification`` table from ``auth.py`` so specialist applications do not
implement their own mail clients.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from auth import EmailNotification, db, send_email


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _bridge_suite_smtp_environment() -> None:
    """Allow canonical TWDS_* mail settings while legacy auth mail is retained.

    Existing Alpha servers already use TOTALRO_SMTP_*. New Suite-owned services
    prefer TWDS_SMTP_*. Until auth.send_email is fully renamed, copy canonical
    values into missing legacy variables in-process. Existing legacy values are
    never overwritten.
    """
    for suffix in ("HOST", "PORT", "STARTTLS", "SSL", "USER", "PASSWORD", "FROM"):
        canonical = os.getenv(f"TWDS_SMTP_{suffix}")
        legacy = f"TOTALRO_SMTP_{suffix}"
        if canonical and not os.getenv(legacy):
            os.environ[legacy] = canonical


@dataclass(frozen=True)
class MailResult:
    notification_id: int
    sent: bool
    detail: str


def send_transactional_email(*, user_id: int | None, recipient: str, event_type: str,
                             subject: str, body: str, template: str) -> MailResult:
    """Persist then immediately attempt one transactional email delivery.

    The SMTP password is read only from the protected server environment. It is
    never stored in the database or returned to the caller.
    """
    _bridge_suite_smtp_environment()
    row = EmailNotification(
        user_id=user_id,
        event_type=str(event_type)[:64],
        recipient=str(recipient).strip().lower()[:254],
        template=str(template)[:80],
        subject=str(subject)[:240],
        body=str(body),
        status="queued",
    )
    db.session.add(row)
    db.session.flush()
    row.attempts = int(row.attempts or 0) + 1
    sent, detail = send_email(row.subject, [row.recipient], row.body)
    row.status = "sent" if sent else "retry"
    row.sent_at = _utcnow() if sent else None
    row.last_error = "" if sent else str(detail)[:2000]
    db.session.flush()
    return MailResult(notification_id=row.id, sent=sent, detail=str(detail))


def first_name(full_name: str | None) -> str:
    value = str(full_name or "").strip()
    return value.split()[0] if value else "there"
