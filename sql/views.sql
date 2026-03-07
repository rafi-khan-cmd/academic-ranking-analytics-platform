-- Analytical Views for Dashboard Access
-- These views simplify common query patterns for the Streamlit dashboard

-- View: Institution rankings with full details
CREATE OR REPLACE VIEW v_institution_rankings AS
SELECT 
    r.ranking_id,
    r.institution_id,
    i.institution_name,
    i.canonical_name,
    i.country,
    i.region,
    r.subject_id,
    s.subject_name,
    r.year,
    r.methodology_name,
    r.overall_score,
    r.rank_position,
    nm.publication_score,
    nm.citation_score,
    nm.collaboration_score,
    nm.quality_score,
    nm.subject_strength_score,
    nm.productivity_score
FROM ranking_results r
JOIN institutions i ON r.institution_id = i.institution_id
LEFT JOIN subjects s ON r.subject_id = s.subject_id
LEFT JOIN normalized_metrics nm ON 
    r.institution_id = nm.institution_id 
    AND (r.subject_id = nm.subject_id OR (r.subject_id IS NULL AND nm.subject_id IS NULL))
    AND r.year = nm.year;

-- View: Top institutions by methodology
CREATE OR REPLACE VIEW v_top_institutions AS
SELECT 
    methodology_name,
    institution_id,
    institution_name,
    canonical_name,
    country,
    overall_score,
    rank_position,
    year
FROM v_institution_rankings
WHERE subject_id IS NULL
ORDER BY methodology_name, rank_position;

-- View: Institution indicator profiles
CREATE OR REPLACE VIEW v_institution_profiles AS
SELECT 
    i.institution_id,
    i.institution_name,
    i.canonical_name,
    i.country,
    i.region,
    nm.year,
    nm.publication_score,
    nm.citation_score,
    nm.collaboration_score,
    nm.quality_score,
    nm.subject_strength_score,
    nm.productivity_score,
    rm.publication_count,
    rm.citation_count,
    rm.citations_per_paper,
    rm.international_collaboration_rate,
    rm.quality_proxy,
    rm.productivity_proxy
FROM institutions i
JOIN normalized_metrics nm ON i.institution_id = nm.institution_id
LEFT JOIN raw_metrics rm ON 
    nm.institution_id = rm.institution_id 
    AND nm.subject_id = rm.subject_id
    AND nm.year = rm.year
WHERE nm.subject_id IS NULL;

-- View: Methodology comparison for institutions
CREATE OR REPLACE VIEW v_methodology_comparison AS
SELECT 
    i.institution_id,
    i.institution_name,
    i.country,
    r.methodology_name,
    r.overall_score,
    r.rank_position,
    r.year
FROM ranking_results r
JOIN institutions i ON r.institution_id = i.institution_id
WHERE r.subject_id IS NULL;

-- View: Subject-level rankings
CREATE OR REPLACE VIEW v_subject_rankings AS
SELECT 
    s.subject_name,
    s.subject_group,
    r.institution_id,
    i.institution_name,
    i.country,
    r.methodology_name,
    r.overall_score,
    r.rank_position,
    r.year
FROM ranking_results r
JOIN institutions i ON r.institution_id = i.institution_id
JOIN subjects s ON r.subject_id = s.subject_id
ORDER BY s.subject_name, r.methodology_name, r.rank_position;

-- View: Country performance summary
CREATE OR REPLACE VIEW v_country_performance AS
SELECT 
    cs.country,
    cs.methodology_name,
    cs.year,
    cs.avg_score,
    cs.institution_count,
    cs.avg_publication_score,
    cs.avg_citation_score,
    cs.avg_collaboration_score,
    cs.avg_quality_score,
    i.institution_name as top_institution_name
FROM country_summary cs
LEFT JOIN institutions i ON cs.top_institution_id = i.institution_id
ORDER BY cs.country, cs.methodology_name, cs.year;

-- View: Institution sensitivity summary
CREATE OR REPLACE VIEW v_institution_sensitivity AS
SELECT 
    i.institution_id,
    i.institution_name,
    i.country,
    sr.year,
    sr.volatility_score,
    sr.average_rank,
    sr.rank_range,
    sr.methodology_count,
    sr.min_rank,
    sr.max_rank
FROM sensitivity_results sr
JOIN institutions i ON sr.institution_id = i.institution_id
WHERE sr.subject_id IS NULL
ORDER BY sr.volatility_score DESC;

-- View: Cluster profiles
CREATE OR REPLACE VIEW v_cluster_profiles AS
SELECT 
    ic.cluster_label,
    ic.cluster_description,
    ic.cluster_method,
    COUNT(DISTINCT ic.institution_id) as institution_count,
    COUNT(DISTINCT i.country) as country_count,
    AVG(vp.publication_score) as avg_publication_score,
    AVG(vp.citation_score) as avg_citation_score,
    AVG(vp.collaboration_score) as avg_collaboration_score,
    AVG(vp.quality_score) as avg_quality_score
FROM institution_clusters ic
JOIN institutions i ON ic.institution_id = i.institution_id
LEFT JOIN v_institution_profiles vp ON ic.institution_id = vp.institution_id
GROUP BY ic.cluster_label, ic.cluster_description, ic.cluster_method;
