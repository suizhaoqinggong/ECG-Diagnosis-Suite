# Auth & Chat History Cloud Storage Design

Date: 2026-04-02

## Summary

Add user registration/login (email + password) and cloud-based conversation history storage to the ECG Diagnosis Suite. The app transitions from a purely local tool to a public SaaS platform where anonymous users can try the diagnosis feature, then optionally sign up to persist their history across devices.

## Requirements

- Email + password registration and login (no email verification for now)
- JWT-based authentication (access + refresh tokens)
- Complete conversation history stored in backend database
- Anonymous users can use diagnosis without logging in
- Seamless migration of local history to cloud on first login
- Cross-device access to conversation history for logged-in users

## Database Model

### New Tables

**`users`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, auto-increment | User ID |
| email | String(255) | unique, not null | Login email |
| hashed_password | String(255) | not null | bcrypt hash |
| display_name | String(100) | nullable | Display name |
| is_active | Boolean | default True | Account status |
| created_at | DateTime | server default now() | Registration time |
| updated_at | DateTime | on update now() | Last update time |

**`chat_sessions`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | String | PK | UUID, matches frontend session ID |
| user_id | Integer | FK -> users.id, not null | Owner |
| title | String(255) | not null | Session title |
| created_at | DateTime | server default now() | Creation time |
| updated_at | DateTime | on update now() | Last update time |

**`chat_messages`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | String | PK | UUID |
| session_id | String | FK -> chat_sessions.id, not null | Parent session |
| role | String(20) | not null | user / assistant |
| type | String(20) | not null | intro/prompt/guidance/diagnosis |
| content | Text | not null | Message text |
| attachments | JSON | nullable | Attachment metadata |
| result | JSON | nullable | Full DiagnosisResultData |
| status | String(20) | not null | pending/completed/error |
| created_at | DateTime | server default now() | Creation time |

### Existing Table Change

`diagnosis_records`: add nullable `user_id` column (FK -> users.id). Nullable to preserve anonymous diagnosis records.

**`refresh_tokens`**

| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, auto-increment | Token ID |
| user_id | Integer | FK -> users.id, not null | Owner |
| token_hash | String(255) | unique, not null | SHA-256 hash of the refresh token |
| expires_at | DateTime | not null | Expiry time |
| created_at | DateTime | server default now() | Creation time |

Used for refresh token revocation. On logout, delete the row. On refresh, verify hash exists and not expired.

## Backend API

### Auth Router (`/api/auth`)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | POST | None | Register with email + password + optional display_name. Returns access + refresh tokens. |
| `/api/auth/login` | POST | None | Login with email + password. Returns access + refresh tokens. |
| `/api/auth/refresh` | POST | None | Body: `{ refresh_token }`. Returns new access token. |
| `/api/auth/me` | GET | Required | Returns current user profile. |
| `/api/auth/change-password` | POST | Required | Body: `{ old_password, new_password }`. |

**Token spec:**
- Access token: 15 min expiry, HS256, payload: `{ sub: user_id, exp }`
- Refresh token: 7 day expiry, stored in `refresh_tokens` table (user_id, token_hash, expires_at) for revocation support
- Signing key: reuses existing `SECRET_KEY` from config

### Chat Router (`/api/chat`)

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/chat/sessions` | GET | Required | List current user's sessions (no message content). |
| `/api/chat/sessions` | POST | Required | Create new session. |
| `/api/chat/sessions/{id}` | GET | Required | Get session with all messages. |
| `/api/chat/sessions/{id}` | PATCH | Required | Update session title. |
| `/api/chat/sessions/{id}` | DELETE | Required | Delete session and its messages. |
| `/api/chat/sessions/{id}/messages` | POST | Required | Append message to session. |

### Auth Middleware

- `get_current_user` dependency: parses JWT from `Authorization: Bearer <token>`, returns User or raises 401
- All chat endpoints use `Depends(get_current_user)`
- Existing diagnosis endpoints (`/api/diagnose`, `/api/diagnose-dat`) remain open but optionally associate with user if token present

### Diagnosis Integration

After diagnosis completes, if authenticated user:
1. Find or create active session for the user
2. Append user message (with attachment metadata) and assistant message (with full result) to the session

Anonymous users: behavior unchanged, result returned without server-side session storage.

## Frontend Architecture

### State Changes

New `auth` slice in WorkspaceState:

```
auth: {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isLoading: boolean
}
```

New UI fields:
- `ui.showAuthModal: boolean`
- `ui.authModalTab: 'login' | 'register'`

Auth state persisted to `localStorage['ecg-auth']` separately from session data.

### API Client Changes (`src/api/client.ts`)

- Request interceptor: attach `Authorization: Bearer <accessToken>` when available
- Response interceptor: on 401, attempt refresh via `/api/auth/refresh`, retry original request, clear auth on failure

### New Components

1. **AuthModal** — modal with login/register tabs
   - Login: email + password fields
   - Register: email + password + confirm password + optional display_name
   - Triggered by user icon button in top bar

2. **UserMenu** — dropdown after login
   - Display name / email
   - Change password
   - Logout

### Persistence Strategy (Dual Channel)

**Logged-in users:**
- Conversation history stored via `/api/chat` endpoints
- On app load: fetch sessions from backend
- On session open: fetch messages from backend
- After each diagnosis: sync messages to backend
- localStorage kept as offline cache

**Anonymous users:**
- Unchanged: all data in localStorage
- No backend sync

**Login migration:**
- On first login, detect local unsynced sessions
- Prompt: "Found N local conversations. Sync to cloud?"
- If confirmed: upload each session and its messages via chat API
- Mark local sessions as synced after successful upload

**Logout:**
- Clear auth state (tokens, user info)
- Cloud data preserved on server
- Return to anonymous mode (localStorage-based new sessions)
- Re-login restores access to all cloud history

## Security

- Password hashing: bcrypt via passlib, cost factor 12
- JWT signing key from `SECRET_KEY` env var (must be set in production)
- Refresh tokens stored in DB, deleted on logout (revocation)
- Rate limiting on auth endpoints: 10 requests per IP per minute
- Existing CORS config unchanged

## Error Handling

- Access token expired -> interceptor auto-refreshes -> transparent to user
- Refresh token expired -> clear auth state, show AuthModal with "session expired" message
- Network offline -> degrade to localStorage, auto-sync when back online
- Upload conflict (session already exists on server) -> skip, use server version

## New Dependencies

**Backend:**
- `python-jose[cryptography]` — JWT encoding/decoding
- `passlib[bcrypt]` — password hashing
- `python-multipart` — already present for form data

**Frontend:**
- No new dependencies (axios and React already available)

## Out of Scope

- Email verification
- OAuth / social login
- Password reset via email
- Two-factor authentication
- Admin panel / user management UI
- Data export functionality
