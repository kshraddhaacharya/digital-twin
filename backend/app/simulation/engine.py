import math
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import numpy as np
from sqlalchemy.orm import Session

from app.models.twin_state import TwinState
from app.models.scenario import Scenario
from app.forecasting.engine import ForecastingEngine


class SimulationEngine:
    """
    Scenario Simulation Engine comparing Scenario A (Current Baseline Trajectory)
    and Scenario B (Hypothetical Altered Condition) rooted in identical active twin states.
    """

    @classmethod
    def run_simulation(
        cls,
        patient_id: str,
        db: Session,
        horizon_minutes: int = 120,
        parameter_name: str = "activity_exertion_factor",
        parameter_value: float = -25.0,
        parameter_unit: str = "%"
    ) -> Dict[str, Any]:
        """
        Executes counterfactual simulation from the active twin state.
        Produces two distinct, reproducible trajectories with identical starting state,
        transparent mathematical formulation, and prominent clinical non-efficacy disclaimers.
        """
        # 1. Fetch current active twin state
        active_state = db.query(TwinState).filter(
            TwinState.patient_id == patient_id,
            TwinState.is_active_version == True
        ).first()

        if not active_state:
            raise ValueError(f"No active digital twin state for patient '{patient_id}'. Please initialize the twin first.")

        # 2. Generate baseline forecast (Scenario A)
        baseline_forecast = ForecastingEngine.generate_forecast(
            patient_id=patient_id,
            db=db,
            horizon_minutes=horizon_minutes,
            model_type="autoregressive_trend"
        )

        base_trajectory = baseline_forecast.predicted_trajectory
        initial_val = active_state.latest_heart_rate

        # 3. Compute Scenario B (Hypothetical Condition)
        # Mathematical rule:
        # Delta from origin: delta_A(k) = y_A(k) - y_0
        # Asymptotic kinetic transition: gamma(k) = 1 - exp(-(k + 1) / tau), with tau = 4 intervals (60 min)
        # Altered delta: delta_B(k) = delta_A(k) * (1 + (param / 100) * gamma(k))
        # Direct baseline shift: shift_B(k) = (param / 100) * offset_scale * gamma(k)
        simulated_b_points: List[Dict[str, Any]] = []
        differences: List[float] = []

        math_rule_doc = (
            f"y_B(t_k) = y_0 + [y_A(t_k) - y_0] * (1.0 + ({parameter_value:.1f} / 100.0) * gamma(t_k)) "
            f"+ ({parameter_value:.1f} / 100.0) * 4.0 * gamma(t_k), "
            f"where gamma(t_k) = 1.0 - exp(-(k + 1) / 4.0) models asymptotic rate-of-change kinetics."
        )

        assumptions_doc = (
            "1. Assumes steady physiological adaptation under stated activity/rest condition without sudden acute stress. "
            "2. Assumes constant ambient environmental and hydration baseline. "
            "3. Assumes hypothetical input change applies proportionally to modeled rate of change."
        )

        limitations_doc = (
            "CRITICAL DISCLAIMER & CLINICAL NOTICE: This alternative is a transparent mathematical simulation of activity "
            "or resting assumptions. It does NOT simulate the pharmacological or therapeutic effects of any medication, "
            "does NOT provide a clinical diagnosis, and must NEVER replace clinician evaluation or urgent medical care."
        )

        for k, pt in enumerate(base_trajectory):
            y_a = float(pt["predicted_value"])
            delta_a = y_a - initial_val
            
            # Asymptotic transition kinetics (tau = 4 intervals = 1 hour)
            gamma = 1.0 - math.exp(-(k + 1) / 4.0)
            adjusted_delta = delta_a * (1.0 + (parameter_value / 100.0) * gamma)
            
            # Direct target offset
            offset_effect = (parameter_value / 100.0) * 4.0 * gamma
            y_b = round(initial_val + adjusted_delta + offset_effect, 2)
            
            # Physiological clamp for resting/active bounds [35.0, 180.0] bpm
            y_b = max(35.0, min(180.0, y_b))

            simulated_b_points.append({
                "timestamp": pt["timestamp"],
                "simulated_value": y_b
            })
            differences.append(abs(y_b - y_a))

        simulated_a_points = [
            {"timestamp": pt["timestamp"], "simulated_value": pt["predicted_value"]}
            for pt in base_trajectory
        ]

        # 4. Create and persist scenario records
        scenario_a_id = f"scen-a-{uuid.uuid4().hex[:8]}"
        scenario_b_id = f"scen-b-{uuid.uuid4().hex[:8]}"

        record_a = Scenario(
            id=scenario_a_id,
            patient_id=patient_id,
            baseline_state_version=active_state.state_version,
            scenario_type="Scenario_A_Current_Trajectory",
            parameter_name="baseline_projection",
            parameter_value=0.0,
            parameter_unit="none",
            mathematical_rule="Autoregressive diurnal trend forward projection from active twin state.",
            assumptions="Continuation of current physiological baseline and circadian rhythm.",
            limitations="Educational short-term forecast. Does not anticipate unobserved clinical acute events.",
            simulated_trajectory=simulated_a_points,
            created_at=datetime.now(timezone.utc)
        )

        record_b = Scenario(
            id=scenario_b_id,
            patient_id=patient_id,
            baseline_state_version=active_state.state_version,
            scenario_type="Scenario_B_Hypothetical_Condition",
            parameter_name=parameter_name,
            parameter_value=parameter_value,
            parameter_unit=parameter_unit,
            mathematical_rule=math_rule_doc,
            assumptions=assumptions_doc,
            limitations=limitations_doc,
            simulated_trajectory=simulated_b_points,
            created_at=datetime.now(timezone.utc)
        )

        db.add(record_a)
        db.add(record_b)
        db.commit()

        delta_summary = {
            "max_absolute_delta_bpm": round(float(np.max(differences)), 2) if differences else 0.0,
            "mean_absolute_delta_bpm": round(float(np.mean(differences)), 2) if differences else 0.0,
            "endpoint_delta_bpm": round(abs(simulated_b_points[-1]["simulated_value"] - simulated_a_points[-1]["simulated_value"]), 2) if differences else 0.0,
            "horizon_hours": round(horizon_minutes / 60.0, 1),
            "step_count": len(simulated_b_points)
        }

        return {
            "patient_id": patient_id,
            "baseline_state_version": active_state.state_version,
            "scenario_a": {
                "id": record_a.id,
                "patient_id": patient_id,
                "baseline_state_version": record_a.baseline_state_version,
                "scenario_type": record_a.scenario_type,
                "parameter_name": record_a.parameter_name,
                "parameter_value": record_a.parameter_value,
                "parameter_unit": record_a.parameter_unit,
                "mathematical_rule": record_a.mathematical_rule,
                "assumptions": record_a.assumptions,
                "limitations": record_a.limitations,
                "simulated_trajectory": record_a.simulated_trajectory,
                "created_at": record_a.created_at
            },
            "scenario_b": {
                "id": record_b.id,
                "patient_id": patient_id,
                "baseline_state_version": record_b.baseline_state_version,
                "scenario_type": record_b.scenario_type,
                "parameter_name": record_b.parameter_name,
                "parameter_value": record_b.parameter_value,
                "parameter_unit": record_b.parameter_unit,
                "mathematical_rule": record_b.mathematical_rule,
                "assumptions": record_b.assumptions,
                "limitations": record_b.limitations,
                "simulated_trajectory": record_b.simulated_trajectory,
                "created_at": record_b.created_at
            },
            "delta_summary": delta_summary,
            "disclaimer": limitations_doc
        }

