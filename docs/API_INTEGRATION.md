# API Integration Guide

## Overview

The Academic Rankings Analytics Platform uses **real-time APIs** as the primary data source, following production best practices for analytics systems.

## Primary APIs

### 1. OpenAlex API

**Base URL:** `https://api.openalex.org`

**Purpose:** Primary source for scholarly data

**Endpoints Used:**

#### `/institutions`
- **Purpose:** Institution discovery and metadata
- **Usage:** Fetch top institutions sorted by citation count
- **Filters Used:**
  - `type:university|institute|research`
  - `cited_by_count:>1000`
- **Sort:** `cited_by_count:desc`
- **Returns:** Institution metadata, summary stats, ROR IDs, country codes

#### `/works`
- **Purpose:** Publication and citation data (MOST IMPORTANT)
- **Usage:** Fetch all works/publications for each institution
- **Filters Used:**
  - `institutions.id:{institution_id}`
  - `publication_year:{year}` (optional)
- **Returns:** Publication records with citations, authorships, concepts, years
- **Rate Limiting:** 0.3-0.5 seconds between requests

**Key Data Extracted:**
- Publication counts
- Citation counts
- Citations per paper
- International collaboration (from authorships)
- Subject classifications (from concepts)
- Publication years

**Authentication:**
- Optional: Set `OPENALEX_EMAIL` in `.env` for better rate limits
- Format: `mailto:your_email@example.com` in User-Agent header

### 2. ROR API

**Base URL:** `https://api.ror.org`

**Purpose:** Entity resolution and institution name standardization

**Endpoints Used:**

#### `/organizations/{ror_id}`
- **Purpose:** Fetch institution metadata by ROR ID
- **Usage:** Resolve canonical names from OpenAlex ROR IDs

#### `/organizations?query={name}`
- **Purpose:** Search for institutions by name
- **Usage:** Find ROR records when ROR ID not available in OpenAlex

**Key Data Extracted:**
- Canonical institution names
- Aliases and name variations
- Country/location metadata
- Organization identifiers

**Rate Limiting:**
- 0.5 seconds between requests
- Batched processing (10 institutions at a time)

## Data Flow

```
1. OpenAlex /institutions
   ↓
   Fetch top N institutions by citation count
   ↓
2. ROR API
   ↓
   Resolve canonical names and validate entities
   ↓
3. OpenAlex /works
   ↓
   Fetch publication data for each institution
   ↓
4. Process & Aggregate
   ↓
   Build indicators from works data
```

## Implementation Details

### Rate Limiting

Both APIs are rate-limited to avoid overwhelming servers:

```python
# OpenAlex: 0.3-0.5 seconds between requests
time.sleep(0.3)

# ROR: 0.5 seconds between requests, batch every 10
if (i + 1) % 10 == 0:
    time.sleep(0.5)
```

### Error Handling

- Retry logic for transient failures
- Graceful degradation if API unavailable
- Logging of all API interactions
- Data persistence at each step

### Data Persistence

Raw API responses are saved to `data/raw/` for:
- Reproducibility
- Debugging
- Offline analysis
- Avoiding redundant API calls

## Configuration

### Environment Variables

```bash
# .env file
OPENALEX_EMAIL=your_email@example.com  # Optional but recommended
```

### API Usage

**OpenAlex:**
- Free, no authentication required
- Email in User-Agent improves rate limits
- No API key needed

**ROR:**
- Free, no authentication required
- No API key needed

## Performance Considerations

### Fetching Works Data

Fetching works data is the slowest step:
- **200 institutions:** ~15-30 minutes
- **500 institutions:** ~45-60 minutes
- **1000 institutions:** ~2-3 hours

**Optimization Options:**
1. Use `--no-works` flag to skip works fetch (uses summary stats only)
2. Limit works per institution (default: 500)
3. Filter by year to reduce data volume

### Caching Strategy

- Raw API responses cached in `data/raw/`
- Processed data cached in `data/processed/`
- Re-running pipeline uses cached data when available

## Troubleshooting

### API Rate Limits

If you hit rate limits:
- Increase delays between requests
- Reduce number of institutions
- Use `--no-works` flag
- Set `OPENALEX_EMAIL` for better limits

### Network Issues

- Check internet connectivity
- Verify API endpoints are accessible
- Check firewall/proxy settings

### Data Quality

- Verify institution names are resolved correctly
- Check ROR API responses for canonical names
- Review entity resolution mappings

## Best Practices

1. **Always use real-time APIs** - Don't rely on static datasets
2. **Respect rate limits** - Built-in delays prevent API abuse
3. **Cache responses** - Save raw data for reproducibility
4. **Handle errors gracefully** - Continue processing even if some requests fail
5. **Log everything** - Track API usage and errors
6. **Use email in headers** - Improves rate limits and helps API maintainers

## Future Enhancements

- Parallel API requests (with rate limit respect)
- Incremental updates (only fetch new/changed data)
- API response validation
- More sophisticated caching
- Support for additional APIs (Crossref, Semantic Scholar)
