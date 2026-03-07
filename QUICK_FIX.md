# Quick Fix Guide for Deployment Issues

## Most Likely Issues

### 1. Database Not Configured (90% of issues)

**Problem:** Dashboard shows "Database connection failed" or "Database is empty"

**Quick Fix:**

1. **Set up a PostgreSQL database:**
   - **Free options:**
     - Supabase: https://supabase.com (recommended)
     - Neon: https://neon.tech
     - Railway: https://railway.app

2. **Get connection details:**
   - Host, Port, Database name, Username, Password

3. **Add to Streamlit Cloud Secrets:**
   - Go to: https://share.streamlit.io
   - Select your app
   - Click "Settings" → "Secrets"
   - Add:
     ```
     POSTGRES_HOST=your_host.supabase.co
     POSTGRES_PORT=5432
     POSTGRES_DB=postgres
     POSTGRES_USER=postgres
     POSTGRES_PASSWORD=your_password
     ```

4. **Create database schema:**
   - Connect to your database
   - Run: `sql/schema.sql`
   - Run: `sql/views.sql`

5. **Load data:**
   ```bash
   # Quick test with sample data
   python scripts/create_sample_data.py
   python scripts/load_to_postgres.py
   python scripts/ranking_engine.py
   python scripts/advanced_analytics.py
   ```

6. **Redeploy app** in Streamlit Cloud

### 2. Database Empty

**Problem:** Dashboard loads but shows "No data available"

**Quick Fix:**
```bash
# Generate and load sample data
python scripts/create_sample_data.py
python scripts/load_to_postgres.py
python scripts/ranking_engine.py
python scripts/advanced_analytics.py
```

### 3. Import Errors

**Problem:** Pages fail to load with import errors

**Quick Fix:**
- Check `requirements.txt` has all dependencies
- Ensure file structure is correct
- Redeploy app (Streamlit Cloud auto-installs from requirements.txt)

## Step-by-Step Fix

### Step 1: Set Up Database (5 minutes)

1. Create free Supabase account: https://supabase.com
2. Create new project
3. Go to Settings → Database
4. Copy connection string
5. Extract: host, port, database, user, password

### Step 2: Configure Streamlit Secrets (2 minutes)

1. Go to https://share.streamlit.io
2. Select your app
3. Settings → Secrets
4. Paste:
   ```
   POSTGRES_HOST=db.xxxxx.supabase.co
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=your_password_here
   ```

### Step 3: Create Schema (2 minutes)

1. Go to Supabase SQL Editor
2. Copy contents of `sql/schema.sql`
3. Paste and run
4. Copy contents of `sql/views.sql`
5. Paste and run

### Step 4: Load Sample Data (5 minutes)

**Option A: Local (then push to cloud DB)**
```bash
# Generate sample data
python scripts/create_sample_data.py

# Update .env with Supabase credentials
# Then run:
python scripts/load_to_postgres.py
python scripts/ranking_engine.py
python scripts/advanced_analytics.py
```

**Option B: Direct SQL (faster)**
- Use Supabase SQL Editor
- Or connect with psql and run the load scripts

### Step 5: Redeploy (1 minute)

1. Go to Streamlit Cloud
2. Click "Reboot app"
3. Wait for deployment
4. Check if dashboard works

## Verification

After fixing, verify:

1. **Database connection:**
   - Dashboard should not show connection error
   - Check Streamlit Cloud logs for errors

2. **Data loaded:**
   - Executive Overview should show institutions
   - Global Rankings should have a table
   - Institution Explorer should have dropdown options

3. **All pages work:**
   - Navigate through all 7 pages
   - Check for errors in logs

## Still Not Working?

1. **Check Streamlit Cloud Logs:**
   - App settings → Logs
   - Look for specific error messages

2. **Test Locally:**
   ```bash
   # Set up .env with database credentials
   streamlit run dashboard/app.py
   ```

3. **Common Issues:**
   - Database not allowing external connections
   - Wrong credentials in secrets
   - Schema not created
   - Data not loaded

## Need More Help?

See `TROUBLESHOOTING.md` for detailed solutions to specific errors.
