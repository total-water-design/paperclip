# Total Water Design Suite Unified Feedback Service v1.0

**Owner:** Suite Core (`platform/suite-core`)  
**Current workflow extension:** see `docs/SUITE_PLATFORM_SECURITY_FEEDBACK_COMMUNICATIONS_v1.0.md`.

## Purpose

All specialist applications use one Suite feedback endpoint and one authoritative Suite database workflow instead of maintaining application-specific SMTP, status, review, or GitHub pipelines.

## Submission endpoint

`POST /api/suite/feedback/report`

Typical payload:

```json
{
  "application": "Total Bio Design",
  "application_version": "0.2.3",
  "category": "calculation",
  "message": "User description",
  "project_id": "TBIO-12-2",
  "project_revision": "Rev 2",
  "workspace": "MBBR Design"
}
```

Optional safe diagnostic fields include `project_name`, `page`, screenshots and `diagnostic_context`. Specialist applications must not place credentials, source code, or unrestricted confidential payloads into diagnostic context.

The shared application shell provides the common Feedback control. Specialist applications may expose additional safe context through `window.TWDSFeedbackContextProvider`.

## Authoritative record

The source of truth is `suite_feedback_reports` in the Suite database. The record includes user/application/project context, feedback text, category, status, administrator review, acceptance state, priority, product/AI review authorization, response draft/approval/sent time, GitHub mirror reference and final disposition.

Implementation/release state is linked in `suite_feedback_implementation_state`.

Email messages, ZIP bundles and GitHub issues are secondary artifacts. They never replace the database record.

## Administrator product gate

Customer submission alone never authorizes product-development processing or code changes.

The administrator must explicitly:

1. review the feedback;
2. accept or reject it;
3. authorize product review;
4. separately authorize AI processing when desired;
5. provide a sanitized technical requirement before GitHub promotion;
6. approve a customer response before it is sent.

## Transactional email

Approved sender identity:

`admin@totalrodesign.com`

Support recipient:

`support@totalrodesign.com`

Canonical SMTP variables are `TWDS_SMTP_*`; existing `TOTALRO_SMTP_*` settings remain supported during migration. No second mailbox credential is required when AWS already contains the `admin@totalrodesign.com` SMTP credentials.

A valid feedback submission also triggers a customer receipt email thanking the user by first name and confirming that the feedback will be reviewed. No implementation date is promised.

## GitHub mirror

Raw customer feedback is not written to GitHub. After explicit administrator acceptance/product authorization, a sanitized issue may be created using the optional runtime `TWDS_GITHUB_TOKEN`.

The issue may contain only the internal feedback ID, affected application, category, priority, product-owner branch, sanitized technical requirement and sanitized reproduction information. Customer name, email, account data and raw project content are intentionally omitted.

## Administrator controls

- `/admin/feedback`
- `GET /api/suite/admin/feedback`
- `POST /api/suite/admin/feedback/<id>/retry`

The dashboard supports application/user/date/status review, categorization, priority, accept/reject, more-information/duplicate handling, product/AI authorization, response approval/sending, sanitized GitHub promotion, and implementation/release tracking.

## Specialist-app migration rule

RO, Bio, ZLD, Pretreatment, Water Balance, Water Economics, Academy, and System Integration should submit to the common Suite endpoint and must not maintain independent SMTP feedback pipelines once migrated.
