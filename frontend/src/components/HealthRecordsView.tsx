import React, { useState } from 'react';
import { RefreshCw, FileText, Activity } from 'lucide-react';
import { Measurement, TwinState, MedicalReport } from '../types';
import { RecordHistoryView } from './RecordHistoryView';
import { ReportsView } from './ReportsView';

interface HealthRecordsViewProps {
  patientId: string;
  measurements: Measurement[];
  twinState: TwinState | null;
  reports: MedicalReport[];
  initialSubTab?: 'measurements' | 'reports';
  onDataChanged: () => void;
  onNavigateTab: (tab: string) => void;
  onReportsChanged: () => void;
}

export const HealthRecordsView: React.FC<HealthRecordsViewProps> = ({
  patientId,
  measurements,
  twinState,
  reports,
  initialSubTab,
  onDataChanged,
  onNavigateTab,
  onReportsChanged,
}) => {
  const [subTab, setSubTab] = useState<'measurements' | 'reports'>(() => {
    if (initialSubTab === 'reports') return 'reports';
    const saved = localStorage.getItem('health_records_subtab');
    if (saved === 'reports' || saved === 'measurements') return saved;
    return initialSubTab || 'reports';
  });

  React.useEffect(() => {
    if (initialSubTab === 'reports') {
      setSubTab('reports');
      localStorage.setItem('health_records_subtab', 'reports');
    }
  }, [initialSubTab]);

  const handleSubTabChange = (tab: 'measurements' | 'reports') => {
    setSubTab(tab);
    localStorage.setItem('health_records_subtab', tab);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Subtab Selector */}
      <div className="bg-white p-2 rounded-2xl border-2 border-slate-200 shadow-sm flex items-center space-x-2 max-w-md mx-auto">
        <button
          onClick={() => handleSubTabChange('measurements')}
          className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl text-base font-extrabold transition ${
            subTab === 'measurements'
              ? 'bg-purple-700 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <Activity className="w-5 h-5" />
          <span>Vital Readings ({measurements.length})</span>
        </button>

        <button
          onClick={() => handleSubTabChange('reports')}
          className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl text-base font-extrabold transition ${
            subTab === 'reports'
              ? 'bg-purple-700 text-white shadow-sm'
              : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          <FileText className="w-5 h-5" />
          <span>Medical Reports ({reports.length})</span>
        </button>
      </div>

      {/* Subtab Content */}
      {subTab === 'measurements' ? (
        <RecordHistoryView
          patientId={patientId}
          measurements={measurements}
          twinState={twinState}
          onDataChanged={onDataChanged}
          onNavigateTab={onNavigateTab}
        />
      ) : (
        <ReportsView
          patientId={patientId}
          reports={reports}
          onReportsChanged={onReportsChanged}
          onNavigateToTwin={() => onNavigateTab('digital-twin')}
        />
      )}
    </div>
  );
};
