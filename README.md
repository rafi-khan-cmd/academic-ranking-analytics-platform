# Academic Rankings Intelligence Platform

**A Python, PostgreSQL, and Streamlit analytics platform for modeling, simulating, and explaining global university ranking methodologies across institutions, countries, and academic subjects.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)](https://www.postgresql.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 Project Overview

The Academic Rankings Intelligence Platform is a comprehensive analytics system that helps users understand how academic rankings can be constructed from measurable research indicators, how different weighting choices affect ranking outcomes, and how institutions compare across methodologies, countries, and academic subjects.

This project demonstrates deep understanding of:
- **Ranking Analytics**: Methodology design, indicator engineering, and normalization
- **Python Data Engineering**: End-to-end data pipelines, entity resolution, and data transformation
- **SQL Analytics**: Complex queries, views, and analytical database design
- **Dashboard Development**: Interactive visualizations and stakeholder-friendly interfaces
- **Advanced Analytics**: Feature importance, clustering, and sensitivity analysis

## 🚀 Why This Project Matters

Academic rankings influence institutional reputation, funding decisions, and student choices. However, ranking methodologies vary significantly, and small changes in indicator weights can dramatically alter outcomes. This platform provides transparency into ranking construction, enables methodology exploration, and reveals how different weighting schemes favor different institutional profiles.

**Key Value Propositions:**
- **Methodology Transparency**: Understand how indicator weights drive ranking outcomes
- **Institutional Insights**: Compare institutions across multiple ranking approaches
- **Sensitivity Analysis**: Identify which institutions are most affected by methodology changes
- **Research Profile Discovery**: Cluster institutions into distinct research archetypes

## 🎓 Role Alignment

This project directly aligns with analytics and dashboard development roles, particularly:

- **Data-Driven Decision Analytics**: Demonstrates ability to translate ambiguous methodology into measurable indicators
- **Python-Based Data Engineering**: End-to-end pipeline from raw data to analytical insights
- **SQL-Backed Analytics**: Complex database design and query optimization
- **Dashboard Development**: Professional, interactive analytics interfaces
- **Methodology Interpretation**: Ability to explain and simulate ranking logic

## 🏗️ Architecture

### High-Level Pipeline

```
External Data Sources (OpenAlex API)
    ↓
Data Ingestion (extract_data.py)
    ↓
Entity Resolution (resolve_entities.py)
    ↓
Indicator Engineering (build_indicators.py)
    ↓
Normalization (normalize_metrics.py)
    ↓
Ranking Methodology Engine (ranking_engine.py)
    ↓
PostgreSQL Analytics Database
    ↓
Streamlit Dashboard
    ↓
Public Deployment
```

### Technology Stack

**Core:**
- Python 3.8+
- pandas & numpy for data processing
- SQLAlchemy & psycopg2 for database operations
- PostgreSQL for analytical database
- Streamlit for interactive dashboard
- Plotly for visualizations

**Analytics:**
- scikit-learn for machine learning (clustering, feature importance)
- statsmodels for statistical analysis
- rapidfuzz for entity resolution

**Data Sources:**
- OpenAlex API for institution and publication data
- Public ranking tables for benchmarking

## 📊 Data Sources

### Primary Data Source: OpenAlex API (Real-Time)

The platform uses **real-time API calls** to the [OpenAlex API](https://openalex.org/) to fetch:
- Institution metadata (name, country, type, ROR IDs)
- Publication counts and citation data from `/works` endpoint
- Research works and authorship information
- Subject classifications via concepts/topics
- Yearly publication and citation trends

**API Endpoints Used:**
- `/institutions` - Institution discovery and metadata
- `/works` - Publication and citation data (most important endpoint)
- `/concepts` - Subject/topic classifications

### Secondary Data Source: ROR API (Entity Resolution)

The platform integrates with the [ROR API](https://ror.org/) for:
- Institution name standardization
- Canonical name resolution
- Entity disambiguation (e.g., MIT vs Massachusetts Institute of Technology)
- Enhanced metadata validation

**Why Real-Time APIs?**
- Always up-to-date data
- No manual dataset maintenance
- Scalable to any number of institutions
- Production-ready data pipeline

### Entity Resolution

Institution names are standardized using:
- **Canonical Name Mappings**: Pre-defined mappings for major institutions (MIT, Harvard, etc.)
- **Fuzzy Matching**: RapidFuzz for approximate string matching
- **Country Normalization**: pycountry for consistent country names

## 🔧 Indicator Engineering

The platform computes six core ranking indicators:

1. **Publication Score**: Normalized total publication count
2. **Citation Score**: Normalized total citation count
3. **Collaboration Score**: International collaboration rate
4. **Quality Score**: High-impact research proxy (top percentile citations)
5. **Subject Strength Score**: Subject-specific excellence metric
6. **Productivity Score**: Impact per publication efficiency metric

All indicators are normalized using **min-max scaling** to ensure fair comparison across institutions.

## 📈 Ranking Methodologies

The platform implements five distinct methodology profiles:

1. **Balanced Model**: Equal weighting across all indicators
2. **Research Impact Model**: Emphasizes citations and quality (35% citation, 25% quality)
3. **Publication Volume Model**: Prioritizes publication output (40% publication)
4. **Collaboration-Forward Model**: Emphasizes international collaboration (40% collaboration)
5. **Subject Excellence Model**: Prioritizes subject-specific strength (25% subject strength)

Each methodology is stored in the database and can be selected in the dashboard.

## 🎮 Methodology Simulator

The interactive simulator allows users to:
- Adjust indicator weights with real-time sliders
- Recalculate rankings instantly
- Compare before/after rankings
- Identify biggest winners and losers
- Filter by country and subject

This feature demonstrates the platform's core value: **transparency into how methodology choices affect outcomes**.

## 📱 Dashboard Pages

### 1. Executive Overview
- Top institutions across methodologies
- Country-level performance summaries
- KPI cards and key insights
- Methodology profile comparison

### 2. Global Rankings
- Sortable ranking tables
- Filters for methodology, country, year
- Score distributions and quartiles
- Methodology comparison tools

### 3. Institution Explorer
- Detailed institution profiles
- Indicator radar charts
- Rankings across methodologies
- Raw vs normalized metrics

### 4. Methodology Simulator
- Dynamic weight adjustment
- Live ranking recalculation
- Rank movement analysis
- Before/after comparisons

### 5. Subject Rankings
- Subject-specific rankings (when data available)
- Subject strength analysis
- Comparison with overall rankings

### 6. Indicator Analytics
- Correlation heatmaps
- Feature importance analysis
- Scatter plots and distributions
- Summary statistics

### 7. Research Clusters
- Institution clustering (KMeans)
- Cluster profiles and descriptions
- Country-level cluster distribution
- Institution cluster lookup

## 🔬 Advanced Analytics

### Feature Importance Analysis
Uses Random Forest regression to identify which indicators are most predictive of overall ranking scores. Reveals which factors drive ranking outcomes.

### Sensitivity/Volatility Analysis
Measures how much institutions move under different methodology assumptions. Identifies institutions that are:
- **Stable**: Rank consistently across methodologies
- **Volatile**: Rank changes significantly with methodology shifts

### Institution Clustering
Groups institutions into distinct research profiles:
- **High-Impact Elite**: Exceptional citation impact
- **High-Volume Output**: Large publication volume
- **Collaboration-Driven**: Strong international partnerships
- **Subject Specialist**: Subject-specific excellence

## 💾 Database Schema

The PostgreSQL database includes:

- **institutions**: Institution metadata and canonical names
- **subjects**: Academic subject classifications
- **raw_metrics**: Unnormalized indicator values
- **normalized_metrics**: Normalized indicator scores
- **methodology_weights**: Methodology weight definitions
- **ranking_results**: Computed rankings by methodology
- **institution_clusters**: Cluster assignments
- **sensitivity_results**: Volatility analysis results
- **country_summary**: Country-level aggregations

See `sql/schema.sql` for complete schema definition.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- pip or conda

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/academic-ranking-analytics-platform.git
cd academic-ranking-analytics-platform
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL database:**
```bash
# Create database
createdb academic_rankings

# Load schema
psql -d academic_rankings -f sql/schema.sql
psql -d academic_rankings -f sql/views.sql
```

5. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your database credentials and OpenAlex email
```

### Running the Data Pipeline

**Option 1: Run Complete Pipeline (Recommended)**

Run the entire pipeline with one command:

```bash
# Full pipeline with works data (takes 15-30 minutes)
python scripts/run_pipeline.py --institutions 200

# Faster: Skip works data (uses summary stats only)
python scripts/run_pipeline.py --institutions 200 --no-works

# Custom year
python scripts/run_pipeline.py --institutions 200 --year 2023
```

**Option 2: Run Steps Individually**

For more control, run each step:

1. **Extract institutions from OpenAlex API:**
```bash
python scripts/extract_data.py
```

2. **Clean data:**
```bash
python scripts/clean_data.py
```

3. **Resolve entities with ROR API:**
```bash
python scripts/resolve_entities.py
```

4. **Build indicators (requires works data):**
```bash
python scripts/build_indicators.py
```

5. **Normalize metrics:**
```bash
python scripts/normalize_metrics.py
```

6. **Load to database:**
```bash
python scripts/load_to_postgres.py
```

7. **Compute rankings:**
```bash
python scripts/ranking_engine.py
```

8. **Run advanced analytics:**
```bash
python scripts/advanced_analytics.py
```

**Note:** The pipeline fetches real-time data from OpenAlex and ROR APIs. Ensure you have internet connectivity and optionally set `OPENALEX_EMAIL` in `.env` for better rate limits.

### Running the Dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

## 📁 Repository Structure

```
academic-ranking-analytics-platform/
├── data/
│   ├── raw/              # Raw data from APIs
│   ├── processed/         # Processed and cleaned data
│   └── external/          # External reference data
├── notebooks/            # Jupyter notebooks for exploration
│   ├── 01_data_exploration.ipynb
│   ├── 02_entity_resolution.ipynb
│   ├── 03_indicator_engineering.ipynb
│   ├── 04_methodology_analysis.ipynb
│   └── 05_advanced_analytics.ipynb
├── scripts/               # Python scripts for data pipeline
│   ├── config.py          # Configuration and constants
│   ├── database.py        # Database utilities
│   ├── extract_data.py    # Data extraction
│   ├── resolve_entities.py # Entity resolution
│   ├── build_indicators.py # Indicator engineering
│   ├── normalize_metrics.py # Normalization
│   ├── load_to_postgres.py  # Database loading
│   ├── ranking_engine.py    # Ranking computation
│   ├── ranking_simulator.py # Dynamic simulation
│   └── advanced_analytics.py # ML and advanced analysis
├── sql/                   # SQL scripts
│   ├── schema.sql         # Database schema
│   ├── views.sql          # Analytical views
│   └── analytical_queries.sql # Example queries
├── dashboard/             # Streamlit dashboard
│   ├── app.py            # Main application
│   ├── pages/            # Dashboard pages
│   │   ├── executive_overview.py
│   │   ├── global_rankings.py
│   │   ├── institution_explorer.py
│   │   ├── methodology_simulator.py
│   │   ├── subject_rankings.py
│   │   ├── indicator_analytics.py
│   │   └── research_clusters.py
│   └── utils/            # Dashboard utilities
│       └── db_utils.py   # Database query functions
├── visuals/              # Screenshots and diagrams
│   ├── screenshots/
│   ├── diagrams/
│   └── gifs/
├── docs/                 # Documentation
│   ├── architecture.md
│   ├── methodology.md
│   └── data_dictionary.md
├── requirements.txt      # Python dependencies
├── .gitignore
└── README.md
```

## 🔍 Key Insights

The platform reveals several important patterns:

1. **Citation-Heavy Methodologies** favor institutions with high-impact research, even if publication volume is lower.

2. **Publication-Heavy Methodologies** reward scale over efficiency, benefiting large research universities.

3. **Subject-Level Excellence** differs significantly from overall institutional strength. Some institutions excel in specific domains.

4. **Mid-Tier Institutions** are more sensitive to methodology changes than top-tier institutions, which rank consistently across methodologies.

5. **Collaboration-Forward Models** elevate globally connected institutions with strong international partnerships.

## 🌐 Live Demo

[Link to deployed Streamlit app will be added here]

## 📸 Screenshots

### Executive Overview
![Executive Overview](visuals/screenshots/executive_overview.png)

### Methodology Simulator
![Methodology Simulator](visuals/screenshots/methodology_simulator.png)

### Institution Explorer
![Institution Explorer](visuals/screenshots/institution_explorer.png)

*Note: Screenshots will be added after deployment*

## 🔮 Future Improvements

- **Real-Time Data Updates**: Automated data refresh from OpenAlex API
- **Subject-Level Analysis**: Full subject-specific ranking implementation
- **Time-Series Analysis**: Multi-year trend analysis and ranking stability
- **Export Functionality**: PDF reports and CSV exports
- **User Authentication**: Save custom methodology profiles
- **API Endpoints**: REST API for programmatic access
- **Enhanced Visualizations**: 3D scatter plots, network graphs
- **Methodology Templates**: Pre-configured methodology profiles from real ranking systems

## 📝 Methodology Notes

This platform uses **ranking-inspired approximations** based on publicly available data. It does not claim to exactly replicate proprietary ranking methodologies (e.g., ShanghaiRanking, QS, THE). Instead, it:

- Uses publicly accessible research indicators
- Implements transparent, documented weighting schemes
- Provides methodology exploration tools
- Focuses on understanding ranking logic rather than exact replication

## 🤝 Contributing

This is a portfolio project, but suggestions and feedback are welcome!

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**Rafiul Alam Khan**

- Portfolio: [Your Portfolio URL]
- LinkedIn: [Your LinkedIn]
- Email: [Your Email]

## 🙏 Acknowledgments

- OpenAlex for providing open access to academic data
- Streamlit for the excellent dashboard framework
- The academic rankings research community for methodology insights

---

## 📋 Resume-Ready Summary

**Academic Rankings Intelligence Platform** - A comprehensive Python, PostgreSQL, and Streamlit analytics platform that models and simulates global university ranking methodologies. Built end-to-end data pipeline from OpenAlex API ingestion through entity resolution, indicator engineering, normalization, and ranking computation. Implemented 5 distinct methodology profiles with interactive simulator for dynamic weight exploration. Developed 7-page Streamlit dashboard with advanced analytics including feature importance analysis, KMeans clustering, and sensitivity/volatility analysis. Designed PostgreSQL analytical database with 9 tables and 8 views supporting complex ranking queries. Demonstrates strong Python data engineering, SQL analytics, dashboard development, and methodology interpretation skills.
