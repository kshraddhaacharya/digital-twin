# Sovereign Health Twin — Continuous Physiological Modeling & Web3 Data Integrity

> **CRITICAL CLINICAL & EDUCATIONAL PROTOTYPE DISCLAIMER**  
> Sovereign Health Twin is a digital health research and educational prototype. It demonstrates dynamic physiological state modeling, bounded counterfactual outcome simulation, and cryptographic record integrity on EVM smart contracts. **It is NOT a medical device, does NOT provide clinical diagnoses, does NOT prescribe medication or medical therapies, and must NEVER replace consultation, diagnosis, or evaluation by a licensed healthcare professional.** In any medical emergency, always call local emergency services immediately.

---

## 1. Problem Statement & Executive Summary

Healthcare decision-making frequently relies on episodic snapshots—isolated, point-in-time vital checks or laboratory panels that fail to capture how an individual's condition continuously evolves. 

**Sovereign Health Twin** transforms snapshot healthcare into continuous, auditable physiological understanding. The platform maintains a canonical, persistent patient digital twin that:
1. **Tracks Inferred Physiological State**: Maintains continuous resting baseline, 60-minute rolling average, hourly trend slope, circadian diurnal phase, and context-aware classification.
2. **Projects Bounded Baseline Trajectories**: Computes a forward-looking short-term forecast over a validated 120-minute horizon (maximum 180 minutes) with statistical prediction intervals rooted in residual standard error.
3. **Simulates Counterfactual Outcomes**: Compares a continuation of the baseline trajectory (Scenario A) against an altered condition (Scenario B, such as resting recovery or mild activity exertion) utilizing transparent, documented asymptotic kinetics ($k = 0.03\text{ min}^{-1}$) with identical starting conditions.
4. **Anchors Cryptographic Provenance on Web3**: Serializes state metadata deterministically, computes tamper-evident SHA-256 commitments and IPFS CIDv1 pointers, anchors them to an EVM smart contract (`PatientDigitalTwinRegistry.sol`), and enforces sovereign patient-controlled consent.
5. **Maintains Medical Data Consistency & Privacy**: Keeps all protected health information, raw documents, and medical notes off-chain. Calculates trusted non-diagnostic metrics (e.g. Body Mass Index screening from current height and weight) consistently across every screen.

---

## 2. Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    React + TypeScript + Vite User Interface                   │
│                                                                              │
│  [1. My Health]      [2. Digital Twin]    [3. Health Records]  [4. Integrity]│
│  - Vitals & Baseline - Baseline Trajectory - Vital Log & Vitals - EVM Status │
│  - Screened BMI      - Scenario Simulation - PDF/PNG Magic-Byte - Verifier   │
│  - Trend Slope       - Outdated Warning    - Lab Confirm Drawer - Consent Hub│
│  └───────────────────────────────────────────────────────────────────────┘   │
│  [More Menu]: Dashboard Overview • Personal Videos • Disease Tracker • Cycle │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ HTTP REST API (Axios + JWT Auth)
┌──────────────────────────────────────▼───────────────────────────────────────┐
│                     FastAPI Transport & Access Control Layer                 │
│      - Server-Side Cross-Patient Authorization Isolation (403 Forbidden)     │
│      - Pydantic v2 Physiological Schema Validation & Bounds [30, 250] bpm    │
│      - Magic-Bytes Content Verification (%PDF, \x89PNG, \xff\xd8\xff)       │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼───────────────────────────────────────┐
│                     DIGITAL TWIN DOMAIN ENGINE (Core)                        │
│      - Latent State Extraction (Rolling Mean 60m, Std, Trend Slope, Context) │
│      - State Versioning Ledger (v1 -> v2 -> v3 ...)                          │
│      - Automatic Stale Forecast Detection & Invalidation Guard               │
│      - Synthetic Telemetry Overwrite Protection for Registered Users         │
└──────────────┬───────────────────────┬──────────────────────┬────────────────┘
               │                       │                      │
┌──────────────▼─────┐       ┌─────────▼──────────┐  ┌────────▼────────────────┐
│ Forecasting Engine │       │ Simulation Engine  │  │ Web3 Integrity Service  │
│ - Autoregressive   │       │ - Scenario A vs B  │  │ - Canonical JSON Spec   │
│ - Diurnal Rhythm   │       │ - Identical Origin │  │ - SHA-256 Commitment    │
│ - Horizon <= 180m  │       │ - Asymptotic Curve │  │ - IPFS CIDv1 Pointers   │
│ - Residual SE Bands│       │ - Calm Guidance    │  │ - Dual-Mode Py-EVM & RPC│
└──────────────┬─────┘       └─────────┬──────────┘  └────────┬────────────────┘
               │                       │                      │
┌──────────────▼───────────────────────▼──────────────────────▼────────────────┐
│               Persistence Layer (SQLite / PostgreSQL & SQLAlchemy)           │
│   patients • users • twin_states • measurements • forecasts • scenarios ...  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Recharts, Lucide React, Axios
- **Backend API**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, pandas, NumPy, scikit-learn, pypdf, Pillow
- **Web3 & Blockchain**:
  - Smart Contract: Solidity `0.8.20` (`PatientDigitalTwinRegistry.sol`)
  - Web3.py with dual-mode support:
    - **In-Process EVM**: High-fidelity local Py-EVM (`EthereumTesterProvider`) executing real gas estimation, transaction signing, and mining locally without external node dependencies.
    - **Remote EVM**: Compatible with Ethereum Sepolia, Polygon, Arbitrum, or local Hardhat/Anvil nodes via `WEB3_PROVIDER_URL`.
  - Cryptographic Commitments: Deterministic canonical JSON serialization (`RFC 8785` principles) and SHA-256.
  - Decentralized Addressing: IPFS CIDv1 content hashing (`ipfs://bafybeih...`).
- **Persistence & Migrations**: SQLite (zero-config local database `patient_twin.db`) with forward migration scripts and automated database backups (`patient_twin.db.backup`).
- **Testing**: pytest (31 automated unit and integration tests).

---

## 4. The 4 Primary Destinations

### 1. My Health (`my-health`)
The personalized health overview showing:
- Patient identity and demographic profile.
- Current physiological measurements, timestamp of the latest observation, and 60-minute rolling mean.
- Context-aware vital status classification (`normal`, `tachycardia`, `bradycardia`, `exercise_response`) taking activity into account.
- Hourly trend slope and plain-English description of physiological trajectory.
- Consistently screened physical metrics: Height, Weight, and calculated Body Mass Index (BMI) explicitly labeled as a general statistical screening tool, not a diagnosis.

### 2. Digital Twin (`digital-twin`)
The core physiological simulation and counterfactual reasoning hub:
- **Baseline Trajectory (Scenario A)**: Bounded forward projection over 120 minutes (up to 180 min max) using autoregressive trend extrapolation and 24-hour diurnal harmonic modeling.
- **Counterfactual Trajectory (Scenario B)**: Simulates the physiological outcome of a hypothetical change in condition (e.g. resting recovery -25% or mild activity exertion +25%).
- **Identical Starting State**: Scenarios A and B originate from the exact same starting measurement timestamp and value.
- **Asymptotic Transition Kinetics**: Scenario B applies exponential relaxation dynamics ($k = 0.03\text{ min}^{-1}$) to model continuous biological response rather than impossible instantaneous jumps.
- **Uncertainty Bands & Data Quality**: Displays prediction intervals rooted in residual standard error, data freshness warnings, and irregular interval notifications.
- **Outdated Forecast Warning Guard**: Automatically detects when new readings or profile changes occurred after the forecast was generated, showing an amber "Forecast Outdated" warning with 1-click update.

### 3. Health Records (`records`)
The unified clinical records management center with two integrated tabs:
- **Vital Readings Log**: Chronological table of all recorded observations, display of measurement context (`resting`, `active`, `post_exercise`), dynamic Web3 blockchain attestation status, and single-click manual entry form with physiological plausibility bounds.
- **Medical Reports & Lab Documents**: Secure document upload supporting PDF, PNG, and JPG files with magic-byte content validation. Instant full-text search across parsed text, and a **Patient Review-and-Confirm Protocol** allowing patients to review and confirm extracted biomarkers before they feed into their digital twin state.

### 4. Data Integrity (`integrity`)
The dedicated Web3 blockchain provenance and data sovereignty center:
- **Educational Framing**: Explains clearly that blockchain establishes mathematical data integrity and provenance, not medical truth or clinical diagnosis.
- **Live Network Status**: Displays connected EVM chain ID, execution mode (remote RPC vs in-process Py-EVM), contract address (`PatientDigitalTwinRegistry.sol`), and latest mined block number.
- **Independent Cryptographic Verification Tool**: Allows anyone to re-run canonical serialization and SHA-256 state recalculation in real time, comparing the candidate hash against the on-chain root. Distinguishes 5 verified states: `VERIFIED`, `SIMULATED`, `PENDING`, `MISMATCH`, and `NOT_ANCHORED`.
- **Sovereign Consent Manager**: Gives patients complete control over their medical data. Patients can grant time-locked access permissions to researcher or clinician Ethereum addresses, verify active access on-chain, or revoke permissions immediately.
- **Cryptographic Audit Trail**: Displays the state hash chain linking each twin state version to the `previous_state_hash`, forming a tamper-evident audit ledger.

---

## 5. Security & Privacy Model

1. **Off-Chain Health Data Storage**: Raw medical documents, diagnosis notes, patient names, and fine-grained physiological telemetry remain in protected off-chain storage.
2. **Cryptographic Hashes On-Chain**: Only deterministic cryptographic commitments (`bytes32` roots) and non-identifying state metadata (version, timestamp, scaled heart rate) are written to the public smart contract.
3. **Server-Side Authorization**: Every API route enforces server-side patient verification (`verify_patient_authorization`). A patient authenticated as Patient A cannot view or manipulate records for Patient B (HTTP 403 Forbidden).
4. **Synthetic Overwrite Protection**: The synthetic patient telemetry generator cannot overwrite registered real patients.
5. **Magic-Byte Document Validation**: Uploaded documents are verified using file header signatures (`%PDF` for PDFs, `\x89PNG\r\n\x1a\n` for PNGs, `\xff\xd8\xff` for JPEGs) to prevent malicious or malformed file spoofing.
6. **No Embedded Secrets**: Private keys, JWT secrets, and credentials use environment configuration with safe development fallbacks.

---

## 6. Setup, Execution & Testing Commands

### Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Node.js 18+ (tested on Node 20 / 24)
- PowerShell (Windows) or Bash (macOS / Linux)

### 6.1 Backend Setup & Startup

```powershell
# 1. Activate virtual environment
.\backend\venv\Scripts\Activate.ps1

# 2. Install dependencies (if not already installed)
pip install -r backend/requirements.txt

# 3. Start the FastAPI backend server
$env:PYTHONPATH="."
.\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend server starts at **`http://127.0.0.1:8000`**.  
Interactive Swagger API documentation is available at **`http://127.0.0.1:8000/docs`**.

### 6.2 Frontend Setup & Startup

```powershell
# In a separate terminal
cd frontend
npm install
npm run dev
```

Open **`http://localhost:5173`** in your browser.

### 6.3 Running Automated Tests

Run the complete backend test suite across all modules:

```powershell
$env:PYTHONPATH="."
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

**Results: 31 passed in ~10s!**
- `backend/tests/test_sovereign_health_twin.py` (11 tests): Canonical serialization, insufficient data refusal, irregular intervals, physiological bounds, scenario comparison with identical origin, stale forecast invalidation, cross-patient authorization isolation, synthetic overwrite guard, magic-bytes file validation, Web3 verification states, and BMI screening calculations.
- `backend/tests/test_new_features.py` (3 tests): Medical report parser, disease tracker, and period cycle tracker.
- `backend/tests/test_twin_system.py` (17 tests): Ingestion, twin initialization, autoregressive diurnal forecasting, scenario simulation, and out-of-sample evaluation.

Run the frontend TypeScript and build check:

```powershell
npm run build --prefix frontend
```

**Result: Built with 0 errors!**

---

## 7. Manual Acceptance Test Checklist

| Step | Action | Expected Result | Verified |
| :--- | :--- | :--- | :---: |
| 1 | Launch Backend & Frontend | Backend runs on `:8000` with in-process EVM deployed; Frontend opens on `:5173` | [x] |
| 2 | Load Demo Patient | Click "Load Demo Patient" button in Navbar | Twin initializes to State Version 1 with verified on-chain attestation | [x] |
| 3 | Inspect "1. My Health" | Navigate to "My Health" tab | Displays current heart rate, resting baseline, trend slope, and BMI screening | [x] |
| 4 | Run Simulation in "2. Digital Twin" | Navigate to "Digital Twin" tab | Compares Scenario A (Baseline) vs Scenario B (Activity/Rest) over 120 min | [x] |
| 5 | Verify Outdated Forecast Warning | Add a new reading in "Health Records", return to "Digital Twin" | Amber "Newer Reading Available — Outlook is Outdated" banner appears | [x] |
| 6 | Ingest Reading in "3. Health Records" | Enter a reading with Context (e.g. 85 bpm, Active) | State advances to Version 2; table shows dynamic attestation badge | [x] |
| 7 | Upload Report & Confirm Biomarker | Upload valid PDF report in "Medical Reports" tab | Parses vitals; clicking "Review & Confirm" feeds verified vital into twin | [x] |
| 8 | Reject Spoofed File Extension | Attempt to upload a text file renamed to `.pdf` | Rejected with 400 Bad Request ("does not match a valid PDF header") | [x] |
| 9 | Verify Data Integrity in "4. Data Integrity" | Click "Verify Record Integrity" button | Computes SHA-256 state hash and confirms match with smart contract | [x] |
| 10 | Sovereign Consent Access Control | Enter an Ethereum address and click "Grant Time-Locked Access" | On-chain transaction executed and permission confirmed on smart contract | [x] |
| 11 | Cross-Patient Isolation Check | User Alpha attempts to access Patient Beta's data | Server returns 403 Forbidden | [x] |

---

## 8. License & Attribution

Developed for **HackLoop 2026**. Built with privacy-first digital twin modeling and EVM cryptographic anchoring. For educational and research purposes only.
# Digital_Twin
