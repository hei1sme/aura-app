"""
Aura Predictor - ML Inference Module (Phase 3)

This module will contain the trained model for predicting optimal break times.
Currently a placeholder for Phase 3 implementation.

Future functionality:
- Load trained scikit-learn model
- Predict whether user will accept/dismiss break
- Optimize break timing based on predictions
"""

from typing import Optional, Dict, Any
import os
from pathlib import Path


class BreakPredictor:
    """
    Predicts optimal break timing using a trained ML model.
    
    Phase 1: Returns rule-based predictions (always suggest break)
    Phase 3: Will use trained Random Forest model
    """
    
    MODEL_FILENAME = "break_predictor.pkl"
    MIN_TRAINING_SAMPLES = 100
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the predictor.
        
        Args:
            model_path: Optional path to trained model file.
                       Defaults to ~/.aura/models/break_predictor.pkl
        """
        if model_path is None:
            model_dir = Path.home() / ".aura" / "models"
            model_dir.mkdir(parents=True, exist_ok=True)
            self.model_path = str(model_dir / self.MODEL_FILENAME)
        else:
            self.model_path = model_path
        
        self._model = None
        self._model_loaded = False
        self._load_model()
    
    def _load_model(self) -> bool:
        """
        Attempt to load a trained model.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        if not os.path.exists(self.model_path):
            return False
        
        try:
            import joblib
            self._model = joblib.load(self.model_path)
            self._model_loaded = True
            return True
        except Exception:
            self._model_loaded = False
            return False
    
    @property
    def is_model_available(self) -> bool:
        """Check if a trained model is available."""
        return self._model_loaded and self._model is not None
    
    def predict(
        self,
        mouse_velocity: float,
        keys_per_min: int,
        app_category: str,
        time_since_last_break: int,
        is_fullscreen: bool = False
    ) -> Dict[str, Any]:
        """
        Predict whether the user will accept a break.
        
        Args:
            mouse_velocity: Current mouse velocity
            keys_per_min: Current keystrokes per minute
            app_category: Category of active app
            time_since_last_break: Seconds since last break
            is_fullscreen: Whether in fullscreen mode
            
        Returns:
            Dictionary with:
            - should_show: Whether to show the break reminder
            - confidence: Prediction confidence (0-1)
            - reason: Human-readable reason
        """
        # Phase 1: Rule-based fallback
        if not self.is_model_available:
            return self._rule_based_prediction(
                mouse_velocity, keys_per_min, app_category,
                time_since_last_break, is_fullscreen
            )
        
        # Phase 3: ML-based prediction
        return self._ml_prediction(
            mouse_velocity, keys_per_min, app_category,
            time_since_last_break, is_fullscreen
        )
    
    def _rule_based_prediction(
        self,
        mouse_velocity: float,
        keys_per_min: int,
        app_category: str,
        time_since_last_break: int,
        is_fullscreen: bool
    ) -> Dict[str, Any]:
        """
        Simple rule-based prediction for Phase 1.
        """
        # Don't interrupt if in immersive mode
        if is_fullscreen:
            return {
                "should_show": False,
                "confidence": 0.9,
                "reason": "User is in fullscreen mode"
            }
        
        # Don't interrupt during gaming
        if app_category == "Game":
            return {
                "should_show": False,
                "confidence": 0.8,
                "reason": "User appears to be gaming"
            }
        
        # Low activity might mean user stepped away
        if mouse_velocity < 5 and keys_per_min < 5:
            return {
                "should_show": False,
                "confidence": 0.6,
                "reason": "Low activity detected"
            }
        
        # Default: show the break
        return {
            "should_show": True,
            "confidence": 0.7,
            "reason": "Time for a break (rule-based)"
        }
    
    def _ml_prediction(
        self,
        mouse_velocity: float,
        keys_per_min: int,
        app_category: str,
        time_since_last_break: int,
        is_fullscreen: bool
    ) -> Dict[str, Any]:
        """
        ML-based prediction using trained model.
        
        This will be fully implemented in Phase 3.
        """
        try:
            import numpy as np
            
            # Encode app category
            category_map = {
                "Code": 0, "Web": 1, "Video": 2, "Game": 3,
                "Productivity": 4, "Communication": 5, "Other": 6
            }
            cat_encoded = category_map.get(app_category, 6)
            
            # Create feature vector
            features = np.array([[
                mouse_velocity,
                keys_per_min,
                cat_encoded,
                time_since_last_break,
                int(is_fullscreen)
            ]])
            
            # Get prediction and probability
            prediction = self._model.predict(features)[0]
            probabilities = self._model.predict_proba(features)[0]
            confidence = max(probabilities)
            
            return {
                "should_show": bool(prediction == 1),
                "confidence": float(confidence),
                "reason": "ML model prediction"
            }
        except Exception as e:
            # Fallback to rules if ML fails
            return self._rule_based_prediction(
                mouse_velocity, keys_per_min, app_category,
                time_since_last_break, is_fullscreen
            )


def train_model(training_data_path: str, output_path: str) -> Dict[str, Any]:
    """
    Train a new break prediction model.
    
    This function will be called during Phase 3 development.
    
    Args:
        training_data_path: Path to training data CSV
        output_path: Path to save trained model
        
    Returns:
        Training results with accuracy metrics
    """
    try:
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder
        import joblib
        
        # Load data
        df = pd.read_csv(training_data_path)
        
        if len(df) < BreakPredictor.MIN_TRAINING_SAMPLES:
            return {
                "success": False,
                "error": f"Need at least {BreakPredictor.MIN_TRAINING_SAMPLES} samples"
            }
        
        # Encode app category
        le = LabelEncoder()
        df['app_category_encoded'] = le.fit_transform(df['app_category'])
        
        # Features and labels
        feature_cols = [
            'mouse_velocity', 'keys_per_min', 'app_category_encoded',
            'time_since_last_break', 'is_fullscreen'
        ]
        X = df[feature_cols].values
        y = df['user_response'].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        model.fit(X_train, y_train)
        
        # Evaluate
        train_acc = model.score(X_train, y_train)
        test_acc = model.score(X_test, y_test)
        
        # Save model
        joblib.dump(model, output_path)
        
        return {
            "success": True,
            "train_accuracy": train_acc,
            "test_accuracy": test_acc,
            "samples_used": len(df),
            "model_path": output_path
        }
    
    except ImportError as e:
        return {
            "success": False,
            "error": f"Missing dependency: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # Test the predictor
    predictor = BreakPredictor()
    
    print(f"Model available: {predictor.is_model_available}")
    
    result = predictor.predict(
        mouse_velocity=150.0,
        keys_per_min=45,
        app_category="Code",
        time_since_last_break=1800,
        is_fullscreen=False
    )
    
    print(f"Prediction: {result}")
