# Methodology Documentation

## Ranking Methodology Framework

The platform implements a flexible ranking framework that can simulate various ranking approaches.

## Core Indicators

### 1. Publication Score
- **Definition**: Normalized total publication count
- **Normalization**: Min-max scaling
- **Purpose**: Measures research output volume

### 2. Citation Score
- **Definition**: Normalized total citation count
- **Normalization**: Min-max scaling
- **Purpose**: Measures research impact

### 3. Collaboration Score
- **Definition**: International collaboration rate
- **Calculation**: Proportion of works with international co-authors
- **Purpose**: Measures global research connectivity

### 4. Quality Score
- **Definition**: High-impact research proxy
- **Calculation**: Top percentile citation performance
- **Purpose**: Measures research excellence

### 5. Subject Strength Score
- **Definition**: Subject-specific excellence metric
- **Calculation**: Weighted combination of quality and productivity
- **Purpose**: Measures domain expertise

### 6. Productivity Score
- **Definition**: Impact per publication efficiency
- **Calculation**: Weighted combination of output and impact
- **Purpose**: Measures research efficiency

## Normalization

All indicators are normalized using **min-max scaling** to ensure:
- Fair comparison across institutions
- Consistent scale (0-1 range)
- Handling of outliers

## Methodology Profiles

Five pre-configured methodologies demonstrate different ranking philosophies:

1. **Balanced Model**: Equal weighting
2. **Research Impact Model**: Citation and quality emphasis
3. **Publication Volume Model**: Output emphasis
4. **Collaboration-Forward Model**: Collaboration emphasis
5. **Subject Excellence Model**: Subject strength emphasis

## Weight Validation

Methodology weights must sum to 1.0 for accurate ranking computation. The simulator includes automatic normalization if weights don't sum correctly.

## Ranking Computation

Overall score = Σ (indicator_score × indicator_weight)

Rankings are computed by:
1. Fetching normalized metrics
2. Applying methodology weights
3. Computing weighted scores
4. Sorting and assigning ranks
