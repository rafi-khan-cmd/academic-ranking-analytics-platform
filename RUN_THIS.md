# Quick Setup - Run These Commands

## ⚠️ Important: You Still Need to Run SQL in Supabase First!

Before running the script, you MUST create the database schema in Supabase:

1. **Go to Supabase SQL Editor:** https://supabase.com/dashboard/project/_/sql
2. **Run `sql/schema.sql`** - Copy/paste and run
3. **Run `sql/views.sql`** - Copy/paste and run

## Then Run This:

```bash
# Make sure you're in the project directory
cd /Users/rafiulalamkhan/AcademicRankingAnalyticsPlatform/academic-ranking-analytics-platform

# Create .env file with your password first
# Edit .env and replace REPLACE_WITH_YOUR_SUPABASE_PASSWORD with your actual password

# Run the setup script
./setup_and_load_data.sh
```

## Or Run Manually:

```bash
# 1. Create .env file (if not exists) and add your Supabase password
# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Generate sample data
PYTHONPATH=$(pwd) python3 scripts/create_sample_data.py

# 4. Load to database
PYTHONPATH=$(pwd) python3 scripts/load_to_postgres.py

# 5. Compute rankings
PYTHONPATH=$(pwd) python3 scripts/ranking_engine.py

# 6. Run analytics
PYTHONPATH=$(pwd) python3 scripts/advanced_analytics.py
```

## What I Can't Do Automatically:

1. ❌ Run SQL in your Supabase account (you need to do this manually)
2. ❌ Know your Supabase password (you need to add it to .env)
3. ❌ Install packages if you don't have pip access

## What the Script Does:

✅ Creates .env file template
✅ Installs Python dependencies
✅ Generates sample data (40 institutions)
✅ Loads data to your Supabase database
✅ Computes rankings for all methodologies
✅ Runs advanced analytics (clustering, feature importance, etc.)

## After Running:

1. Check Supabase Table Editor - you should see data in `institutions` table
2. Check your Streamlit app - it should work now!
3. Navigate through all 7 dashboard pages
