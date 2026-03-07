# Troubleshooting Guide

## Common Deployment Issues

### Issue 1: "Database connection failed"

**Symptoms:**
- Error message about database connection
- Dashboard shows warning about database

**Solutions:**

1. **Check Streamlit Cloud Secrets:**
   - Go to your Streamlit Cloud app settings
   - Click "Secrets" tab
   - Ensure these are set:
     ```
     POSTGRES_HOST=your_host
     POSTGRES_PORT=5432
     POSTGRES_DB=academic_rankings
     POSTGRES_USER=your_username
     POSTGRES_PASSWORD=your_password
     ```

2. **Verify Database is Accessible:**
   - Check if your database allows external connections
   - For cloud databases (Supabase, Neon, Railway), ensure:
     - Connection pooling is enabled (if available)
     - IP whitelist allows Streamlit Cloud IPs
     - SSL mode is set correctly

3. **Test Connection Locally:**
   ```bash
   # Test database connection
   python -c "from scripts.database import test_connection; test_connection()"
   ```

### Issue 2: "Database is empty"

**Symptoms:**
- Dashboard loads but shows "No data available"
- Empty tables in database

**Solutions:**

1. **Run Data Pipeline:**
   ```bash
   # Option A: Real API data (recommended)
   python scripts/run_pipeline.py --institutions 200
   
   # Option B: Sample data (quick test)
   python scripts/create_sample_data.py
   python scripts/load_to_postgres.py
   python scripts/ranking_engine.py
   python scripts/advanced_analytics.py
   ```

2. **Verify Data Loaded:**
   ```sql
   -- Check institutions
   SELECT COUNT(*) FROM institutions;
   
   -- Check rankings
   SELECT COUNT(*) FROM ranking_results;
   ```

3. **Re-run Pipeline if Needed:**
   - If database was reset, re-run the pipeline
   - Data persists in `data/processed/` so you can reload

### Issue 3: Import Errors

**Symptoms:**
- `ModuleNotFoundError` or `ImportError`
- Pages fail to load

**Solutions:**

1. **Check requirements.txt:**
   - Ensure all dependencies are listed
   - Streamlit Cloud installs from `requirements.txt`

2. **Verify File Structure:**
   - Ensure `scripts/` and `dashboard/` directories exist
   - Check `__init__.py` files are present

3. **Check Import Paths:**
   - All imports use relative paths from project root
   - `sys.path.insert(0, str(Path(__file__).parent.parent))` in app.py

### Issue 4: Pages Not Loading

**Symptoms:**
- Specific pages show errors
- Blank pages

**Solutions:**

1. **Check Page Imports:**
   - Each page should have `render()` function
   - Verify imports in `dashboard/app.py`

2. **Check Database Queries:**
   - Some pages require specific tables
   - Verify tables exist: `ranking_results`, `institutions`, etc.

3. **Check Streamlit Cloud Logs:**
   - Go to app settings → "Logs"
   - Look for specific error messages

### Issue 5: API Rate Limits

**Symptoms:**
- Pipeline fails during data extraction
- "429 Too Many Requests" errors

**Solutions:**

1. **Set OpenAlex Email:**
   ```bash
   # In .env or Streamlit secrets
   OPENALEX_EMAIL=your_email@example.com
   ```

2. **Reduce Institution Count:**
   ```bash
   python scripts/run_pipeline.py --institutions 100
   ```

3. **Skip Works Data:**
   ```bash
   python scripts/run_pipeline.py --institutions 200 --no-works
   ```

4. **Wait and Retry:**
   - OpenAlex rate limits reset
   - Wait 10-15 minutes and retry

### Issue 6: Methodology Simulator Not Working

**Symptoms:**
- Simulator page loads but doesn't calculate
- "Calculate Rankings" button does nothing

**Solutions:**

1. **Check Database Has Rankings:**
   ```sql
   SELECT COUNT(*) FROM ranking_results;
   ```

2. **Verify Methodology Weights:**
   ```sql
   SELECT * FROM methodology_weights;
   ```

3. **Check Normalized Metrics:**
   ```sql
   SELECT COUNT(*) FROM normalized_metrics;
   ```

### Issue 7: Charts Not Displaying

**Symptoms:**
- Empty charts or errors
- Plotly charts fail to render

**Solutions:**

1. **Check Data Availability:**
   - Ensure queries return data
   - Verify DataFrames are not empty

2. **Check Plotly Version:**
   - Ensure `plotly>=5.17.0` in requirements.txt

3. **Verify Data Types:**
   - Numeric columns should be numeric
   - Check for NaN values

## Quick Diagnostic Commands

### Check Database Connection
```python
from scripts.database import test_connection
test_connection()  # Should return True
```

### Check Data Counts
```sql
SELECT 
    (SELECT COUNT(*) FROM institutions) as institutions,
    (SELECT COUNT(*) FROM ranking_results) as rankings,
    (SELECT COUNT(*) FROM normalized_metrics) as metrics;
```

### Check Environment Variables
```python
import os
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("POSTGRES_HOST"))
print(os.getenv("POSTGRES_DB"))
```

## Streamlit Cloud Specific Issues

### Secrets Not Working

1. **Format Check:**
   - Secrets should be in TOML format
   - No quotes around values
   - Correct section headers

2. **Redeploy:**
   - After changing secrets, redeploy app
   - Changes take effect on next deployment

### App Not Updating

1. **Check Git Push:**
   - Ensure latest code is pushed to GitHub
   - Streamlit Cloud auto-deploys on push

2. **Manual Redeploy:**
   - Go to app settings
   - Click "Reboot app"

### Performance Issues

1. **Database Connection Pooling:**
   - Use connection pooling if available
   - Supabase/Neon offer connection pooling

2. **Query Optimization:**
   - Add indexes (already in schema.sql)
   - Limit query results where possible

## Getting Help

1. **Check Logs:**
   - Streamlit Cloud: App settings → Logs
   - Local: Terminal output

2. **Verify Setup:**
   - Follow `NEXT_STEPS.md` step by step
   - Check `DEPLOYMENT.md` for deployment details

3. **Test Locally First:**
   - Always test dashboard locally before deploying
   - Use `streamlit run dashboard/app.py`

## Common Error Messages

### "No module named 'scripts'"
- **Fix:** Ensure project structure is correct
- Check `sys.path` in app.py

### "relation does not exist"
- **Fix:** Run `sql/schema.sql` to create tables

### "connection refused"
- **Fix:** Check database host/port in secrets
- Verify database is running and accessible

### "authentication failed"
- **Fix:** Check username/password in secrets
- Verify database credentials

### "timeout expired"
- **Fix:** Database may be slow or unreachable
- Check database status
- Consider connection pooling
