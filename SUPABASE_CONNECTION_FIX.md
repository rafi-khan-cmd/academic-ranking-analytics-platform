# Supabase Connection Fix for Streamlit Cloud

## The Issue

Connection is being refused even with port 6543. This usually means:

1. **Connection pooling not enabled** in Supabase
2. **Port 6543 blocked** by Streamlit Cloud
3. **Need to use direct connection** with IP whitelisting

## Solution Options

### Option 1: Enable Connection Pooling in Supabase (Recommended)

1. **Go to Supabase Dashboard:**
   - https://supabase.com/dashboard
   - Select your project

2. **Enable Connection Pooling:**
   - Go to **Settings** → **Database**
   - Scroll to **"Connection Pooling"** section
   - Make sure **"Connection Pooling"** is **ENABLED**
   - Note the pooling connection string

3. **Use Pooling Connection String:**
   - The pooling connection string should have port **6543**
   - Update Streamlit secrets with the exact values from pooling connection string

### Option 2: Use Direct Connection with IP Whitelisting

If pooling doesn't work, use direct connection (port 5432):

1. **Get Streamlit Cloud IPs:**
   - Streamlit Cloud uses dynamic IPs
   - You may need to allow all IPs or use a different approach

2. **Whitelist in Supabase:**
   - Go to Supabase → **Settings** → **Database**
   - Find **"Network Restrictions"** or **"Allowed IPs"**
   - Add: `0.0.0.0/0` (allows all IPs - less secure but works)
   - Or find Streamlit Cloud IP ranges and add them

3. **Update Streamlit Secrets:**
   ```toml
   POSTGRES_HOST="db.peawexmwwmkqszcdqwjv.supabase.co"
   POSTGRES_PORT=5432
   POSTGRES_DB="postgres"
   POSTGRES_USER="postgres"
   POSTGRES_PASSWORD="JxhkAQBPSQD8hfCG"
   ```

### Option 3: Use Supabase Connection String Directly

1. **Get Connection String from Supabase:**
   - Go to **Settings** → **Database**
   - Copy the **"Connection string"** (URI format)
   - It looks like: `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres`

2. **Parse and Use:**
   - The connection string has all info embedded
   - We can modify the code to accept a full connection string

## Quick Test: Try Port 5432 with IP Whitelisting

1. **In Supabase:**
   - Settings → Database → Network Restrictions
   - Allow all IPs temporarily: `0.0.0.0/0`

2. **Update Streamlit Secrets:**
   ```toml
   POSTGRES_PORT=5432
   ```
   (Keep everything else the same)

3. **Save and test**

## Alternative: Use Supabase's Transaction Mode Pooling

Supabase also offers "Transaction" mode pooling which uses a different port. Check your Supabase dashboard for:
- **Session mode** (port 5432)
- **Transaction mode** (different port, better for serverless)

## Most Likely Solution

**Enable connection pooling in Supabase and verify the pooling connection string:**

1. Supabase Dashboard → Settings → Database
2. Check "Connection Pooling" is enabled
3. Copy the **exact** pooling connection string
4. Extract host, port, database, user, password
5. Update Streamlit secrets with those exact values

The pooling connection string should work from Streamlit Cloud.
