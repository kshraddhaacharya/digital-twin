import math
from datetime import datetime, timezone
from typing import Dict, Any, List
import numpy as np
from sklearn.linear_model import Ridge
from sqlalchemy.orm import Session

from app.models.measurement import Measurement
from app.models.evaluation import ModelEvaluation


class EvaluationEngine:
    """
    Model Evaluation Engine performing strict chronological train/test validation
    comparing the Autoregressive Trend model against the Baseline Persistence model.
    """

    @classmethod
    def evaluate_models(
        cls,
        patient_id: str,
        db: Session,
        test_split_ratio: float = 0.20
    ) -> Dict[str, Any]:
        """
        Executes chronological out-of-sample evaluation on held-out test observations.
        Guarantees zero data leakage from future observations.
        """
        # 1. Fetch observations strictly ordered by timestamp
        measurements = db.query(Measurement).filter(
            Measurement.patient_id == patient_id,
            Measurement.measurement_type == "heart_rate"
        ).order_by(Measurement.timestamp.asc()).all()

        if len(measurements) < 16:
            raise ValueError(
                f"Insufficient data for chronological evaluation: Found {len(measurements)} observations, "
                f"minimum 16 required for train/test split."
            )

        total_count = len(measurements)
        test_count = max(4, int(total_count * test_split_ratio))
        train_count = total_count - test_count

        train_obs = measurements[:train_count]
        test_obs = measurements[train_count:]

        train_vals = np.array([float(m.value) for m in train_obs])
        test_vals = np.array([float(m.value) for m in test_obs])

        train_timestamps = [
            (m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp)
            for m in train_obs
        ]
        test_timestamps = [
            (m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp)
            for m in test_obs
        ]

        # 2. Evaluate Baseline Persistence Model
        # Baseline predicts the last observed training value across all test steps
        last_train_val = train_vals[-1]
        baseline_preds = np.full_like(test_vals, fill_value=last_train_val)

        base_mae = float(np.mean(np.abs(test_vals - baseline_preds)))
        base_rmse = float(np.sqrt(np.mean((test_vals - baseline_preds) ** 2)))

        # 3. Evaluate Autoregressive Trend Model
        t0 = train_timestamps[0]
        train_hours = np.array([(ts - t0).total_seconds() / 3600.0 for ts in train_timestamps])
        sin_train = np.sin(2 * np.pi * np.array([ts.hour + ts.minute / 60.0 for ts in train_timestamps]) / 24.0)
        cos_train = np.cos(2 * np.pi * np.array([ts.hour + ts.minute / 60.0 for ts in train_timestamps]) / 24.0)

        # Build feature matrix
        lags = 2
        X_train_list, y_train_list = [], []
        for i in range(lags, len(train_vals)):
            feats = [
                train_hours[i],
                sin_train[i],
                cos_train[i],
                train_vals[i - 1],
                train_vals[i - 2]
            ]
            X_train_list.append(feats)
            y_train_list.append(train_vals[i])

        ridge = Ridge(alpha=1.0)
        ridge.fit(np.array(X_train_list), np.array(y_train_list))

        # Iterative forecasting over the held-out test timestamps
        current_lags = [train_vals[-1], train_vals[-2]]
        model_preds: List[float] = []

        for ts in test_timestamps:
            fut_elapsed = (ts - t0).total_seconds() / 3600.0
            fut_hour = ts.hour + ts.minute / 60.0
            fut_sin = math.sin(2 * math.pi * fut_hour / 24.0)
            fut_cos = math.cos(2 * math.pi * fut_hour / 24.0)

            feats = np.array([[fut_elapsed, fut_sin, fut_cos, current_lags[0], current_lags[1]]])
            pred_v = float(ridge.predict(feats)[0])
            pred_v = max(40.0, min(180.0, pred_v))
            model_preds.append(pred_v)
            current_lags = [pred_v, current_lags[0]]

        model_preds_arr = np.array(model_preds)
        model_mae = float(np.mean(np.abs(test_vals - model_preds_arr)))
        model_rmse = float(np.sqrt(np.mean((test_vals - model_preds_arr) ** 2)))

        improvement = float(((base_mae - model_mae) / base_mae) * 100.0) if base_mae > 0 else 0.0

        eval_disclaimer = (
            "IMPORTANT NOTICE: Evaluation was performed on synthetic patient benchmark data using strict "
            "chronological train/test splitting. These metrics demonstrate the mathematical convergence "
            "of the autoregressive diurnal trend model on synthetic patterns, but DO NOT constitute clinical "
            "accuracy, clinical safety, or diagnostic reliability in real human patients."
        )

        eval_record = ModelEvaluation(
            patient_id=patient_id,
            model_name="AutoregressiveTrendModel vs BaselinePersistence",
            evaluation_period_start=test_timestamps[0],
            evaluation_period_end=test_timestamps[-1],
            train_samples=train_count,
            test_samples=test_count,
            mae=round(model_mae, 2),
            rmse=round(model_rmse, 2),
            baseline_mae=round(base_mae, 2),
            baseline_rmse=round(base_rmse, 2),
            is_synthetic_data=True,
            disclaimer=eval_disclaimer,
            created_at=datetime.now(timezone.utc)
        )

        db.add(eval_record)
        db.commit()
        db.refresh(eval_record)

        return {
            "patient_id": patient_id,
            "model_name": eval_record.model_name,
            "evaluation_period_start": eval_record.evaluation_period_start,
            "evaluation_period_end": eval_record.evaluation_period_end,
            "train_samples": eval_record.train_samples,
            "test_samples": eval_record.test_samples,
            "mae": eval_record.mae,
            "rmse": eval_record.rmse,
            "baseline_mae": eval_record.baseline_mae,
            "baseline_rmse": eval_record.baseline_rmse,
            "mae_improvement_pct": round(improvement, 1),
            "is_synthetic_data": True,
            "disclaimer": eval_disclaimer,
            "created_at": eval_record.created_at
        }

