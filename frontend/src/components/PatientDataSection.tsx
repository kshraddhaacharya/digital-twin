import React, { useState } from 'react';
import {
  Upload,
  FileSpreadsheet,
  FileCode,
  FileText,
  AlertCircle,
  CheckCircle,
  Database,
  Filter,
  Search,
  Sparkles
} from 'lucide-react';
import { Measurement } from '../types';
import { api } from '../services/api';
import { formatIST } from '../utils/dateUtils';

interface PatientDataSectionProps {
  patientId: string;
  measurements: Measurement[];
  onDataChanged: () => void;
  onLoadSynthetic: () => void;
}

export const PatientDataSection: React.FC<PatientDataSectionProps> = ({
  patientId,
  measurements,
  onDataChanged,
  onLoadSynthetic,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [uploadStatus, setUploadStatus] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);

  // File upload handlers
  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setErrorMessage(null);
    setUploadStatus(null);

    try {
      const res = await api.uploadCsv(patientId, file);
      setUploadStatus(res);
      onDataChanged();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to parse CSV upload.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setErrorMessage(null);
    setUploadStatus(null);

    try {
      const res = await api.uploadPdf(patientId, file);
      setUploadStatus(res);
      onDataChanged();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to parse PDF report.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const filteredMeasurements = measurements.filter((m) => {
    if (filterType === 'all') return true;
    return m.measurement_type === filterType;
  });

  return (
    <div className="space-y-6">
      {/* Upload and Ingestion Methods Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Synthetic Telemetry Generator */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="p-3 bg-twin-50 text-twin-600 rounded-xl w-fit">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">
              Deterministic Synthetic Generator
            </h3>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              Generate 24 hours of physiologically plausible telemetry featuring circadian diurnal swings, transient exertion events, and autoregressive noise.
            </p>
          </div>
          <button
            onClick={onLoadSynthetic}
            className="mt-6 w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs py-2.5 px-4 rounded-lg shadow-sm transition-all"
          >
            Regenerate 24-hr Stream
          </button>
        </div>

        {/* Card 2: CSV Upload */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl w-fit">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">
              CSV Telemetry Ingestion
            </h3>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              Upload comma-separated observations. Required headers:{' '}
              <code className="text-slate-700 bg-slate-100 px-1 py-0.5 rounded font-mono text-[10px]">
                timestamp,measurement_type,value,unit
              </code>
            </p>
          </div>
          <label className="mt-6 w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs py-2.5 px-4 rounded-lg shadow-sm transition-all text-center cursor-pointer block">
            {uploading ? 'Processing...' : 'Upload CSV File'}
            <input
              type="file"
              accept=".csv"
              onChange={handleCsvUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>

        {/* Card 3: PDF Telemetry Report */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="p-3 bg-rose-50 text-rose-600 rounded-xl w-fit">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-slate-900 mt-4">
              Clinical PDF Report Parser
            </h3>
            <p className="text-xs text-slate-500 mt-2 leading-relaxed">
              Extracts heart rate observations from clinical telemetry PDFs using pypdf text parsing and regex pattern matching.
            </p>
          </div>
          <label className="mt-6 w-full bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs py-2.5 px-4 rounded-lg shadow-sm transition-all text-center cursor-pointer block">
            {uploading ? 'Extracting...' : 'Upload PDF Report'}
            <input
              type="file"
              accept=".pdf"
              onChange={handlePdfUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Ingestion Feedback Alerts */}
      {uploadStatus && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start space-x-3 text-xs text-emerald-950">
          <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="font-bold text-sm text-emerald-800">
              Batch Ingestion Completed
            </div>
            <p className="mt-1">
              Processed {uploadStatus.total_processed} records: <strong>{uploadStatus.valid_inserted} valid observations inserted</strong>, {uploadStatus.duplicates_skipped} duplicates skipped.
            </p>
            {uploadStatus.twin_state_version && (
              <p className="mt-1 font-semibold text-emerald-700">
                Digital Twin evolved to State Version {uploadStatus.twin_state_version}.
              </p>
            )}
            {uploadStatus.errors && uploadStatus.errors.length > 0 && (
              <div className="mt-2 text-rose-800 bg-rose-50 p-2 rounded border border-rose-200">
                <span className="font-bold">Validation Warnings:</span>
                <ul className="list-disc pl-4 mt-1 space-y-0.5">
                  {uploadStatus.errors.slice(0, 5).map((err: string, i: number) => (
                    <li key={i}>{err}</li>
                  ))}
                  {uploadStatus.errors.length > 5 && (
                    <li>...and {uploadStatus.errors.length - 5} more errors.</li>
                  )}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3 text-xs text-rose-950">
          <AlertCircle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-sm text-rose-800">Upload Processing Failed</div>
            <p className="mt-1">{errorMessage}</p>
          </div>
        </div>
      )}

      {/* Measurement Observation History Table */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Patient Measurement History ({filteredMeasurements.length} records)
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Immutable ledger of raw physiological telemetry observations.
            </p>
          </div>

          {/* Filter Controls */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 text-slate-800 font-medium"
            >
              <option value="all">All Measurement Types</option>
              <option value="heart_rate">Heart Rate only</option>
              <option value="systolic_bp">Systolic BP</option>
              <option value="diastolic_bp">Diastolic BP</option>
            </select>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto max-h-96">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">ID</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Timestamp (UTC)</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Type</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Observed Value</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Unit</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Source</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Late Arrival</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredMeasurements.slice(0, 100).map((m) => (
                <tr key={m.id} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 font-mono text-slate-400">#{m.id}</td>
                  <td className="px-4 py-2.5 text-slate-700 font-mono text-xs">
                    {formatIST(m.timestamp)}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded font-mono text-[11px]">
                      {m.measurement_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 font-bold text-slate-900">{m.value}</td>
                  <td className="px-4 py-2.5 text-slate-500">{m.unit}</td>
                  <td className="px-4 py-2.5 text-slate-500 truncate max-w-xs">{m.source}</td>
                  <td className="px-4 py-2.5">
                    {m.is_late_arrival ? (
                      <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded">
                        LATE
                      </span>
                    ) : (
                      <span className="text-slate-300">--</span>
                    )}
                  </td>
                </tr>
              ))}
              {filteredMeasurements.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                    No measurements match the selected filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
