from __future__ import annotations

import numpy as np
import pandas as pd


# ============================================================================
# REGRESSION EVALUATION METRICS
# ============================================================================

def mae(y_true: pd.Series, y_pred: pd.Series) -> float:
    """
    Calculates Mean Absolute Error (MAE).
    
    MAE measures the average absolute difference between actual bookings (y_true)
    and predicted bookings (y_pred). 
    
    Interpretation: An MAE of 1.5 means predictions are off by 1.5 bookings on average.
    """
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    """
    Calculates Root Mean Squared Error (RMSE).
    
    RMSE squares errors before averaging, making it penalize large prediction errors 
    much more heavily than MAE.
    
    Interpretation: Useful for catching rare days where demand predictions are 
    drastically inaccurate.
    """
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


# ============================================================================
# MODEL EVALUATION & BENCHMARK COMPARISON
# ============================================================================

def evaluate(y_true: pd.Series, y_pred: pd.Series, model_name: str) -> dict:
    """
    Evaluates a model's prediction performance against actual ground-truth values.
    
    Returns a dictionary summarizing model performance metrics (MAE, RMSE, sample size).
    """
    return {
        "model": model_name,
        "mae": round(mae(y_true, y_pred), 3),
        "rmse": round(rmse(y_true, y_pred), 3),
        "n": len(y_true),
    }


def print_comparison(results: list[dict]) -> None:
    """
    Prints a formatted summary table comparing performance across multiple baseline 
    and trained ML models (e.g., Naive 7-day Average vs. XGBoost).
    
    Sorts models by MAE in ascending order and highlights the top performer.
    """
    # Convert list of metric dictionaries to DataFrame and rank by lowest MAE
    df = pd.DataFrame(results).sort_values("mae")
    
    # Print clean comparison matrix
    print("\nModel Performance Summary:")
    print(df.to_string(index=False))
    
    # Identify top-performing model
    best = df.iloc[0]
    print(f"\nBest Model by MAE: {best['model']} (MAE={best['mae']}, RMSE={best['rmse']})")