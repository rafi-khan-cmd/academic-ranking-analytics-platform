# Deployment Guide

## Streamlit Community Cloud Deployment

### Prerequisites
1. GitHub repository with the project
2. Streamlit Community Cloud account (free)
3. PostgreSQL database (can use free tier from providers like Supabase, Neon, or Railway)

### Steps

1. **Prepare Repository**
   - Ensure all code is committed to GitHub
   - Create `streamlit_app.py` in root (or point to `dashboard/app.py`)
   - Add `requirements.txt` with all dependencies

2. **Set Up Database**
   - Create PostgreSQL database on your chosen provider
   - Run `sql/schema.sql` and `sql/views.sql` to initialize schema
   - Note database connection details

3. **Deploy to Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect GitHub repository
   - Set main file path: `dashboard/app.py`
   - Add secrets for database connection:
     ```
     POSTGRES_HOST=your_host
     POSTGRES_PORT=5432
     POSTGRES_DB=academic_rankings
     POSTGRES_USER=your_user
     POSTGRES_PASSWORD=your_password
     ```

4. **Load Data**
   - Run data pipeline scripts locally or on a server
   - Populate database with processed data
   - Verify data is accessible from Streamlit app

5. **Test Deployment**
   - Access deployed app URL
   - Test all dashboard pages
   - Verify database connections

## Alternative: Render Deployment

1. **Create `render.yaml`**:
```yaml
services:
  - type: web
    name: academic-rankings-dashboard
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run dashboard/app.py --server.port=$PORT --server.address=0.0.0.0
    envVars:
      - key: POSTGRES_HOST
        sync: false
      - key: POSTGRES_PORT
        value: 5432
      - key: POSTGRES_DB
        sync: false
      - key: POSTGRES_USER
        sync: false
      - key: POSTGRES_PASSWORD
        sync: false
```

2. **Deploy on Render**
   - Connect GitHub repository
   - Render will detect `render.yaml`
   - Add environment variables in dashboard
   - Deploy

## Local Development

1. **Set up environment**:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure database**:
```bash
# Create .env file
cp .env.example .env
# Edit .env with your database credentials
```

3. **Run dashboard**:
```bash
streamlit run dashboard/app.py
```

## Data Pipeline Execution

For production deployment, consider:

1. **Scheduled Data Updates**: Use cron jobs or GitHub Actions to run data pipeline periodically
2. **Data Validation**: Add checks to ensure data quality before loading
3. **Error Handling**: Implement robust error handling and logging
4. **Monitoring**: Set up monitoring for data pipeline and dashboard

## Environment Variables

Required environment variables:
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port (default: 5432)
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `OPENALEX_EMAIL`: (Optional) Email for OpenAlex API

## Troubleshooting

### Database Connection Issues
- Verify database is accessible from deployment environment
- Check firewall rules and IP whitelisting
- Verify credentials in environment variables

### Missing Data
- Ensure data pipeline has been run
- Check database tables are populated
- Verify views are created correctly

### Performance Issues
- Add database indexes (already in schema.sql)
- Consider caching for dashboard queries
- Optimize slow queries
