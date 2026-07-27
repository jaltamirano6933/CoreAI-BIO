import os
import json
import joblib
import pandas as pd
import numpy as np
import shap

class ExplainabilityService:
    """
    Modular service to generate Explainable AI (XAI) feature attributions
    using SHAP TreeExplainer for the AI Culture Optimizer model.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExplainabilityService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(self.base_dir, "models", "culture_optimizer_model.joblib")
        self.features_path = os.path.join(self.base_dir, "models", "culture_optimizer_features.json")
        
        self.model = None
        self.features = []
        self.explainer = None
        self.load_artifacts()

    def load_artifacts(self):
        if not os.path.exists(self.model_path) or not os.path.exists(self.features_path):
            return False

        try:
            self.model = joblib.load(self.model_path)
            with open(self.features_path, "r", encoding="utf-8") as f:
                self.features = json.load(f)

            # Initialize SHAP TreeExplainer for tree ensemble models
            self.explainer = shap.TreeExplainer(self.model)
            return True
        except Exception as e:
            print(f"[Error] Failed to initialize SHAP TreeExplainer: {e}")
            return False

    def explain_instance(self, X_input_df):
        if self.explainer is None:
            success = self.load_artifacts()
            if not success or self.explainer is None:
                return {
                    "top_positive_features": [],
                    "top_negative_features": [],
                    "shap_values": {},
                    "prediction_explanation": {
                        "top_positive_features": [],
                        "top_negative_features": []
                    }
                }

        try:
            # Calculate SHAP values for the single input row
            raw_shap = self.explainer.shap_values(X_input_df)
            if isinstance(raw_shap, list):
                raw_shap = raw_shap[0]
            if len(raw_shap.shape) > 1:
                raw_shap = raw_shap[0]

            # Base value / expected value E[f(X)]
            base_val = self.explainer.expected_value
            if isinstance(base_val, (np.ndarray, list)):
                base_val = float(base_val[0])
            else:
                base_val = float(base_val)

            # Map features to values
            shap_dict = {}
            positives = []
            negatives = []

            for feat, val in zip(self.features, raw_shap):
                feat_clean = feat.strip()
                val_float = round(float(val), 4)
                shap_dict[feat_clean] = val_float

                if val_float > 0:
                    positives.append({"feature": feat_clean, "impact": val_float})
                elif val_float < 0:
                    negatives.append({"feature": feat_clean, "impact": val_float})

            # Sort positives descending and negatives ascending
            positives.sort(key=lambda x: x["impact"], reverse=True)
            negatives.sort(key=lambda x: x["impact"])

            explanation_payload = {
                "top_positive_features": positives[:5],
                "top_negative_features": negatives[:5],
                "shap_values": shap_dict,
                "base_value": round(base_val, 4),
                "prediction_explanation": {
                    "top_positive_features": positives[:5],
                    "top_negative_features": negatives[:5]
                }
            }
            return explanation_payload
        except Exception as e:
            print(f"[Error] Error computing SHAP values: {e}")
            return {
                "top_positive_features": [],
                "top_negative_features": [],
                "shap_values": {},
                "prediction_explanation": {
                    "top_positive_features": [],
                    "top_negative_features": []
                }
            }

explainability_service = ExplainabilityService()
