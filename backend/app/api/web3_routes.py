from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database.connection import get_db
from app.models.patient import Patient
from app.models.twin_state import TwinState
from app.models.user import User
from app.services.auth import get_optional_current_user, verify_patient_authorization
from app.web3.service import Web3Service
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/web3", tags=["Web3 & Decentralized Patient Sovereignty"])


class GrantAccessRequest(BaseModel):
    researcher_address: str = Field(..., description="Ethereum wallet address of clinician or researcher")
    duration_seconds: int = Field(86400, ge=60, description="Duration of access permission in seconds (default 24h)")


class RevokeAccessRequest(BaseModel):
    researcher_address: str = Field(..., description="Ethereum wallet address to revoke")


@router.get("/status")
def get_web3_network_status():
    """
    Returns connection status, EVM network, deployed smart contract address,
    active wallet, balance, and latest block height. Gracefully reports offline/unavailable mode.
    """
    try:
        service = Web3Service.get_instance()
        return service.get_network_status()
    except Exception as e:
        return {
            "is_connected": False,
            "chain_id": None,
            "network_name": "Unavailable",
            "contract_address": None,
            "active_wallet_address": None,
            "wallet_balance_eth": 0.0,
            "latest_block_number": None,
            "error": str(e)
        }


@router.get("/patients/{patient_id}/twin/{version}/verify")
def verify_twin_state_on_chain(
    patient_id: str,
    version: int,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Performs on-chain cryptographic verification by querying the PatientDigitalTwinRegistry smart contract.
    Proves that the digital twin state features have not been altered or tampered with off-chain.
    """
    verify_patient_authorization(patient_id, current_user, db)

    twin_state = db.query(TwinState).filter(
        TwinState.patient_id == patient_id,
        TwinState.state_version == version
    ).first()

    if not twin_state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Twin state version {version} not found.")

    features = {
        "latest_heart_rate": twin_state.latest_heart_rate,
        "rolling_mean_60m": twin_state.rolling_mean_60m,
        "trend_slope_per_hour": twin_state.trend_slope_per_hour,
        "vital_status": twin_state.vital_status,
        "measurement_context": twin_state.measurement_context,
    }

    service = Web3Service.get_instance()
    result = service.verify_twin_attestation(
        patient_id=patient_id,
        version=version,
        timestamp=twin_state.timestamp_latest_observation,
        features=features,
        model_version=twin_state.model_version,
        data_quality_status=twin_state.data_quality_status,
        previous_state_hash=twin_state.previous_state_hash
    )

    return {
        **result,
        "on_chain_tx_hash": twin_state.on_chain_tx_hash,
        "on_chain_block_number": twin_state.on_chain_block_number,
        "contract_address": twin_state.contract_address or (service.contract.address if service.contract else None),
        "timestamp_observation": to_utc_iso(twin_state.timestamp_latest_observation)
    }


@router.post("/patients/{patient_id}/access/grant")
def grant_access_on_chain(
    patient_id: str,
    payload: GrantAccessRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Sovereign Patient Consent: Submits an on-chain transaction to grant access
    to a clinician or researcher Ethereum wallet address.
    """
    verify_patient_authorization(patient_id, current_user, db)

    try:
        service = Web3Service.get_instance()
        tx_hash = service.grant_researcher_access(patient_id, payload.researcher_address, payload.duration_seconds)
        return {
            "success": True,
            "patient_id": patient_id,
            "researcher_address": payload.researcher_address,
            "tx_hash": tx_hash,
            "duration_seconds": payload.duration_seconds,
            "message": f"Access granted on-chain to {payload.researcher_address}."
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/patients/{patient_id}/access/revoke")
def revoke_access_on_chain(
    patient_id: str,
    payload: RevokeAccessRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Sovereign Patient Consent: Submits an on-chain transaction to revoke access
    from a clinician or researcher Ethereum wallet address.
    """
    verify_patient_authorization(patient_id, current_user, db)

    try:
        service = Web3Service.get_instance()
        tx_hash = service.revoke_researcher_access(patient_id, payload.researcher_address)
        return {
            "success": True,
            "patient_id": patient_id,
            "researcher_address": payload.researcher_address,
            "tx_hash": tx_hash,
            "message": f"Access revoked on-chain from {payload.researcher_address}."
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/patients/{patient_id}/access/check")
def check_access_on_chain(
    patient_id: str,
    user_address: str = Query(..., description="Ethereum wallet address to check"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Queries the smart contract to check if a wallet address has active access to the patient's twin.
    """
    verify_patient_authorization(patient_id, current_user, db)

    try:
        service = Web3Service.get_instance()
        has_perm = service.check_access(patient_id, user_address)
        return {
            "patient_id": patient_id,
            "user_address": user_address,
            "has_access": has_perm
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

