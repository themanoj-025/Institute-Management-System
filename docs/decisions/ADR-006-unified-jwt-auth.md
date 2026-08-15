# ADR-006: Unified JWT Authentication for Desktop & Web

**Status**: Accepted
**Date**: 2026-07-25
**Author**: Architecture Team

## Context

The desktop client (CustomTkinter) originally authenticated directly against
a local SQLite database using `AuthService(self.db_session)`. The web
dashboard (React) authenticated via `POST /v1/auth/login` against the FastAPI
API. This meant:

- **Two authentication paths**: Desktop used local DB; web used API
- **Two session models**: Desktop used a local timer; web used JWT expiry
- **No shared session**: A user couldn't be logged in on both surfaces
  simultaneously with the same token
- **Token blacklisting**: Desktop had no logout mechanism that invalidated
  the session server-side

## Decision

1. **Desktop authenticates via API**: `landing/login_dialog.py` now calls
   `POST /v1/auth/login` over HTTP (using `httpx` with `urllib` fallback)
   — the same endpoint the web dashboard uses
2. **JWT-based session tracker**: `auth/session.py` stores the JWT and
   validates it by checking expiry, rather than using a local timer
3. **Server-side logout**: `landing/landing_page.py` calls
   `POST /v1/auth/logout` to blacklist the JWT (`RevokedToken` table)
4. **Desktop-UI data calls remain local**: ~37 desktop screens still call
   service-layer classes directly rather than going through the API
   (documented scoped exception)

## Rationale

### Why API-based auth for desktop

| Option | Pros | Cons |
| -------- | ------ | ------ |
| **API-based (chosen)** | Shared JWT; same auth logic; blacklisting works | Requires network; adds latency |
| **Local SQLite (previous)** | No network needed; fast | Two auth paths; no shared session; no blacklisting |
| **Hybrid: API auth, local data** | Shared auth; desktop data calls fast | Partially inconsistent transport |

### Why JWT with server-side blacklisting

| Mechanism | Pros | Cons |
| ----------- | ------ | ------ |
| **JWT + blacklist table** | Immediate revocation; stateless verification | Extra DB lookup per request |
| **JWT alone** | Fully stateless | No revocation before expiry |
| **Session cookies** | Revocable; no token management | Stateful; not ideal for API |

### Known scoped exception: Desktop data calls

The 37 desktop module files (`modules/admin/*`, `modules/staff/*`,
`modules/student/*`, `modules/shared/*`) still call service-layer classes
directly rather than routing through the `/v1/` API. This was scoped out
because:

- Full desktop-to-API migration would require rewriting every screen to use
  HTTP calls — a significant UI refactoring project
- The blueprint's core requirement was shared auth, which is fully complete
- Both paths call the same underlying service-layer functions, so business
  logic is not duplicated — only the transport differs

Future work ("Phase: Desktop API Migration") should refactor each screen
to call the /v1/ API endpoints using the shared JWT.

## Consequences

- **Desktop login**: Now requires API server to be running (same as web)
- **Shared JWT**: Desktop and web use the same token type with `jti` claims
- **Token blacklisting**: Desktop logout blacklists via API
- **Single auth code path**: `AuthService` is only called from the API layer,
  not from the desktop client
- **Known gap**: Desktop data operations bypass API middleware (IDOR guards,
  rate limiting, request validation)

## Related

- `landing/login_dialog.py` — Desktop login dialog (API-based)
- `auth/session.py` — JWT session tracker
- `landing/landing_page.py` — Logout with token blacklisting
- `api/main.py` — `/v1/auth/login` and `/v1/auth/logout` endpoints
- `IMPLEMENTATION_NOTES.md` — Documented scoped exception
