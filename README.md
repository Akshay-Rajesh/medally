# MedAlly MVP

Family medication management — Streamlit + Supabase + SendGrid.

## Project structure

```
medally/
├── app.py                   # Streamlit entry point
├── requirements.txt
├── schema.sql               # Run once in Supabase SQL editor
├── .env.example             # Copy to .env for local dev
├── .streamlit/
│   ├── config.toml          # Theme
│   └── secrets.toml.example # Copy to secrets.toml (never commit real values)
├── pages/
│   ├── dashboard.py         # Today's reminders + confirm/skip
│   ├── family.py            # Family member management
│   └── medications.py       # Medication CRUD
├── utils/
│   ├── db.py                # All Supabase queries
│   ├── email.py             # SendGrid alerts
│   └── session.py           # Streamlit auth state
└── scheduler/
    └── worker.py            # Background job — runs separately
```

## Setup

### 1. Supabase (free tier)
1. Create project at supabase.com
2. Run `schema.sql` in the SQL editor
3. Copy your project URL and anon key

### 2. SendGrid (free tier — 100 emails/day)
1. Create account at sendgrid.com
2. Verify a sender email address
3. Generate an API key

### 3. Local development

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in your keys
cp .streamlit/secrets.toml.example .streamlit/secrets.toml  # fill in keys

# Terminal 1 — Streamlit UI
streamlit run app.py

# Terminal 2 — Scheduler worker
python scheduler/worker.py
```

### 4. Deploy to Streamlit Cloud (free)
1. Push repo to GitHub
2. Go to share.streamlit.io → deploy from your repo, main file = `app.py`
3. Add secrets in App Settings → Secrets (copy from secrets.toml.example)

### 5. Deploy scheduler worker (free options)
- **Railway** — add as a second service, start command: `python scheduler/worker.py`
- **Render** — background worker, same start command
- **Fly.io** — free tier supports always-on workers

## Environment variables

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |
| `SENDGRID_API_KEY` | SendGrid API key |
| `ALERT_FROM_EMAIL` | Verified sender email for alerts |
| `APP_SECRET_KEY` | Random string for session security |

## How it works

1. User signs up → creates family member profiles
2. User adds medications per profile (name, dose, frequency, times)
3. Scheduler worker runs at midnight → seeds `reminders` rows for the day
4. Dashboard shows today's reminders → user clicks Taken / Skip
5. Scheduler checks every 5 min → if a reminder is 30+ min overdue and unconfirmed → sends email alert to account owner
