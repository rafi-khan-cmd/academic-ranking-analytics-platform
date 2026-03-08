# 🔧 Enable Supabase Connection Pooling (REQUIRED)

## The Problem

Streamlit Cloud can't connect because **connection pooling is not enabled** in your Supabase project.

## The Solution (2 minutes)

### Step 1: Go to Supabase Dashboard

1. Visit: https://supabase.com/dashboard
2. Sign in
3. Select your project: `peawexmwwmkqszcdqwjv` (or find it by hostname)

### Step 2: Enable Connection Pooling

1. Click **"Settings"** in the left sidebar
2. Click **"Database"** 
3. Scroll down to **"Connection Pooling"** section
4. Look for **"Connection Pooling"** toggle or settings
5. **Enable it** (if it's not already enabled)

### Step 3: Get Pooling Connection String

1. In the same "Connection Pooling" section
2. Find the **"Connection string"** or **"Pooling URI"**
3. It should look like:
   ```
   postgresql://postgres:[PASSWORD]@db.peawexmwwmkqszcdqwjv.supabase.co:6543/postgres
   ```
4. Note the **port 6543** (this is the pooling port)

### Step 4: Verify Port 6543 Works

The pooling connection uses port **6543** instead of **5432**.

### Step 5: Update Streamlit Secrets (if needed)

If pooling is enabled, your secrets should be:
```toml
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

## Alternative: Use Direct Connection (If Pooling Not Available)

If connection pooling is not available in your Supabase plan:

### Option A: Whitelist All IPs (Less Secure, But Works)

1. Go to Supabase → Settings → Database
2. Find **"Network Restrictions"** or **"Allowed IPs"**
3. Add: `0.0.0.0/0` (allows all IPs)
4. Use port **5432** in Streamlit secrets:
   ```toml
   POSTGRES_PORT=5432
   ```

### Option B: Find Streamlit Cloud IP Ranges

1. Contact Streamlit support for IP ranges
2. Add those IPs to Supabase whitelist
3. Use port **5432**

## Verify It's Working

After enabling pooling:

1. Wait 30 seconds
2. Refresh your Streamlit dashboard
3. Should see: "✅ Database connected with 40 institutions"

## Still Not Working?

1. **Check Supabase logs:**
   - Settings → Database → Logs
   - Look for connection attempts

2. **Test connection locally:**
   ```bash
   psql "postgresql://postgres:JxhkAQBPSQD8hfCG@db.peawexmwwmkqszcdqwjv.supabase.co:6543/postgres?sslmode=prefer"
   ```

3. **Verify pooling is enabled:**
   - Settings → Database → Connection Pooling
   - Should show "Enabled" or active status

## Most Common Issue

**Connection pooling is disabled by default** in some Supabase projects. You must enable it manually in the dashboard.

Once enabled, port 6543 will work from Streamlit Cloud.
