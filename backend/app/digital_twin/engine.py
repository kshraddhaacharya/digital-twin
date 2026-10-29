from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from sqlalchemy.orm import Session

from app.models.measurement import Measurement
from app.models.patient import Patient
from app.models.twin_state import TwinState
from app.models.forecast import Forecast
from app.web3.service import Web3Service
from app.services.clinical_metrics import classify_vital_status


class DigitalTwinEngine:
    """
    Core Digital Twin Engine maintaining, updating, and versioning a patient's
    dynamic physiological modeled state with transparent provenance and Web3 anchoring.
    """

    @staticmethod
    def compute_state_features(
        measurements: List[Measurement],
        baseline_hr: float = 70.0,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculates inferred physiological features from chronologically sorted observations.
        Keeps raw latest observations distinct from derived state metrics.
        """
        if not measurements:
            raise ValueError("Cannot compute digital twin state without at least one observation.")

        # Ensure sorted by timestamp
        sorted_m = sorted(measurements, key=lambda m: m.timestamp)
        latest_m = sorted_m[-1]
        
        latest_val = float(latest_m.value)
        latest_ts = latest_m.timestamp
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.replace(tzinfo=timezone.utc)
        else:
            latest_ts = latest_ts.astimezone(timezone.utc)
            
        now_utc = current_time or datetime.now(timezone.utc)
        freshness_seconds = max(0.0, (now_utc - latest_ts).total_seconds())

        # Determine context of latest observation
        latest_context = getattr(latest_m, "context", "resting") or "resting"

        # Filter observations from the last 60 minutes relative to the latest observation
        cutoff_60m = latest_ts - timedelta(minutes=60)
        recent_60m = [
            m for m in sorted_m
            if (m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp) >= cutoff_60m
        ]
        
        # If fewer than 3 observations in the 60m window, use last 4 observations as fallback
        if len(recent_60m) < 3 and len(sorted_m) >= 3:
            recent_eval = sorted_m[-4:]
        else:
            recent_eval = recent_60m if recent_60m else sorted_m

        recent_vals = [float(m.value) for m in recent_eval]
        rolling_mean = float(np.mean(recent_vals))
        rolling_std = float(np.std(recent_vals, ddof=1)) if len(recent_vals) > 1 else 0.0

        # Calculate slope (rate of change per hour) over recent window (up to 3 hours)
        cutoff_trend = latest_ts - timedelta(hours=3)
        trend_obs = [
            m for m in sorted_m
            if (m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp) >= cutoff_trend
        ]
        if len(trend_obs) < 2:
            trend_obs = sorted_m[-3:] if len(sorted_m) >= 2 else sorted_m

        trend_slope_per_hour = 0.0
        if len(trend_obs) >= 2:
            t0 = trend_obs[0].timestamp.replace(tzinfo=timezone.utc) if trend_obs[0].timestamp.tzinfo is None else trend_obs[0].timestamp
            time_hours = np.array([
                ((m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp) - t0).total_seconds() / 3600.0
                for m in trend_obs
            ])
            vals = np.array([float(m.value) for m in trend_obs])
            
            time_span = time_hours[-1] - time_hours[0]
            if time_span > 0.01:
                p = np.polyfit(time_hours, vals, deg=1)
                trend_slope_per_hour = float(p[0])

        # Variability index (CV = std / mean * 100)
        variability_idx = float((rolling_std / rolling_mean) * 100.0) if rolling_mean > 0 else 0.0

        # Circadian phase estimate (expected diurnal offset from baseline at this hour)
        hour_of_day = latest_ts.hour + latest_ts.minute / 60.0
        circadian_offset = float(6.0 * np.sin(2 * np.pi * (hour_of_day - 10.0) / 24.0))

        # Context-aware clinical status classification
        classification = classify_vital_status(latest_val, context=latest_context)
        vital_status = classification["status"]

        # Assess data quality status
        data_quality_status = "good"
        if len(sorted_m) < 6:
            data_quality_status = "insufficient_history"
        elif freshness_seconds > 86400 * 2:  # > 48 hours
            data_quality_status = "stale_data"
        elif len(sorted_m) >= 4:
            ts_list = [
                (m.timestamp.replace(tzinfo=timezone.utc) if m.timestamp.tzinfo is None else m.timestamp)
                for m in sorted_m
            ]
            diffs = [(ts_list[i] - ts_list[i - 1]).total_seconds() / 60.0 for i in range(1, len(ts_list))]
            med_diff = float(np.median(diffs))
            if med_diff > 0 and max(diffs) > (med_diff * 4.0):
                data_quality_status = "irregular_intervals"

        return {
            "latest_heart_rate": round(latest_val, 2),
            "measurement_context": latest_context,
            "timestamp_latest_observation": latest_ts,
            "last_processed_measurement_id": latest_m.id,
            "rolling_mean_60m": round(rolling_mean, 2),
            "rolling_std_60m": round(rolling_std, 2),
            "trend_slope_per_hour": round(trend_slope_per_hour, 2),
            "circadian_phase_estimate": round(circadian_offset, 2),
            "physiological_variability_index": round(variability_idx, 2),
            "vital_status": vital_status,
            "data_quality_status": data_quality_status,
            "data_freshness_seconds": round(freshness_seconds, 1),
            "model_version": "1.0.0"
        }

    @classmethod
    def initialize_twin(cls, patient_id: str, db: Session) -> TwinState:
        """
        Initializes or resets the digital twin from stored historical observations.
        Creates TwinState Version 1 and anchors on-chain.
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        # Fetch all heart rate observations
        hr_measurements = db.query(Measurement).filter(
            Measurement.patient_id == patient_id,
            Measurement.measurement_type == "heart_rate"
        ).order_by(Measurement.timestamp.asc()).all()

        if not hr_measurements:
            raise ValueError(f"Cannot initialize digital twin for patient '{patient_id}': No heart rate observations found.")

        # Deactivate any previous twin states for this patient
        db.query(TwinState).filter(TwinState.patient_id == patient_id).update({"is_active_version": False})

        features = cls.compute_state_features(hr_measurements, baseline_hr=patient.baseline_heart_rate)

        # On-Chain Web3 State Attestation
        web3_meta = {}
        try:
            w3_service = Web3Service.get_instance()
            att = w3_service.attest_twin_state(
                patient_id=patient_id,
                version=1,
                timestamp=features["timestamp_latest_observation"],
                latest_hr=features["latest_heart_rate"],
                rolling_mean=features["rolling_mean_60m"],
                features=features,
                model_version=features["model_version"],
                data_quality_status=features["data_quality_status"],
                previous_state_hash=None
            )
            web3_meta = {
                "attestation_status": att.get("attestation_status", "PENDING"),
                "on_chain_tx_hash": att.get("on_chain_tx_hash"),
                "on_chain_block_number": att.get("on_chain_block_number"),
                "state_hash_sha256": att.get("state_hash_sha256"),
                "ipfs_cid": att.get("ipfs_cid"),
                "contract_address": att.get("contract_address"),
            }
        except Exception as e:
            print(f"[Web3] State attestation skipped: {e}")
            web3_meta = {
                "attestation_status": "UNAVAILABLE",
                "state_hash_sha256": Web3Service.calculate_state_hash(
                    patient_id=patient_id,
                    version=1,
                    timestamp=features["timestamp_latest_observation"],
                    features=features,
                    model_version=features["model_version"],
                    data_quality_status=features["data_quality_status"]
                )
            }

        new_state = TwinState(
            patient_id=patient_id,
            state_version=1,
            is_active_version=True,
            previous_state_hash=None,
            **features,
            **web3_meta
        )

        db.add(new_state)
        # Invalidate any old forecasts
        cls.invalidate_stale_forecasts(patient_id=patient_id, current_state_version=1, db=db)
        db.commit()
        db.refresh(new_state)
        return new_state

    @classmethod
    def update_twin_with_measurement(
        cls,
        patient_id: str,
        measurement: Measurement,
        db: Session
    ) -> Tuple[TwinState, int]:
        """
        Transactional update of the digital twin when a new valid measurement is accepted.
        Increments the state version (v -> v + 1), computes fresh features, marks older forecasts stale.
        Returns (new_twin_state, count_of_invalidated_forecasts).
        """
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        # Get current active state version
        current_state = db.query(TwinState).filter(
            TwinState.patient_id == patient_id,
            TwinState.is_active_version == True
        ).first()

        next_version = (current_state.state_version + 1) if current_state else 1
        prev_hash = current_state.state_hash_sha256 if current_state else None

        # Query all heart rate measurements to compute fresh features
        hr_measurements = db.query(Measurement).filter(
            Measurement.patient_id == patient_id,
            Measurement.measurement_type == "heart_rate"
        ).order_by(Measurement.timestamp.asc()).all()

        features = cls.compute_state_features(hr_measurements, baseline_hr=patient.baseline_heart_rate)

        # On-Chain Web3 State Attestation
        web3_meta = {}
        try:
            w3_service = Web3Service.get_instance()
            att = w3_service.attest_twin_state(
                patient_id=patient_id,
                version=next_version,
                timestamp=features["timestamp_latest_observation"],
                latest_hr=features["latest_heart_rate"],
                rolling_mean=features["rolling_mean_60m"],
                features=features,
                model_version=features["model_version"],
                data_quality_status=features["data_quality_status"],
                previous_state_hash=prev_hash
            )
            web3_meta = {
                "attestation_status": att.get("attestation_status", "PENDING"),
                "on_chain_tx_hash": att.get("on_chain_tx_hash"),
                "on_chain_block_number": att.get("on_chain_block_number"),
                "state_hash_sha256": att.get("state_hash_sha256"),
                "ipfs_cid": att.get("ipfs_cid"),
                "contract_address": att.get("contract_address"),
            }
        except Exception as e:
            print(f"[Web3] State attestation skipped: {e}")
            web3_meta = {
                "attestation_status": "UNAVAILABLE",
                "state_hash_sha256": Web3Service.calculate_state_hash(
                    patient_id=patient_id,
                    version=next_version,
                    timestamp=features["timestamp_latest_observation"],
                    features=features,
                    model_version=features["model_version"],
                    data_quality_status=features["data_quality_status"],
                    previous_state_hash=prev_hash
                )
            }

        # Deactivate previous active states
        db.query(TwinState).filter(
            TwinState.patient_id == patient_id,
            TwinState.is_active_version == True
        ).update({"is_active_version": False})

        new_state = TwinState(
            patient_id=patient_id,
            state_version=next_version,
            is_active_version=True,
            previous_state_hash=prev_hash,
            **features,
            **web3_meta
        )
        db.add(new_state)

        # Invalidate forecasts produced under older state versions
        stale_count = cls.invalidate_stale_forecasts(patient_id, next_version, db)

        db.commit()
        db.refresh(new_state)
        return new_state, stale_count

    @classmethod
    def invalidate_stale_forecasts(
        cls,
        patient_id: str,
        current_state_version: int,
        db: Session
    ) -> int:
        """
        Marks any forecasts generated from earlier twin state versions as stale.
        Preserves historical forecasts in the database for auditing and comparison.
        """
        stale_forecasts = db.query(Forecast).filter(
            Forecast.patient_id == patient_id,
            Forecast.twin_state_version < current_state_version,
            Forecast.is_stale == False
        ).all()

        count = len(stale_forecasts)
        for f in stale_forecasts:
            f.is_stale = True
            f.stale_reason = (
                f"Twin state evolved to Version {current_state_version}. "
                f"This forecast was generated from State Version {f.twin_state_version} "
                f"at {f.last_observation_timestamp.isoformat()}."
            )

        if count > 0:
            db.commit()

        return count

    @classmethod
    def get_active_twin_state(cls, patient_id: str, db: Session) -> Optional[TwinState]:
        """Retrieves the active twin state snapshot for a patient, updating freshness."""
        state = db.query(TwinState).filter(
            TwinState.patient_id == patient_id,
            TwinState.is_active_version == True
        ).first()

        if state and state.timestamp_latest_observation:
            latest_ts = state.timestamp_latest_observation
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            freshness = max(0.0, (datetime.now(timezone.utc) - latest_ts).total_seconds())
            state.data_freshness_seconds = round(freshness, 1)

        return state

