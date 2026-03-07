# Next Steps Guide

## Current Status

✅ **Code Complete** - All scripts, dashboard, and documentation are ready
✅ **Git Initialized** - Repository is connected to GitHub
⏳ **Not Yet Pushed** - Files need to be committed and pushed
⏳ **Not Yet Deployed** - Dashboard needs to be deployed
⏳ **Database Empty** - Need to run data pipeline

## Step-by-Step Action Plan

### Step 1: Commit and Push to GitHub

```bash
# Add all files
git add .

# Commit with descriptive message
git commit -m "Initial commit: Academic Rankings Analytics Platform

- Complete data pipeline with OpenAlex and ROR API integration
- Streamlit dashboard with 7 pages
- PostgreSQL schema and analytical views
- Advanced analytics (clustering, feature importance, sensitivity)
- Comprehensive documentation"

# Push to GitHub
git push origin main
```

### Step 2: Set Up PostgreSQL Database

**Option A: Local PostgreSQL**
```bash
# Install PostgreSQL (if not installed)
# macOS: brew install postgresql
# Ubuntu: sudo apt-get install postgresql

# Create database
createdb academic_rankings

# Load schema
psql -d academic_rankings -f sql/schema.sql
psql -d academic_rankings -f sql/views.sql
```

**Option B: Cloud PostgreSQL (Recommended for Deployment)**
- Use **Supabase** (free tier): https://supabase.com
- Use **Neon** (free tier): https://neon.tech
- Use **Railway** (free tier): https://railway.app

1. Create a new PostgreSQL database
2. Get connection string
3. Update `.env` file with credentials

### Step 3: Configure Environment Variables

Create/update `.env` file:

```bash
# Database Configuration
POSTGRES_HOST=localhost  # or your cloud DB host
POSTGRES_PORT=5432
POSTGRES_DB=academic_rankings
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# OpenAlex API (optional but recommended)
OPENALEX_EMAIL=your_email@example.com
```

### Step 4: Run Data Pipeline

**Quick Test (Sample Data - Fast):**
```bash
# Generate sample data for testing
python scripts/create_sample_data.py

# Load to database
python scripts/load_to_postgres.py
python scripts/ranking_engine.py
python scripts/advanced_analytics.py
```

**Production (Real API Data - Takes 15-30 min):**
```bash
# Run complete pipeline with real OpenAlex data
python scripts/run_pipeline.py --institutions 200

# This will:
# - Fetch 200 institutions from OpenAlex API
# - Resolve names with ROR API
# - Fetch works/publication data
# - Build indicators, compute rankings, run analytics
```

### Step 5: Test Dashboard Locally

```bash
# Start Streamlit dashboard
streamlit run dashboard/app.py

# Or use the root entry point
streamlit run streamlit_app.py
```

Visit `http://localhost:8501` and verify all pages work.

### Step 6: Deploy to Streamlit Community Cloud

1. **Go to Streamlit Cloud:** https://share.streamlit.io
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Select your repository:** `academic-ranking-analytics-platform`
5. **Configure:**
   - **Main file path:** `dashboard/app.py`
   - **Python version:** 3.8+
6. **Add Secrets** (click "Advanced settings"):
   ```
   POSTGRES_HOST=your_db_host
   POSTGRES_PORT=5432
   POSTGRES_DB=academic_rankings
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   OPENALEX_EMAIL=your_email@example.com
   ```
7. **Click "Deploy"**

### Step 7: Update README with Live Link

After deployment, update `README.md`:

```markdown
## 🌐 Live Demo

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-name.streamlit.app)
```

### Step 8: Add Screenshots

1. Take screenshots of each dashboard page
2. Save to `visuals/screenshots/`
3. Update README with screenshot links
4. Commit and push

### Step 9: Final Polish

- [ ] Verify all dashboard pages work
- [ ] Test methodology simulator
- [ ] Check database queries
- [ ] Review README for accuracy
- [ ] Add architecture diagram (optional)
- [ ] Create GIF of methodology simulator (optional)

## Quick Reference Commands

```bash
# Full pipeline (real data)
python scripts/run_pipeline.py --institutions 200

# Sample data (fast testing)
python scripts/create_sample_data.py
python scripts/load_to_postgres.py
python scripts/ranking_engine.py
python scripts/advanced_analytics.py

# Test dashboard
streamlit run dashboard/app.py

# Git operations
git add .
git commit -m "Your message"
git push origin main
```

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running: `pg_isready`
- Check `.env` file has correct credentials
- Test connection: `psql -h localhost -U your_user -d academic_rankings`

### API Rate Limits
- Set `OPENALEX_EMAIL` in `.env`
- Reduce number of institutions: `--institutions 100`
- Use `--no-works` flag for faster testing

### Dashboard Not Loading
- Check database has data: `SELECT COUNT(*) FROM institutions;`
- Verify environment variables in Streamlit Cloud
- Check Streamlit Cloud logs for errors

## Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] PostgreSQL database set up
- [ ] Environment variables configured
- [ ] Data pipeline run successfully
- [ ] Dashboard tested locally
- [ ] Deployed to Streamlit Cloud
- [ ] Live link added to README
- [ ] Screenshots added
- [ ] README polished

## Timeline Estimate

- **Step 1-2:** 10 minutes (Git push + DB setup)
- **Step 3:** 5 minutes (Environment config)
- **Step 4:** 15-30 minutes (Data pipeline)
- **Step 5:** 10 minutes (Local testing)
- **Step 6:** 10 minutes (Streamlit deployment)
- **Step 7-8:** 15 minutes (Documentation)

**Total:** ~1-1.5 hours to fully deploy

## Need Help?

- Check `DEPLOYMENT.md` for detailed deployment guide
- Check `API_INTEGRATION.md` for API usage
- Check `DATA_GUIDE.md` for data pipeline options
