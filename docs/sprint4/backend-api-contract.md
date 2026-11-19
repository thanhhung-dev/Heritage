# Sprint 4 backend API contract

FastAPI `/docs` and `/openapi.json` are the generated schema source. All admin APIs require `Authorization: Bearer <access_token>` from `POST /api/admin/login`; current database ADMIN role and active/unlocked account are checked. Missing/expired/revoked/invalidated credentials: 401; regular role: 403; missing record: 404; conflict: 409; invalid input: 422; database/configuration failure: 503. Errors follow `{"detail":"message"}` or FastAPI's `detail` validation array. No cookies are issued. Existing auth contract: `apps/backend/docs/admin-auth-api.md`.

## Account status (BE-03/04)

`PATCH /api/admin/accounts/{account_id}/status`, positive signed-64-bit ID, body `{"is_active":false}`. Only JSON booleans accepted; unknown fields rejected. Success 200:

```json
{"account_id":"2","email":"user@example.com","username":"user","role":"user","is_active":false}
```

Use `true` to reactivate. Repeated requests are idempotent. Deactivation permanently invalidates all existing tokens using a persisted credential generation; reactivation requires a fresh login. The shared guard checks availability and generation for ordinary protected endpoints too. Legacy tokens without `ver` work only while the database version remains zero. No passwords, lock metadata or internal token version are returned. No pagination/filtering applies. Self-deactivation is allowed and ends that administrator's access immediately after the request.

```sh
curl -X PATCH http://localhost:8000/api/admin/accounts/2/status -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"is_active":false}'
```

Rollout prerequisite: `apps/backend/migrations/2026-11-19_account_token_version.sql`, prepared but not applied by the agent. Deploy migration before the application. Existing tokens remain compatible until first deactivation.
