# ADR-006 · Sign-in with Container Apps authentication, the code flow and a client secret in Key Vault

**Status:** accepted, pending the live proof of phase 7 · **Date:** 2026-11-01

## Context

Only the firm's members with the app role `Juriscope.User` may use Juriscope (REQ-07), and each sees only their own conversations.
The web client and the API are served by one container app. Building sign-in into the code would add tokens, sessions and secrets to
every request path.

## Options

1. **Container Apps built-in authentication (Easy Auth) with Microsoft Entra ID**, code flow, client secret (chosen).
2. **Easy Auth with a managed identity as a federated credential of the app registration:** no secret at all, but Learn documents it
   for App Service, not for Container Apps.
3. **The implicit flow:** no secret, but Learn discourages it.
4. **MSAL in the web client and token validation in the API:** more code for what the platform already does.

## Decision

Option 1.

- **Secret:** the sign-in app's client secret is the only secret in the system.
  - It reaches Bicep as a `@secure()` parameter from the GitHub environment secret `AUTH_CLIENT_SECRET`.
  - Bicep stores it as `auth-client-secret` in the environment's Key Vault.
  - The container app declares a secret of the same name by Key Vault reference, read with the runtime identity, which holds Key
    Vault Secrets User on the vault.
- **`clientSecretSettingName` points at that secret.** The portal stores the provider's secret this way; pointing it at a Key Vault
  reference is inferred from that and proven in phase 7. **Fallback:** a plain Container Apps secret from the same `@secure()`
  parameter, one line in `infra/modules/app.bicep`.
- **The platform authenticates; the app authorizes.**
  - Unauthenticated requests are allowed through (`AllowAnonymous`), and the platform injects `X-MS-CLIENT-PRINCIPAL` only for a
    valid session or bearer token.
  - `app/auth.py` answers **401** without that header and **403** without the `Juriscope.User` role claim; Easy Auth does not enforce
    app roles.
  - The web client sends a 401 to `/.auth/login/aad`.
  - `RedirectToLoginPage` was rejected: an API call without a session would receive a 302 to the sign-in page instead of the 401
    that REQ-07 requires, and a `fetch` cannot follow it.
- **Validation:**
  - issuer `https://login.microsoftonline.com/<tenant>/v2.0`;
  - audiences `api://<client id>` and the client id, so that tokens issued to the CI principals for the smoke and load tests are
    accepted.
  - The phase 7 and 8 scripts set the app registration to issue v2 access tokens, so their issuer matches.
- **Assignment required** on the enterprise application: a member without an assignment cannot sign in at all.
- **Ownership:** every lookup uses the Entra object id as the Cosmos DB partition key, so another user's conversation is a 404.

## Consequences

- **Spoofing:** the forged-header check runs live in phase 7. It sends `X-MS-CLIENT-PRINCIPAL` from outside with no session, and
  the API must answer 401. Learn states that the platform strips the header from external requests; the check proves it.
- **Ordering:** the Key Vault role is assigned in the same deployment, before the container app (module dependency). RBAC can take
  minutes to propagate, so a first deployment may fail to resolve the secret; rerunning `deploy.yml` fixes it, and `OPERATIONS.md`
  says so.
- **Rotation** (`OPERATIONS.md`): add a new client secret, update `AUTH_CLIENT_SECRET`, redeploy (Bicep writes the vault secret and
  the container app reads the latest version), then delete the old secret.
- Purge protection stays off so that prompt 06 can remove the vault; soft delete keeps it for seven days.
