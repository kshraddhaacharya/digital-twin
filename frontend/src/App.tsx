import React, { useState, useEffect } from 'react';
import { ArrowLeft, Home, Heart } from 'lucide-react';
import { LandingPage } from './components/LandingPage';
import { Navbar } from './components/Navbar';
import { DashboardView } from './components/DashboardView';
import { MyHealthView } from './components/MyHealthView';
import { DigitalTwinView } from './components/DigitalTwinView';
import { HealthRecordsView } from './components/HealthRecordsView';
import { DataIntegrityView } from './components/DataIntegrityView';
import { FutureOutlookView } from './components/FutureOutlookView';
import { RecordHistoryView } from './components/RecordHistoryView';
import { ProfileView } from './components/ProfileView';
import { ReportsView } from './components/ReportsView';
import { VideosView } from './components/VideosView';
import { DiseaseTrackerView } from './components/DiseaseTrackerView';
import { CycleTrackerView } from './components/CycleTrackerView';
import { api } from './services/api';
import {
  User,
  Patient,
  TwinState,
  Measurement,
  Forecast,
  MedicalReport,
  UserVideo,
  HealthCondition,
  ConditionLog,
  DiseaseAnalytics,
  CycleSummary,
  CycleLog
} from './types';

export function App() {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>('landing');
  const [tabHistory, setTabHistory] = useState<string[]>(['my-health']);

  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>(() => {
    return localStorage.getItem('selected_patient_id') || 'PT-DEMO-001';
  });

  const [currentPatient, setCurrentPatient] = useState<Patient | null>(null);
  const [twinState, setTwinState] = useState<TwinState | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [forecasts, setForecasts] = useState<Forecast[]>([]);

  // Features data
  const [reports, setReports] = useState<MedicalReport[]>([]);
  const [videos, setVideos] = useState<UserVideo[]>([]);
  const [conditions, setConditions] = useState<HealthCondition[]>([]);
  const [conditionLogs, setConditionLogs] = useState<ConditionLog[]>([]);
  const [diseaseAnalytics, setDiseaseAnalytics] = useState<DiseaseAnalytics | null>(null);
  const [cycleSummary, setCycleSummary] = useState<CycleSummary | null>(null);
  const [cycleHistory, setCycleHistory] = useState<CycleLog[]>([]);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const getTabDisplayName = (tab: string): string => {
    switch (tab) {
      case 'my-health': return '1. My Health';
      case 'digital-twin':
      case 'future-outlook': return '2. Digital Twin';
      case 'records':
      case 'record-history':
      case 'reports': return '3. Health Records';
      case 'integrity':
      case 'web3': return '4. Data Integrity';
      case 'dashboard': return 'Dashboard Overview';
      case 'videos': return 'Personal Videos';
      case 'disease-tracker': return 'Disease Tracker';
      case 'cycle-tracker': return 'Period Tracker';
      case 'profile': return 'My Health Profile';
      default: return tab;
    }
  };

  const navigateTab = (newTab: string) => {
    if (newTab === 'landing') {
      setActiveTab('landing');
      return;
    }
    setActiveTab(newTab);
    window.location.hash = newTab;
    setTabHistory((prev) => {
      if (prev[prev.length - 1] === newTab) return prev;
      return [...prev, newTab];
    });
  };

  const handleGoBack = () => {
    setTabHistory((prev) => {
      if (prev.length <= 1) {
        setActiveTab('my-health');
        window.location.hash = 'my-health';
        return ['my-health'];
      }
      const updated = prev.slice(0, -1);
      const target = updated[updated.length - 1] || 'my-health';
      setActiveTab(target);
      window.location.hash = target;
      return updated;
    });
  };

  // Sync hash routing on browser back/forward
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '');
      if (hash && hash !== activeTab) {
        setActiveTab(hash);
        setTabHistory((prev) => (prev[prev.length - 1] === hash ? prev : [...prev, hash]));
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [activeTab]);

  // Initialize session from token if available
  useEffect(() => {
    const initSession = async () => {
      const token = api.getToken();
      if (token) {
        try {
          const user = await api.getMe();
          setCurrentUser(user);
          setSelectedPatientId(user.patient_id);
          localStorage.setItem('selected_patient_id', user.patient_id);
          const currentHash = window.location.hash.replace('#', '');
          if (currentHash && currentHash !== 'landing') {
            setActiveTab(currentHash);
          } else {
            navigateTab('my-health');
          }
          await loadPatients(user.patient_id);
        } catch (err) {
          api.setToken(null);
          setCurrentUser(null);
          await loadPatients();
        }
      } else {
        await loadPatients();
      }
    };
    initSession();
  }, []);

  const loadPatients = async (preferredPid?: string) => {
    try {
      const pts = await api.getPatients();
      setPatients(pts);
      const activePid = preferredPid || selectedPatientId;
      if (pts.length > 0 && !pts.some((p) => p.id === activePid)) {
        setSelectedPatientId(pts[0].id);
        localStorage.setItem('selected_patient_id', pts[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch patients:', err);
    }
  };

  const loadReportsForPatient = async (patientId: string) => {
    try {
      const reps = await api.getReports(undefined, undefined, undefined, patientId);
      setReports(reps);
    } catch (err) {
      console.error('Failed to fetch patient reports:', err);
    }
  };

  const loadPatientData = async (patientId: string) => {
    setLoading(true);
    setError(null);
    try {
      const [ptData, tState, meas, fcs] = await Promise.allSettled([
        api.getPatient(patientId),
        api.getTwinState(patientId),
        api.getMeasurements(patientId, 300),
        api.getForecasts(patientId, true),
      ]);

      if (ptData.status === 'fulfilled') setCurrentPatient(ptData.value);
      if (tState.status === 'fulfilled') setTwinState(tState.value);
      else setTwinState(null);

      if (meas.status === 'fulfilled') setMeasurements(meas.value);
      else setMeasurements([]);

      if (fcs.status === 'fulfilled') setForecasts(fcs.value);
      else setForecasts([]);

      // Always load reports for current patient
      await loadReportsForPatient(patientId);
    } catch (err) {
      setError('Failed to load patient records.');
    } finally {
      setLoading(false);
    }
  };

  const loadUserFeatures = async () => {
    loadReportsForPatient(selectedPatientId);
    if (!currentUser) return;
    try {
      const [vids, conds, logs, analytics, cSum, cHist] = await Promise.allSettled([
        api.getVideos(),
        api.getConditions(),
        api.getConditionLogs(),
        api.getDiseaseAnalytics(),
        api.getCycleSummary(),
        api.getCycleHistory(),
      ]);

      if (vids.status === 'fulfilled') setVideos(vids.value);
      if (conds.status === 'fulfilled') setConditions(conds.value);
      if (logs.status === 'fulfilled') setConditionLogs(logs.value);
      if (analytics.status === 'fulfilled') setDiseaseAnalytics(analytics.value);
      if (cSum.status === 'fulfilled') setCycleSummary(cSum.value);
      if (cHist.status === 'fulfilled') setCycleHistory(cHist.value);
    } catch (err) {
      console.error('Error loading user features:', err);
    }
  };

  useEffect(() => {
    if (selectedPatientId) {
      loadPatientData(selectedPatientId);
    }
  }, [selectedPatientId]);

  useEffect(() => {
    if (currentUser) {
      loadUserFeatures();
    }
  }, [currentUser]);

  const handleLoginSuccess = (user: User) => {
    setCurrentUser(user);
    setSelectedPatientId(user.patient_id);
    localStorage.setItem('selected_patient_id', user.patient_id);
    navigateTab('my-health');
    loadPatients(user.patient_id);
    loadPatientData(user.patient_id);
  };

  const handleLogout = () => {
    api.setToken(null);
    setCurrentUser(null);
    localStorage.removeItem('selected_patient_id');
    navigateTab('landing');
  };

  const handleExploreDemo = () => {
    setSelectedPatientId('PT-DEMO-001');
    localStorage.setItem('selected_patient_id', 'PT-DEMO-001');
    navigateTab('my-health');
    loadPatientData('PT-DEMO-001');
  };

  const handleLoadSynthetic = async () => {
    setLoading(true);
    try {
      await api.loadSyntheticPatient({
        patient_id: 'PT-DEMO-001',
        name: 'Alice M. Taylor',
        baseline_hr: 72.0,
        duration_hours: 24,
      });
      await loadPatients();
      setSelectedPatientId('PT-DEMO-001');
      await loadPatientData('PT-DEMO-001');
      navigateTab('my-health');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load demo patient.');
      setLoading(false);
    }
  };

  // If user is on landing page, display the public landing page
  if (activeTab === 'landing' && !currentUser) {
    return (
      <LandingPage
        onLoginSuccess={handleLoginSuccess}
        onExploreDemo={handleExploreDemo}
      />
    );
  }

  // Authenticated or Demo Dashboard Layout
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900 font-sans" style={{ fontSize: '18px' }}>
      <Navbar
        user={currentUser}
        patients={patients}
        selectedPatientId={selectedPatientId}
        onSelectPatient={(id) => {
          setSelectedPatientId(id);
          localStorage.setItem('selected_patient_id', id);
        }}
        onRefresh={() => {
          loadPatientData(selectedPatientId);
          if (currentUser) loadUserFeatures();
        }}
        onLoadSynthetic={handleLoadSynthetic}
        activeTab={activeTab}
        setActiveTab={navigateTab}
        loading={loading}
        onLogout={handleLogout}
        onGoHome={() => navigateTab('landing')}
      />

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Navigation Breadcrumb and Universal Back Button */}
        {activeTab !== 'my-health' && activeTab !== 'landing' && (
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-2xl border-2 border-slate-200 shadow-sm">
            <div className="flex items-center space-x-2 text-sm text-slate-600 font-semibold">
              <button
                onClick={() => navigateTab('my-health')}
                className="hover:text-purple-700 hover:underline flex items-center space-x-1"
              >
                <Heart className="w-4 h-4 text-purple-600" />
                <span>My Health</span>
              </button>
              <span>/</span>
              <span className="text-slate-900 font-black">{getTabDisplayName(activeTab)}</span>
            </div>

            <button
              onClick={handleGoBack}
              className="inline-flex items-center space-x-2 bg-purple-50 hover:bg-purple-100 text-purple-900 font-extrabold text-sm px-4 py-2 rounded-xl border border-purple-200 transition active:scale-95 min-h-[40px] self-start sm:self-auto"
            >
              <ArrowLeft className="w-4 h-4 text-purple-700" />
              <span>Back to Previous Section</span>
            </button>
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border-2 border-red-300 text-red-900 rounded-2xl text-base font-semibold shadow-sm">
            {error}
          </div>
        )}

        {/* Primary Destination 1: My Health Screen */}
        {activeTab === 'my-health' && (
          <MyHealthView
            patient={currentPatient}
            twinState={twinState}
            recentMeasurements={measurements}
            onNavigateTab={(tab) => navigateTab(tab)}
            onLoadSynthetic={handleLoadSynthetic}
          />
        )}

        {/* Primary Destination 2: Digital Twin Simulation & Outlook */}
        {(activeTab === 'digital-twin' || activeTab === 'future-outlook') && (
          <DigitalTwinView
            patientId={selectedPatientId}
            twinState={twinState}
            measurements={measurements}
            forecasts={forecasts}
            onRefreshData={() => loadPatientData(selectedPatientId)}
          />
        )}

        {/* Primary Destination 3: Health Records & Lab Reports Hub */}
        {(activeTab === 'records' || activeTab === 'record-history' || activeTab === 'reports') && (
          <HealthRecordsView
            patientId={selectedPatientId}
            measurements={measurements}
            twinState={twinState}
            reports={reports}
            initialSubTab={activeTab === 'reports' ? 'reports' : undefined}
            onDataChanged={() => loadPatientData(selectedPatientId)}
            onNavigateTab={(tab) => navigateTab(tab)}
            onReportsChanged={loadUserFeatures}
          />
        )}

        {/* Primary Destination 4: Data Integrity & Sovereign Consent */}
        {(activeTab === 'integrity' || activeTab === 'web3') && (
          <DataIntegrityView
            patient={currentPatient}
            twinState={twinState}
            onRefresh={() => loadPatientData(selectedPatientId)}
          />
        )}

        {/* More Module 1: Personalized Dashboard Overview */}
        {activeTab === 'dashboard' && (
          <DashboardView
            user={currentUser || {
              id: 'USR-DEMO',
              email: 'demo@patient.org',
              full_name: currentPatient?.name || 'Alice M. Taylor',
              patient_id: selectedPatientId,
              gender: currentPatient?.gender || 'Female',
              age: currentPatient?.age || 56,
              height: currentPatient?.height_cm || 165,
              body_weight: currentPatient?.weight_kg || 68,
              existing_conditions: currentPatient?.medical_notes || 'Demonstration Patient',
              created_at: new Date().toISOString()
            }}
            twinState={twinState}
            recentMeasurements={measurements}
            reports={reports}
            videos={videos}
            diseaseAnalytics={diseaseAnalytics}
            onNavigate={(tab) => navigateTab(tab)}
            onQuickLoadDemo={handleLoadSynthetic}
          />
        )}

        {/* More Module 2: Personal Video Library */}
        {activeTab === 'videos' && (
          <VideosView
            videos={videos}
            onVideosChanged={loadUserFeatures}
          />
        )}

        {/* More Module 3: Disease Tracker & Timeline */}
        {activeTab === 'disease-tracker' && (
          <DiseaseTrackerView
            conditions={conditions}
            logs={conditionLogs}
            analytics={diseaseAnalytics}
            onDataChanged={loadUserFeatures}
          />
        )}

        {/* More Module 4: Period Cycle Tracker */}
        {activeTab === 'cycle-tracker' && (
          <CycleTrackerView
            summary={cycleSummary}
            history={cycleHistory}
            onDataChanged={loadUserFeatures}
          />
        )}

        {/* More Module 5: My Health Profile Management */}
        {activeTab === 'profile' && (
          <ProfileView
            user={currentUser || {
              id: 'USR-DEMO',
              email: 'demo@patient.org',
              full_name: currentPatient?.name || 'Alice M. Taylor',
              patient_id: selectedPatientId,
              gender: currentPatient?.gender || 'Female',
              age: currentPatient?.age || 56,
              height: currentPatient?.height_cm || 165,
              body_weight: currentPatient?.weight_kg || 68,
              existing_conditions: currentPatient?.medical_notes || 'Demonstration Patient',
              created_at: new Date().toISOString()
            }}
            onProfileUpdated={(updated) => {
              setCurrentUser(updated);
              loadUserFeatures();
            }}
            onLogout={handleLogout}
          />
        )}
      </main>

      {/* Reassuring Footer */}
      <footer className="bg-white border-t border-slate-200 py-6 mt-12 text-center text-slate-600 text-sm">
        <div className="max-w-5xl mx-auto px-4 space-y-2">
          <p className="font-semibold text-slate-800">
            HackLoop 2026: Sovereign Health Twin Platform
          </p>
          <p className="text-xs text-slate-500">
            Continuous Physiological Modeling • Web3 Ethereum Smart Contract Integrity • Medical Report Search • Privacy First.
            For research & educational purposes only.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
