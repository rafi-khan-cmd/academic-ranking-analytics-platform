# Architecture Documentation

## System Architecture

The Academic Rankings Intelligence Platform follows a modular, pipeline-based architecture designed for scalability and maintainability.

## Components

### 1. Data Ingestion Layer
- **extract_data.py**: Fetches data from OpenAlex API
- Handles rate limiting and error recovery
- Stores raw data in JSON format

### 2. Data Processing Layer
- **resolve_entities.py**: Institution name standardization
- **build_indicators.py**: Indicator computation
- **normalize_metrics.py**: Normalization and scaling

### 3. Ranking Engine
- **ranking_engine.py**: Core ranking computation
- **ranking_simulator.py**: Dynamic methodology simulation
- Supports multiple methodology profiles

### 4. Database Layer
- PostgreSQL analytical database
- Normalized schema with 9 core tables
- 8 analytical views for dashboard access

### 5. Dashboard Layer
- Streamlit-based interactive dashboard
- 7 distinct pages for different analyses
- Real-time computation for simulator

### 6. Advanced Analytics
- **advanced_analytics.py**: ML and statistical analysis
- Feature importance, clustering, sensitivity

## Data Flow

```
API → Raw Data → Entity Resolution → Indicators → Normalization → Rankings → Database → Dashboard
```

## Technology Choices

- **Python**: Primary language for data processing
- **PostgreSQL**: Analytical database for complex queries
- **Streamlit**: Rapid dashboard development
- **Plotly**: Interactive visualizations
- **scikit-learn**: Machine learning components

## Scalability Considerations

- Modular script design allows parallel processing
- Database indexing for query performance
- Caching strategies for dashboard queries
- Batch processing for large datasets
