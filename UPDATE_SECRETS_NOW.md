# ✅ Update Streamlit Secrets with Session Pooler

## Your Session Pooler Connection String

From Supabase:
```
postgresql://postgres.peawexmwwmkqszcdqwjv:[YOUR-PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

## Extract These Values:

- **Host:** `aws-1-us-east-1.pooler.supabase.com`
- **Port:** `5432`
- **Database:** `postgres`
- **User:** `postgres.peawexmwwmkqszcdqwjv` (includes project ID!)
- **Password:** `JxhkAQBPSQD8hfCG` (your actual password)

## Update Streamlit Cloud Secrets

1. Go to: https://share.streamlit.io
2. Your app → **Manage app** → **Settings** → **Secrets**
3. **Delete all old secrets**
4. **Add these EXACT values:**

```toml
POSTGRES_HOST=aws-1-us-east-1.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres.peawexmwwmkqszcdqwjv
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

**CRITICAL:**
- Host is `aws-1-us-east-1.pooler.supabase.com` (NOT `db.peawexmwwmkqszcdqwjv.supabase.co`)
- User is `postgres.peawexmwwmkqszcdqwjv` (includes project ID!)
- Port is `5432` (NOT 6543)
- No quotes around values

5. Click **Save**
6. Wait 30 seconds
7. Refresh your dashboard

## This Should Work Now!

The Session Pooler connection string is IPv4-compatible and will work with Streamlit Cloud.
