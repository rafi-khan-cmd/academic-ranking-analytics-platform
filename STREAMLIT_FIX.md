# Streamlit Cloud Connection Fix

## The Problem

Streamlit Cloud is still showing connection errors even though:
- ✅ Database is set up in Supabase
- ✅ Data is loaded
- ✅ Local connection works

## Solution: Update Streamlit Cloud Secrets

### Step 1: Go to Streamlit Cloud Secrets

1. Visit: https://share.streamlit.io
2. Find your app: `academic-ranking-analytics-platform`
3. Click "Manage app" (three dots menu) → "Settings"
4. Click "Secrets" tab

### Step 2: Delete Old Secrets

- Delete ALL existing secrets
- Make sure the secrets section is empty

### Step 3: Add These EXACT Secrets

Copy and paste this **EXACTLY** (no extra spaces, no quotes):

```toml
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

### Step 4: Save and Wait

1. Click "Save" button
2. Wait 30-60 seconds for app to redeploy
3. Refresh your dashboard

## Important Notes

- **Port 6543** is REQUIRED (connection pooling port)
- **No quotes** around values
- **No spaces** around `=`
- Password is case-sensitive

## Verify Secrets Are Correct

After saving, check:
1. All 5 secrets are listed
2. Port shows `6543` (not 5432)
3. Host is exactly: `db.peawexmwwmkqszcdqwjv.supabase.co`
4. Password matches: `JxhkAQBPSQD8hfCG`

## If Still Not Working

1. **Check Streamlit Cloud Logs:**
   - Go to app → "Manage app" → "Logs"
   - Look for specific error messages

2. **Try Direct Connection (Alternative):**
   If port 6543 doesn't work, try:
   ```toml
   POSTGRES_PORT=5432
   ```
   But you'll need to whitelist Streamlit Cloud IPs in Supabase

3. **Verify Supabase Database:**
   - Go to Supabase → Table Editor
   - Check `institutions` table has 40 rows
   - Check `ranking_results` table has data

## Expected Result

After updating secrets correctly:
- ✅ Dashboard loads without errors
- ✅ Shows "Database connected with 40 institutions"
- ✅ All pages work
- ✅ Data displays correctly
