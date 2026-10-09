# SecurityAndCompliance — BB-IMS: Security

| Field | Value |
| --- | --- |
| Version | v0.1 |
| Last Updated | 2026-08-06 |
| Owner | Security Engineer |
| Status | In Review |

---

## 1. Threat Model (STRIDE)

| Threat | Surface | Impact | Mitigation |
| --- | --- | --- | --- |
| Spoofing | JWT forgery | Account takeover | RS256 JWT + jti blacklist |
| Tampering | Payloads | Data corruption | Pydantic + magic-byte uploads |
| Repudiation | Admin actions | No audit | Activity log + promotion_history |
| Info disclosure | PII | Leak | Masked logs, RBAC |
| DoS | Brute force | Lockout/flood | Rate limits + 15-min lockout |
| Elevation | Privilege | Admin access | RBAC + IDOR prevention on every endpoint |

## 2. Auth / Authorization

- JWT (jti) access + refresh; bcrypt cost 14.
- TOTP 2FA enforced on admin login (SHA-256, 5-min TTL, single-use).
- RBAC roles: admin/staff/student; IDOR checks per object.
- Account lockout: 5 failures → 15-min freeze.

## 3. Data Classification

| Data | Class | Handling |
| --- | --- | --- |
| Student PII | PII | masked logs, access-controlled |
| Fee/financial | financial | RBAC admin |
| OTP hash | credential | SHA-256, never logged |
| JWT jti | auth | blacklist store |

## 4. Encryption

- In transit: TLS; headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Permissions-Policy).
- At rest: passwords bcrypt; OTP hashed.

## 5. Compliance Checklist

- [ ] RBAC + IDOR tests on every endpoint
- [ ] Rate limits + lockout
- [ ] 7 security headers
- [ ] Magic-byte upload validation
- [ ] Dependency scans (bandit, Dependabot)
- [ ] No secrets in git

## 6. Incident Response Plan (outline)

1. Detect: log/alert.
2. Triage.
3. Contain: revoke tokens / rotate SECRET_KEY.
4. Remediate + regression tests.
5. Recover.
6. Postmortem (blameless).

## 7. Related Documents

| Document | Relationship |
| --- | --- |
| [Rules.md](../project/Rules.md) | Security baseline |
| [API.md](API.md) | Auth + limits |
| [Schema.md](Schema.md) | Sensitive map |
| [TechSpec.md](TechSpec.md) | NFRs |
| [PRD.md](../product/PRD.md) | Goals |
| [AppFlow.md](../design/AppFlow.md) | Flows |
| [Design.md](../design/Design.md) | Design |
| [ImplementationPlan.md](../project/ImplementationPlan.md) | Tasks |
| [Tracker.md](../project/Tracker.md) | Status |
| [Testing.md](Testing.md) | Security tests |
| [Deployment.md](Deployment.md) | Secrets |
| [Glossary.md](../reference/Glossary.md) | Vocabulary |
| [RiskRegister.md](../project/RiskRegister.md) | Risks |
