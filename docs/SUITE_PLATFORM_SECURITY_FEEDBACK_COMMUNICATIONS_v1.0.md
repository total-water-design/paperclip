# Total Water Design Suite — Security, Feedback, Communications & Reporting Contract v1.0

**Owner:** Suite Core (`platform/suite-core`)  
**Scope:** cross-application platform services only. Specialist engineering calculations remain owned by specialist applications/engines.

## 1. Mandatory two-step verification

Hosted authenticated Suite deployments require a second factor for every active user and administrator.

### Primary factor

The first supported second factor is RFC 6238 TOTP using standard authenticator applications.

- TOTP secrets are encrypted at rest with Fernet.
- Production should configure a stable `TWDS_MFA_ENCRYPTION_KEY` before broad enrollment.
- The strong Suite `SECRET_KEY` is available as a backward-compatible bootstrap/decryption fallback so introducing a dedicated key does not immediately strand previously enrolled credentials.
- Recovery codes are random, single-use and stored only as scrypt hashes.
- A successfully used TOTP counter is persisted and cannot be replayed.
- Verification attempts are rate limited.
- Enrollment, verification failures, recovery-code regeneration and administrator/CLI reset are audited.

### Staged migration

Existing password authentication is retained. On the next authenticated request after password login:

1. an account without an enrolled factor is redirected to enrollment;
2. an enrolled account without an MFA-verified session is redirected to the TOTP/recovery-code challenge;
3. existing remembered sessions are intercepted by the same enforcement layer;
4. API requests that require MFA receive a controlled 428 response rather than silently bypassing the requirement.

This allows existing users to enroll without pre-populating a second-factor secret and avoids app-specific MFA implementations.

### Recovery

Users receive one-time recovery codes at enrollment and may replace them only after a valid current TOTP code. An administrator may reset another user's MFA; this invalidates existing sessions and requires fresh enrollment. Administrators cannot use the web console to reset their own factor. Controlled server-console recovery is provided for emergency/sole-administrator recovery.

### Future WebAuthn/passkeys

`MfaCredential` separates credential method, credential ID and public credential metadata from the MFA profile. Future WebAuthn/passkey credentials can therefore be added without changing the Suite account/MFA state model. No WebAuthn private key would be stored by the Suite.

## 2. Authoritative feedback workflow

The authoritative feedback record is `suite_feedback_reports` in the Suite database. Email, ZIP diagnostic bundles and GitHub issues are secondary delivery/mirror artifacts.

Lifecycle states include:

`NEW → ADMIN_REVIEW → ACCEPTED / REJECTED → APPROVED_FOR_PRODUCT_REVIEW → GITHUB_ISSUE_CREATED → RESPONSE_DRAFTED → RESPONSE_APPROVED → RESPONSE_SENT → IMPLEMENTED / CLOSED`

Additional controlled states include `MORE_INFORMATION_REQUESTED` and `DUPLICATE`.

The database records user identity, application, project/revision/workspace, category, raw feedback, safe context, admin review, acceptance state, priority, product-review authorization, AI-processing authorization, sanitized technical requirement/reproduction information, response draft/approval/sent time, GitHub mirror reference and final disposition.

Implementation/release tracking is linked through `suite_feedback_implementation_state` so administrators can record development status and target/released version without altering raw customer feedback.

### Administrator product gate

- Customer feedback never modifies product code automatically.
- AI/product-development processing is not authorized by submission.
- The administrator must first accept feedback and then explicitly authorize product review.
- AI processing has a separate explicit authorization flag.
- A GitHub issue can be created only after acceptance + product-review authorization + a sanitized technical requirement.

### GitHub mirror

Optional runtime issue promotion uses `TWDS_GITHUB_TOKEN`. The token is a protected server secret.

The GitHub issue contains only the internal feedback reference, affected app, category, priority, product-owner branch, sanitized technical requirement and sanitized reproduction information. Customer name, email, account information and raw project data are deliberately omitted.

## 3. Feedback receipt and response email

After a valid feedback submission, the Suite attempts a transactional receipt from the configured `admin@totalrodesign.com` sender identity to the submitting user. It thanks the user by first name, confirms receipt, explains that feedback is taken seriously and reviewed, and says follow-up may occur where appropriate. It does not promise implementation or dates.

Administrator-approved responses use the same centralized transactional-email path. A draft cannot be sent until it is explicitly approved.

## 4. What's New and release communications

Customer-facing updates are controlled by Suite database records, not by branch discovery.

### Recently Updated

Only release records that are all of the following may appear:

- validated;
- deployed;
- deployment health verified;
- explicitly public.

### What We're Working On

Only administrator-approved, explicitly public high-level roadmap records appear. Source-code details, customer projects, security internals and unvalidated promises are not generated from repository state.

### Commercial Launch

The launch date/window is a Suite setting controlled by administrators and is never hard-coded into the landing page.

### Product-update email

Product-update announcements are opt-in. An administrator may send an announcement only when the release is validated, deployed, health-verified and explicitly approved for update email. The message uses first name, thanks the user/community, provides 3–6 plain-language improvements and avoids internal Git terminology.

## 5. Project Library full-report provider

Suite Core owns:

- project identity/authorization;
- retrieval of the saved `ProjectRevision.snapshot_json`;
- provider registration;
- report-generation audit/history;
- customer Project Library controls.

A specialist application owns its engineering report implementation and registers exactly one provider through `register_report_provider(...)`. The provider receives the immutable saved snapshot and project context and returns a customer-facing `ReportResult` reference.

If no provider is registered, Suite Core returns a controlled `provider_required` response and does not fabricate a report.

Administrator project JSON/debug inspection remains a separate read-only administration function and is never included merely because a normal user selected Generate Full Report.

Future integrated/facility-wide Total Water Design reporting can register its own system-level provider without moving its engineering report engine into Suite Core.

## 6. Total Water Academy commercial/entitlement preparation

`Total Water Academy` is registered as a planned Suite product with future branch `app/total-water-academy`.

Default commercial policy:

- commercial activation: off;
- commercial target price: USD 5.00;
- billing cadence: deliberately undefined;
- pre-commercial mode: approved students;
- free student pre-commercial access: enabled by policy but still requires an administrator-granted active product entitlement.

Price, commercial activation, billing cadence, pre-commercial mode and eligibility notes are administrator-configurable. Suite Core does not assume monthly, annual or one-time billing.

## 7. Deployment requirements

Before enabling this milestone in a hosted environment:

1. install updated Python dependencies (`pyotp`, `cryptography`);
2. generate and securely install a stable `TWDS_MFA_ENCRYPTION_KEY`;
3. verify existing `admin@totalrodesign.com` SMTP credentials;
4. run additive database/table migrations/startup initialization;
5. confirm at least one controlled administrator recovery route is operational;
6. test an existing-user MFA enrollment and an already-enrolled login;
7. test recovery-code use and administrator reset on a non-production test account;
8. validate feedback receipt/support email and admin-gated response;
9. leave `TWDS_GITHUB_TOKEN` blank unless sanitized runtime issue promotion is intentionally enabled;
10. register specialist report-provider adapters before advertising Generate Full Report for those products;
11. create release/roadmap records only after deployment/release authority confirms their status.

## 8. Security boundaries

Suite Core does not ingest specialist source code into feedback, reports or communications. Customer feedback is never trusted as executable instruction. GitHub promotion is sanitized and administrator-gated. MFA credentials and SMTP/GitHub secrets stay out of GitHub. Normal project reports use saved project state and registered customer-facing providers, not administrator debugging output.
