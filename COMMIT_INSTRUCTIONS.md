# Commit and Push Instructions

## Files That Need to Be Committed

The following files have been modified/created for the production ingestion pipeline:

### New Files:
- `scripts/enrich_crossref.py` - Crossref enrichment module
- `scripts/enrich_semantic_scholar.py` - Semantic Scholar enrichment module
- `docs/data_dictionary.md` - Complete data dictionary

### Modified Files:
- `sql/schema.sql` - Added new tables (topics, works, institution_resolution, api_ingestion_log, benchmark_rankings)
- `scripts/config.py` - Added API keys and pipeline settings
- `scripts/extract_data.py` - Complete rewrite with caching, retry, checkpointing
- `scripts/resolve_entities.py` - Enhanced with confidence scoring
- `scripts/build_indicators.py` - Rebuilt for work-level data with year/subject support
- `scripts/load_to_postgres.py` - Added loaders for all new tables
- `scripts/run_pipeline.py` - Complete 11-phase orchestration
- `README.md` - Updated with production pipeline details

## Commands to Run

```bash
# 1. Make sure you're on main branch
git checkout main

# 2. Add all changes
git add -A

# 3. Check what will be committed
git status

# 4. Commit with descriptive message
git commit -m "Build full production ingestion pipeline

- Add OpenAlex API extraction with caching, retry, checkpointing
- Add ROR entity resolution with confidence scoring  
- Add optional Crossref and Semantic Scholar enrichment
- Rebuild indicator engineering from work-level data
- Update database schema with topics, works, resolution tables
- Update pipeline orchestration with 11 phases
- Update documentation with production pipeline details
- Create comprehensive data dictionary"

# 5. Push to GitHub
git push origin main

# 6. Verify on GitHub
# Go to: https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform
# Check that you see:
# - scripts/enrich_crossref.py
# - scripts/enrich_semantic_scholar.py
# - docs/data_dictionary.md
# - Updated sql/schema.sql (should have 302 lines, not 171)
# - Updated scripts/run_pipeline.py (should import enrich modules)
```

## Verification Checklist

After pushing, verify on GitHub:

- [ ] `scripts/enrich_crossref.py` exists
- [ ] `scripts/enrich_semantic_scholar.py` exists
- [ ] `docs/data_dictionary.md` exists
- [ ] `sql/schema.sql` shows 302 lines (has new tables)
- [ ] `scripts/run_pipeline.py` imports `enrich_crossref` and `enrich_semantic_scholar`
- [ ] `scripts/extract_data.py` has `fetch_topics()` function
- [ ] `scripts/config.py` has `OPENALEX_API_KEY`, `CROSSREF_MAILTO`, `SEMANTIC_SCHOLAR_API_KEY`
- [ ] `README.md` mentions Crossref and Semantic Scholar enrichment

## If Changes Still Don't Show

1. **Check you're viewing the correct branch on GitHub:**
   - Click the branch dropdown (should say "main")
   - Make sure you're not looking at "checkpoint-1" or another branch

2. **Verify the commit was pushed:**
   ```bash
   git log --oneline -5
   git remote -v
   ```

3. **Force refresh GitHub page:**
   - Hard refresh: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
   - Clear browser cache if needed

4. **Check if files are in .gitignore:**
   ```bash
   git check-ignore scripts/enrich_crossref.py
   git check-ignore docs/data_dictionary.md
   ```
   (Should return nothing - if it returns a path, the file is ignored)
