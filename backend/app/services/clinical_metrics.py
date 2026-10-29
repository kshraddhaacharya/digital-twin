from typing import Optional, Tuple, Dict, Any

def calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
    """
    Computes Body Mass Index (BMI) from valid height and weight.
    Labels BMI as a statistical screening indicator, NOT as a clinical diagnosis.
    Returns (bmi_value, category_label).
    """
    if height_cm is None or weight_kg is None:
        return None, None
    if height_cm < 30.0 or height_cm > 280.0 or weight_kg < 2.0 or weight_kg > 500.0:
        return None, None

    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)

    if bmi < 18.5:
        category = "Underweight screening range (< 18.5)"
    elif bmi < 25.0:
        category = "Normal screening range (18.5 - 24.9)"
    elif bmi < 30.0:
        category = "Overweight screening range (25.0 - 29.9)"
    else:
        category = "Higher weight screening range (>= 30.0)"

    return bmi, category


def classify_vital_status(heart_rate: float, context: str = "resting") -> Dict[str, Any]:
    """
    Classifies observed heart rate taking measurement context into account.
    Returns status, severity, and calm educational guidance.
    """
    hr = round(heart_rate, 1)

    if context in ["active", "post_exercise"]:
        # Activity context: higher rates are normal physiological response
        if hr > 180.0:
            return {
                "status": "peak_exertion",
                "severity": "caution",
                "label": "Peak Exertion (> 180 bpm)",
                "urgent_guidance": "Rest and hydrate. If dizziness or chest discomfort occurs, seek medical attention.",
                "requires_urgent_care": False
            }
        elif hr > 120.0:
            return {
                "status": "exercise_response",
                "severity": "normal",
                "label": "Active Exercise Response (120 - 180 bpm)",
                "urgent_guidance": None,
                "requires_urgent_care": False
            }
        else:
            return {
                "status": "active_moderate",
                "severity": "normal",
                "label": "Moderate Activity Dynamics (< 120 bpm)",
                "urgent_guidance": None,
                "requires_urgent_care": False
            }

    # Resting context
    if hr >= 140.0:
        return {
            "status": "severe_tachycardia",
            "severity": "urgent",
            "label": "Severe Resting Tachycardia (>= 140 bpm)",
            "urgent_guidance": (
                "Resting heart rate is substantially elevated. If accompanied by shortness of breath, "
                "chest pressure, lightheadedness, or palpitations, please seek urgent medical care immediately."
            ),
            "requires_urgent_care": True
        }
    elif hr > 100.0:
        return {
            "status": "tachycardia",
            "severity": "caution",
            "label": "Elevated Resting Rate (> 100 bpm)",
            "urgent_guidance": "Rest quietly and re-check in 15 minutes. Contact your clinician if sustained.",
            "requires_urgent_care": False
        }
    elif hr < 40.0:
        return {
            "status": "severe_bradycardia",
            "severity": "urgent",
            "label": "Severe Resting Bradycardia (< 40 bpm)",
            "urgent_guidance": (
                "Resting heart rate is notably low. If you experience dizziness, weakness, or fainting, "
                "contact emergency medical services promptly."
            ),
            "requires_urgent_care": True
        }
    elif hr < 60.0:
        return {
            "status": "bradycardia",
            "severity": "caution",
            "label": "Low Resting Rate (< 60 bpm)",
            "urgent_guidance": "Common in endurance athletes; consult your doctor if accompanied by fatigue or lightheadedness.",
            "requires_urgent_care": False
        }
    elif hr > 90.0:
        return {
            "status": "elevated",
            "severity": "normal",
            "label": "High-Normal Resting Rate (90 - 100 bpm)",
            "urgent_guidance": None,
            "requires_urgent_care": False
        }
    else:
        return {
            "status": "normal",
            "severity": "normal",
            "label": "Normal Resting Range (60 - 90 bpm)",
            "urgent_guidance": None,
            "requires_urgent_care": False
        }
