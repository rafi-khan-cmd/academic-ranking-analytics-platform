# GitHub Repository Verification

## Repository URL
https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform

## What Should Be on GitHub (Main Branch)

### ✅ Production Pipeline Files (Must Exist)

1. **`scripts/enrich_crossref.py`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/scripts/enrich_crossref.py
   - Should exist: YES
   - Lines: ~152

2. **`scripts/enrich_semantic_scholar.py`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/scripts/enrich_semantic_scholar.py
   - Should exist: YES
   - Lines: ~240

3. **`docs/data_dictionary.md`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/docs/data_dictionary.md
   - Should exist: YES
   - Lines: ~417

4. **`sql/schema.sql`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/sql/schema.sql
   - Should have: 302 lines (not 171)
   - Should contain: `CREATE TABLE topics`, `CREATE TABLE works`, `CREATE TABLE institution_resolution`

5. **`scripts/run_pipeline.py`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/scripts/run_pipeline.py
   - Should import: `enrich_crossref`, `enrich_semantic_scholar`
   - Should have: `load_topics`, `load_works`, `load_institution_resolution`
   - Default: 200 institutions from OpenAlex API

6. **`scripts/extract_data.py`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/scripts/extract_data.py
   - Should have: `fetch_topics()` function
   - Should have: Caching, retry, checkpointing

7. **`scripts/config.py`**
   - URL: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/scripts/config.py
   - Should have: `DEFAULT_INSTITUTION_COUNT = 200`
   - Should have: `OPENALEX_API_KEY`, `CROSSREF_MAILTO`, `SEMANTIC_SCHOLAR_API_KEY`

## How to Verify on GitHub

### Step 1: Check Main Branch
1. Go to: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform
2. Click branch dropdown (top left)
3. Make sure "main" is selected (not "checkpoint-1")

### Step 2: Check Scripts Directory
1. Go to: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/tree/main/scripts
2. Look for:
   - `enrich_crossref.py` ✅
   - `enrich_semantic_scholar.py` ✅
   - `run_pipeline.py` (should import enrichment modules) ✅

### Step 3: Check Schema
1. Go to: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/blob/main/sql/schema.sql
2. Scroll to bottom
3. Should see line 302 with `CREATE INDEX idx_benchmark_rank`
4. Should see `CREATE TABLE topics` around line 194
5. Should see `CREATE TABLE works` around line 212

### Step 4: Check Documentation
1. Go to: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform/tree/main/docs
2. Should see: `data_dictionary.md` ✅

## If Files Are Missing

**The production pipeline code exists locally but hasn't been pushed to GitHub.**

**To push:**

```bash
# 1. Make sure you're on main
git checkout main

# 2. Check what's changed
git status

# 3. Add all files
git add -A

# 4. Commit
git commit -m "Build full production ingestion pipeline

- Add OpenAlex API extraction (200 institutions default)
- Add ROR entity resolution with confidence scoring
- Add optional Crossref and Semantic Scholar enrichment
- Rebuild indicator engineering from work-level data
- Update database schema with topics, works, resolution tables
- Update pipeline orchestration with 11 phases
- Create comprehensive data dictionary
- Clarify production pipeline is default (not sample data)"

# 5. Push
git push origin main

# 6. Verify on GitHub (wait 10 seconds, then refresh)
```

## Local Verification (What I Checked)

✅ **All production pipeline files exist locally:**
- `scripts/enrich_crossref.py` - EXISTS
- `scripts/enrich_semantic_scholar.py` - EXISTS
- `docs/data_dictionary.md` - EXISTS
- `sql/schema.sql` - 302 lines with all new tables
- `scripts/run_pipeline.py` - Imports enrichment modules
- `scripts/extract_data.py` - Has `fetch_topics()` function
- `scripts/config.py` - Has `DEFAULT_INSTITUTION_COUNT = 200`

## Key Point

**The production pipeline defaults to 200 institutions from OpenAlex API, NOT 40 sample institutions.**

The `create_sample_data.py` script (40 institutions) exists but is **optional/demo only** and is NOT used by the production pipeline.
