# Walk It Backend (Django + DRF)

Production-ready Django REST API for activity tracking, missions, referrals, leaderboards, and blockchain logging (EVM + Solana). Includes Google Sign-In, JWT auth, caching, and Docker/Gunicorn deployment.

- Django 5.x, Django REST Framework
- JWT auth (SimpleJWT)
- Google OAuth (ID token verification)
- Device binding per account
- Invite/referral flow and rewards
- Daily activities with 23h rate limit
- Missions with aura rewards and completion tracking
- Leaderboards (day/week/month/year) and user streaks
- EVM/Solana keypair generation and on-chain step logging
- Production caching and Vary on Authorization
- Dockerized with Gunicorn and staticfiles collection

## Project structure

```
manage.py
README.md
Dockerfile
.env
contracts/
  steps.vy
  # (compiled artifacts, ABIs, helpers if any)
trekknbackend/
  settings.py
  urls.py
  wsgi.py
  asgi.py
trekkn/
  models.py
  views.py
  serializers.py
  permissions.py
  actions.py
  admin.py
  apps.py
  migrations/
```

## Features

- Google Sign-In: verify id_token, create/bind user to device, process optional invite_code.
- JWT auth: issue access/refresh tokens; refresh blacklist enabled; signout blacklists refresh.
- Referrals: inviter credited when referred user signs up or first binds device. Logs events and “referral” DailyActivity rewards.
- Daily Activity:
  - POST log steps (rate limited to once every 23 hours).
  - Rewards: step_count -> balance via conversion_rate; aura via rules.
  - Mission checks on save (completes and rewards aura when requirements met).
- Leaderboard: aggregate steps by day/week/month/year; top 100; serializer returns total_steps.
- Streak: calculated to persist through the current day if you haven’t logged yet (e.g., Mon–Wed stays 3 all Thursday).
- Blockchain:
  - EVM: `eth_account.Account.create()` on user save; store evm_key/evm_addr.
  - Solana: `solders.Keypair()` on user save; store sol_key/sol_addr.
  - Contract write helper to log steps to multiple networks.

## Environment variables

Place them in `.env` at repo root (already present in this project):

- Core
  - `DEBUG` (True/False)
  - `SECRET_KEY`
  - `ALLOWED_HOSTS` (comma-separated)
  - `CSRF_TRUSTED_ORIGINS` (comma-separated, https URLs)
- Google
  - `GOOGLE_CLIENT_ID`
- Database (used when DEBUG=False; otherwise SQLite)
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

Notes:
- In production (DEBUG=False) settings switch to PostgreSQL using the DB_* vars.
- For CSRF in production, ensure your frontend/domain is listed in `CSRF_TRUSTED_ORIGINS`.
- Recommended for production static files in `settings.py`:
  ```python
  STATIC_ROOT = BASE_DIR / "staticfiles"
  STATIC_URL = "static/"
  ```

## Models overview

- TrekknUser (extends AbstractUser)
  - Custom PK (UUID)
  - Email as USERNAME_FIELD
  - Device binding (unique device_id)
  - Gamification: balance, aura, level, streak
  - Blockchain: evm_key/evm_addr, sol_key/sol_addr
  - Invites: invite_code (unique), invited_by (code)
  - Auto-generate wallets, invite_code, and displayname on save
- DailyActivity
  - user (FK, CASCADE)
  - step_count, timestamp, amount_rewarded, conversion_rate, aura_gained, source
  - On save: compute reward/aura, update user, then check missions
- Mission
  - name, description, requirement_steps, aura_reward
- UserMission
  - user, mission (unique together)
  - achieved timestamp, is_completed
  - complete() adds aura to user and timestamps achievement
- UserEventLog
  - user, event_type, description, timestamp, metadata

## API overview

Actual paths depend on your urls.py; below describes behaviors implemented in views:

- Auth
  - GoogleAuthView (POST): body includes `id_token`, `device_id`, optional `invite_code`.
    - Verifies token, binds device, handles inviter rewards if applicable, returns access/refresh tokens.
  - SignOutView (POST): body includes `refresh`, `access`; blacklists refresh.
- Users
  - List (GET): supports `leaderboard` query param: `day|week|month|year` (aggregates steps); supports `level` listing.
  - Detail (GET/PATCH): returns current user; PATCH ignores changes to `device_id` and `invited_by` once set.
- DailyActivity
  - List (GET): current user’s recent activities.
  - Create (POST): logs steps with 23h cooldown; triggers rewards and mission checks.
- Missions
  - List/Detail: standard read endpoints.
- UserMission
  - List (GET): current user’s missions.
- UserEventLog
  - List (GET): recent events (extend as needed).

Permissions:
- In production (DEBUG=False), most GET endpoints require IsOwner + IsAuthenticated and are cached with Vary on Authorization.

## Streak calculation

- Serializer computes streak from the user’s `DailyActivity` dates (source="steps").
- If you logged on Mon/Tue/Wed, it reports 3 all day Thursday even if you haven’t logged yet on Thursday.
- Implemented as a `SerializerMethodField` so it’s always fresh.

## Referral flow

- When a new or first-time-binding user presents a valid `invite_code`, set `invited_by` and call `get_referred(inviter, user)`.
- That function:
  - Creates “referral” DailyActivity for both referrer and referred.
  - Creates corresponding UserEventLog entries.

## Caching

- In production, selected view methods are decorated with:
  - `cache_page` (short TTLs)
  - `vary_on_headers("Authorization")`
- This avoids leaking personalized responses while enabling caching.

## Running locally

Prereqs:
- Python 3.12
- pip or Poetry
- SQLite (built-in) or configure Postgres

Steps:
- Create a virtualenv and install dependencies from `requirements.txt`.
- Create `.env` (already present here) and set `DEBUG=True` for local dev.
- Run database migrations:
  ```bash
  python manage.py migrate
  ```
- Start the server:
  ```bash
  python manage.py runserver 0.0.0.0:8000
  ```

## Docker (production-like)

Dockerfile builds a Gunicorn image and runs `collectstatic` during build.

Build:
```bash
docker build -t trekknbackend:latest .
```

Run:
```bash
docker run --rm -p 8000:8000 --env-file .env trekknbackend:latest
```

Or with docker-compose (if you add one):
```bash
docker-compose up --build
```

Static files:
- Ensure `STATIC_ROOT` is set in settings.
- `collectstatic` runs in the image; serve `/app/staticfiles` via your proxy (e.g., Nginx) or WhiteNoise.

## Admin

- All models are registered in `trekkn/admin.py`.
- Create a superuser and log in at `/admin/`:
  ```bash
  python manage.py createsuperuser
  ```

## Tests

Run tests with Django’s test runner:
```bash
python manage.py test
```

## Troubleshooting

- FOREIGN KEY constraint failed when deleting a user:
  - Delete related `DailyActivity`, `UserMission`, and `UserEventLog` first, or delete via Django ORM (CASCADE will apply).
- Admin static files 404:
  - Set `STATIC_ROOT`, run `collectstatic` in the image, configure your proxy to serve the files.
- Google login fails verification:
  - Confirm `GOOGLE_CLIENT_ID` matches your OAuth client and the token is a valid ID token.
- Caching and Vary:
  - Personalized endpoints must include `vary_on_headers("Authorization")` to avoid cross-user cache leaks.
- Device binding:
  - A `device_id` can only bind to one account; attempting to bind to another user returns 403.

## Security notes

- Keep `SECRET_KEY` and database credentials out of source control (use environment variables).
- Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` correctly in production.
- Serve over HTTPS in production.
- Consider rotating JWT refresh tokens and setting reasonable lifetimes.

## License

Add your license of choice here (e.g., MIT).
