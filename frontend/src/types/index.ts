export interface User {
  id: string;
  email: string;
  full_name: string;
  patient_id: string;
  age?: number;
  date_of_birth?: string;
  gender?: string;
  height?: number; // cm
  body_weight?: number; // kg
  profile_version?: number;
  calculated_bmi?: number;
  bmi_category?: string;
  existing_conditions?: string;
  allergies?: string;
  medications?: string;
  emergency_contact?: string;
  profile_photo?: string;
  health_notes?: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: string;
  baseline_heart_rate: number;
  height_cm?: number;
  weight_kg?: number;
  profile_version?: number;
  calculated_bmi?: number;
  bmi_category?: string;
  medical_notes?: string;
  is_synthetic: boolean;
  created_at: string;
  total_measurements?: number;
  active_twin_state_version?: number;
  latest_heart_rate?: number;
  measurement_context?: string;
  latest_observation_time?: string;
  vital_status?: string;
  data_quality_status?: string;
  attestation_status?: string;
  on_chain_tx_hash?: string;
}

export interface Measurement {
  id: number;
  patient_id: string;
  timestamp: string;
  measurement_type: string;
  value: number;
  unit: string;
  source: string;
  context?: string;
  data_quality?: string;
  is_late_arrival: boolean;
  created_at: string;
}

export interface TwinState {
  id: number;
  patient_id: string;
  state_version: number;
  timestamp_latest_observation: string;
  last_processed_measurement_id?: number;
  latest_heart_rate: number;
  measurement_context?: string;
  rolling_mean_60m?: number;
  rolling_std_60m?: number;
  trend_slope_per_hour?: number;
  circadian_phase_estimate?: number;
  physiological_variability_index?: number;
  vital_status: 'normal' | 'elevated' | 'tachycardia' | 'bradycardia' | 'severe_tachycardia' | 'severe_bradycardia' | 'peak_exertion' | 'exercise_response' | 'active_moderate';
  model_version?: string;
  data_quality_status?: string;
  attestation_status?: string;
  previous_state_hash?: string;
  latest_forecast_time?: string;
  data_freshness_seconds: number;
  is_active_version: boolean;
  on_chain_tx_hash?: string;
  on_chain_block_number?: number;
  state_hash_sha256?: string;
  ipfs_cid?: string;
  contract_address?: string;
  created_at: string;
}

export interface Web3NetworkStatus {
  is_connected: boolean;
  chain_id?: number;
  network_name: string;
  contract_address?: string;
  active_wallet_address?: string;
  wallet_balance_eth: number;
  latest_block_number?: number;
  network_mode?: string;
  error?: string;
}

export interface Web3VerificationResult {
  is_valid: boolean;
  verification_status: string; // 'VERIFIED' | 'MISMATCH' | 'PENDING' | 'UNAVAILABLE' | 'NOT_ANCHORED' | 'FAILED'
  patient_id: string;
  state_version: number;
  candidate_hash: string;
  on_chain_root?: string;
  ipfs_cid?: string;
  block_number?: number;
  on_chain_tx_hash?: string;
  contract_address?: string;
  timestamp_observation?: string;
  reason?: string;
  network_mode?: string;
}

export interface ForecastPoint {
  timestamp: string;
  predicted_value: number;
  lower_bound_95: number;
  upper_bound_95: number;
  lower_bound_80: number;
  upper_bound_80: number;
}

export interface Forecast {
  id: number;
  patient_id: string;
  twin_state_version: number;
  last_observation_timestamp: string;
  model_name: string;
  model_version: string;
  forecast_horizon_minutes: number;
  predicted_trajectory: ForecastPoint[];
  is_stale: boolean;
  stale_reason?: string;
  quality_warnings: string[];
  created_at: string;
}

export interface ScenarioPoint {
  timestamp: string;
  simulated_value: number;
}

export interface Scenario {
  id: string;
  patient_id: string;
  baseline_state_version: number;
  scenario_type: string;
  parameter_name: string;
  parameter_value: number;
  parameter_unit: string;
  mathematical_rule: string;
  assumptions: string;
  limitations: string;
  simulated_trajectory: ScenarioPoint[];
  created_at: string;
}

export interface ScenarioComparison {
  patient_id: string;
  baseline_state_version: number;
  scenario_a: Scenario;
  scenario_b: Scenario;
  delta_summary: {
    max_absolute_delta_bpm: number;
    mean_absolute_delta_bpm: number;
    endpoint_delta_bpm: number;
    horizon_hours: number;
    step_count: number;
  };
  disclaimer: string;
}

export interface ModelEvaluation {
  patient_id: string;
  model_name: string;
  evaluation_period_start: string;
  evaluation_period_end: string;
  train_samples: number;
  test_samples: number;
  mae: number;
  rmse: number;
  baseline_mae: number;
  baseline_rmse: number;
  mae_improvement_pct: number;
  is_synthetic_data: boolean;
  disclaimer: string;
  created_at: string;
}

export interface Biomarker {
  name: string;
  key: string;
  value: string | number;
  unit: string;
  reference_range: string;
  status: 'normal' | 'elevated' | 'low';
  confidence?: string;
  requires_confirmation?: boolean;
}

export interface TumorMarkerItem {
  name: string;
  key: string;
  value: string | number;
  unit?: string;
  reference_range?: string;
  status?: string;
  snippet?: string;
  page_number?: number;
  confidence?: string;
}

export interface HistopathologyDiagnosis {
  specimen_site?: string;
  procedure?: string;
  stated_diagnosis?: string;
  histologic_type?: string;
  tumor_grade?: string;
  surgical_margins?: string;
  lymph_nodes?: string;
  lymphovascular_invasion?: string;
  perineural_invasion?: string;
  pathologic_stage?: string;
  is_malignant?: boolean;
  is_benign_or_negative?: boolean;
  page_number?: number;
  source_snippet?: string;
}

export interface IhcMarkerItem {
  marker: string;
  result: string;
  status?: string;
  percentage?: string;
  snippet?: string;
  page_number?: number;
}

export interface MolecularTestItem {
  gene: string;
  test_name?: string;
  alteration: string;
  clinical_significance?: string;
  vaf?: string;
  page_number?: number;
  snippet?: string;
}

export interface RadiologyFindings {
  modality?: string;
  study_name?: string;
  indication?: string;
  technique?: string;
  observations?: Array<{ region: string; observation: string }>;
  impression?: string;
  classification?: string;
  page_number?: number;
}

export interface LaboratoryParameterItem {
  name: string;
  key?: string;
  value: string | number;
  unit?: string;
  reference_range?: string;
  status?: string;
  snippet?: string;
  page_number?: number;
}

export interface ConsultationNotes {
  purpose?: string;
  context?: string;
  assessment?: string;
  next_steps?: string;
  limitations?: string;
}

export interface StructuredFindings {
  category_id?: string;
  specimen?: { site?: string; procedure?: string };
  diagnosis?: HistopathologyDiagnosis;
  tumor_markers?: TumorMarkerItem[];
  ihc_markers?: IhcMarkerItem[];
  molecular_tests?: MolecularTestItem[];
  radiology?: RadiologyFindings;
  laboratory_parameters?: LaboratoryParameterItem[];
  consultation_notes?: ConsultationNotes;
  vitals_for_twin?: Biomarker[];
  missing_fields?: string[];
  page_references?: Array<{ page_number: number; key_findings: string[] }>;
}

export interface SearchMatch {
  line_number: number;
  matched_line: string;
  snippet: string;
}

export interface MedicalReport {
  id: number;
  patient_id?: string;
  title: string;
  report_date: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  file_hash_sha256?: string;
  report_category?: string;
  category_name?: string;
  classification_confidence?: string;
  classification_evidence?: string[];
  processing_status?: 'Uploaded' | 'Text extracted' | 'Clinically structured' | 'Partially processed' | 'Needs review' | 'Failed';
  description?: string;
  summary?: string;
  clinical_summary?: string;
  structured_findings?: StructuredFindings;
  processing_warnings?: string[];
  extracted_text?: string;
  is_scanned?: boolean;
  biomarkers: Biomarker[];
  requires_review?: boolean;
  search_matches?: {
    query: string;
    matches_found: number;
    snippets: SearchMatch[];
  };
  created_at: string;
  upload_timestamp_ist?: string;
  persisted?: boolean;
  storage_reference?: string;
}

export interface ReportIntegrityVerification {
  report_id: number;
  patient_id: string;
  title: string;
  file_name: string;
  file_exists: boolean;
  file_size_bytes?: number;
  stored_sha256: string | null;
  recomputed_sha256: string | null;
  is_tamper_free: boolean;
  verification_status: string;
  verified_at: string;
}

export interface UserVideo {
  id: number;
  title: string;
  video_date: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  description?: string;
  stream_url: string;
  created_at: string;
}

export interface HealthCondition {
  id: number;
  condition_name: string;
  diagnosed_date?: string;
  severity: string;
  status: string;
  notes?: string;
  total_logs?: number;
  created_at: string;
}

export interface ConditionLog {
  id: number;
  condition_id?: number;
  condition_name?: string;
  log_date: string;
  metric_name: string;
  metric_value: number;
  metric_unit: string;
  symptoms?: string;
  notes?: string;
  created_at: string;
}

export interface DiseaseAnalytics {
  cardiovascular: {
    status: string;
    risk_level: string;
    latest_heart_rate_bpm: number;
    trend_slope_bpm_per_hr: number;
  };
  stress_fatigue: {
    score_0_to_100: number;
    status: string;
    physiological_variability: number;
  };
  body_mass_index: {
    bmi?: number;
    category?: string;
    height_cm?: number;
    body_weight_kg?: number;
  };
  tracking_summary: {
    monitored_conditions_count: number;
    total_timeline_logs: number;
  };
  disclaimer: string;
}

export interface CycleSummary {
  has_data: boolean;
  message?: string;
  last_period_start?: string;
  cycle_length_days?: number;
  period_length_days?: number;
  current_cycle_day?: number;
  current_phase?: string;
  phase_description?: string;
  days_until_next_period?: number;
  predicted_next_period?: string;
  fertile_window?: {
    start: string;
    end: string;
    is_in_fertile_window: boolean;
  };
  physiological_correlation?: {
    current_twin_heart_rate_bpm: number;
    expected_phase_shift: string;
  };
}

export interface CycleLog {
  id: number;
  start_date: string;
  end_date?: string;
  cycle_length_days: number;
  period_length_days: number;
  flow_intensity: string;
  symptoms?: string;
  notes?: string;
  created_at: string;
}
