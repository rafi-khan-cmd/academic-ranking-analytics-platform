# Production Pipeline Status

## What You Should See on GitHub

### ✅ Production Pipeline Code (Should Be Committed)

The following files contain the **production ingestion pipeline** that uses **real OpenAlex API data** (200+ institutions by default):

1. **`scripts/run_pipeline.py`** - Main pipeline orchestrator
   - Default: 200 institutions from OpenAlex API
   - Configurable: `--institutions 300`, `--years-back 10`, etc.
   - 11 phases including OpenAlex extraction, ROR resolution, enrichment, etc.

2. **`scripts/extract_data.py`** - OpenAlex API extraction
   - `extract_top_institutions()` - Fetches from OpenAlex API (default: 200)
   - `fetch_institution_works_batch()` - Fetches works/publications
   - `fetch_topics()` - Fetches topics from OpenAlex
   - Caching, retry/backoff, checkpointing

3. **`scripts/enrich_crossref.py`** - Crossref enrichment (optional)
4. **`scripts/enrich_semantic_scholar.py`** - Semantic Scholar enrichment (optional)
5. **`sql/schema.sql`** - Should have 302 lines (includes topics, works, resolution tables)
6. **`docs/data_dictionary.md`** - Complete data dictionary

### ⚠️ Sample Data Script (Optional/Demo Only)

**`scripts/create_sample_data.py`** exists but is **NOT the default path**:
- Creates 40 synthetic institutions for quick testing
- Only used if you explicitly run: `python scripts/create_sample_data.py`
- **The production pipeline does NOT use this** - it uses real OpenAlex API data

## Default Behavior

**When you run:**
```bash
python scripts/run_pipeline.py
```

**It does:**
- ✅ Fetches 200 institutions from OpenAlex API (real data)
- ✅ Resolves with ROR API
- ✅ Fetches works/publications from OpenAlex
- ✅ Builds indicators from real work-level data
- ❌ Does NOT use sample data

## How to Verify on GitHub

1. **Check `scripts/run_pipeline.py`:**
   - Should import `enrich_crossref` and `enrich_semantic_scholar`
   - Should have `DEFAULT_INSTITUTION_COUNT = 200`
   - Should have 11 phases in the pipeline

2. **Check `scripts/extract_data.py`:**
   - Should have `extract_top_institutions()` function
   - Should have `fetch_topics()` function
   - Should have caching and retry logic

3. **Check `sql/schema.sql`:**
   - Should be ~302 lines (not 171)
   - Should have `topics`, `works`, `institution_resolution` tables

4. **Check `scripts/config.py`:**
   - Should have `DEFAULT_INSTITUTION_COUNT = 200`
   - Should have `OPENALEX_API_KEY`, `CROSSREF_MAILTO`, `SEMANTIC_SCHOLAR_API_KEY`

## If You Still See References to 40 Institutions

The number "40" might appear in:
- `scripts/create_sample_data.py` - This is fine, it's optional demo data
- README methodology descriptions (40% weight) - This is about methodology weights, not institution count
- Old documentation - Should be updated

**The production pipeline uses 200 institutions from OpenAlex API by default.**

## Committing Changes

If the production pipeline code isn't on GitHub yet:

```bash
git checkout main
git add -A
git commit -m "Build full production ingestion pipeline

- Add OpenAlex API extraction with caching, retry, checkpointing
- Add ROR entity resolution with confidence scoring
- Add optional Crossref and Semantic Scholar enrichment
- Rebuild indicator engineering from work-level data
- Update database schema with topics, works, resolution tables
- Update pipeline orchestration with 11 phases
- Update documentation with production pipeline details
- Create comprehensive data dictionary
- Clarify that production pipeline is default (200 institutions from OpenAlex)"

git push origin main
```
