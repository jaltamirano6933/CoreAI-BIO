import os
import json
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
from datetime import datetime, timezone

class CultureOptimizerService:
    """
    Modular backend service for AI Culture Optimizer predictions.
    Loads joblib model and feature specification once upon initialization.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CultureOptimizerService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(self.base_dir, "models", "culture_optimizer_model.joblib")
        self.features_path = os.path.join(self.base_dir, "models", "culture_optimizer_features.json")
        self.metrics_path = os.path.join(self.base_dir, "models", "culture_optimizer_metrics.json")
        
        self.model = None
        self.features = []
        self.metrics = {}
        self.default_medians = {
            "Arginine": 0.6, "Glutamine": 2.0, "Histidine": 0.2, "Isoleucine": 0.4,
            "Leucine": 0.4, "Lysine": 0.4, "Methionine": 0.1, "Phenylalanine": 0.2,
            "Threonine": 0.4, "Tryptophane": 0.05, "Tyrosine": 0.2, "Valine": 0.4,
            "Cystine": 0.1, "Choline": 0.007, "Calcium pantothenate": 0.002,
            "Folic acid": 0.002, "Niacinamide": 0.008, "Pyridoxal": 0.005,
            "Riboflavin": 0.0003, "Thiamine": 0.003, "Inositol": 0.01, "CaCl2": 1.8,
            "MgSO4": 0.8, "KCl": 5.5, "NaHCO3": 26.0, "NaCl": 120.0, "NaH2PO4": 1.0,
            "Glucose": 5.6, "FBS": 0.05
        }
        
        # Initialize static result directories
        self.root_dir = os.path.dirname(self.base_dir)
        self.static_dirs = [
            os.path.join(self.root_dir, "static", "results", "culture_optimizer"),
            os.path.join(self.root_dir, "frontend", "static", "results", "culture_optimizer")
        ]
        for d in self.static_dirs:
            os.makedirs(d, exist_ok=True)

        self.load_artifacts()
        self._generate_trend_charts()

    def _generate_trend_charts(self):
        import matplotlib.pyplot as plt
        plt.style.use('dark_background')

        days = np.array([1, 2, 3, 4, 5, 6, 7])
        density = np.array([0.2, 0.35, 0.65, 1.25, 2.1, 3.4, 4.8])  # x10^5 cells/cm2
        confluency = np.array([15, 28, 52, 85, 92, 96, 99])         # %
        score = np.array([95, 93, 90, 88, 82, 75, 65])              # 0-100

        # Chart 1: Cell Density Over Time
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')
        ax.plot(days, density, marker='o', color='#38bdf8', linewidth=2.5, markersize=7)
        ax.set_title("Cell Density Over Time (10^5 cells/cm²)", fontsize=11, fontweight='bold', color='#ffffff', pad=10)
        ax.set_xlabel("Culture Age (Days)", fontsize=9, color='#cbd5e1')
        ax.set_ylabel("Density (x10^5 cells/cm²)", fontsize=9, color='#cbd5e1')
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)
        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "density_over_time.png"), dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()

        # Chart 2: Confluency Over Time
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')
        ax.plot(days, confluency, marker='s', color='#10b981', linewidth=2.5, markersize=7)
        ax.axhline(85, color='#f59e0b', linestyle='--', linewidth=1, label='Passage Threshold (85%)')
        ax.set_title("Confluency Over Time (%)", fontsize=11, fontweight='bold', color='#ffffff', pad=10)
        ax.set_xlabel("Culture Age (Days)", fontsize=9, color='#cbd5e1')
        ax.set_ylabel("Confluency (%)", fontsize=9, color='#cbd5e1')
        ax.legend(loc='lower right', fontsize=8)
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)
        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "confluency_over_time.png"), dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()

        # Chart 3: Culture Score Trend
        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')
        ax.plot(days, score, marker='^', color='#f59e0b', linewidth=2.5, markersize=7)
        ax.set_title("Overall Culture Score Trend (0-100)", fontsize=11, fontweight='bold', color='#ffffff', pad=10)
        ax.set_xlabel("Culture Age (Days)", fontsize=9, color='#cbd5e1')
        ax.set_ylabel("Culture Score", fontsize=9, color='#cbd5e1')
        ax.grid(True, color='#334155', linestyle=':', alpha=0.6)
        for s_dir in self.static_dirs:
            plt.savefig(os.path.join(s_dir, "culture_score_trend.png"), dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()

    def get_summary(self, custom_inputs=None):
        if custom_inputs and isinstance(custom_inputs, dict):
            try:
                confluency = float(custom_inputs.get("confluency", 85.0))
                cell_density_num = float(custom_inputs.get("cell_density", 1.25))
                passage_num = int(custom_inputs.get("passage_number", 4))
                temp = float(custom_inputs.get("incubator_temperature_c", 37.0))
                co2 = float(custom_inputs.get("co2_percent", 5.0))
                humidity = float(custom_inputs.get("relative_humidity_percent", 95.0))
                age_days = float(custom_inputs.get("culture_age_days", 4.0))
                data_source = str(custom_inputs.get("data_source", "manual")).strip()
            except (ValueError, TypeError):
                confluency, cell_density_num, passage_num, temp, co2, humidity, age_days, data_source = 85.0, 1.25, 4, 37.0, 5.0, 95.0, 4.0, "example"
        else:
            confluency, cell_density_num, passage_num, temp, co2, humidity, age_days, data_source = 85.0, 1.25, 4, 37.0, 5.0, 95.0, 4.0, "example"

        # Dynamic Culture Score Calculation
        score = 100
        if temp < 36.5 or temp > 37.5:
            score -= int(abs(temp - 37.0) * 15)
        if co2 < 4.5 or co2 > 5.5:
            score -= int(abs(co2 - 5.0) * 10)
        if humidity < 90.0:
            score -= int((90.0 - humidity) * 0.5)
        if confluency >= 85.0:
            score -= 12
        if confluency > 90.0:
            score -= int((confluency - 90.0) * 1.5)
        score = max(10, min(100, score))

        if score >= 80:
            growth_status = "Optimal Exponential Growth" if confluency < 85 else "Near Confluent (Passage Required)"
            risk_level = "Low"
        elif score >= 60:
            growth_status = "Sub-Optimal Growth"
            risk_level = "Moderate"
        else:
            growth_status = "Stressed / Inhibited Environment"
            risk_level = "High"

        culture_status = "Near Confluent" if confluency >= 85.0 else ("Optimal Growth" if confluency >= 40.0 else "Early Expansion")
        source_label = "Example Demonstration Dataset" if data_source == "example" else "Manual User Input"

        return {
            "status": "success",
            "data_source": data_source,
            "data_source_label": source_label,
            "culture_status": culture_status,
            "cell_density": f"{cell_density_num:.2f} x 10⁵ cells/cm²",
            "confluency": round(confluency, 1),
            "passage_number": f"P{passage_num}",
            "incubator_temperature_c": round(temp, 1),
            "co2_percent": round(co2, 1),
            "relative_humidity_percent": round(humidity, 1),
            "culture_age_days": round(age_days, 1),
            "quality_indicators": {
                "overall_culture_score": score,
                "growth_status": growth_status,
                "risk_level": risk_level
            },
            "figures": {
                "density_chart": "/static/results/culture_optimizer/density_over_time.png",
                "confluency_chart": "/static/results/culture_optimizer/confluency_over_time.png",
                "score_chart": "/static/results/culture_optimizer/culture_score_trend.png"
            },
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "limitation_notice": "This module provides research-oriented culture monitoring recommendations and is not intended to replace laboratory protocols or expert judgment."
        }

    def get_recommendations(self, custom_inputs=None):
        summary = self.get_summary(custom_inputs)
        conf = summary["confluency"]
        age = summary["culture_age_days"]
        temp = summary["incubator_temperature_c"]
        co2 = summary["co2_percent"]
        rh = summary["relative_humidity_percent"]

        recs = []

        # Rule 1: Passage Threshold
        if conf >= 85.0:
            recs.append({
                "rule_id": "R1_PASSAGE",
                "action": "Passage cells soon",
                "priority": "High",
                "category": "Subculture",
                "reason": f"Confluency has reached {conf}%, risk of contact inhibition and cell senescence."
            })

        # Rule 2: Medium Change
        if age >= 3 and conf < 90.0:
            recs.append({
                "rule_id": "R2_FEEDING",
                "action": "Change medium",
                "priority": "Medium",
                "category": "Feeding",
                "reason": f"Culture age is {age} days; nutrient replenishment recommended."
            })

        # Rule 3: Temperature Verification
        if temp < 36.5 or temp > 37.5:
            recs.append({
                "rule_id": "R3_TEMP",
                "action": "Verify incubator settings",
                "priority": "High",
                "category": "Incubator",
                "reason": f"Incubator temperature is {temp}°C (optimal: 37.0°C)."
            })
        else:
            recs.append({
                "rule_id": "R3_TEMP_OK",
                "action": "Maintain incubator settings",
                "priority": "Low",
                "category": "Incubator",
                "reason": f"Incubator temperature is optimal at {temp}°C."
            })

        # Rule 4: CO2 Gas Verification
        if co2 < 4.5 or co2 > 5.5:
            recs.append({
                "rule_id": "R4_CO2",
                "action": "Check CO2 cylinder & regulator",
                "priority": "High",
                "category": "Incubator",
                "reason": f"CO2 level is {co2}% (optimal: 5.0%)."
            })

        # Rule 5: Humidity Verification
        if rh < 90.0:
            recs.append({
                "rule_id": "R5_HUMIDITY",
                "action": "Replenish incubator water pan",
                "priority": "Medium",
                "category": "Incubator",
                "reason": f"Relative humidity is {rh}% (optimal: >= 90.0%)."
            })

        # Rule 6: General Monitoring
        recs.append({
            "rule_id": "R6_MONITOR",
            "action": "Increase monitoring frequency",
            "priority": "Low",
            "category": "Routine",
            "reason": "Routine protocol monitoring for active cultures."
        })

        return {
            "status": "success",
            "recommendations_count": len(recs),
            "recommendations": recs,
            "data_source_label": summary["data_source_label"],
            "timestamp": summary["timestamp"],
            "limitation_notice": summary["limitation_notice"]
        }

    def load_artifacts(self):
        if not os.path.exists(self.model_path):
            print(f"[Warning] Model file not found at: {self.model_path}")
            return False
            
        if not os.path.exists(self.features_path):
            print(f"[Warning] Features file not found at: {self.features_path}")
            return False
            
        try:
            self.model = joblib.load(self.model_path)
            with open(self.features_path, "r", encoding="utf-8") as f:
                self.features = json.load(f)
                
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path, "r", encoding="utf-8") as f:
                    self.metrics = json.load(f)
            return True
        except Exception as e:
            print(f"[Error] Failed to load culture optimizer model artifacts: {e}")
            return False

    def predict(self, input_data):
        if self.model is None or not self.features:
            success = self.load_artifacts()
            if not success or self.model is None:
                return {
                    "error": "Culture Optimizer model or feature specifications are not available on the server.",
                    "prediction_status": "error",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                }

        if not isinstance(input_data, dict):
            return {
                "error": "Input payload must be a valid JSON dictionary.",
                "prediction_status": "invalid_input",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }

        feature_vector = {}
        errors = []

        for feat in self.features:
            feat_clean = feat.strip()
            val = input_data.get(feat, input_data.get(feat_clean))
            
            if val is None:
                val = self.default_medians.get(feat_clean, 0.0)
            else:
                try:
                    val = float(val)
                    if val < 0:
                        errors.append(f"Component concentration for '{feat_clean}' cannot be negative.")
                except (ValueError, TypeError):
                    errors.append(f"Invalid numeric value '{val}' for component '{feat_clean}'.")
            
            feature_vector[feat] = val

        if errors:
            return {
                "error": "Input validation failed",
                "validation_details": errors,
                "prediction_status": "invalid_input",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }

        X_input = pd.DataFrame([feature_vector], columns=self.features)
        
        try:
            pred_value = float(self.model.predict(X_input)[0])
            pred_value = max(0.0, round(pred_value, 4))
            
            model_name = self.metrics.get("best_model", type(self.model).__name__)
            
            if pred_value >= 1.2:
                growth_category = "Optimal High Biomass Yield"
                rating_badge = "Excellent"
            elif pred_value >= 0.5:
                growth_category = "Moderate Cell Proliferation"
                rating_badge = "Good"
            else:
                growth_category = "Low Growth / Nutrient Stagnation"
                rating_badge = "Sub-optimal"

            from backend.explainability_service import explainability_service
            xai_data = explainability_service.explain_instance(X_input)

            response_payload = {
                "predicted_mean_A450_168h": pred_value,
                "prediction_status": "success",
                "growth_category": growth_category,
                "rating_badge": rating_badge,
                "model_name": model_name,
                "num_features_used": len(self.features),
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "top_positive_features": xai_data.get("top_positive_features", []),
                "top_negative_features": xai_data.get("top_negative_features", []),
                "shap_values": xai_data.get("shap_values", {}),
                "base_value": xai_data.get("base_value", 0.0),
                "prediction_explanation": xai_data.get("prediction_explanation", {})
            }
            return response_payload
        except Exception as e:
            return {
                "error": f"Internal prediction failure: {str(e)}",
                "prediction_status": "prediction_error",
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            }

culture_optimizer_service = CultureOptimizerService()
