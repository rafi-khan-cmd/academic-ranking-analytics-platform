# Use Session Pooler for Streamlit Cloud

## The Problem

Streamlit Cloud is **IPv4-only**, and Supabase's direct connection (port 5432) is **not IPv4 compatible**. That's why it's not working!

## The Solution: Use Session Pooler

You need to use the **Session Pooler** or **Transaction Pooler** connection string instead.

### Step 1: Get Session Pooler Connection String

1. In Supabase Dashboard → **Settings** → **Database**
2. Scroll to **"Connection string"** section
3. Click the **"Session Pooler"** tab (or "Transaction Pooler")
4. Copy the connection string - it should look like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.peawexmwwmkqszcdqwjv.supabase.co:6543/postgres?pgbouncer=true
   ```
   OR it might have a different hostname like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@pooler.supabase.co:6543/postgres?pgbouncer=true
   ```

### Step 2: Extract Values from Connection String

From the Session Pooler connection string, extract:
- **Host** (the part after `@` and before `:`)
- **Port** (should be `6543`)
- **Database** (usually `postgres`)
- **User** (usually `postgres`)
- **Password** (the part in brackets)

### Step 3: Update Streamlit Secrets

Go to Streamlit Cloud → Your App → Settings → Secrets

Use the values from the Session Pooler connection string:

```toml
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

**Important:** 
- If the hostname is different (like `pooler.xxxxx.supabase.co`), use that instead
- Port should be `6543`
- No quotes around values

### Step 4: Save and Test

1. Click "Save" in Streamlit
2. Wait 30 seconds
3. Refresh your dashboard

## Why This Works

- **Session Pooler** works with IPv4 networks (like Streamlit Cloud)
- **Direct connection** (port 5432) only works with IPv6
- Session Pooler uses port **6543** and is compatible with Streamlit Cloud

## If You See a Different Hostname

If the Session Pooler connection string shows a different hostname (like `pooler.supabase.co` instead of `db.supabase.co`), use that hostname in your Streamlit secrets!
