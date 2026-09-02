# TWDS mobile authentication and device-session contract

Contract identifier: `twds.mobile.auth/v1`

Schema: `auth-device-session.schema.json`

Owner: Systems Integration (cross-application contract and serialization)

Implementation owner: Suite/Core (authentication, authorization, persistence, token storage, and delivery)

## Transport and security invariants

All endpoints use TLS, UTF-8 JSON, RFC 3339 UTC timestamps, `Cache-Control: no-store`, and `Accept-Contract: twds.mobile.auth/v1`. Tokens, MFA secrets, recovery codes, privacy archives, and raw deep-link URLs must never appear in logs, analytics, notifications, crash reports, or URL query strings. Access tokens are short-lived bearer tokens; refresh tokens are opaque, single-use, stored only in OS secure storage, and bound server-side to the tenant, user, device, session, and generation.

The server derives tenant/user ownership from the authenticated principal. A client cannot submit or widen `owner`, scopes, roles, `session_id`, or `refresh_generation`. Every list/read/revoke/export/delete operation rechecks tenant and user ownership. Cross-owner identifiers return `404 NOT_FOUND` where existence would leak; administrative action requires a separate explicit administrative contract and is outside v1.

## Endpoint contract

| Endpoint | Request | Success | Required semantics |
|---|---|---|---|
| `POST /v1/auth/mfa/enrollments` | `{method}` after recent reauthentication | MFA transaction | Creates a short-lived enrollment transaction. The response may disclose a TOTP secret only here and only once. |
| `POST /v1/auth/mfa/enrollments/{transaction_id}/verify` | `{proof}` | consumed transaction plus recovery codes | Proof is attempt-limited. Recovery codes are returned once, stored hashed, and individually consumed atomically. |
| `POST /v1/auth/mfa/challenges` | `{login_transaction_id}` | MFA transaction | Does not reveal whether an account or method exists. Server selects allowed methods. |
| `POST /v1/auth/mfa/challenges/{transaction_id}/verify` | `{method, proof}` | access/refresh token envelope | Transaction is single-use, expiring, attempt-limited, and bound to the login transaction. |
| `POST /v1/auth/mfa/recovery` | `{login_transaction_id, recovery_code}` | consumed transaction or replacement enrollment requirement | Recovery code comparison is constant-time and consumption is atomic. Successful recovery revokes other refresh-token families unless policy explicitly retains them. |
| `POST /v1/auth/refresh` | `{refresh_token, device_id}` | rotated access/refresh token envelope | Exactly-once rotation increments `refresh_generation`. Presenting an already consumed token yields `TOKEN_REUSED` and atomically marks the entire device session `compromised`; no tokens are issued. Concurrent refreshes permit at most one success. |
| `POST /v1/auth/logout` | current refresh token or authenticated session | `204` | Idempotently revokes the current device session; access-token denial uses the Suite/Core revocation strategy. |
| `GET /v1/auth/device-sessions` | authenticated principal | array of device sessions | Returns only the caller's tenant/user sessions, sorted by `last_seen_at` descending; contains display metadata only, never tokens or IP history. |
| `DELETE /v1/auth/device-sessions/{session_id}` | authenticated principal plus recent reauthentication when policy requires | `204` | Idempotently revokes only an owned session. Revoking the current session completes the response before local credentials are cleared. |
| `POST /v1/privacy/exports` | authenticated principal plus recent reauthentication | privacy request | Idempotency key required. State path: `requested -> identity_verification_required? -> queued -> processing -> ready -> completed`; `failed` is terminal/retriable only by a new request. Download is a short-lived authenticated or signed HTTPS URL, never serialized into notifications. |
| `POST /v1/privacy/deletions` | authenticated principal plus explicit confirmation and recent reauthentication | privacy request | State path: `requested -> identity_verification_required? -> queued -> processing -> completed`; cancellation is allowed only before `processing`. On entering `processing`, all sessions are revoked. Legal-retention exclusions must be reported without disclosing internal security data. |
| `GET /v1/privacy/requests/{request_id}` | authenticated principal | privacy request | Ownership-isolated polling; `ready` applies only to exports. |

Token envelopes are intentionally not represented by the shared JSON Schema: Suite/Core owns token encoding and credential delivery. The stable cross-app fields are `token_type: "Bearer"`, positive `expires_in`, `session_id`, and `refresh_generation`; mobile code must treat both tokens as opaque.

## Deep-link and navigation inputs

Only the structured `navigationInput` object is accepted. The allowlist is `mfa`, `device_sessions`, `privacy`, `project`, `job`, and `report`. Clients reject absolute URLs, custom schemes, hosts, paths, fragments, JavaScript, and unknown routes. A navigation request never conveys authorization: the app reauthenticates when `reauthentication_required` is true and always refetches the resource through its authorized API before rendering it. Sensitive routes (`mfa`, `device_sessions`, `privacy`) require an authenticated foreground session and cannot be opened from notification payload data alone.

## Error and degraded/offline behavior

The schema error codes are stable. `OFFLINE` is client-synthesized when the OS reports no connectivity; `NETWORK_UNAVAILABLE` covers connection failure; `TIMEOUT` means outcome unknown; `SERVICE_DEGRADED` is a server response. Automatic retry is allowed only when `retryable=true`, honors `retry_after_seconds`, and must not retry MFA proofs, recovery codes, deletion confirmations, or non-idempotent mutations. Refresh timeout is outcome-unknown: retry the same refresh token once through a serialized refresh coordinator; `TOKEN_REUSED` or `SESSION_REVOKED` then requires credential purge and interactive sign-in. Offline mode exposes previously cached non-sensitive UI only and never treats cached authentication state as authorization.

Expected negative paths include expired/consumed/locked MFA transactions, wrong proof without account enumeration, cross-owner session and privacy IDs, refresh reuse and concurrent refresh, revoked/expired sessions, cancellation after privacy processing begins, export URL expiry, unknown contract major, and malformed or non-allowlisted navigation. No error response contains secrets, submitted proofs, valid-method hints beyond the transaction, or resource-owner metadata.

## Persistence, compatibility, and limitations

Suite/Core persists opaque token hashes/family identifiers, refresh generation and consumption, session state/reason/timestamps, MFA transaction expiry and attempt counters, hashed recovery codes, and privacy transitions as atomic auditable records. Security audit records are append-only and redact credential material. Device display metadata is user-editable presentation data, not an authorization signal.

Within v1, optional fields may be added and consumers ignore unknown optional fields after contract negotiation. Removing/renaming fields, changing types or meanings, adding enum values to an exhaustively consumed enum, weakening ownership, or changing refresh-reuse consequences requires `twds.mobile.auth/v2`. Unknown majors return `406 VERSION_UNSUPPORTED`. Persist the contract major with durable session/privacy records so migrations remain explicit; v1 readers must continue to deserialize existing v1 records during a supported migration window.

Limitations: this contract does not choose an identity provider, MFA factor policy, access-token format, cryptographic algorithms, OS keychain implementation, administrative session controls, legal retention policy, notification provider, or independent certification criteria. Those remain with Suite/Core, Security/Privacy governance, application owners, or Independent Validation & Release as applicable.
