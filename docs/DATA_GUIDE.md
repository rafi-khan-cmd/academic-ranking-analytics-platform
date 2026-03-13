# Data Population Guide

## Understanding Data Sources

The Academic Rankings Intelligence Platform uses **real-time APIs** as the primary data source, following best practices for production analytics systems.

### Option 1: Real-Time API Data (OpenAlex + ROR) ⭐ PRIMARY METHOD

**What it is:** Fetch real, up-to-date data from OpenAlex API

**How to use:**

**Quick Start (Recommended):**
```bash
# Run complete pipeline with one command
python scripts/run_pipeline.py --institutions 200

# This will:
# 1. Fetch top 200 institutions from OpenAlex API
# 2. Resolve entity names using ROR API
# 3. Fetch works/publication data from OpenAlex
# 4. Build indicators, normalize, and load to database
# 5. Compute rankings and run advanced analytics
```

**Step-by-Step:**
```bash
# 1. Set up OpenAlex email in .env (optional but recommended for rate limits)
OPENALEX_EMAIL=your_email@example.com

# 2. Extract institutions from OpenAlex API
python scripts/extract_data.py

# 3. Clean data
python scripts/clean_data.py

# 4. Resolve entities with ROR API
python scripts/resolve_entities.py

# 5. Build indicators (uses real works data)
python scripts/build_indicators.py

# 6. Normalize metrics
python scripts/normalize_metrics.py

# 7. Load to database
python scripts/load_to_postgres.py

# 8. Compute rankings
python scripts/ranking_engine.py

# 9. Run advanced analytics
python scripts/advanced_analytics.py
```

**Pros:**
- ✅ **Real, current data** - Always up-to-date
- ✅ **Large dataset available** - Access to millions of publications
- ✅ **No manual data preparation** - Fully automated
- ✅ **Production-ready** - Scalable and maintainable
- ✅ **Entity resolution via ROR** - Accurate institution matching

**Cons:**
- Requires internet connection
- API rate limits (handled automatically with delays)
- Takes 15-30 minutes for full pipeline (200 institutions with works data)

**API Endpoints Used:**
- OpenAlex `/institutions` - Institution discovery
- OpenAlex `/works` - Publication and citation data
- ROR API - Entity resolution and canonical names

### Option 2: Sample/Demo Data ⭐ Recommended for Testing

**What it is:** Generate synthetic but realistic data for testing

**How to use:**
```bash
# Generate sample data (40 institutions with realistic metrics)
python scripts/create_sample_data.py

# Then load to database
python scripts/load_to_postgres.py
python scripts/ranking_engine.py
python scripts/advanced_analytics.py
```

**Pros:**
- Instant setup
- No API dependencies
- Perfect for testing and demos
- Works offline

**Cons:**
- Not real data
- Limited to ~40 sample institutions

### Option 3: Your Own Dataset

**What it is:** Use your own CSV/JSON file with institution data

**How to adapt:**
1. Create a script to convert your data format to match the expected structure
2. Save as `data/raw/institutions_raw.json` with this structure:
```json
[
  {
    "id": "https://openalex.org/I123456",
    "display_name": "Institution Name",
    "country_code": "US",
    "type": "university",
    "summary_stats": {
      "2yr_mean_citedness": 2.5,
      "h_index": 100
    }
  }
]
```
3. Continue with the pipeline from `resolve_entities.py`

## Current Status

**Right now:** The database is empty. You need to populate it using one of the options above.

**What "data population" means:**
- Running the scripts to fetch/create data
- Processing it through the pipeline
- Loading it into PostgreSQL
- Computing rankings and analytics

## Quick Start (Sample Data)

For the fastest setup to test the dashboard:

```bash
# 1. Generate sample data
python scripts/create_sample_data.py

# 2. Set up PostgreSQL (if not already done)
createdb academic_rankings
psql -d academic_rankings -f sql/schema.sql
psql -d academic_rankings -f sql/views.sql

# 3. Configure database in .env file
# Edit .env with your PostgreSQL credentials

# 4. Load data to database
python scripts/load_to_postgres.py

# 5. Compute rankings
python scripts/ranking_engine.py

# 6. Run advanced analytics
python scripts/advanced_analytics.py

# 7. Start dashboard
streamlit run dashboard/app.py
```

## Data Flow

```
Option 1 (API):          Option 2 (Sample):        Option 3 (Your Data):
OpenAlex API      →      create_sample_data.py →   Your CSV/JSON
    ↓                         ↓                          ↓
extract_data.py          (generates files)         (convert format)
    ↓                         ↓                          ↓
resolve_entities.py  →  resolve_entities.py  →  resolve_entities.py
    ↓                         ↓                          ↓
build_indicators.py →  build_indicators.py  →  build_indicators.py
    ↓                         ↓                          ↓
normalize_metrics.py → normalize_metrics.py → normalize_metrics.py
    ↓                         ↓                          ↓
load_to_postgres.py →  load_to_postgres.py  →  load_to_postgres.py
    ↓                         ↓                          ↓
ranking_engine.py    →  ranking_engine.py   →  ranking_engine.py
    ↓                         ↓                          ↓
advanced_analytics.py → advanced_analytics.py → advanced_analytics.py
    ↓                         ↓                          ↓
Dashboard Ready!       →  Dashboard Ready!   →  Dashboard Ready!
```

## Which Option Should You Use?

- **Testing/Demo:** Use Option 2 (Sample Data) - fastest setup
- **Production/Real Analysis:** Use Option 1 (OpenAlex API) - real data
- **Custom Analysis:** Use Option 3 (Your Dataset) - your specific data

## Troubleshooting

**"No data available" in dashboard:**
- Make sure you've run the data pipeline
- Check that data is loaded in PostgreSQL
- Verify database connection in `.env`

**"File not found" errors:**
- Run `create_sample_data.py` first (Option 2)
- Or run `extract_data.py` for API data (Option 1)

**Database connection errors:**
- Check `.env` file has correct PostgreSQL credentials
- Ensure PostgreSQL is running
- Verify database `academic_rankings` exists
