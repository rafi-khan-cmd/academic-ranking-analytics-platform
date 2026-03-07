# Data Dictionary

## Database Tables

### institutions
Stores institution metadata and canonical names.

| Column | Type | Description |
|--------|------|-------------|
| institution_id | SERIAL | Primary key |
| institution_name | VARCHAR(500) | Original institution name |
| canonical_name | VARCHAR(500) | Standardized canonical name |
| country | VARCHAR(100) | Country name |
| region | VARCHAR(100) | Geographic region |
| institution_type | VARCHAR(100) | Type of institution |
| openalex_id | VARCHAR(100) | OpenAlex identifier |

### raw_metrics
Stores unnormalized indicator values.

| Column | Type | Description |
|--------|------|-------------|
| metric_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (nullable) |
| year | INTEGER | Year of metrics |
| publication_count | INTEGER | Total publications |
| citation_count | INTEGER | Total citations |
| citations_per_paper | NUMERIC | Average citations per paper |
| international_collaboration_rate | NUMERIC | Proportion of collaborative works |
| quality_proxy | NUMERIC | High-impact research proxy |
| productivity_proxy | NUMERIC | Impact per publication |
| h_index | INTEGER | H-index value |
| top_percentile_citations | NUMERIC | Top percentile citation count |

### normalized_metrics
Stores normalized indicator scores (0-1 range).

| Column | Type | Description |
|--------|------|-------------|
| metric_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (nullable) |
| year | INTEGER | Year of metrics |
| publication_score | NUMERIC | Normalized publication score |
| citation_score | NUMERIC | Normalized citation score |
| collaboration_score | NUMERIC | Normalized collaboration score |
| quality_score | NUMERIC | Normalized quality score |
| subject_strength_score | NUMERIC | Normalized subject strength score |
| productivity_score | NUMERIC | Normalized productivity score |
| normalization_method | VARCHAR(50) | Method used (e.g., 'min_max') |

### ranking_results
Stores computed rankings by methodology.

| Column | Type | Description |
|--------|------|-------------|
| ranking_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (nullable) |
| year | INTEGER | Year of ranking |
| methodology_name | VARCHAR(100) | Methodology name |
| overall_score | NUMERIC | Weighted overall score |
| rank_position | INTEGER | Rank position (1 = best) |

### methodology_weights
Stores methodology weight definitions.

| Column | Type | Description |
|--------|------|-------------|
| methodology_id | SERIAL | Primary key |
| methodology_name | VARCHAR(100) | Unique methodology name |
| publication_weight | NUMERIC | Weight for publication indicator |
| citation_weight | NUMERIC | Weight for citation indicator |
| collaboration_weight | NUMERIC | Weight for collaboration indicator |
| quality_weight | NUMERIC | Weight for quality indicator |
| subject_strength_weight | NUMERIC | Weight for subject strength indicator |
| productivity_weight | NUMERIC | Weight for productivity indicator |
| description | TEXT | Methodology description |

### institution_clusters
Stores cluster assignments from KMeans clustering.

| Column | Type | Description |
|--------|------|-------------|
| cluster_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| cluster_label | VARCHAR(100) | Cluster label (e.g., 'High-Impact Elite') |
| cluster_description | TEXT | Cluster description |
| cluster_method | VARCHAR(50) | Clustering method (e.g., 'kmeans') |
| n_clusters | INTEGER | Number of clusters used |

### sensitivity_results
Stores volatility/sensitivity analysis results.

| Column | Type | Description |
|--------|------|-------------|
| sensitivity_id | SERIAL | Primary key |
| institution_id | INTEGER | Foreign key to institutions |
| subject_id | INTEGER | Foreign key to subjects (nullable) |
| year | INTEGER | Year of analysis |
| volatility_score | NUMERIC | Volatility metric |
| average_rank | NUMERIC | Average rank across methodologies |
| rank_range | INTEGER | Range of ranks (max - min) |
| methodology_count | INTEGER | Number of methodologies analyzed |
| min_rank | INTEGER | Best (lowest) rank |
| max_rank | INTEGER | Worst (highest) rank |

## Views

### v_institution_rankings
Combines ranking results with institution and metric details.

### v_top_institutions
Top institutions by methodology.

### v_institution_profiles
Institution indicator profiles with raw and normalized metrics.

### v_methodology_comparison
Methodology comparison for institutions.

### v_subject_rankings
Subject-level rankings.

### v_country_performance
Country-level performance summaries.

### v_institution_sensitivity
Institution sensitivity/volatility summaries.

### v_cluster_profiles
Cluster-level metric summaries.
