# Quick Setup with Your Supabase Database

## Your Connection Details

From your connection string:
- **Host:** `db.peawexmwwmkqszcdqwjv.supabase.co`
- **Port:** `5432`
- **Database:** `postgres`
- **User:** `postgres`
- **Password:** (the password you created when setting up Supabase)

## Step 1: Create Database Schema (2 minutes)

1. **Go to Supabase SQL Editor:**
   - Open: https://supabase.com/dashboard/project/_/sql
   - Or: Click "SQL Editor" in left sidebar

2. **Run Schema:**
   - Click "New query"
   - Copy ALL contents from `sql/schema.sql` in your project
   - Paste into Supabase SQL Editor
   - Click "Run" (or press Ctrl/Cmd + Enter)
   - Should see "Success. No rows returned"

3. **Run Views:**
   - Click "New query" again
   - Copy ALL contents from `sql/views.sql` in your project
   - Paste into Supabase SQL Editor
   - Click "Run"
   - Should see "Success. No rows returned"

4. **Verify:**
   - Go to "Table Editor" in left sidebar
   - You should see tables: `institutions`, `ranking_results`, etc.

## Step 2: Configure Streamlit Cloud Secrets (2 minutes)

1. **Go to Streamlit Cloud:**
   - https://share.streamlit.io
   - Sign in with GitHub
   - Find your app: `academic-ranking-analytics-platform`
   - Click "Manage app" → "Settings" → "Secrets"

2. **Add These Secrets:**
   ```toml
   POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=YOUR_ACTUAL_PASSWORD_HERE
   ```
   
   **Important:**
   - Replace `YOUR_ACTUAL_PASSWORD_HERE` with the password you created in Supabase
   - No quotes around values
   - No spaces around `=`

3. **Click "Save"**
   - Streamlit will automatically redeploy

## Step 3: Update Local .env File (1 minute)

1. **Open `.env` file** in your project (create it if it doesn't exist)

2. **Add:**
   ```bash
   POSTGRES_HOST=db.peawexmwwmkqszcdqwjv.supabase.co
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=YOUR_ACTUAL_PASSWORD_HERE
   ```

3. **Save the file**

## Step 4: Load Sample Data (5 minutes)

Run these commands in your terminal:

```bash
# Make sure you're in the project directory
cd /Users/rafiulalamkhan/AcademicRankingAnalyticsPlatform/academic-ranking-analytics-platform

# Generate sample data
python scripts/create_sample_data.py

# Load to Supabase database
python scripts/load_to_postgres.py

# Compute rankings
python scripts/ranking_engine.py

# Run advanced analytics
python scripts/advanced_analytics.py
```

You should see success messages after each command.

## Step 5: Verify (1 minute)

1. **Check Supabase:**
   - Go to Supabase → Table Editor
   - Click on `institutions` table
   - You should see ~40 rows of data

2. **Check Streamlit App:**
   - Go to your app: https://academic-ranking-analytics-platform-dx7vmjupnvzrtfgxpznpxt.streamlit.app/
   - It should now show data instead of errors!
   - Try navigating through pages

## Troubleshooting

### "Connection refused" or "could not connect"
- Make sure Supabase project is fully created (wait a few minutes)
- Verify password is correct in both `.env` and Streamlit secrets
- Check host name is exactly: `db.peawexmwwmkqszcdqwjv.supabase.co`

### "Table does not exist"
- Make sure you ran both `schema.sql` and `views.sql` in Supabase SQL Editor
- Check Table Editor to see if tables exist

### "Database is empty"
- Make sure you ran all 4 data loading commands
- Check `institutions` table in Supabase has rows

### Scripts fail with import errors
- Make sure you're in the project directory
- Try: `pip install -r requirements.txt`

## Quick Command Reference

```bash
# Generate sample data
python scripts/create_sample_data.py

# Load to database
python scripts/load_to_postgres.py

# Compute rankings
python scripts/ranking_engine.py

# Advanced analytics
python scripts/advanced_analytics.py
```

## What's Next?

Once everything works:
1. ✅ Dashboard should show data
2. ✅ All 7 pages should work
3. ✅ You can explore rankings, institutions, etc.
4. 📸 Take screenshots for README
5. 🔗 Update README with live demo link
