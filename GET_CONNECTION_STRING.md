# Get Your Supabase Connection String

## What You Need to Do

Since connection pooling is enabled, you need to get the **exact connection string** from Supabase.

### Step 1: Find the Connection String

1. In Supabase Dashboard, go to **Settings** → **Database**
2. Scroll down to **"Connection string"** section
3. You'll see tabs like:
   - **URI** (direct connection)
   - **Connection pooling** (this is what we need!)
4. Click the **"Connection pooling"** tab
5. You'll see a connection string that looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.peawexmwwmkqszcdqwjv.supabase.co:6543/postgres
   ```
   OR it might use a different hostname like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@pooler.supabase.co:6543/postgres?pgbouncer=true
   ```

### Step 2: Extract the Values

From the connection string, extract:
- **Host** (the part after `@` and before `:`)
- **Port** (should be `6543`)
- **Database** (usually `postgres`)
- **User** (usually `postgres`)
- **Password** (the part in brackets `[YOUR-PASSWORD]`)

### Step 3: Update Streamlit Secrets

Go to Streamlit Cloud → Your App → Settings → Secrets

Replace with the values from the connection string:

```toml
POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
POSTGRES_PORT=6543
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

**Important:** 
- If the hostname is different (like `pooler.supabase.co`), use that instead
- Make sure port is `6543`
- No quotes around values

### Step 4: Save and Test

1. Click "Save" in Streamlit
2. Wait 30 seconds
3. Refresh your dashboard

## Still Not Working?

If you see a different hostname in the pooling connection string (like `pooler.xxxxx.supabase.co`), that's the one you need to use!

Send me the connection string (you can hide the password) and I'll help you extract the right values.
