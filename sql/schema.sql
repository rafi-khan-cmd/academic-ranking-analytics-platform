-- Academic Rankings Analytics Platform
-- PostgreSQL Schema
-- This schema supports multi-methodology ranking analysis with institution, subject, and country-level aggregation

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Institutions table
CREATE TABLE IF NOT EXISTS institutions (
    institution_id SERIAL PRIMARY KEY,
    institution_name VARCHAR(500) NOT NULL,
    canonical_name VARCHAR(500) NOT NULL,
    ror_id VARCHAR(100),
    country VARCHAR(100),
    region VARCHAR(100),
    institution_type VARCHAR(100),
    openalex_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(canonical_name, country)
);

CREATE INDEX idx_institutions_country ON institutions(country);
CREATE INDEX idx_institutions_canonical_name ON institutions(canonical_name);

-- Subjects table
CREATE TABLE IF NOT EXISTS subjects (
    subject_id SERIAL PRIMARY KEY,
    subject_name VARCHAR(200) NOT NULL UNIQUE,
    subject_group VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_subjects_group ON subjects(subject_group);

-- Raw metrics table
CREATE TABLE IF NOT EXISTS raw_metrics (
    metric_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE SET NULL,
    year INTEGER NOT NULL,
    publication_count INTEGER DEFAULT 0,
    citation_count INTEGER DEFAULT 0,
    citations_per_paper NUMERIC(10, 2),
    international_collaboration_rate NUMERIC(5, 4),
    quality_proxy NUMERIC(10, 4),
    productivity_proxy NUMERIC(10, 4),
    h_index INTEGER,
    top_percentile_citations NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institution_id, subject_id, year)
);

CREATE INDEX idx_raw_metrics_institution ON raw_metrics(institution_id);
CREATE INDEX idx_raw_metrics_subject ON raw_metrics(subject_id);
CREATE INDEX idx_raw_metrics_year ON raw_metrics(year);

-- Normalized metrics table
CREATE TABLE IF NOT EXISTS normalized_metrics (
    metric_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE SET NULL,
    year INTEGER NOT NULL,
    publication_score NUMERIC(10, 6) DEFAULT 0,
    citation_score NUMERIC(10, 6) DEFAULT 0,
    collaboration_score NUMERIC(10, 6) DEFAULT 0,
    quality_score NUMERIC(10, 6) DEFAULT 0,
    subject_strength_score NUMERIC(10, 6) DEFAULT 0,
    productivity_score NUMERIC(10, 6) DEFAULT 0,
    normalization_method VARCHAR(50) DEFAULT 'min_max',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institution_id, subject_id, year)
);

CREATE INDEX idx_normalized_metrics_institution ON normalized_metrics(institution_id);
CREATE INDEX idx_normalized_metrics_subject ON normalized_metrics(subject_id);
CREATE INDEX idx_normalized_metrics_year ON normalized_metrics(year);

-- Methodology weights table
CREATE TABLE IF NOT EXISTS methodology_weights (
    methodology_id SERIAL PRIMARY KEY,
    methodology_name VARCHAR(100) NOT NULL UNIQUE,
    publication_weight NUMERIC(5, 3) DEFAULT 0.2,
    citation_weight NUMERIC(5, 3) DEFAULT 0.2,
    collaboration_weight NUMERIC(5, 3) DEFAULT 0.2,
    quality_weight NUMERIC(5, 3) DEFAULT 0.2,
    subject_strength_weight NUMERIC(5, 3) DEFAULT 0.1,
    productivity_weight NUMERIC(5, 3) DEFAULT 0.1,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        ABS((publication_weight + citation_weight + collaboration_weight + 
             quality_weight + subject_strength_weight + productivity_weight) - 1.0) < 0.001
    )
);

-- Ranking results table
CREATE TABLE IF NOT EXISTS ranking_results (
    ranking_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE SET NULL,
    year INTEGER NOT NULL,
    methodology_name VARCHAR(100) NOT NULL,
    overall_score NUMERIC(10, 6) NOT NULL,
    rank_position INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (methodology_name) REFERENCES methodology_weights(methodology_name),
    UNIQUE(institution_id, subject_id, year, methodology_name)
);

CREATE INDEX idx_ranking_results_institution ON ranking_results(institution_id);
CREATE INDEX idx_ranking_results_subject ON ranking_results(subject_id);
CREATE INDEX idx_ranking_results_methodology ON ranking_results(methodology_name);
CREATE INDEX idx_ranking_results_year ON ranking_results(year);
CREATE INDEX idx_ranking_results_rank ON ranking_results(rank_position);

-- Institution clusters table
CREATE TABLE IF NOT EXISTS institution_clusters (
    cluster_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    cluster_label VARCHAR(100) NOT NULL,
    cluster_description TEXT,
    cluster_method VARCHAR(50) DEFAULT 'kmeans',
    n_clusters INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institution_id, cluster_method)
);

CREATE INDEX idx_clusters_institution ON institution_clusters(institution_id);
CREATE INDEX idx_clusters_label ON institution_clusters(cluster_label);

-- Sensitivity results table
CREATE TABLE IF NOT EXISTS sensitivity_results (
    sensitivity_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(subject_id) ON DELETE SET NULL,
    year INTEGER NOT NULL,
    volatility_score NUMERIC(10, 6),
    average_rank NUMERIC(10, 2),
    rank_range INTEGER,
    methodology_count INTEGER,
    min_rank INTEGER,
    max_rank INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institution_id, subject_id, year)
);

CREATE INDEX idx_sensitivity_institution ON sensitivity_results(institution_id);
CREATE INDEX idx_sensitivity_subject ON sensitivity_results(subject_id);

-- Country summary table
CREATE TABLE IF NOT EXISTS country_summary (
    summary_id SERIAL PRIMARY KEY,
    country VARCHAR(100) NOT NULL,
    methodology_name VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    avg_score NUMERIC(10, 6),
    institution_count INTEGER,
    avg_publication_score NUMERIC(10, 6),
    avg_citation_score NUMERIC(10, 6),
    avg_collaboration_score NUMERIC(10, 6),
    avg_quality_score NUMERIC(10, 6),
    top_institution_id INTEGER REFERENCES institutions(institution_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (methodology_name) REFERENCES methodology_weights(methodology_name),
    UNIQUE(country, methodology_name, year)
);

CREATE INDEX idx_country_summary_country ON country_summary(country);
CREATE INDEX idx_country_summary_methodology ON country_summary(methodology_name);

-- Institution resolution table (for ROR entity resolution tracking)
CREATE TABLE IF NOT EXISTS institution_resolution (
    resolution_id SERIAL PRIMARY KEY,
    institution_id INTEGER REFERENCES institutions(institution_id) ON DELETE CASCADE,
    openalex_id VARCHAR(100) NOT NULL,
    openalex_name VARCHAR(500) NOT NULL,
    ror_id VARCHAR(100),
    resolved_name VARCHAR(500),
    canonical_name VARCHAR(500),
    match_method VARCHAR(50), -- 'exact', 'fuzzy', 'ror_api', 'manual'
    match_confidence NUMERIC(5, 2), -- 0-100
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(openalex_id)
);

CREATE INDEX idx_resolution_openalex_id ON institution_resolution(openalex_id);
CREATE INDEX idx_resolution_ror_id ON institution_resolution(ror_id);
CREATE INDEX idx_resolution_institution_id ON institution_resolution(institution_id);

-- Topics table (OpenAlex topics/subjects)
CREATE TABLE IF NOT EXISTS topics (
    topic_id SERIAL PRIMARY KEY,
    openalex_topic_id VARCHAR(100) NOT NULL UNIQUE,
    topic_name VARCHAR(500) NOT NULL,
    domain VARCHAR(200),
    field VARCHAR(200),
    subfield VARCHAR(200),
    custom_subject_group VARCHAR(100), -- Maps to dashboard subject groups
    works_count INTEGER DEFAULT 0,
    cited_by_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_topics_name ON topics(topic_name);
CREATE INDEX idx_topics_domain ON topics(domain);
CREATE INDEX idx_topics_subject_group ON topics(custom_subject_group);

-- Works table (publication-level data from OpenAlex)
CREATE TABLE IF NOT EXISTS works (
    work_id SERIAL PRIMARY KEY,
    openalex_work_id VARCHAR(100) NOT NULL UNIQUE,
    title TEXT,
    publication_year INTEGER,
    publication_date DATE,
    doi VARCHAR(500),
    work_type VARCHAR(100),
    cited_by_count INTEGER DEFAULT 0,
    source_name VARCHAR(500), -- Journal/venue name
    source_id VARCHAR(100), -- OpenAlex source ID
    language VARCHAR(10),
    is_retracted BOOLEAN DEFAULT FALSE,
    is_paratext BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_works_openalex_id ON works(openalex_work_id);
CREATE INDEX idx_works_year ON works(publication_year);
CREATE INDEX idx_works_doi ON works(doi);
CREATE INDEX idx_works_type ON works(work_type);
CREATE INDEX idx_works_cited_by ON works(cited_by_count);

-- Work topics junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS work_topics (
    work_topic_id SERIAL PRIMARY KEY,
    work_id INTEGER NOT NULL REFERENCES works(work_id) ON DELETE CASCADE,
    topic_id INTEGER NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    score NUMERIC(5, 4), -- Relevance score from OpenAlex
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(work_id, topic_id)
);

CREATE INDEX idx_work_topics_work ON work_topics(work_id);
CREATE INDEX idx_work_topics_topic ON work_topics(topic_id);

-- Institution works junction table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS institution_works (
    institution_work_id SERIAL PRIMARY KEY,
    institution_id INTEGER NOT NULL REFERENCES institutions(institution_id) ON DELETE CASCADE,
    work_id INTEGER NOT NULL REFERENCES works(work_id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE, -- Primary affiliation vs secondary
    author_position INTEGER, -- Author order if available
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(institution_id, work_id)
);

CREATE INDEX idx_institution_works_inst ON institution_works(institution_id);
CREATE INDEX idx_institution_works_work ON institution_works(work_id);

-- API ingestion log table (for tracking ingestion runs)
CREATE TABLE IF NOT EXISTS api_ingestion_log (
    log_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL, -- 'openalex', 'ror', 'crossref', 'semantic_scholar'
    entity_type VARCHAR(100) NOT NULL, -- 'institution', 'work', 'topic', 'enrichment'
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(50) NOT NULL, -- 'running', 'completed', 'failed', 'partial'
    records_fetched INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    notes TEXT,
    config_json JSONB, -- Store configuration used for this run
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ingestion_log_source ON api_ingestion_log(source_name);
CREATE INDEX idx_ingestion_log_status ON api_ingestion_log(status);
CREATE INDEX idx_ingestion_log_started ON api_ingestion_log(started_at);

-- Benchmark rankings table (for external ranking tables)
CREATE TABLE IF NOT EXISTS benchmark_rankings (
    benchmark_id SERIAL PRIMARY KEY,
    benchmark_source VARCHAR(100) NOT NULL, -- 'ARWU', 'QS', 'THE', 'USNews', etc.
    year INTEGER NOT NULL,
    institution_name_raw VARCHAR(500) NOT NULL, -- Original name from source
    canonical_name VARCHAR(500), -- Resolved canonical name
    institution_id INTEGER REFERENCES institutions(institution_id) ON DELETE SET NULL,
    rank INTEGER,
    score NUMERIC(10, 4),
    metadata_json JSONB, -- Additional fields from source
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_benchmark_source ON benchmark_rankings(benchmark_source);
CREATE INDEX idx_benchmark_year ON benchmark_rankings(year);
CREATE INDEX idx_benchmark_institution_id ON benchmark_rankings(institution_id);
CREATE INDEX idx_benchmark_rank ON benchmark_rankings(rank);
