# DreamAxis Deployment Modes

DreamAxis ships in two auth modes:

- `local_open` — default, no signup required
- `password` — optional shared-instance login mode

## `local_open` (default)

Use this for:

- local development
- personal self-hosting
- open-source first-run experience

Behavior:

- the API auto-seeds a local owner user
- the API auto-seeds a default workspace and demo conversation
- the Web app calls `POST /api/v1/auth/bootstrap`
- the browser receives a local JWT without showing a login gate
- no public signup page is required

Data location in this mode:

- users / workspaces / provider connections / runtime / skills / knowledge metadata live in your own PostgreSQL
- provider API keys are encrypted before being stored in `provider_connections`
- uploaded knowledge files live under `KNOWLEDGE_STORAGE_PATH`
- the browser token is stored in localStorage on the machine running the UI

Official open-source answer:

> DreamAxis free open-source mode does not require registration. If you deploy it yourself, your data stays inside your own infrastructure.

## `password`

Use this for:

- team-internal deployments
- private shared servers
- environments where you explicitly want login before access

Behavior:

- `/login` stays enabled
- `POST /api/v1/auth/login` is the entrypoint
- no public self-service signup flow is included yet

Current scope:

- simple email + password login
- JWT session model
- no OAuth
- no email verification
- no multi-tenant RBAC

## How to switch

Set:

```env
AUTH_MODE=local_open
```

or:

```env
AUTH_MODE=password
```

Then restart the API and Web containers.

## Recommended default for GitHub users

Keep:

```env
AUTH_MODE=local_open
```

That gives the intended DreamAxis onboarding:

1. `docker compose up --build`
2. open the app
3. enter directly without signup
4. add a provider API key
5. run CLI / Browser / Knowledge flows
