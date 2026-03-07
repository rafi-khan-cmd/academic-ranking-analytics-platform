-- Analytical Queries for Academic Rankings Analytics Platform
-- These queries demonstrate common analytical patterns and can be used for dashboard insights

-- Query 1: Top 20 institutions by methodology (overall rankings)
SELECT 
    methodology_name,
    institution_name,
    country,
    overall_score,
    rank_position
FROM v_top_institutions
WHERE year = (SELECT MAX(year) FROM ranking_results)
ORDER BY methodology_name, rank_position
LIMIT 20;

-- Query 2: Top institutions by subject
SELECT 
    subject_name,
    institution_name,
    country,
    overall_score,
    rank_position
FROM v_subject_rankings
WHERE methodology_name = 'Balanced Model'
  AND year = (SELECT MAX(year) FROM ranking_results)
ORDER BY subject_name, rank_position
LIMIT 10;

-- Query 3: Average score by country
SELECT 
    country,
    methodology_name,
    AVG(overall_score) as avg_score,
    COUNT(DISTINCT institution_id) as institution_count,
    MIN(rank_position) as best_rank,
    MAX(rank_position) as worst_rank
FROM v_methodology_comparison
WHERE year = (SELECT MAX(year) FROM ranking_results)
GROUP BY country, methodology_name
ORDER BY avg_score DESC;

-- Query 4: Institutions with highest methodology sensitivity
SELECT 
    institution_name,
    country,
    volatility_score,
    average_rank,
    rank_range,
    min_rank,
    max_rank
FROM v_institution_sensitivity
WHERE year = (SELECT MAX(year) FROM sensitivity_results)
ORDER BY volatility_score DESC
LIMIT 20;

-- Query 5: Highest productivity institutions
SELECT 
    institution_name,
    country,
    productivity_score,
    publication_count,
    citation_count,
    citations_per_paper
FROM v_institution_profiles
WHERE year = (SELECT MAX(year) FROM normalized_metrics)
ORDER BY productivity_score DESC
LIMIT 20;

-- Query 6: Cluster-level metric summaries
SELECT 
    cluster_label,
    cluster_description,
    institution_count,
    country_count,
    ROUND(avg_publication_score::numeric, 4) as avg_publication,
    ROUND(avg_citation_score::numeric, 4) as avg_citation,
    ROUND(avg_collaboration_score::numeric, 4) as avg_collaboration,
    ROUND(avg_quality_score::numeric, 4) as avg_quality
FROM v_cluster_profiles
ORDER BY avg_citation_score DESC;

-- Query 7: Methodology comparison for specific institution
SELECT 
    methodology_name,
    overall_score,
    rank_position,
    publication_score,
    citation_score,
    collaboration_score,
    quality_score
FROM v_institution_rankings
WHERE canonical_name = 'Massachusetts Institute of Technology'
  AND subject_id IS NULL
  AND year = (SELECT MAX(year) FROM ranking_results)
ORDER BY rank_position;

-- Query 8: Subject specialization analysis
SELECT 
    institution_name,
    country,
    subject_name,
    overall_score,
    rank_position,
    (SELECT rank_position 
     FROM v_institution_rankings r2 
     WHERE r2.institution_id = r.institution_id 
       AND r2.subject_id IS NULL 
       AND r2.methodology_name = r.methodology_name
       AND r2.year = r.year) as overall_rank,
    (SELECT rank_position 
     FROM v_institution_rankings r2 
     WHERE r2.institution_id = r.institution_id 
       AND r2.subject_id IS NULL 
       AND r2.methodology_name = r.methodology_name
       AND r2.year = r.year) - r.rank_position as rank_improvement
FROM v_institution_rankings r
WHERE methodology_name = 'Balanced Model'
  AND year = (SELECT MAX(year) FROM ranking_results)
  AND subject_id IS NOT NULL
ORDER BY rank_improvement DESC
LIMIT 20;

-- Query 9: Country-level performance by methodology
SELECT 
    country,
    methodology_name,
    avg_score,
    institution_count,
    avg_publication_score,
    avg_citation_score,
    avg_collaboration_score,
    top_institution_name
FROM v_country_performance
WHERE year = (SELECT MAX(year) FROM country_summary)
ORDER BY avg_score DESC;

-- Query 10: Institutions with best citation impact
SELECT 
    institution_name,
    country,
    citation_score,
    citation_count,
    citations_per_paper,
    quality_proxy
FROM v_institution_profiles
WHERE year = (SELECT MAX(year) FROM normalized_metrics)
ORDER BY citation_score DESC
LIMIT 20;
