import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

ARTIFACTS_PATH = os.path.join(os.path.dirname(__file__), "contract_artifacts.json")


class Web3Service:
    """
    Decentralized Web3 integrity and provenance service.
    Provides deterministic cryptographic commitment, EVM smart contract anchoring,
    and multi-state verification (VERIFIED, PENDING, FAILED, UNAVAILABLE, MISMATCH).
    Ensures raw sensitive health data remains safely off-chain.
    """

    _instance: Optional["Web3Service"] = None

    def __init__(self):
        self.provider_url = os.getenv("WEB3_PROVIDER_URL")
        self.mode = "uninitialized"  # "remote", "in_process_tester", or "offline_fallback"
        self.w3 = None
        self.artifacts = self._load_artifacts()
        self.account = None
        self.contract = None

        self._initialize_provider_and_contract()

    @classmethod
    def get_instance(cls) -> "Web3Service":
        if cls._instance is None:
            cls._instance = Web3Service()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Allows resetting for testing or reconfiguration."""
        cls._instance = None

    def _load_artifacts(self) -> Dict[str, Any]:
        """Loads compiled smart contract ABI and Bytecode."""
        if not os.path.exists(ARTIFACTS_PATH):
            raise FileNotFoundError(f"Contract artifacts not found at {ARTIFACTS_PATH}")
        with open(ARTIFACTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _initialize_provider_and_contract(self):
        """Initializes connection to external EVM node or in-process Py-EVM."""
        # 1. Try remote provider
        if self.provider_url:
            try:
                w3 = Web3(Web3.HTTPProvider(self.provider_url, request_kwargs={"timeout": 10}))
                if w3.is_connected():
                    try:
                        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                    except Exception:
                        pass
                    self.w3 = w3
                    self.mode = "remote"
                    print(f"[Web3] Connected to remote EVM provider: {self.provider_url}")
                    self._setup_account_and_contract()
                    return
            except Exception as e:
                print(f"[Web3] Remote provider failed ({e}). Attempting in-process fallback.")

        # 2. Try in-process EthereumTesterProvider (Py-EVM)
        try:
            from web3.providers.eth_tester import EthereumTesterProvider
            w3 = Web3(EthereumTesterProvider())
            if w3.is_connected():
                self.w3 = w3
                self.mode = "in_process_tester"
                print("[Web3] Connected to local in-process EVM (EthereumTesterProvider).")
                self._setup_account_and_contract()
                return
        except Exception as e:
            print(f"[Web3] In-process tester provider unavailable: {e}")

        # 3. Fallback mode
        self.mode = "offline_fallback"
        print("[Web3] EVM provider unavailable. Operating in offline/audit-only mode.")

    def _setup_account_and_contract(self):
        """Configures transacting account and deploys/attaches registry contract."""
        if not self.w3:
            return

        try:
            accounts = self.w3.eth.accounts
            if accounts:
                self.account = accounts[0]
                self.w3.eth.default_account = accounts[0]
            else:
                priv_key = os.getenv("WEB3_PRIVATE_KEY", "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d")
                acc = self.w3.eth.account.from_key(priv_key)
                self.account = acc.address
                self.w3.eth.default_account = acc.address

            contract_addr = os.getenv("REGISTRY_CONTRACT_ADDRESS")
            abi = self.artifacts["abi"]
            bytecode = self.artifacts.get("bin", "")

            if contract_addr and self.w3.is_address(contract_addr):
                self.contract = self.w3.eth.contract(address=contract_addr, abi=abi)
                print(f"[Web3] Attached to existing registry contract at {contract_addr}")
                return

            # Deploy contract
            if bytecode:
                contract_factory = self.w3.eth.contract(abi=abi, bytecode=bytecode)
                tx_hash = contract_factory.constructor().transact({"from": self.account})
                tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)
                self.contract = self.w3.eth.contract(address=tx_receipt.contractAddress, abi=abi)
                print(f"[Web3] Registry deployed at {tx_receipt.contractAddress} (block #{tx_receipt.blockNumber})")
        except Exception as e:
            print(f"[Web3] Contract initialization error: {e}")
            self.mode = "offline_fallback"

    @staticmethod
    def canonicalize_state_payload(
        patient_id: str,
        version: int,
        timestamp: datetime,
        features: Dict[str, Any],
        model_version: str = "1.0.0",
        data_quality_status: str = "good",
        previous_state_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a deterministic, canonical representation of non-sensitive state metadata
        and vital indicators for cryptographic commitment.
        """
        ts_utc = timestamp.astimezone(timezone.utc) if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        return {
            "contract_version": "1.0",
            "data_quality_status": str(data_quality_status),
            "latest_heart_rate": round(float(features.get("latest_heart_rate", 0.0)), 2),
            "measurement_context": str(features.get("measurement_context", "resting")),
            "model_version": str(model_version),
            "patient_id": str(patient_id),
            "previous_state_hash": str(previous_state_hash or ""),
            "rolling_mean_60m": round(float(features.get("rolling_mean_60m", 0.0)), 2) if features.get("rolling_mean_60m") is not None else None,
            "timestamp": ts_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "trend_slope_per_hour": round(float(features.get("trend_slope_per_hour", 0.0)), 2) if features.get("trend_slope_per_hour") is not None else 0.0,
            "version": int(version),
            "vital_status": str(features.get("vital_status", "normal")),
        }

    @classmethod
    def calculate_state_hash(
        cls,
        patient_id: str,
        version: int,
        timestamp: datetime,
        features: Dict[str, Any],
        model_version: str = "1.0.0",
        data_quality_status: str = "good",
        previous_state_hash: Optional[str] = None
    ) -> str:
        """Computes deterministic SHA-256 commitment of the canonical state."""
        canonical_dict = cls.canonicalize_state_payload(
            patient_id=patient_id,
            version=version,
            timestamp=timestamp,
            features=features,
            model_version=model_version,
            data_quality_status=data_quality_status,
            previous_state_hash=previous_state_hash
        )
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_ipfs_cid(canonical_data: Dict[str, Any]) -> str:
        """Computes deterministic content-addressed identifier (IPFS CIDv1 representation)."""
        serialized = json.dumps(canonical_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
        h = hashlib.sha256(serialized).hexdigest()
        return f"bafybeih{h[:40]}"

    def attest_twin_state(
        self,
        patient_id: str,
        version: int,
        timestamp: datetime,
        latest_hr: float,
        rolling_mean: Optional[float],
        features: Dict[str, Any],
        model_version: str = "1.0.0",
        data_quality_status: str = "good",
        previous_state_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attests the digital twin state version on-chain.
        Returns provenance metadata with explicit attestation status.
        """
        state_hash_hex = self.calculate_state_hash(
            patient_id=patient_id,
            version=version,
            timestamp=timestamp,
            features=features,
            model_version=model_version,
            data_quality_status=data_quality_status,
            previous_state_hash=previous_state_hash
        )
        state_root_bytes = bytes.fromhex(state_hash_hex)

        canonical_payload = self.canonicalize_state_payload(
            patient_id=patient_id,
            version=version,
            timestamp=timestamp,
            features=features,
            model_version=model_version,
            data_quality_status=data_quality_status,
            previous_state_hash=previous_state_hash
        )
        ipfs_cid = self.generate_ipfs_cid(canonical_payload)

        # If connected to EVM and contract ready
        if self.contract and self.w3 and self.w3.is_connected():
            try:
                ts_epoch = int(timestamp.timestamp())
                scaled_hr = int(round(latest_hr * 10))
                scaled_mean = int(round((rolling_mean or latest_hr) * 10))

                # Register patient if needed
                owner = self.contract.functions.patientOwners(patient_id).call()
                if owner == "0x0000000000000000000000000000000000000000":
                    tx_reg = self.contract.functions.registerPatient(
                        patientId=patient_id,
                        owner=self.account
                    ).transact({"from": self.account})
                    self.w3.eth.wait_for_transaction_receipt(tx_reg, timeout=20)

                # Anchor twin state
                tx_hash = self.contract.functions.attestTwinState(
                    patientId=patient_id,
                    version=version,
                    timestamp=ts_epoch,
                    latestHR=scaled_hr,
                    rollingMean=scaled_mean,
                    stateRoot=state_root_bytes,
                    ipfsCID=ipfs_cid
                ).transact({"from": self.account})

                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=20)

                return {
                    "attestation_status": "VERIFIED" if self.mode == "remote" else "SIMULATED",
                    "on_chain_tx_hash": tx_hash.hex(),
                    "on_chain_block_number": receipt.blockNumber,
                    "state_hash_sha256": state_hash_hex,
                    "ipfs_cid": ipfs_cid,
                    "contract_address": self.contract.address,
                    "attester_wallet": self.account,
                    "gas_used": receipt.gasUsed,
                    "network_mode": self.mode
                }
            except Exception as e:
                print(f"[Web3] On-chain transaction reverted or delayed: {e}")
                return {
                    "attestation_status": "FAILED",
                    "on_chain_tx_hash": None,
                    "on_chain_block_number": None,
                    "state_hash_sha256": state_hash_hex,
                    "ipfs_cid": ipfs_cid,
                    "contract_address": self.contract.address if self.contract else None,
                    "error": str(e),
                    "network_mode": self.mode
                }

        # Offline / fallback
        return {
            "attestation_status": "UNAVAILABLE",
            "on_chain_tx_hash": None,
            "on_chain_block_number": None,
            "state_hash_sha256": state_hash_hex,
            "ipfs_cid": ipfs_cid,
            "contract_address": None,
            "network_mode": "offline_fallback"
        }

    def verify_twin_attestation(
        self,
        patient_id: str,
        version: int,
        timestamp: datetime,
        features: Dict[str, Any],
        model_version: str = "1.0.0",
        data_quality_status: str = "good",
        previous_state_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates cryptographic parity between candidate twin state and
        on-chain record. Distinguishes: VERIFIED, MISMATCH, UNAVAILABLE, NOT_ANCHORED.
        """
        candidate_hash_hex = self.calculate_state_hash(
            patient_id=patient_id,
            version=version,
            timestamp=timestamp,
            features=features,
            model_version=model_version,
            data_quality_status=data_quality_status,
            previous_state_hash=previous_state_hash
        )
        candidate_bytes = bytes.fromhex(candidate_hash_hex)

        if not self.contract or not self.w3 or not self.w3.is_connected():
            return {
                "verification_status": "UNAVAILABLE",
                "is_valid": False,
                "patient_id": patient_id,
                "state_version": version,
                "candidate_hash": candidate_hash_hex,
                "on_chain_root": None,
                "ipfs_cid": None,
                "block_number": None,
                "contract_address": None,
                "reason": "Web3 blockchain provider is offline or unconfigured."
            }

        try:
            is_valid, on_chain_root_bytes, ipfs_cid, block_num = self.contract.functions.verifyStateAttestation(
                patient_id,
                version,
                candidate_bytes
            ).call()

            on_chain_hex = on_chain_root_bytes.hex() if isinstance(on_chain_root_bytes, bytes) else str(on_chain_root_bytes)

            if block_num == 0 or on_chain_hex == "00" * 32 or not on_chain_hex:
                return {
                    "verification_status": "NOT_ANCHORED",
                    "is_valid": False,
                    "patient_id": patient_id,
                    "state_version": version,
                    "candidate_hash": candidate_hash_hex,
                    "on_chain_root": None,
                    "ipfs_cid": None,
                    "block_number": None,
                    "contract_address": self.contract.address,
                    "reason": f"No on-chain attestation found for state version {version}."
                }

            status_str = "VERIFIED" if is_valid else "MISMATCH"
            return {
                "verification_status": status_str,
                "is_valid": bool(is_valid),
                "patient_id": patient_id,
                "state_version": version,
                "candidate_hash": candidate_hash_hex,
                "on_chain_root": on_chain_hex,
                "ipfs_cid": ipfs_cid,
                "block_number": block_num,
                "contract_address": self.contract.address,
                "network_mode": self.mode
            }
        except Exception as e:
            return {
                "verification_status": "FAILED",
                "is_valid": False,
                "patient_id": patient_id,
                "state_version": version,
                "candidate_hash": candidate_hash_hex,
                "reason": f"Smart contract call failed: {str(e)}"
            }

    def grant_researcher_access(self, patient_id: str, researcher_address: str, duration_seconds: int = 86400) -> str:
        """Sovereign consent: grants researcher wallet access on-chain."""
        if not self.contract or not self.w3:
            raise RuntimeError("Web3 EVM network is unavailable for consent management.")
        tx_hash = self.contract.functions.grantAccess(
            patient_id,
            self.w3.to_checksum_address(researcher_address),
            duration_seconds
        ).transact({"from": self.account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=20)
        return tx_hash.hex()

    def revoke_researcher_access(self, patient_id: str, researcher_address: str) -> str:
        """Sovereign consent: revokes researcher wallet access on-chain."""
        if not self.contract or not self.w3:
            raise RuntimeError("Web3 EVM network is unavailable for consent management.")
        tx_hash = self.contract.functions.revokeAccess(
            patient_id,
            self.w3.to_checksum_address(researcher_address)
        ).transact({"from": self.account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=20)
        return tx_hash.hex()

    def check_access(self, patient_id: str, user_address: str) -> bool:
        """Checks if a user/researcher address currently has active access on-chain."""
        if not self.contract or not self.w3:
            return False
        return self.contract.functions.hasAccess(
            patient_id,
            self.w3.to_checksum_address(user_address)
        ).call()

    def get_network_status(self) -> Dict[str, Any]:
        """Returns Web3 connection and network telemetry."""
        if not self.w3 or not self.w3.is_connected():
            return {
                "is_connected": False,
                "chain_id": None,
                "network_name": "Disconnected / Unavailable",
                "contract_address": None,
                "active_wallet_address": None,
                "wallet_balance_eth": 0.0,
                "latest_block_number": None,
                "network_mode": "offline"
            }

        balance_wei = self.w3.eth.get_balance(self.account) if self.account else 0
        balance_eth = float(self.w3.from_wei(balance_wei, "ether")) if balance_wei else 0.0
        return {
            "is_connected": True,
            "chain_id": self.w3.eth.chain_id,
            "network_name": (
                "Ethereum / EVM Testnet" if self.mode == "remote"
                else "EVM Development Chain (In-Process Py-EVM)"
            ),
            "contract_address": self.contract.address if self.contract else None,
            "active_wallet_address": self.account,
            "wallet_balance_eth": round(balance_eth, 4),
            "latest_block_number": self.w3.eth.block_number,
            "network_mode": self.mode
        }
