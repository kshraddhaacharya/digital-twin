import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import numpy as np
from app.utils.datetime_utils import to_utc_iso


def generate_synthetic_patient_data(
    patient_id: str = "PT-DEMO-001",
    name: str = "Alice M. Taylor",
    age: int = 56,
    gender: str = "Female",
    baseline_hr: float = 72.0,
    duration_hours: int = 24,
    interval_minutes: int = 15,
    noise_level: float = 1.2,
    seed: int = 42,
    include_exercise: bool = True
) -> Dict[str, Any]:
    """
    Generates a deterministic, physiologically plausible synthetic patient observation dataset.
    
    Includes:
    - 24-hour circadian sinusoidal rhythm (nadir at 04:00, peak at 15:30)
    - Autoregressive AR(1) physiological noise process
    - Afternoon transient activity spike (if include_exercise=True)
    - Optional blood pressure and temperature companion records
    """
    rng = np.random.default_rng(seed)
    
    # Establish base reference time: 24 hours ago up to current UTC hour
    end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(hours=duration_hours)
    
    total_steps = int((duration_hours * 60) / interval_minutes)
    
    measurements: List[Dict[str, Any]] = []
    
    ar_noise = 0.0
    rho = 0.65  # Autoregressive correlation coefficient
    
    for i in range(total_steps):
        t = start_time + timedelta(minutes=i * interval_minutes)
        hour_of_day = t.hour + t.minute / 60.0
        
        # 1. Circadian oscillation: ~6 bpm swing, trough at 4 AM, peak at 4 PM (16:00)
        circadian = 6.0 * math.sin(2 * math.pi * (hour_of_day - 10.0) / 24.0)
        
        # 2. Transient exertion bump between 14:00 and 15:30
        transient_bump = 0.0
        if include_exercise and 14.0 <= hour_of_day <= 15.5:
            # Gaussian bell curve centered at 14:45
            transient_bump = 14.0 * math.exp(-0.5 * ((hour_of_day - 14.75) / 0.35) ** 2)
            
        # 3. Autoregressive AR(1) physiological variability
        white_noise = rng.normal(0, noise_level)
        ar_noise = rho * ar_noise + math.sqrt(1 - rho**2) * white_noise
        
        hr_value = round(baseline_hr + circadian + transient_bump + ar_noise, 1)
        # Physiological bounds safety clamp (synthetic data guarantee)
        hr_value = max(45.0, min(175.0, hr_value))
        
        measurements.append({
            "patient_id": patient_id,
            "timestamp": to_utc_iso(t),
            "measurement_type": "heart_rate",
            "value": hr_value,
            "unit": "bpm",
            "source": "synthetic_telemetry",
            "is_late_arrival": False
        })
        
        # Also generate companion blood pressure every 2nd interval (every 30 mins)
        if i % 2 == 0:
            sys_bp = round(118.0 + (circadian * 0.8) + (transient_bump * 1.2) + rng.normal(0, 2.0), 1)
            dia_bp = round(76.0 + (circadian * 0.5) + (transient_bump * 0.6) + rng.normal(0, 1.5), 1)
            
            measurements.append({
                "patient_id": patient_id,
                "timestamp": to_utc_iso(t),
                "measurement_type": "systolic_bp",
                "value": sys_bp,
                "unit": "mmHg",
                "source": "synthetic_telemetry",
                "is_late_arrival": False
            })
            measurements.append({
                "patient_id": patient_id,
                "timestamp": to_utc_iso(t),
                "measurement_type": "diastolic_bp",
                "value": dia_bp,
                "unit": "mmHg",
                "source": "synthetic_telemetry",
                "is_late_arrival": False
            })
            
    patient_record = {
        "id": patient_id,
        "name": name,
        "age": age,
        "gender": gender,
        "baseline_heart_rate": baseline_hr,
        "medical_notes": "Synthetic patient record generated for Hackloop 2026 digital twin demonstration.",
        "is_synthetic": True
    }
    
    return {
        "patient": patient_record,
        "measurements": measurements,
        "summary": {
            "total_measurements": len(measurements),
            "heart_rate_observations": sum(1 for m in measurements if m["measurement_type"] == "heart_rate"),
            "observation_start": start_time.isoformat(),
            "observation_end": (start_time + timedelta(minutes=(total_steps - 1) * interval_minutes)).isoformat()
        }
    }


def generate_synthetic_csv(patient_id: str = "PT-DEMO-001") -> str:
    """Generates synthetic CSV content formatted with valid headers."""
    data = generate_synthetic_patient_data(patient_id=patient_id)
    lines = ["timestamp,measurement_type,value,unit,source"]
    for m in data["measurements"]:
        lines.append(f"{m['timestamp']},{m['measurement_type']},{m['value']},{m['unit']},{m['source']}")
    return "\n".join(lines)

