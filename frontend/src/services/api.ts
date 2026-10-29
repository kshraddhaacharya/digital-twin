import axios from 'axios';
import {
  User,
  TokenResponse,
  Patient,
  Measurement,
  TwinState,
  Forecast,
  ScenarioComparison,
  ModelEvaluation,
  MedicalReport,
  UserVideo,
  HealthCondition,
  ConditionLog,
  DiseaseAnalytics,
  CycleSummary,
  CycleLog,
  ReportIntegrityVerification
} from '../types';

const API_BASE = '/api';

const client = axios.create({
  baseURL: API_BASE,
});

// Interceptor to attach JWT token to every request if available
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Auth & Session
  setToken: (token: string | null) => {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  },

  getToken: () => localStorage.getItem('auth_token'),

  register: async (payload: {
    full_name: string;
    email: string;
    password: string;
    age?: number;
    gender?: string;
    height?: number;
    body_weight?: number;
    existing_conditions?: string;
    allergies?: string;
    medications?: string;
    emergency_contact?: string;
    health_notes?: string;
  }): Promise<TokenResponse> => {
    const res = await client.post('/auth/register', payload);
    return res.data;
  },

  login: async (payload: { email: string; password: string }): Promise<TokenResponse> => {
    const res = await client.post('/auth/login', payload);
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await client.get('/auth/me');
    return res.data;
  },

  updateProfile: async (payload: Partial<User>): Promise<User> => {
    const res = await client.put('/auth/profile', payload);
    return res.data;
  },

  deleteAccount: async () => {
    const res = await client.delete('/auth/account');
    return res.data;
  },

  // Health
  getHealth: async () => {
    const res = await client.get('/health');
    return res.data;
  },

  // Patients
  getPatients: async (): Promise<Patient[]> => {
    const res = await client.get('/patients');
    return res.data;
  },

  getPatient: async (patientId: string): Promise<Patient> => {
    const res = await client.get(`/patients/${patientId}`);
    return res.data;
  },

  createPatient: async (data: Partial<Patient>): Promise<Patient> => {
    const res = await client.post('/patients', data);
    return res.data;
  },

  loadSyntheticPatient: async (params: {
    patient_id?: string;
    name?: string;
    baseline_hr?: number;
    duration_hours?: number;
    interval_minutes?: number;
    noise_level?: number;
    include_exercise_transient?: boolean;
  }) => {
    const res = await client.post('/patients/synthetic', params);
    return res.data;
  },

  // Measurements
  getMeasurements: async (patientId: string, limit: number = 200, type?: string): Promise<Measurement[]> => {
    const params: any = { limit };
    if (type) params.measurement_type = type;
    const res = await client.get(`/patients/${patientId}/measurements`, { params });
    return res.data;
  },

  addMeasurement: async (patientId: string, data: {
    timestamp: string;
    measurement_type: string;
    value: number;
    unit: string;
    source?: string;
    context?: string;
  }) => {
    const res = await client.post(`/patients/${patientId}/measurements`, data);
    return res.data;
  },

  uploadCsv: async (patientId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/patients/${patientId}/upload-csv`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  uploadJson: async (patientId: string, payload: any) => {
    const res = await client.post(`/patients/${patientId}/upload-json`, payload);
    return res.data;
  },

  uploadPdf: async (patientId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post(`/patients/${patientId}/upload-pdf`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  // Digital Twin
  getTwinState: async (patientId: string): Promise<TwinState> => {
    const res = await client.get(`/patients/${patientId}/twin`);
    return res.data;
  },

  getTwinHistory: async (patientId: string): Promise<TwinState[]> => {
    const res = await client.get(`/patients/${patientId}/twin/history`);
    return res.data;
  },

  initializeTwin: async (patientId: string): Promise<TwinState> => {
    const res = await client.post(`/patients/${patientId}/twin/initialize`);
    return res.data;
  },

  // Forecasting
  generateForecast: async (patientId: string, params: {
    horizon_minutes?: number;
    model_type?: string;
  }): Promise<Forecast> => {
    const res = await client.post(`/patients/${patientId}/forecast`, params);
    return res.data;
  },

  getForecasts: async (patientId: string, includeStale: boolean = true): Promise<Forecast[]> => {
    const res = await client.get(`/patients/${patientId}/forecasts`, {
      params: { include_stale: includeStale }
    });
    return res.data;
  },

  // Scenarios
  simulateScenarios: async (patientId: string, params: {
    horizon_minutes?: number;
    parameter_name?: string;
    parameter_value: number;
    parameter_unit?: string;
  }): Promise<ScenarioComparison> => {
    const res = await client.post(`/patients/${patientId}/simulate`, params);
    return res.data;
  },

  // Model Evaluation
  getEvaluation: async (patientId: string, splitRatio: number = 0.20): Promise<ModelEvaluation> => {
    const res = await client.get(`/patients/${patientId}/evaluation`, {
      params: { test_split_ratio: splitRatio }
    });
    return res.data;
  },

  // Web3 & Integrity
  getWeb3Status: async () => {
    const res = await client.get('/web3/status');
    return res.data;
  },

  verifyTwinStateOnChain: async (patientId: string, version: number) => {
    const res = await client.get(`/web3/patients/${patientId}/twin/${version}/verify`);
    return res.data;
  },

  grantAccessOnChain: async (patientId: string, researcherAddress: string, durationSeconds: number = 86400) => {
    const res = await client.post(`/web3/patients/${patientId}/access/grant`, {
      researcher_address: researcherAddress,
      duration_seconds: durationSeconds
    });
    return res.data;
  },

  revokeAccessOnChain: async (patientId: string, researcherAddress: string) => {
    const res = await client.post(`/web3/patients/${patientId}/access/revoke`, {
      researcher_address: researcherAddress
    });
    return res.data;
  },

  checkAccessOnChain: async (patientId: string, userAddress: string) => {
    const res = await client.get(`/web3/patients/${patientId}/access/check`, {
      params: { user_address: userAddress }
    });
    return res.data;
  },

  // Medical Reports (Upload & Search Engine)
  uploadReport: async (file: File, title: string, reportDate: string, description?: string, patientId?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('report_date', reportDate);
    if (description) formData.append('description', description);
    if (patientId) formData.append('patient_id', patientId);

    const res = await client.post('/reports/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getReports: async (search?: string, startDate?: string, endDate?: string, patientId?: string, category?: string): Promise<MedicalReport[]> => {
    const params: any = {};
    if (search) params.search = search;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (patientId) params.patient_id = patientId;
    if (category && category !== 'ALL') params.category = category;
    const res = await client.get('/reports', { params });
    return res.data;
  },

  getReportDetails: async (reportId: number, search?: string): Promise<MedicalReport> => {
    const params: any = {};
    if (search) params.search = search;
    const res = await client.get(`/reports/${reportId}`, { params });
    return res.data;
  },

  deleteReport: async (reportId: number) => {
    const res = await client.delete(`/reports/${reportId}`);
    return res.data;
  },

  syncReportTwin: async (reportId: number) => {
    const res = await client.post(`/reports/${reportId}/sync-twin`);
    return res.data;
  },

  confirmReportBiomarkers: async (reportId: number, data: {
    key: string;
    value: number;
    unit?: string;
    context?: string;
    observation_timestamp?: string;
    notes?: string;
  }) => {
    const res = await client.post(`/reports/${reportId}/confirm-biomarkers`, data);
    return res.data;
  },

  reprocessReport: async (reportId: number): Promise<{ success: boolean; message: string; report: MedicalReport }> => {
    const res = await client.post(`/reports/${reportId}/reprocess`);
    return res.data;
  },

  verifyReportIntegrity: async (reportId: number): Promise<ReportIntegrityVerification> => {
    const res = await client.get(`/reports/${reportId}/verify-integrity`);
    return res.data;
  },

  // Videos
  uploadVideo: async (file: File, title: string, videoDate: string, description?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('video_date', videoDate);
    if (description) formData.append('description', description);

    const res = await client.post('/videos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getVideos: async (): Promise<UserVideo[]> => {
    const res = await client.get('/videos');
    return res.data;
  },

  deleteVideo: async (videoId: number) => {
    const res = await client.delete(`/videos/${videoId}`);
    return res.data;
  },

  // Disease Tracker
  getConditions: async (): Promise<HealthCondition[]> => {
    const res = await client.get('/disease-tracker/conditions');
    return res.data;
  },

  createCondition: async (data: {
    condition_name: string;
    diagnosed_date?: string;
    severity?: string;
    status?: string;
    notes?: string;
  }): Promise<HealthCondition> => {
    const res = await client.post('/disease-tracker/conditions', data);
    return res.data;
  },

  deleteCondition: async (conditionId: number) => {
    const res = await client.delete(`/disease-tracker/conditions/${conditionId}`);
    return res.data;
  },

  getConditionLogs: async (conditionId?: number, metricName?: string): Promise<ConditionLog[]> => {
    const params: any = {};
    if (conditionId) params.condition_id = conditionId;
    if (metricName) params.metric_name = metricName;
    const res = await client.get('/disease-tracker/logs', { params });
    return res.data;
  },

  createConditionLog: async (data: {
    condition_id?: number;
    log_date: string;
    metric_name: string;
    metric_value: number;
    metric_unit: string;
    symptoms?: string;
    notes?: string;
  }): Promise<ConditionLog> => {
    const res = await client.post('/disease-tracker/logs', data);
    return res.data;
  },

  deleteConditionLog: async (logId: number) => {
    const res = await client.delete(`/disease-tracker/logs/${logId}`);
    return res.data;
  },

  getDiseaseAnalytics: async (): Promise<DiseaseAnalytics> => {
    const res = await client.get('/disease-tracker/analytics');
    return res.data;
  },

  // Menstrual Cycle Tracker
  getCycleSummary: async (): Promise<CycleSummary> => {
    const res = await client.get('/cycle/summary');
    return res.data;
  },

  getCycleHistory: async (): Promise<CycleLog[]> => {
    const res = await client.get('/cycle/history');
    return res.data;
  },

  logCycle: async (data: {
    start_date: string;
    end_date?: string;
    cycle_length_days?: number;
    period_length_days?: number;
    flow_intensity?: string;
    symptoms?: string;
    notes?: string;
  }) => {
    const res = await client.post('/cycle/log', data);
    return res.data;
  },

  deleteCycle: async (cycleId: number) => {
    const res = await client.delete(`/cycle/${cycleId}`);
    return res.data;
  },
};
