# Database Connection Fix

## The Issue

Connection to Supabase is being refused. This is usually because:

1. **Wrong password in .env** - Most common issue
2. **Need connection pooling** - Supabase recommends using port 6543 for external connections
3. **IP not whitelisted** - Direct connection (port 5432) requires IP whitelisting

## Quick Fix Options

### Option 1: Use Connection Pooling (Easiest)

Supabase provides a connection pooling URL that doesn't require IP whitelisting.

1. **Get Pooling Connection String:**
   - Go to Supabase Dashboard → Settings → Database
   - Find "Connection string" section
   - Select "Connection pooling" tab
   - Copy the URI (looks like: `postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:6543/postgres`)

2. **Update .env:**
   ```bash
   POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
   POSTGRES_PORT=6543  # ← Change to 6543 for pooling
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_actual_password
   ```

3. **Try again:**
   ```bash
   PYTHONPATH=$(pwd) python3 scripts/load_to_postgres.py
   ```

### Option 2: Whitelist Your IP (For Direct Connection)

If you want to use port 5432 (direct connection):

1. **Get your IP address:**
   - Visit: https://whatismyipaddress.com/
   - Copy your IP

2. **Whitelist in Supabase:**
   - Go to Supabase Dashboard → Settings → Database
   - Scroll to "Connection Pooling" section
   - Add your IP to "Allowed IPs"
   - Or go to "Network Restrictions" and add your IP

3. **Keep port 5432 in .env**

### Option 3: Verify Password

1. **Check your password:**
   - Go to Supabase Dashboard → Settings → Database
   - You can reset the password if needed
   - Make sure .env has the EXACT password (no extra spaces)

2. **Test connection manually:**
   ```bash
   # Test with psql (if installed)
   psql "postgresql://postgres:YOUR_PASSWORD@db.peawexmwwmkqszcdqwjv.supabase.co:5432/postgres?sslmode=require"
   ```

## Most Likely Solution

**Use connection pooling (port 6543):**

1. Update `.env`:
   ```bash
   POSTGRES_PORT=6543
   ```

2. Make sure password is correct in `.env`

3. Run:
   ```bash
   PYTHONPATH=$(pwd) python3 scripts/load_to_postgres.py
   ```

## Verify Connection

Test if connection works:
```bash
PYTHONPATH=$(pwd) python3 -c "from scripts.database import test_connection; test_connection()"
```

If this returns `True`, connection is working!
