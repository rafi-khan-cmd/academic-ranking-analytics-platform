# 🔧 Fix Connection Now (2 Steps)

## The Problem
Connection pooling (port 6543) isn't working from Streamlit Cloud. Let's use direct connection instead.

## Solution: Use Direct Connection with IP Whitelisting

### Step 1: Whitelist All IPs in Supabase

1. Go to: https://supabase.com/dashboard
2. Select your project
3. Click **Settings** → **Database**
4. Scroll to **"Network Restrictions"** or **"Connection Pooling"** section
5. Look for **"Allowed IPs"** or **"IP Allowlist"**
6. Add: `0.0.0.0/0` (this allows all IPs - less secure but works)
7. Click **Save**

### Step 2: Update Streamlit Secrets

1. Go to: https://share.streamlit.io
2. Your app → **Manage app** → **Settings** → **Secrets**
3. Update to use port **5432** (direct connection):

```toml
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

4. Click **Save**
5. Wait 30 seconds
6. Refresh your dashboard

## That's It!

After whitelisting IPs and changing port to 5432, it should work.

## Why This Works

- Port 5432 is the direct database connection
- Whitelisting `0.0.0.0/0` allows connections from anywhere (including Streamlit Cloud)
- This bypasses the pooling connection issues
