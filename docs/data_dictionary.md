# Data Dictionary

Complete documentation of all data sources, tables, indicators, and mappings in the Academic Rankings Intelligence Platform.

## Data Sources

### OpenAlex API (Primary Source)

**Base URL:** `https://api.openalex.org`

**Documentation:** https://docs.openalex.org/api

**Authentication:** API key required (free from https://openalex.org/)

**Endpoints Used:**
- `/institutions` - Institution metadata
- `/works` - Publication and citation data
- `/topics` - Subject/topic classifications (preferred over deprecated concepts)
- `/authors` - Author metadata (optional)
- `/sources` - Journal/venue metadata (optional)

**Key Features:**
- Real-time data
- Cursor pagination for large datasets
- Filtering and sorting
- Rate limiting: ~10 requests/second (with polite delays)

### ROR API (Entity Resolution)

**Base URL:** `https://api.ror.org`

**Documentation:** https://ror.readme.io/docs/rest-api

**Endpoints Used:**
- `/organizations/{ror_id}` - Fetch organization by ROR ID
- `/organizations?query={name}` - Search organizations by name

**Purpose:** Institution name standardization and canonical resolution

### Crossref API (Optional Enrichment)

**Base URL:** `https://api.crossref.org`

**Documentation:** https://www.crossref.org/documentation/retrieve-metadata/rest-api/

**Endpoints Used:**
- `/works/{doi}` - Fetch work metadata by DOI

**Purpose:** DOI-based publication metadata enrichment

**Rate Limits:** Polite usage required (set `CROSSREF_MAILTO`)

### Semantic Scholar API (Optional Enrichment)

**Base URL:** `https://api.semanticscholar.org`

**Documentation:** https://www.semanticscholar.org/product/api

**Endpoints Used:**
- `/graph/v1/paper/DOI:{doi}` - Fetch paper by DOI
- `/graph/v1/paper/search` - Search papers by title

**Purpose:** Influence and citation metrics enrichment

**Rate Limits:** Free tier: 100 requests/day (with API key)

## Database Tables

### institutions

Institution metadata and canonical names.

| Column | Type | Description |
|--------|------|-------------|
| institution_id | SERIAL | Primary key |
| institution_name | VARCHAR(500) | Original name from OpenAlex |
| canonical_name | VARCHAR(500) | Resolved canonical name |
| ror_id | VARCHAR(100) | ROR identifier (if resolved) |
| country | VARCHAR(100) | Country name |
| region | VARCHAR(100) | Region (optional) |
| institution_type | VARCHAR(100) | Type (university, institute, research) |
| openalex_id | VARCHAR(100) | OpenAlex institution ID |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

**Indexes:**
- `idx_institutions_country` on `country`
- `idx_institutions_canonical_name` on `canonical_name`

**Unique Constraint:** `(canonical_name, country)`

### institution_resolution

ROR entity resolution tracking with confidence scores.

| Column | Type | Description |
|--------|------|-------------|
| resolution_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| openalex_id | VARCHAR(100) | OpenAlex institution ID |
| openalex_name | VARCHAR(500) | Original OpenAlex name |
| ror_id | VARCHAR(100) | ROR identifier (if found) |
| resolved_name | VARCHAR(500) | Resolved name |
| canonical_name | VARCHAR(500) | Canonical name |
| match_method | VARCHAR(50) | 'exact_ror', 'ror_search', 'exact_mapping', 'fuzzy_mapping', 'none' |
| match_confidence | NUMERIC(5,2) | Confidence score (0-100) |
| country | VARCHAR(100) | Country |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

**Indexes:**
- `idx_resolution_openalex_id` on `openalex_id`
- `idx_resolution_ror_id` on `ror_id`
- `idx_resolution_institution_id` on `institution_id`

**Unique Constraint:** `openalex_id`

### topics

OpenAlex topics/subjects (preferred over deprecated concepts).

| Column | Type | Description |
|--------|------|-------------|
| topic_id | SERIAL | Primary key |
| openalex_topic_id | VARCHAR(100) | OpenAlex topic ID |
| topic_name | VARCHAR(500) | Topic display name |
| domain | VARCHAR(200) | Domain (e.g., "Computer Science") |
| field | VARCHAR(200) | Field (e.g., "Machine Learning") |
| subfield | VARCHAR(200) | Subfield (optional) |
| custom_subject_group | VARCHAR(100) | Dashboard subject group mapping |
| works_count | INTEGER | Number of works in this topic |
| cited_by_count | INTEGER | Total citations |
| created_at | TIMESTAMP | Record creation timestamp |

**Indexes:**
- `idx_topics_name` on `topic_name`
- `idx_topics_domain` on `domain`
- `idx_topics_subject_group` on `custom_subject_group`

**Unique Constraint:** `openalex_topic_id`

### works

Publication-level data from OpenAlex.

| Column | Type | Description |
|--------|------|-------------|
| work_id | SERIAL | Primary key |
| openalex_work_id | VARCHAR(100) | OpenAlex work ID |
| title | TEXT | Work title |
| publication_year | INTEGER | Publication year |
| publication_date | DATE | Publication date (if available) |
| doi | VARCHAR(500) | DOI (if available) |
| work_type | VARCHAR(100) | Type (article, book, etc.) |
| cited_by_count | INTEGER | Citation count |
| source_name | VARCHAR(500) | Journal/venue name |
| source_id | VARCHAR(100) | OpenAlex source ID |
| language | VARCHAR(10) | Language code |
| is_retracted | BOOLEAN | Retraction status |
| is_paratext | BOOLEAN | Paratext flag |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

**Indexes:**
- `idx_works_openalex_id` on `openalex_work_id`
- `idx_works_year` on `publication_year`
- `idx_works_doi` on `doi`
- `idx_works_type` on `work_type`
- `idx_works_cited_by` on `cited_by_count`

**Unique Constraint:** `openalex_work_id`

### work_topics

Many-to-many relationship between works and topics.

| Column | Type | Description |
|--------|------|-------------|
| work_topic_id | SERIAL | Primary key |
| work_id | INTEGER | Foreign key to works |
| topic_id | INTEGER | Foreign key to topics |
| score | NUMERIC(5,4) | Relevance score from OpenAlex (0-1) |
| created_at | TIMESTAMP | Record creation timestamp |

**Unique Constraint:** `(work_id, topic_id)`

### institution_works

Many-to-many relationship between institutions and works.

| Column | Type | Description |
|--------|------|-------------|
| institution_work_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| work_id | INTEGER | Foreign key to works |
| is_primary | BOOLEAN | Primary affiliation flag |
| author_position | INTEGER | Author order (if available) |
| created_at | TIMESTAMP | Record creation timestamp |

**Unique Constraint:** `(institution_id, work_id)`

### raw_metrics

Unnormalized indicator values (institution-year and institution-subject-year).

| Column | Type | Description |
|--------|------|-------------|
| metric_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (NULL for overall) |
| year | INTEGER | Year |
| publication_count | INTEGER | Total publications |
| citation_count | INTEGER | Total citations |
| citations_per_paper | NUMERIC(10,2) | Average citations per paper |
| international_collaboration_rate | NUMERIC(5,4) | International collaboration rate (0-1) |
| quality_proxy | NUMERIC(10,4) | Quality proxy (top percentile citations) |
| productivity_proxy | NUMERIC(10,4) | Productivity proxy (impact per publication) |
| h_index | INTEGER | H-index |
| top_percentile_citations | NUMERIC(10,2) | Top percentile citation threshold |
| created_at | TIMESTAMP | Record creation timestamp |

**Unique Constraint:** `(institution_id, subject_id, year)`

### normalized_metrics

Normalized indicator scores (0-1 scale).

| Column | Type | Description |
|--------|------|-------------|
| metric_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (NULL for overall) |
| year | INTEGER | Year |
| publication_score | NUMERIC(10,6) | Normalized publication score |
| citation_score | NUMERIC(10,6) | Normalized citation score |
| collaboration_score | NUMERIC(10,6) | Normalized collaboration score |
| quality_score | NUMERIC(10,6) | Normalized quality score |
| subject_strength_score | NUMERIC(10,6) | Normalized subject strength score |
| productivity_score | NUMERIC(10,6) | Normalized productivity score |
| normalization_method | VARCHAR(50) | Method used ('min_max', 'z_score', 'robust') |
| created_at | TIMESTAMP | Record creation timestamp |

**Unique Constraint:** `(institution_id, subject_id, year)`

### api_ingestion_log

Tracks all API ingestion runs.

| Column | Type | Description |
|--------|------|-------------|
| log_id | SERIAL | Primary key |
| source_name | VARCHAR(100) | Source ('openalex', 'ror', 'crossref', 'semantic_scholar', 'pipeline') |
| entity_type | VARCHAR(100) | Entity type ('institution', 'work', 'topic', 'enrichment') |
| started_at | TIMESTAMP | Start time |
| completed_at | TIMESTAMP | Completion time (NULL if running/failed) |
| status | VARCHAR(50) | 'running', 'completed', 'failed', 'partial' |
| records_fetched | INTEGER | Number of records fetched |
| records_processed | INTEGER | Number of records processed |
| records_failed | INTEGER | Number of records failed |
| notes | TEXT | Additional notes |
| config_json | JSONB | Configuration used for this run |
| created_at | TIMESTAMP | Record creation timestamp |

### benchmark_rankings

External ranking tables (ARWU, QS, THE, USNews, etc.).

| Column | Type | Description |
|--------|------|-------------|
| benchmark_id | SERIAL | Primary key |
| benchmark_source | VARCHAR(100) | Source ('ARWU', 'QS', 'THE', 'USNews', etc.) |
| year | INTEGER | Ranking year |
| institution_name_raw | VARCHAR(500) | Original name from source |
| canonical_name | VARCHAR(500) | Resolved canonical name |
| institution_id | INTEGER | Foreign key to institutions (NULL until resolved) |
| rank | INTEGER | Ranking position |
| score | NUMERIC(10,4) | Score (if available) |
| metadata_json | JSONB | Additional fields from source |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Record update timestamp |

## Indicators

### Publication Count
**Definition:** Total number of publications (works) for an institution in a given year.

**Calculation:** Count of works where `publication_year = year` and institution is an author affiliation.

**Normalization:** Min-max scaling across all institutions for the year.

### Citation Count
**Definition:** Total number of citations received by all publications.

**Calculation:** Sum of `cited_by_count` for all works.

**Normalization:** Min-max scaling across all institutions for the year.

### Citations Per Paper
**Definition:** Average citations per publication.

**Calculation:** `citation_count / publication_count`

**Normalization:** Min-max scaling.

### Multi-Institution Rate
**Definition:** Proportion of works involving multiple institutions.

**Calculation:** Count of works with >1 institution affiliation / total works

**Range:** 0-1

### International Collaboration Rate
**Definition:** Proportion of works involving institutions from multiple countries.

**Calculation:** Count of works with institutions from >1 country / total works

**Range:** 0-1

**Normalization:** Min-max scaling (used as collaboration_score).

### Quality Proxy
**Definition:** High-impact research proxy based on top percentile citations.

**Calculation:** 
1. Identify top 90th percentile citation threshold
2. Sum citations for papers above threshold
3. Divide by total citations

**Purpose:** Measures concentration of high-impact research.

**Normalization:** Min-max scaling.

### Productivity Proxy
**Definition:** Impact per publication efficiency metric.

**Calculation:** Weighted combination of:
- Publications per year (30% weight)
- Citations per year (70% weight)

**Normalization:** Min-max scaling.

### Subject Strength Basis
**Definition:** Subject-specific output and impact (for subject-level metrics).

**Calculation:** Citation count in subject / publication count in subject

**Normalization:** Min-max scaling within subject and year.

## Subject Mapping

OpenAlex topics are mapped to dashboard-friendly subject groups:

### Subject Groups

1. **Computer Science** - CS, AI, ML, Data Science topics
2. **Engineering** - All engineering disciplines
3. **Life Sciences** - Biology, Medicine, Biochemistry
4. **Physical Sciences** - Physics, Chemistry, Mathematics
5. **Social Sciences** - Economics, Psychology, Sociology
6. **Business / Economics** - Business, Finance, Economics
7. **Medicine** - Medical research topics
8. **Natural Sciences** - General natural sciences

**Mapping Logic:**
- Topics are mapped based on domain/field/subfield from OpenAlex
- Custom mapping can be configured in `scripts/config.py`
- Unmapped topics are assigned to "Other"

## Enrichment Layers

### Crossref Enrichment (Optional)

**When Enabled:** Works with DOIs are enriched with Crossref metadata.

**Fields Added:**
- `journal` - Journal/container title
- `publisher` - Publisher name
- `published_date` - Publication date
- `type` - Work type
- `funder` - Funder information
- `subject` - Subject classifications

**Usage:** Fills missing metadata when OpenAlex fields are incomplete.

### Semantic Scholar Enrichment (Optional)

**When Enabled:** Works are enriched with Semantic Scholar influence metrics.

**Fields Added:**
- `influentialCitationCount` - Highly cited papers count
- `citationCount` - Total citations (cross-validated)
- `referenceCount` - Reference count
- `venue` - Venue information
- `authors` - Author metadata

**Usage:** Provides influence proxies and citation network data.

## Benchmark Rankings

External ranking tables are loaded separately and resolved to canonical institution names.

**Supported Sources:**
- ARWU (ShanghaiRanking)
- QS World University Rankings
- THE World University Rankings
- US News Global Rankings
- Other curated CSV/XLS sources

**Resolution Process:**
1. Load raw ranking table
2. Extract institution names
3. Resolve to canonical names using entity resolution layer
4. Match to `institutions` table
5. Store in `benchmark_rankings` table

**Usage:** Compare computed rankings with established benchmarks.
