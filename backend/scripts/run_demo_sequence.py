#!/usr/bin/env python3
"""
Hackloop 2026 — Digital Twin of a Patient
Repeatable End-to-End Demonstration Script

Executes the exact 14-step sequence specified in Section 11 of the hackathon requirements.
"""

import sys
import os

# Add root directory to sys.path so 'backend' package is discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import Base, engine


def log_step(step_num: int, title: str):
    print(f"\n{'='*75}")
    print(f"STEP {step_num:02d}: {title}")
    print(f"{'='*75}")


def main():
    print("\nStarting Hackloop 2026 Patient Digital Twin Verification Script...")
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    demo_patient_id = "PT-HACKLOOP-DEMO"

    # Step 1: Load a synthetic patient with historical measurements
    log_step(1, "Load a synthetic patient with historical measurements")
    res1 = client.post("/api/patients/synthetic", json={
        "patient_id": demo_patient_id,
        "name": "Sarah Connor",
        "baseline_hr": 72.0,
        "duration_hours": 24,
        "interval_minutes": 15
    })
    assert res1.status_code == 201, f"Failed: {res1.text}"
    data1 = res1.json()
    print(f"[OK] Patient {demo_patient_id} created with {data1['measurements_loaded']} synthetic measurements.")

    # Step 2 & 3: Display current modeled state and initial state version
    log_step(2, "Inspect active Digital Twin modeled state & initial state version (Web3 Anchored)")
    res2 = client.get(f"/api/patients/{demo_patient_id}/twin")
    assert res2.status_code == 200, f"Failed: {res2.text}"
    twin_v1 = res2.json()
    print(f"[OK] Active Twin State Version: {twin_v1['state_version']}")
    print(f"     Latest Observed Heart Rate: {twin_v1['latest_heart_rate']} bpm")
    print(f"     60-min Rolling Mean: {twin_v1['rolling_mean_60m']} bpm")
    print(f"     60-min Rolling Std:  ±{twin_v1['rolling_std_60m']} bpm")
    print(f"     Trend Slope:         {twin_v1['trend_slope_per_hour']} bpm/hour")
    print(f"     Observation Time:    {twin_v1['timestamp_latest_observation']}")
    print(f"     Vital Status:        {twin_v1['vital_status']}")
    print(f"     [Web3] Smart Contract:    {twin_v1.get('contract_address')}")
    print(f"     [Web3] On-Chain TX Hash:  0x{twin_v1.get('on_chain_tx_hash')}")
    print(f"     [Web3] Mined in Block:    #{twin_v1.get('on_chain_block_number')}")
    print(f"     [Web3] IPFS Storage CID:  ipfs://{twin_v1.get('ipfs_cid')}")
    assert twin_v1['state_version'] == 1, "Expected Version 1 upon initialization"

    # Verify on-chain cryptographic parity
    res_web3_ver = client.get(f"/api/web3/patients/{demo_patient_id}/twin/1/verify")
    assert res_web3_ver.status_code == 200
    assert res_web3_ver.json()["is_valid"] is True
    print(f"     [Web3] On-Chain Proof:    VERIFIED (is_valid == True, SHA-256 state root matches smart contract)")

    # Step 4: Generate a forecast using that state
    log_step(4, "Generate a forecast using Twin State Version 1")
    res4 = client.post(f"/api/patients/{demo_patient_id}/forecast", json={"horizon_minutes": 360})
    assert res4.status_code == 200, f"Failed: {res4.text}"
    fc_v1 = res4.json()
    print(f"[OK] Forecast #{fc_v1['id']} generated using State Version: {fc_v1['twin_state_version']}")
    print(f"     Model: {fc_v1['model_name']} (v{fc_v1['model_version']})")
    print(f"     Horizon: {fc_v1['forecast_horizon_minutes']} min ({len(fc_v1['predicted_trajectory'])} steps)")
    print(f"     Freshness: is_stale = {fc_v1['is_stale']}")
    assert fc_v1['is_stale'] is False
    assert fc_v1['twin_state_version'] == 1

    # Step 5 & 6: Generate Scenario A and Scenario B from the same state version
    log_step(5, "Generate Scenario A and Scenario B from identical Twin State Version")
    res5 = client.post(f"/api/patients/{demo_patient_id}/simulate", json={
        "horizon_minutes": 360,
        "parameter_name": "trend_damping_pct",
        "parameter_value": -30.0
    })
    assert res5.status_code == 200, f"Failed: {res5.text}"
    sim_data = res5.json()
    scen_a = sim_data['scenario_a']
    scen_b = sim_data['scenario_b']
    print(f"[OK] Baseline State Version: {sim_data['baseline_state_version']}")
    print(f"     Scenario A Type: {scen_a['scenario_type']}")
    print(f"     Scenario B Type: {scen_b['scenario_type']} ({scen_b['parameter_value']}%)")
    print(f"     Mathematical Rule: {scen_b['mathematical_rule']}")
    print(f"     Assumptions: {scen_b['assumptions']}")
    print(f"     Limitations: {scen_b['limitations'][:80]}...")
    print(f"     Trajectory Max Delta: {sim_data['delta_summary']['max_absolute_delta_bpm']} bpm")
    print(f"     Trajectory Mean Delta: {sim_data['delta_summary']['mean_absolute_delta_bpm']} bpm")

    # Step 7 & 8: Submit a new, valid timestamped measurement & verify state updates
    log_step(7, "Submit a new valid timestamped measurement (Live Observation)")
    new_obs_time = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    new_obs_val = 82.5
    res7 = client.post(f"/api/patients/{demo_patient_id}/measurements", json={
        "timestamp": new_obs_time,
        "measurement_type": "heart_rate",
        "value": new_obs_val,
        "unit": "bpm",
        "source": "bedside_telemetry"
    })
    assert res7.status_code == 201, f"Failed: {res7.text}"
    update_info = res7.json()
    print(f"[OK] New measurement recorded: {new_obs_val} bpm at {new_obs_time}")

    # Step 9: Verify that state version increments
    log_step(9, "Verify Digital Twin State Version increments from v1 -> v2")
    prev_ver = update_info['digital_twin_update']['previous_version']
    curr_ver = update_info['digital_twin_update']['current_state_version']
    print(f"[OK] State Version transitioned: v{prev_ver} -> v{curr_ver}")
    assert curr_ver == prev_ver + 1, "State version did not increment!"

    res_twin_v2 = client.get(f"/api/patients/{demo_patient_id}/twin")
    twin_v2 = res_twin_v2.json()
    print(f"     New Active Twin Version: {twin_v2['state_version']}")
    print(f"     New Latest HR: {twin_v2['latest_heart_rate']} bpm")
    print(f"     [Web3] Version 2 On-Chain TX: 0x{twin_v2.get('on_chain_tx_hash')}")
    print(f"     [Web3] Version 2 Mined Block: #{twin_v2.get('on_chain_block_number')}")
    print(f"     [Web3] Version 2 IPFS CID:    ipfs://{twin_v2.get('ipfs_cid')}")

    # Verify on-chain cryptographic parity for Version 2
    res_web3_v2 = client.get(f"/api/web3/patients/{demo_patient_id}/twin/2/verify")
    assert res_web3_v2.status_code == 200
    assert res_web3_v2.json()["is_valid"] is True
    print(f"     [Web3] Version 2 Cryptographic Proof: VERIFIED on smart contract!")

    # Step 10: Verify previous forecasts are marked stale
    log_step(10, "Verify previous forecast is marked STALE rather than silently overwritten")
    res10 = client.get(f"/api/patients/{demo_patient_id}/forecasts")
    forecasts = res10.json()
    old_fc = next(f for f in forecasts if f['id'] == fc_v1['id'])
    print(f"[OK] Historical Forecast #{old_fc['id']} is_stale: {old_fc['is_stale']}")
    print(f"     Stale Reason: {old_fc['stale_reason']}")
    assert old_fc['is_stale'] is True, "Previous forecast was not marked stale!"

    # Step 11 & 12: Generate fresh forecast and new scenarios referencing v2
    log_step(11, "Generate fresh forecast & verify association to State Version 2")
    res11 = client.post(f"/api/patients/{demo_patient_id}/forecast", json={"horizon_minutes": 360})
    fresh_fc = res11.json()
    print(f"[OK] New Forecast #{fresh_fc['id']} generated:")
    print(f"     Twin State Version: {fresh_fc['twin_state_version']}")
    print(f"     Observation Anchor: {fresh_fc['last_observation_timestamp']}")
    print(f"     Freshness: is_stale = {fresh_fc['is_stale']}")
    assert fresh_fc['twin_state_version'] == 2, "Expected forecast to be rooted in State Version 2!"
    assert fresh_fc['is_stale'] is False

    # Step 13: Display held-out chronological evaluation metrics
    log_step(13, "Execute chronological model evaluation on held-out test data")
    res13 = client.get(f"/api/patients/{demo_patient_id}/evaluation")
    assert res13.status_code == 200, f"Failed: {res13.text}"
    eval_metrics = res13.json()
    print(f"[OK] Chronological Train/Test Partition: {eval_metrics['train_samples']} train / {eval_metrics['test_samples']} test")
    print(f"     Autoregressive Model MAE: {eval_metrics['mae']:.2f} bpm")
    print(f"     Autoregressive Model RMSE: {eval_metrics['rmse']:.2f} bpm")
    print(f"     Baseline Persistence MAE: {eval_metrics['baseline_mae']:.2f} bpm")
    print(f"     Baseline Persistence RMSE: {eval_metrics['baseline_rmse']:.2f} bpm")
    print(f"     Error Reduction: {eval_metrics['mae_improvement_pct']}% improvement")
    print(f"     Synthetic Warning: {eval_metrics['disclaimer'][:80]}...")

    # Step 14: Demonstrate invalid measurement rejected without corrupting twin
    log_step(14, "Verify invalid measurement is rejected without corrupting twin state")
    res14_val = client.post(f"/api/patients/{demo_patient_id}/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 450.0,  # Far above physiological ceiling (250 bpm)
        "unit": "bpm"
    })
    print(f"[OK] Rejected out-of-range value (450 bpm) with HTTP {res14_val.status_code}")
    assert res14_val.status_code == 422

    res14_unit = client.post(f"/api/patients/{demo_patient_id}/measurements", json={
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "measurement_type": "heart_rate",
        "value": 75.0,
        "unit": "meters/second"  # Invalid unit
    })
    print(f"[OK] Rejected invalid unit ('meters/second') with HTTP {res14_unit.status_code}")
    assert res14_unit.status_code == 422

    # Check twin state remains intact at Version 2
    res14_twin = client.get(f"/api/patients/{demo_patient_id}/twin")
    twin_after_bad = res14_twin.json()
    print(f"[OK] Twin state verified: Still at Version {twin_after_bad['state_version']}, value {twin_after_bad['latest_heart_rate']} bpm.")
    assert twin_after_bad['state_version'] == curr_ver

    print(f"\n{'*'*75}")
    print("ALL 14 HACKLOOP 2026 DEMONSTRATION STEPS COMPLETED & VERIFIED SUCCESSFULLY!")
    print(f"{'*'*75}\n")


if __name__ == "__main__":
    main()

