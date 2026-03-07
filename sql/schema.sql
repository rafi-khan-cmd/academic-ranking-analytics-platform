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
