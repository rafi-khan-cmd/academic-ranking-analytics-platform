"""
Normalization module for ranking indicators.
Implements min-max scaling and other normalization methods.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np

from scripts.config import PROCESSED_DATA_DIR, NORMALIZATION_METHOD

logger = logging.getLogger(__name__)


def min_max_normalize(series: pd.Series, feature_range: tuple = (0, 1)) -> pd.Series:
    """
    Min-max normalization: (x - min) / (max - min)
    
    Args:
        series: Input series to normalize
        feature_range: Target range (min, max)
    
    Returns:
        Normalized series
    """
    if series.empty:
        return series
    
    min_val = series.min()
    max_val = series.max()
    
    # Handle constant columns
    if max_val == min_val:
        return pd.Series([feature_range[0]] * len(series), index=series.index)
    
    normalized = (series - min_val) / (max_val - min_val)
    
    # Scale to feature range
    if feature_range != (0, 1):
        normalized = normalized * (feature_range[1] - feature_range[0]) + feature_range[0]
    
    return normalized


def z_score_normalize(series: pd.Series) -> pd.Series:
    """
    Z-score normalization: (x - mean) / std
    """
    if series.empty:
        return series
    
    mean_val = series.mean()
    std_val = series.std()
    
    # Handle constant columns
    if std_val == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    
    return (series - mean_val) / std_val


def robust_normalize(series: pd.Series) -> pd.Series:
    """
    Robust normalization using median and IQR (less sensitive to outliers).
    """
    if series.empty:
        return series
    
    median_val = series.median()
    q75 = series.quantile(0.75)
    q25 = series.quantile(0.25)
    iqr = q75 - q25
    
    # Handle constant columns
    if iqr == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    
    return (series - median_val) / iqr


def get_normalization_function(method: str) -> Callable:
    """Get normalization function by method name."""
    methods = {
        "min_max": min_max_normalize,
        "z_score": z_score_normalize,
        "robust": robust_normalize
    }
    return methods.get(method, min_max_normalize)


def normalize_indicators(indicators: List[Dict], method: str = NORMALIZATION_METHOD) -> List[Dict]:
    """
    Normalize all indicators for ranking computation.
    
    Args:
        indicators: List of indicator dictionaries
        method: Normalization method to use
    
    Returns:
        List of normalized indicator dictionaries
    """
    logger.info(f"Normalizing {len(indicators)} indicator records using {method} method...")
    
    if not indicators:
        return []
    
    # Convert to DataFrame for easier processing
    df = pd.DataFrame(indicators)
    
    # Define which columns to normalize
    indicator_columns = {
        "publication_count": "publication_score",
        "citation_count": "citation_score",
        "international_collaboration_rate": "collaboration_score",
        "quality_proxy": "quality_score",
        "productivity_proxy": "productivity_score"
    }
    
    # Get normalization function
    normalize_func = get_normalization_function(method)
    
    # Normalize each indicator
    normalized_df = df.copy()
    for raw_col, normalized_col in indicator_columns.items():
        if raw_col in df.columns:
            normalized_df[normalized_col] = normalize_func(df[raw_col])
        else:
            normalized_df[normalized_col] = 0.0
    
    # Handle subject strength score (if available)
    if "subject_strength_score" not in normalized_df.columns:
        # For now, use a combination of quality and productivity
        normalized_df["subject_strength_score"] = (
            normalized_df["quality_score"] * 0.6 + 
            normalized_df["productivity_score"] * 0.4
        )
    
    # Convert back to list of dictionaries
    normalized_indicators = normalized_df.to_dict('records')
    
    logger.info(f"Normalized {len(normalized_indicators)} records")
    
    return normalized_indicators


def save_normalized_metrics(normalized_indicators: List[Dict], 
                           filename: str = "metrics_normalized.json") -> None:
    """Save normalized metrics to JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(normalized_indicators, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(normalized_indicators)} normalized metric records to {filepath}")


def load_normalized_metrics(filename: str = "metrics_normalized.json") -> List[Dict]:
    """Load normalized metrics from JSON file."""
    filepath = PROCESSED_DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Normalized metrics file not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    from scripts.build_indicators import load_indicators
    raw_indicators = load_indicators()
    
    if raw_indicators:
        normalized = normalize_indicators(raw_indicators)
        save_normalized_metrics(normalized)
    else:
        logger.error("No raw indicators found. Run build_indicators.py first.")
