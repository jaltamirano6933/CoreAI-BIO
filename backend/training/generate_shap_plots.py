import os
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap

def generate_shap_visualizations():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    excel_path = os.path.join(base_dir, "dataset", "culture_optimizer", "Data.xlsx")
    model_path = os.path.join(base_dir, "models", "culture_optimizer_model.joblib")
    features_path = os.path.join(base_dir, "models", "culture_optimizer_features.json")

    static_dirs = [
        os.path.join(base_dir, "static", "results", "culture_optimizer"),
        os.path.join(base_dir, "frontend", "static", "results", "culture_optimizer")
    ]

    for s_dir in static_dirs:
        os.makedirs(s_dir, exist_ok=True)

    print("Loading model and dataset for SHAP plots...")
    model = joblib.load(model_path)
    features = json.load(open(features_path))

    df = pd.read_excel(excel_path, sheet_name="time-saving")
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    X = df[features]

    # Initialize SHAP TreeExplainer
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X)

    # 1. SHAP Summary Plot (Beeswarm / Dot Plot)
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X, max_display=15, show=False)
    plt.title("SHAP Feature Attribution Summary (Global Drivers)", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()

    for s_dir in static_dirs:
        summary_plot_path = os.path.join(s_dir, "shap_summary.png")
        plt.savefig(summary_plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved SHAP summary plot to: {summary_plot_path}")
    plt.close()

    # 2. SHAP Waterfall Plot (Sample Prediction Decomposition)
    # Generate waterfall plot for median baseline sample (row 0 or sample instance)
    plt.figure(figsize=(10, 7))
    shap.plots.waterfall(shap_values[0], max_display=12, show=False)
    plt.title("SHAP Waterfall Plot (Sample Prediction Decomposition)", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()

    for s_dir in static_dirs:
        waterfall_plot_path = os.path.join(s_dir, "shap_waterfall.png")
        plt.savefig(waterfall_plot_path, dpi=300, bbox_inches="tight")
        print(f"Saved SHAP waterfall plot to: {waterfall_plot_path}")
    plt.close()

    print("SHAP visualizations generated successfully!")

if __name__ == "__main__":
    generate_shap_visualizations()
