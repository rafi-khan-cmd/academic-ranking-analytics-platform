# ⚠️ URGENT: Fix Streamlit Cloud Connection

## The Problem

Your dashboard is deployed but can't connect to Supabase because the secrets are wrong.

## The Fix (2 minutes)

### Step 1: Open Streamlit Cloud Secrets

1. Go to: https://share.streamlit.io
2. Click on your app
3. Click **"Manage app"** (three dots ⋮) → **"Settings"**
4. Click **"Secrets"** tab

### Step 2: DELETE All Old Secrets

- Select all existing secrets
- Delete them
- Make sure secrets section is **completely empty**

### Step 3: Add These 5 Secrets

Copy and paste this **EXACTLY** (no quotes, no extra spaces):

```
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

### Step 4: Save

1. Click **"Save"** button
2. Wait 30-60 seconds
3. Refresh your dashboard

## ⚠️ CRITICAL: Port Must Be 6543

- ❌ **WRONG:** `POSTGRES_PORT=5432`
- ✅ **CORRECT:** `POSTGRES_PORT=6543`

Port 6543 is Supabase's connection pooling port and works from Streamlit Cloud.

## Verify It Worked

After saving and waiting:
1. Refresh dashboard
2. Should see: "Database connected with 40 institutions" (not an error)
3. All pages should load with data

## Still Not Working?

1. **Double-check secrets:**
   - All 5 are there
   - Port is 6543 (not 5432)
   - No typos in password

2. **Check Streamlit Cloud logs:**
   - App → "Manage app" → "Logs"
   - Look for specific error

3. **Verify Supabase:**
   - Go to Supabase → Table Editor
   - Check `institutions` table has 40 rows

## Your Current Secrets Should Be:

```
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

That's it! Update the secrets and it should work.
