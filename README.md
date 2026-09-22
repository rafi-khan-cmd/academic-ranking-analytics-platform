# Academic Rankings Intelligence Platform

An analytics platform that reconstructs and stress-tests global university ranking methodologies from raw research indicators. It pulls institution and publication data from the OpenAlex API, resolves institutions to canonical entities, engineers normalized indicators, and lets you see how different weighting choices reshuffle the rankings. Everything is backed by a PostgreSQL analytics schema and surfaced through a Streamlit dashboard.

The idea started from a simple observation: rankings like ARWU, QS, and THE all measure "research quality," yet they disagree, because they weight indicators differently. This project makes those trade-offs explicit and lets you explore them interactively.

## What it does

- Ingests institutions, works, topics, and citation data from the [OpenAlex API](https://openalex.org/)
- Resolves institution names to canonical entities using the [ROR API](https://ror.org/) plus fuzzy matching for the long tail
- Engineers six research indicators (publication, citation, collaboration, quality, subject strength, productivity) and normalizes them with min-max scaling
- Applies five configurable weighting methodologies and recomputes rankings for each
- Runs feature-importance, KMeans clustering, and weight-sensitivity analysis on top of the rankings
- Serves a seven-page Streamlit dashboard for exploring institutions, methodologies, and clusters

## Stack

- **Python** (pandas, numpy) for the data pipeline
- **PostgreSQL** with SQLAlchemy and psycopg2 for the analytics database
- **scikit-learn** for clustering and feature importance, **statsmodels** for statistical checks
- **rapidfuzz** and **pycountry** for entity resolution and country normalization
- **Streamlit** and **Plotly** for the dashboard

Optional enrichment layers use the Crossref and Semantic Scholar APIs.

## Pipeline

```
OpenAlex API  →  extract  →  clean  →  resolve entities (ROR)
             →  build indicators  →  normalize  →  load to PostgreSQL
             →  compute rankings  →  advanced analytics  →  Streamlit dashboard
```

## Indicators and methodologies

Six indicators feed the ranking engine:

| Indicator | Meaning |
|-----------|---------|
| Publication score | Normalized publication count |
| Citation score | Normalized total citations |
| Collaboration score | International collaboration rate |
| Quality score | High-impact research proxy (top-percentile citations) |
| Subject strength score | Subject-specific excellence |
| Productivity score | Impact per publication |

Five weighting profiles are defined in `scripts/config.py`:

1. **Balanced** – equal weight across indicators
2. **Research Impact** – 35% citation, 25% quality
3. **Publication Volume** – 40% publication
4. **Collaboration-Forward** – 40% collaboration
5. **Subject Excellence** – 25% subject strength

The methodology simulator lets you drag the weights yourself and watch the rankings move.

## Database

The schema (`sql/schema.sql`) defines 16 tables covering institutions and entity resolution, works and topics, raw and normalized metrics, methodology weights and ranking results, clustering and sensitivity outputs, country summaries, ingestion logging, and external benchmark rankings. Eight analytical views (`sql/views.sql`) sit on top for the dashboard. Field-level descriptions are in `docs/data_dictionary.md`.

## Dashboard pages

1. **Executive Overview** – top institutions, country summaries, KPI cards
2. **Global Rankings** – sortable tables with methodology/country/year filters
3. **Institution Explorer** – per-institution profiles and indicator radar charts
4. **Methodology Simulator** – live weight adjustment and rank-movement analysis
5. **Subject Rankings** – subject-specific rankings where data allows
6. **Indicator Analytics** – correlation heatmaps, feature importance, distributions
7. **Research Clusters** – KMeans institution clusters and their profiles

## Getting started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+

### Setup

```bash
git clone https://github.com/rafi-khan-cmd/academic-ranking-analytics-platform.git
cd academic-ranking-analytics-platform

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then fill in your database + API details
```

Load the schema and views:

```bash
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f sql/schema.sql
psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f sql/views.sql
```

### Running the pipeline

The full pipeline fetches live data from OpenAlex and ROR, so you need an internet connection and an email set in `OPENALEX_EMAIL` for polite API usage.

```bash
# Full run: 200 institutions, last 5 years (15-30 min with works data)
python scripts/run_pipeline.py --institutions 200

# Faster run without work-level data
python scripts/run_pipeline.py --institutions 200 --no-works

# Optional enrichment layers
python scripts/run_pipeline.py --enable-crossref --enable-semantic-scholar
```

You can also run the steps individually (`extract_data.py`, `clean_data.py`, `resolve_entities.py`, `build_indicators.py`, `normalize_metrics.py`, `load_to_postgres.py`, `ranking_engine.py`, `advanced_analytics.py`).

If you just want to click around the dashboard without hitting the APIs, `scripts/create_sample_data.py` loads 40 synthetic institutions for demo purposes.

### Running the dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard runs at `http://localhost:8501`. `streamlit_app.py` is the Streamlit Cloud entrypoint and validates the database connection before launching.

## Repository layout

```
scripts/        data pipeline (extract, clean, resolve, indicators, rankings, analytics)
sql/            schema.sql, views.sql, analytical_queries.sql
dashboard/      Streamlit app and the seven pages
docs/           architecture, methodology, data dictionary, API + deployment notes
notebooks/      01_data_exploration.ipynb
```

## A few things I found

- Citation-weighted methodologies reward high-impact institutions even when their publication volume is lower.
- Publication-weighted methodologies reward scale, favoring large research universities.
- Mid-tier institutions move around far more between methodologies than top-tier ones, which stay put.
- Subject-level strength often diverges from overall institutional strength.

## Notes on methodology

This platform uses ranking-inspired approximations built on publicly available data. It does not claim to replicate proprietary methodologies (ShanghaiRanking, QS, THE) exactly. The goal is transparency into how weighting choices drive outcomes, using documented indicators and open data.

## License

MIT — see [LICENSE](LICENSE).

## Author

Rafiul Alam Khan
[GitHub](https://github.com/rafi-khan-cmd) · [LinkedIn](https://www.linkedin.com/in/rafiul-alam-k-3a20392b0/) · alamkhanrafiul@gmail.com
