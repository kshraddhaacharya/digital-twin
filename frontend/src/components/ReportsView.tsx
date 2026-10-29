import React, { useState, useEffect, useMemo } from 'react';
import {
  FileText,
  Upload,
  Search,
  CheckCircle2,
  AlertTriangle,
  Download,
  Trash2,
  RefreshCw,
  Sparkles,
  X,
  FileCheck,
  ChevronDown,
  ShieldCheck,
  HelpCircle,
  Clock,
  Layers,
  Activity,
  Microscope,
  Dna,
  Scan,
  FlaskConical,
  Eye,
  Check
} from 'lucide-react';
import { MedicalReport, ReportIntegrityVerification } from '../types';
import { api } from '../services/api';
import { formatISTDateOnly, formatIST } from '../utils/dateUtils';

interface ReportsViewProps {
  patientId: string;
  reports: MedicalReport[];
  onReportsChanged: () => void;
  onNavigateToTwin: () => void;
}

export const ReportsView: React.FC<ReportsViewProps> = ({
  patientId,
  reports,
  onReportsChanged,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [uploading, setUploading] = useState(false);
  const [reprocessingId, setReprocessingId] = useState<number | null>(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadDate, setUploadDate] = useState(new Date().toISOString().slice(0, 10));
  const [uploadDesc, setUploadDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Persistence & History State
  const [reportsList, setReportsList] = useState<MedicalReport[]>(reports || []);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [latestUploadedReport, setLatestUploadedReport] = useState<MedicalReport | null>(null);

  const [activeReport, setActiveReport] = useState<MedicalReport | null>(null);
  const [confirmModalReport, setConfirmModalReport] = useState<MedicalReport | null>(null);
  const [confirmedItems, setConfirmedItems] = useState<Record<string, { key: string; value: number; unit?: string; selected: boolean }>>({});
  const [confirmingBiomarkers, setConfirmingBiomarkers] = useState<boolean>(false);
  const [syncingId, setSyncingId] = useState<number | null>(null);
  const [bannerMsg, setBannerMsg] = useState<{ text: string; type: 'success' | 'error' | 'warning' } | null>(null);

  // Web3 Verification Modal State
  const [verifyingIntegrityId, setVerifyingIntegrityId] = useState<number | null>(null);
  const [integrityModalData, setIntegrityModalData] = useState<ReportIntegrityVerification | null>(null);

  // Fetch report history for current patient
  const fetchHistory = async (targetPatientId: string) => {
    if (!targetPatientId) return;
    setLoadingHistory(true);
    setHistoryError(null);
    try {
      const data = await api.getReports(undefined, undefined, undefined, targetPatientId);
      setReportsList(data);
    } catch (err: any) {
      console.error('[HealthRecords] Error retrieving saved medical records:', err);
      const detail = err.response?.data?.detail || err.message || 'Failed to retrieve saved medical records.';
      setHistoryError(detail);
    } finally {
      setLoadingHistory(false);
    }
  };

  // On mount or when patientId changes, fetch fresh history
  useEffect(() => {
    if (patientId) {
      setLatestUploadedReport(null);
      setSelectedReportId(null);
      setActiveReport(null);
      fetchHistory(patientId);
    }
  }, [patientId]);

  // Keep reportsList in sync if parent updates reports
  useEffect(() => {
    if (reports && reports.length > 0) {
      setReportsList(reports);
    }
  }, [reports]);

  // Determine currently displayed report:
  // 1. latestUploadedReport if user just uploaded
  // 2. Or explicitly selected report from history
  // 3. Or default to the newest saved report in history
  const displayedReport: MedicalReport | null = useMemo(() => {
    if (latestUploadedReport) return latestUploadedReport;
    if (selectedReportId) {
      const found = reportsList.find((r) => r.id === selectedReportId);
      if (found) return found;
    }
    if (reportsList.length > 0) {
      return reportsList[0];
    }
    return null;
  }, [latestUploadedReport, selectedReportId, reportsList]);

  const openConfirmModal = (report: MedicalReport) => {
    setConfirmModalReport(report);
    const initial: Record<string, { key: string; value: number; unit?: string; selected: boolean }> = {};
    (report.biomarkers || []).forEach((b) => {
      initial[b.key] = {
        key: b.key,
        value: typeof b.value === 'number' ? b.value : parseFloat(String(b.value)) || 0,
        unit: b.unit,
        selected: true,
      };
    });
    setConfirmedItems(initial);
  };

  const handleConfirmBiomarkers = async () => {
    if (!confirmModalReport) return;
    setConfirmingBiomarkers(true);
    try {
      const itemsToConfirm = Object.values(confirmedItems)
        .filter((i) => i.selected)
        .map((i) => ({ key: i.key, value: i.value, unit: i.unit }));

      if (itemsToConfirm.length === 0) {
        alert('Please select at least one extracted vital to confirm.');
        setConfirmingBiomarkers(false);
        return;
      }

      let confirmedCount = 0;
      for (const item of itemsToConfirm) {
        if (item.key === 'heart_rate') {
          await api.confirmReportBiomarkers(confirmModalReport.id, {
            key: item.key,
            value: item.value,
            unit: item.unit || 'bpm',
            context: 'resting',
          });
          confirmedCount++;
        }
      }

      setBannerMsg({
        text: `✓ Successfully confirmed ${confirmedCount} clinical vital reading(s)! Digital twin updated and anchored on-chain.`,
        type: 'success'
      });
      setConfirmModalReport(null);
      await fetchHistory(patientId);
      onReportsChanged();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to confirm biomarkers.');
    } finally {
      setConfirmingBiomarkers(false);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setBannerMsg({ text: 'Please select a PDF, JPG, or PNG report file to upload.', type: 'error' });
      return;
    }

    setUploading(true);
    setBannerMsg(null);
    try {
      const res = await api.uploadReport(selectedFile, uploadTitle, uploadDate, uploadDesc, patientId);
      setLatestUploadedReport(res.report);
      setSelectedReportId(res.report.id);
      const statusDesc = res.report.processing_status || 'Processed';
      const catDesc = res.report.category_name || res.report.report_category || 'Medical Report';
      const dupNotice = res.is_duplicate ? ' (Existing Record Retrieved)' : '';
      setBannerMsg({
        text: `Report "${res.report.title}" saved successfully!${dupNotice} Category: ${catDesc} • Extraction Status: ${statusDesc}.`,
        type: res.report.processing_status === 'Failed' ? 'error' : (res.report.processing_status === 'Needs review' ? 'warning' : 'success')
      });
      setUploadTitle('');
      setUploadDesc('');
      setSelectedFile(null);
      await fetchHistory(patientId);
      onReportsChanged();
    } catch (err: any) {
      setBannerMsg({
        text: err.response?.data?.detail || 'Failed to upload report. Please check file format and integrity.',
        type: 'error'
      });
    } finally {
      setUploading(false);
    }
  };

  const handleReprocess = async (reportId: number) => {
    setReprocessingId(reportId);
    setBannerMsg(null);
    try {
      const res = await api.reprocessReport(reportId);
      if (latestUploadedReport?.id === reportId) {
        setLatestUploadedReport(res.report);
      }
      if (activeReport?.id === reportId) {
        setActiveReport(res.report);
      }
      setBannerMsg({
        text: `Report #${reportId} re-analyzed and updated! Category: ${res.report.category_name || res.report.report_category} • Status: ${res.report.processing_status}.`,
        type: 'success'
      });
      await fetchHistory(patientId);
      onReportsChanged();
    } catch (err: any) {
      setBannerMsg({
        text: err.response?.data?.detail || 'Failed to reprocess report.',
        type: 'error'
      });
    } finally {
      setReprocessingId(null);
    }
  };

  const handleSyncToTwin = async (reportId: number) => {
    setSyncingId(reportId);
    setBannerMsg(null);
    try {
      const res = await api.syncReportTwin(reportId);
      setBannerMsg({
        text: `${res.message} Twin updated to Version ${res.twin_state_version} and verified on blockchain!`,
        type: 'success'
      });
      await fetchHistory(patientId);
      onReportsChanged();
    } catch (err: any) {
      setBannerMsg({
        text: err.response?.data?.detail || 'Failed to sync vital to Digital Twin.',
        type: 'error'
      });
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (reportId: number) => {
    if (!window.confirm(`Are you sure you want to permanently delete report #${reportId}?`)) return;
    try {
      await api.deleteReport(reportId);
      if (activeReport?.id === reportId) setActiveReport(null);
      if (latestUploadedReport?.id === reportId) setLatestUploadedReport(null);
      if (selectedReportId === reportId) setSelectedReportId(null);
      setBannerMsg({ text: `Report #${reportId} deleted successfully from database.`, type: 'success' });
      await fetchHistory(patientId);
      onReportsChanged();
    } catch (err: any) {
      setBannerMsg({ text: err.response?.data?.detail || 'Failed to delete report.', type: 'error' });
    }
  };

  const handleVerifyIntegrity = async (reportId: number) => {
    setVerifyingIntegrityId(reportId);
    try {
      const res = await api.verifyReportIntegrity(reportId);
      setIntegrityModalData(res);
    } catch (err: any) {
      setBannerMsg({
        text: err.response?.data?.detail || 'Failed to verify cryptographic integrity.',
        type: 'error'
      });
    } finally {
      setVerifyingIntegrityId(null);
    }
  };

  // Helper for Status Badge Styling
  const renderStatusBadge = (status?: string) => {
    switch (status) {
      case 'Clinically structured':
        return (
          <span className="bg-emerald-100 text-emerald-900 border border-emerald-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700" />
            <span>Clinically structured</span>
          </span>
        );
      case 'Partially processed':
        return (
          <span className="bg-amber-100 text-amber-900 border border-amber-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
            <span>Partially processed</span>
          </span>
        );
      case 'Needs review':
        return (
          <span className="bg-orange-100 text-orange-900 border border-orange-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <Clock className="w-3.5 h-3.5 text-orange-700" />
            <span>Needs review</span>
          </span>
        );
      case 'Failed':
        return (
          <span className="bg-red-100 text-red-900 border border-red-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <AlertTriangle className="w-3.5 h-3.5 text-red-700" />
            <span>Failed</span>
          </span>
        );
      case 'Text extracted':
        return (
          <span className="bg-blue-100 text-blue-900 border border-blue-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <FileText className="w-3.5 h-3.5 text-blue-700" />
            <span>Text extracted</span>
          </span>
        );
      default:
        return (
          <span className="bg-slate-100 text-slate-800 border border-slate-300 font-bold text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
            <Layers className="w-3.5 h-3.5 text-slate-600" />
            <span>Uploaded</span>
          </span>
        );
    }
  };

  // Helper for Category Icon and Label
  const renderCategoryPill = (catId?: string, catName?: string, confidence?: string) => {
    let icon = <FileText className="w-3.5 h-3.5 text-purple-600" />;
    if (catId === 'tumour_markers') icon = <FlaskConical className="w-3.5 h-3.5 text-pink-600" />;
    else if (catId === 'histopathology_biopsy') icon = <Microscope className="w-3.5 h-3.5 text-indigo-600" />;
    else if (catId === 'immunohistochemistry') icon = <Layers className="w-3.5 h-3.5 text-purple-600" />;
    else if (catId === 'molecular_genetics') icon = <Dna className="w-3.5 h-3.5 text-teal-600" />;
    else if (catId === 'radiology_imaging') icon = <Scan className="w-3.5 h-3.5 text-blue-600" />;
    else if (catId === 'cbc_routine_blood' || catId === 'biochemistry_metabolic') icon = <Activity className="w-3.5 h-3.5 text-rose-600" />;
    else if (catId === 'uncertain') icon = <HelpCircle className="w-3.5 h-3.5 text-amber-600" />;

    const displayName = catName || catId || 'General Report';
    return (
      <span className="bg-slate-100 border border-slate-300 text-slate-800 text-xs font-bold px-2.5 py-1 rounded-xl inline-flex items-center space-x-1.5">
        {icon}
        <span>{displayName}</span>
        {confidence && (
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-extrabold bg-white px-1.5 py-0.2 rounded border border-slate-200">
            {confidence}
          </span>
        )}
      </span>
    );
  };

  // Filter reports locally by search query and category from reportsList (database persisted)
  const filteredReports = reportsList.filter((r) => {
    if (categoryFilter !== 'ALL' && r.report_category !== categoryFilter) {
      return false;
    }
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const sf = r.structured_findings;
    const diagMatch = sf?.diagnosis?.stated_diagnosis?.toLowerCase().includes(q);
    const tmMatch = sf?.tumor_markers?.some((tm) => tm.name.toLowerCase().includes(q));
    const ihcMatch = sf?.ihc_markers?.some((ihc) => ihc.marker.toLowerCase().includes(q));
    const molMatch = sf?.molecular_tests?.some((mol) => mol.gene.toLowerCase().includes(q));
    const radMatch = sf?.radiology?.impression?.toLowerCase().includes(q);
    return (
      r.title.toLowerCase().includes(q) ||
      (r.description && r.description.toLowerCase().includes(q)) ||
      (r.clinical_summary && r.clinical_summary.toLowerCase().includes(q)) ||
      (r.extracted_text && r.extracted_text.toLowerCase().includes(q)) ||
      (r.category_name && r.category_name.toLowerCase().includes(q)) ||
      (r.biomarkers || []).some((b) => b.name.toLowerCase().includes(q)) ||
      diagMatch ||
      tmMatch ||
      ihcMatch ||
      molMatch ||
      radMatch
    );
  });

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center space-x-3">
            <FileText className="w-8 h-8 text-blue-600" />
            <span>Medical Records & Oncology Diagnostic Reader</span>
          </h1>
          <p className="text-slate-600 text-base mt-1">
            Upload oncology pathology, tumour marker panels, biopsy reports, radiology scans, and laboratory blood tests.
            Automatic medical classification, grounded clinical summaries, and Web3 off-chain cryptographic provenance.
          </p>
        </div>
      </div>

      {bannerMsg && (
        <div
          className={`p-4 rounded-2xl text-base font-semibold flex items-center space-x-2 border-2 ${
            bannerMsg.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : bannerMsg.type === 'warning'
              ? 'bg-amber-50 border-amber-300 text-amber-900'
              : 'bg-red-50 border-red-300 text-red-900'
          }`}
        >
          {bannerMsg.type === 'success' ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
          )}
          <span>{bannerMsg.text}</span>
        </div>
      )}

      {/* Upload Form Card */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-6">
        <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2 border-b border-slate-200 pb-3">
          <Upload className="w-5 h-5 text-purple-700" />
          <span>Upload Medical or Laboratory Report</span>
        </h2>

        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Report Title *</label>
              <input
                type="text"
                required
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="e.g. Surgical Pathology Biopsy or Serum Tumor Marker Panel"
                className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
              />
            </div>

            <div>
              <label className="block text-sm font-bold text-slate-700 mb-1">Report Date *</label>
              <input
                type="date"
                required
                value={uploadDate}
                onChange={(e) => setUploadDate(e.target.value)}
                className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Optional Notes / Clinical Description</label>
            <input
              type="text"
              value={uploadDesc}
              onChange={(e) => setUploadDesc(e.target.value)}
              placeholder="e.g. Performed at Regional Cancer Center following outpatient excision"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">
              Select Document File (PDF, JPG, JPEG, PNG • max 25MB) *
            </label>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              required
              onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
              className="w-full p-2.5 bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl text-sm font-medium cursor-pointer"
            />
          </div>

          <button
            type="submit"
            disabled={uploading}
            className="bg-purple-700 hover:bg-purple-800 text-white font-extrabold text-lg px-8 py-3.5 rounded-2xl shadow-md transition flex items-center space-x-2 min-h-[48px] disabled:opacity-50"
          >
            <Upload className="w-5 h-5" />
            <span>{uploading ? 'Classifying & Structuring Document...' : 'Upload & Analyze Document'}</span>
          </button>
        </form>
      </div>

      {/* ACTIVE / DISPLAYED REPORT CARD */}
      {displayedReport && (
        <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-purple-400 shadow-md space-y-6 animate-in fade-in duration-200">
          {/* Header row */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-purple-100 pb-4">
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="bg-purple-100 text-purple-900 font-bold text-xs px-3 py-1 rounded-full uppercase">
                  {latestUploadedReport && displayedReport.id === latestUploadedReport.id ? 'Latest Uploaded Record' : `Saved Health Record #${displayedReport.id}`}
                </span>
                {renderStatusBadge(displayedReport.processing_status)}
                {renderCategoryPill(
                  displayedReport.report_category,
                  displayedReport.category_name,
                  displayedReport.classification_confidence
                )}
                {displayedReport.file_hash_sha256 && (
                  <span
                    className="bg-slate-100 text-slate-700 border border-slate-300 font-mono text-[11px] px-2.5 py-0.5 rounded-full flex items-center space-x-1"
                    title={`Cryptographic SHA-256: ${displayedReport.file_hash_sha256}`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                    <span>SHA-256: {displayedReport.file_hash_sha256.substring(0, 8)}...</span>
                  </span>
                )}
              </div>
              <h3 className="text-2xl font-black text-slate-900">{displayedReport.title}</h3>
              <p className="text-xs text-slate-500 font-semibold">
                Report Date: {formatISTDateOnly(displayedReport.report_date)} • Uploaded: {displayedReport.upload_timestamp_ist || formatIST(displayedReport.created_at)} • Format: {displayedReport.file_type?.toUpperCase()} ({(displayedReport.file_size_bytes / 1024).toFixed(1)} KB) • Patient: {displayedReport.patient_id || patientId}
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleVerifyIntegrity(displayedReport.id)}
                disabled={verifyingIntegrityId === displayedReport.id}
                className="bg-blue-50 hover:bg-blue-100 text-blue-900 font-bold text-xs px-3 py-1.5 rounded-xl border border-blue-200 flex items-center space-x-1 transition"
                title="Verify Web3 cryptographic integrity against storage file"
              >
                <ShieldCheck className={`w-3.5 h-3.5 ${verifyingIntegrityId === displayedReport.id ? 'animate-spin' : 'text-blue-600'}`} />
                <span>{verifyingIntegrityId === displayedReport.id ? 'Verifying...' : 'Verify Hash'}</span>
              </button>
              <a
                href={`/api/reports/${displayedReport.id}/download`}
                target="_blank"
                rel="noreferrer"
                className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs px-3 py-1.5 rounded-xl border border-slate-300 flex items-center space-x-1 transition"
                title="Download original report file"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download</span>
              </a>
              <button
                onClick={() => handleReprocess(displayedReport.id)}
                disabled={reprocessingId === displayedReport.id}
                className="bg-purple-50 hover:bg-purple-100 text-purple-900 font-bold text-xs px-3 py-1.5 rounded-xl border border-purple-200 flex items-center space-x-1 transition"
                title="Re-analyze extraction"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${reprocessingId === displayedReport.id ? 'animate-spin' : ''}`} />
                <span>{reprocessingId === displayedReport.id ? 'Processing...' : 'Re-analyze'}</span>
              </button>
              <button
                onClick={() => {
                  setSelectedReportId(null);
                  setLatestUploadedReport(null);
                }}
                className="text-slate-400 hover:text-slate-600 p-2 rounded-xl transition"
                title="Dismiss viewer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Warnings Banner if Partially Processed or Uncertain */}
          {displayedReport.processing_warnings && displayedReport.processing_warnings.length > 0 && (
            <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-2xl text-amber-950 space-y-1">
              <div className="flex items-center space-x-2 font-bold text-sm text-amber-900">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Extraction Notice & Incomplete Fields</span>
              </div>
              <ul className="list-disc list-inside text-xs text-amber-800 space-y-0.5">
                {displayedReport.processing_warnings.map((w, idx) => (
                  <li key={idx}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Grounded Clinical Summary Box */}
          <div className="p-5 bg-purple-50/80 border-2 border-purple-200 rounded-2xl space-y-2">
            <h4 className="text-sm font-bold text-purple-950 flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-purple-700" />
              <span>Grounded Clinical Summary</span>
            </h4>
            <div className="text-sm text-slate-800 leading-relaxed font-medium whitespace-pre-line">
              {displayedReport.clinical_summary || displayedReport.summary || displayedReport.description || 'Document uploaded and analyzed.'}
            </div>
          </div>

          {/* Structured Findings: Category-Specific Visuals */}
          {/* A. Tumour Markers */}
          {displayedReport.structured_findings?.tumor_markers && displayedReport.structured_findings.tumor_markers.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-2">
                <FlaskConical className="w-4 h-4 text-pink-600" />
                <span>Extracted Tumour Markers ({displayedReport.structured_findings.tumor_markers.length}):</span>
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse bg-slate-50 rounded-2xl overflow-hidden border border-slate-200">
                  <thead className="bg-slate-100 text-slate-700 font-extrabold text-xs uppercase border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Tumour Marker</th>
                      <th className="px-4 py-3">Reported Value</th>
                      <th className="px-4 py-3">Unit</th>
                      <th className="px-4 py-3">Reference Range</th>
                      <th className="px-4 py-3">Clinical Status</th>
                      <th className="px-4 py-3 text-right">Source Context</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 font-semibold text-slate-900">
                    {displayedReport.structured_findings.tumor_markers.map((tm, idx) => (
                      <tr key={idx} className="hover:bg-white transition-colors">
                        <td className="px-4 py-3 font-bold text-slate-900">{tm.name}</td>
                        <td className="px-4 py-3">
                          <span className={`text-base font-black ${tm.status === 'elevated' ? 'text-amber-700' : 'text-purple-900'}`}>
                            {tm.value}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600 font-mono">{tm.unit || <span className="text-slate-400 italic">Unspecified</span>}</td>
                        <td className="px-4 py-3 text-xs text-slate-600 font-mono">{tm.reference_range || <span className="text-slate-400 italic">Not stated</span>}</td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold capitalize ${
                              tm.status === 'elevated'
                                ? 'bg-amber-100 text-amber-800 border border-amber-300'
                                : tm.status === 'normal'
                                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                                : 'bg-slate-100 text-slate-700 border border-slate-300'
                            }`}
                          >
                            {tm.status || 'Reported'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right text-[11px] text-slate-500 max-w-xs truncate" title={tm.snippet}>
                          Page {tm.page_number || 1} • {tm.snippet || 'Extracted'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* B. Histopathology Findings */}
          {displayedReport.structured_findings?.diagnosis && (displayedReport.structured_findings.diagnosis.stated_diagnosis || displayedReport.structured_findings.diagnosis.histologic_type) && (
            <div className="p-5 bg-indigo-50/60 border-2 border-indigo-200 rounded-2xl space-y-3">
              <h4 className="text-sm font-bold text-indigo-950 flex items-center space-x-2">
                <Microscope className="w-4 h-4 text-indigo-600" />
                <span>Histopathology & Biopsy Findings</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                {displayedReport.structured_findings.diagnosis.specimen_site && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Specimen / Site</span>
                    <span className="font-extrabold text-slate-900 text-sm">{displayedReport.structured_findings.diagnosis.specimen_site}</span>
                  </div>
                )}
                {displayedReport.structured_findings.diagnosis.stated_diagnosis && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100 sm:col-span-2">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Documented Diagnosis</span>
                    <span className="font-extrabold text-indigo-950 text-sm">{displayedReport.structured_findings.diagnosis.stated_diagnosis}</span>
                  </div>
                )}
                {displayedReport.structured_findings.diagnosis.tumor_grade && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Histologic Grade</span>
                    <span className="font-extrabold text-slate-900 text-sm">{displayedReport.structured_findings.diagnosis.tumor_grade}</span>
                  </div>
                )}
                {displayedReport.structured_findings.diagnosis.surgical_margins && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Surgical Margins</span>
                    <span className="font-extrabold text-slate-900 text-sm">{displayedReport.structured_findings.diagnosis.surgical_margins}</span>
                  </div>
                )}
                {displayedReport.structured_findings.diagnosis.lymph_nodes && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Lymph Nodes</span>
                    <span className="font-extrabold text-slate-900 text-sm">{displayedReport.structured_findings.diagnosis.lymph_nodes}</span>
                  </div>
                )}
                {displayedReport.structured_findings.diagnosis.pathologic_stage && (
                  <div className="bg-white p-3 rounded-xl border border-indigo-100">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Pathologic Stage</span>
                    <span className="font-extrabold text-indigo-700 text-sm">{displayedReport.structured_findings.diagnosis.pathologic_stage}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* C. IHC Markers */}
          {displayedReport.structured_findings?.ihc_markers && displayedReport.structured_findings.ihc_markers.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-2">
                <Layers className="w-4 h-4 text-purple-600" />
                <span>Immunohistochemistry (IHC) Profile ({displayedReport.structured_findings.ihc_markers.length}):</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {displayedReport.structured_findings.ihc_markers.map((ihc, idx) => (
                  <div key={idx} className="bg-purple-50/50 p-3.5 rounded-2xl border border-purple-200 text-xs space-y-1">
                    <span className="font-bold text-slate-700">{ihc.marker}</span>
                    <p className="text-sm font-extrabold text-purple-950">{ihc.result}</p>
                    <span className="text-[10px] text-slate-500 block">Page {ihc.page_number || 1}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* D. Molecular & Genetic Tests */}
          {displayedReport.structured_findings?.molecular_tests && displayedReport.structured_findings.molecular_tests.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-2">
                <Dna className="w-4 h-4 text-teal-600" />
                <span>Molecular & Genomic Variations ({displayedReport.structured_findings.molecular_tests.length}):</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {displayedReport.structured_findings.molecular_tests.map((mol, idx) => (
                  <div key={idx} className="bg-teal-50/50 p-3.5 rounded-2xl border border-teal-200 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-extrabold text-teal-950 text-sm">{mol.gene}</span>
                      <span className="bg-teal-100 text-teal-900 font-bold px-2 py-0.5 rounded-full text-[10px]">
                        {mol.clinical_significance}
                      </span>
                    </div>
                    <p className="text-xs text-slate-800 font-medium">{mol.alteration}</p>
                    {mol.vaf && <span className="text-[10px] text-teal-800 font-mono block">VAF: {mol.vaf}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* E. Radiology & Imaging */}
          {displayedReport.structured_findings?.radiology && displayedReport.structured_findings.radiology.impression && (
            <div className="p-5 bg-blue-50/60 border-2 border-blue-200 rounded-2xl space-y-3">
              <h4 className="text-sm font-bold text-blue-950 flex items-center space-x-2">
                <Scan className="w-4 h-4 text-blue-600" />
                <span>Radiology & Imaging Assessment</span>
              </h4>
              <div className="text-xs space-y-2">
                {displayedReport.structured_findings.radiology.modality && (
                  <span className="bg-blue-100 text-blue-900 font-bold px-2.5 py-1 rounded-lg text-xs inline-block">
                    Modality: {displayedReport.structured_findings.radiology.modality}
                  </span>
                )}
                <div className="bg-white p-3 rounded-xl border border-blue-100">
                  <span className="font-bold text-slate-500 uppercase block text-[10px]">Radiologist Stated Impression</span>
                  <p className="text-sm font-extrabold text-blue-950 mt-0.5">{displayedReport.structured_findings.radiology.impression}</p>
                </div>
              </div>
            </div>
          )}

          {/* F. Routine Blood & Metabolic Tests */}
          {displayedReport.structured_findings?.laboratory_parameters && displayedReport.structured_findings.laboratory_parameters.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-2">
                <Activity className="w-4 h-4 text-rose-600" />
                <span>Laboratory Parameters ({displayedReport.structured_findings.laboratory_parameters.length}):</span>
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
                {displayedReport.structured_findings.laboratory_parameters.map((lab, idx) => (
                  <div key={idx} className="bg-slate-50 p-2.5 rounded-xl border border-slate-200 text-xs">
                    <span className="font-bold text-slate-700 block truncate">{lab.name}</span>
                    <span className="text-sm font-black text-slate-900">{lab.value} <span className="text-[10px] text-slate-500 font-normal">{lab.unit}</span></span>
                    <span className="text-[10px] text-slate-500 block truncate">Ref: {lab.reference_range || 'Standard'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* G. Consultation Notes & Risk Assessments */}
          {displayedReport.structured_findings?.consultation_notes && (
            <div className="p-5 bg-slate-50 border-2 border-slate-300 rounded-2xl space-y-3">
              <h4 className="text-sm font-bold text-slate-900 flex items-center space-x-2">
                <FileText className="w-4 h-4 text-purple-700" />
                <span>Clinical Consultation & Document Context</span>
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                {displayedReport.structured_findings.consultation_notes.purpose && (
                  <div className="bg-white p-3 rounded-xl border border-slate-200">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Document Purpose</span>
                    <span className="font-extrabold text-slate-900">{displayedReport.structured_findings.consultation_notes.purpose}</span>
                  </div>
                )}
                {displayedReport.structured_findings.consultation_notes.next_steps && (
                  <div className="bg-white p-3 rounded-xl border border-slate-200">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Recommended Actions</span>
                    <span className="font-medium text-slate-800">{displayedReport.structured_findings.consultation_notes.next_steps}</span>
                  </div>
                )}
                {displayedReport.structured_findings.consultation_notes.context && (
                  <div className="bg-white p-3 rounded-xl border border-slate-200 sm:col-span-2">
                    <span className="font-bold text-slate-500 uppercase block text-[10px]">Stated Clinical Context</span>
                    <span className="font-medium text-slate-800">{displayedReport.structured_findings.consultation_notes.context}</span>
                  </div>
                )}
                {displayedReport.structured_findings.consultation_notes.limitations && (
                  <div className="bg-amber-50/50 p-3 rounded-xl border border-amber-200 sm:col-span-2">
                    <span className="font-bold text-amber-800 uppercase block text-[10px]">Documented Limitations</span>
                    <span className="font-medium text-amber-900">{displayedReport.structured_findings.consultation_notes.limitations}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* G. Physiological Vitals for Digital Twin Sync */}
          {displayedReport.biomarkers && displayedReport.biomarkers.some((b) => b.key === 'heart_rate') && (
            <div className="p-4 bg-emerald-50/80 border-2 border-emerald-300 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h5 className="font-bold text-sm text-emerald-950 flex items-center space-x-1.5">
                  <Activity className="w-4 h-4 text-emerald-600" />
                  <span>Physiological Vital Detected (Heart Rate)</span>
                </h5>
                <p className="text-xs text-emerald-800 mt-0.5">
                  Review and confirm this reading to synchronize and advance your persistent Digital Twin state.
                </p>
              </div>
              <button
                onClick={() => openConfirmModal(displayedReport)}
                className="bg-emerald-700 hover:bg-emerald-800 text-white font-extrabold text-xs px-4 py-2.5 rounded-xl shadow-sm transition flex items-center space-x-1.5 self-start sm:self-auto"
              >
                <FileCheck className="w-4 h-4" />
                <span>Review & Confirm Vital</span>
              </button>
            </div>
          )}

          {/* Raw Extracted Text Preview */}
          {displayedReport.extracted_text && (
            <details className="mt-3 group">
              <summary className="cursor-pointer text-xs font-bold text-purple-700 hover:text-purple-900 flex items-center space-x-1 select-none">
                <span>View Full Extracted Document Text</span>
                <ChevronDown className="w-4 h-4 transition group-open:rotate-180" />
              </summary>
              <div className="mt-2 p-4 bg-slate-900 text-slate-100 rounded-2xl font-mono text-xs whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed border border-slate-700">
                {displayedReport.extracted_text}
              </div>
            </details>
          )}
        </div>
      )}

      {/* Search Engine & Report Library */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Search className="w-5 h-5 text-purple-700" />
              <span>Report Library & Search Engine</span>
            </h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Full-text keyword search across parsed text, oncology findings, diagnoses, and tumor markers.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="p-2.5 bg-slate-50 border-2 border-slate-300 rounded-xl text-xs font-bold text-slate-700 focus:outline-none focus:border-purple-700"
            >
              <option value="ALL">All Report Types</option>
              <option value="tumour_markers">Tumour Markers</option>
              <option value="histopathology_biopsy">Histopathology & Biopsy</option>
              <option value="immunohistochemistry">Immunohistochemistry (IHC)</option>
              <option value="molecular_genetics">Molecular & Genetic Tests</option>
              <option value="radiology_imaging">Radiology & Imaging</option>
              <option value="cbc_routine_blood">Complete Blood Count (CBC)</option>
              <option value="biochemistry_metabolic">Biochemistry & Metabolic</option>
              <option value="uncertain">Report Type Uncertain</option>
            </select>

            {/* Search Bar */}
            <div className="relative w-full sm:w-64">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search e.g. PSA, CEA, biopsy, CT..."
                className="w-full pl-9 pr-3 py-2 bg-slate-50 border-2 border-slate-300 rounded-xl text-sm font-semibold focus:outline-none focus:border-purple-700"
              />
            </div>

            {/* Reload History Button */}
            <button
              onClick={() => {
                fetchHistory(patientId);
                onReportsChanged?.();
              }}
              disabled={loadingHistory}
              className="p-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl border border-slate-300 font-bold text-xs flex items-center space-x-1.5 transition"
              title="Reload saved medical report history from database"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingHistory ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">{loadingHistory ? 'Fetching...' : 'Reload'}</span>
            </button>
          </div>
        </div>

        {/* Loading State */}
        {loadingHistory && (
          <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200 flex flex-col items-center justify-center space-y-2">
            <RefreshCw className="w-6 h-6 text-purple-700 animate-spin" />
            <p className="text-sm font-semibold text-slate-600">Retrieving permanent health records from database...</p>
          </div>
        )}

        {/* Error Alert with Retry */}
        {!loadingHistory && historyError && (
          <div className="p-4 bg-red-50 border-2 border-red-300 rounded-2xl text-red-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2 text-sm font-semibold">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <span>{historyError}</span>
            </div>
            <button
              onClick={() => {
                fetchHistory(patientId);
                onReportsChanged?.();
              }}
              className="bg-red-600 hover:bg-red-700 text-white font-bold text-xs px-4 py-2 rounded-xl transition self-start sm:self-auto"
            >
              Retry Loading History
            </button>
          </div>
        )}

        {/* Reports List */}
        {!loadingHistory && !historyError && filteredReports.length === 0 ? (
          <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200">
            {reportsList.length === 0 ? (
              <>
                <p className="text-base font-bold text-slate-700">No medical reports found for this patient.</p>
                <p className="text-sm text-slate-500 mt-1">
                  Upload your lab results or test sheets above to start searching. Saved reports persist across sessions and page refreshes.
                </p>
              </>
            ) : (
              <>
                <p className="text-base font-bold text-slate-700">No matching medical reports found.</p>
                <p className="text-sm text-slate-500 mt-1">
                  No saved reports match your search query &ldquo;{searchQuery}&rdquo; or selected category filter. Try clearing your filters or searching for different keywords.
                </p>
              </>
            )}
          </div>
        ) : !loadingHistory && !historyError && (
          <div className="grid grid-cols-1 gap-4">
            {filteredReports.map((report) => {
              const isSelected = displayedReport?.id === report.id;
              return (
                <div
                  key={report.id}
                  className={`p-5 rounded-2xl border-2 transition shadow-sm space-y-3 ${
                    isSelected
                      ? 'border-purple-500 bg-purple-50/20 shadow-md ring-2 ring-purple-200'
                      : 'border-slate-200 bg-white hover:border-purple-300'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="bg-purple-100 text-purple-900 font-extrabold text-xs px-2.5 py-0.5 rounded-full">
                          #{report.id}
                        </span>
                        <span className="font-black text-lg text-slate-900">{report.title}</span>
                        {renderStatusBadge(report.processing_status)}
                        {renderCategoryPill(report.report_category, report.category_name, report.classification_confidence)}
                        {report.file_hash_sha256 && (
                          <span className="bg-slate-50 text-slate-600 border border-slate-200 text-[10px] font-mono px-2 py-0.5 rounded-full flex items-center space-x-1">
                            <ShieldCheck className="w-3 h-3 text-blue-600" />
                            <span>SHA-256: {report.file_hash_sha256.substring(0, 8)}...</span>
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 font-semibold">
                        Date: {formatISTDateOnly(report.report_date)} • Uploaded: {report.upload_timestamp_ist || formatIST(report.created_at)} • File: {report.file_name} ({(report.file_size_bytes / 1024).toFixed(1)} KB) • Patient: {report.patient_id || patientId}
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5">
                      <button
                        onClick={() => {
                          setSelectedReportId(report.id);
                          setLatestUploadedReport(null);
                          window.scrollTo({ top: 380, behavior: 'smooth' });
                        }}
                        className={`font-bold px-3 py-1.5 rounded-xl border text-xs flex items-center space-x-1 transition ${
                          isSelected
                            ? 'bg-purple-700 text-white border-purple-700'
                            : 'bg-purple-50 hover:bg-purple-100 text-purple-900 border-purple-200'
                        }`}
                        title="Display full structured findings and grounded summary in main card above"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{isSelected ? 'Viewing Findings' : 'View Findings'}</span>
                      </button>

                      <button
                        onClick={() => handleVerifyIntegrity(report.id)}
                        disabled={verifyingIntegrityId === report.id}
                        className="bg-blue-50 hover:bg-blue-100 text-blue-900 font-bold px-2.5 py-1.5 rounded-xl border border-blue-200 text-xs flex items-center space-x-1 transition"
                        title="Verify cryptographic integrity against stored document bytes"
                      >
                        <ShieldCheck className={`w-3.5 h-3.5 ${verifyingIntegrityId === report.id ? 'animate-spin' : 'text-blue-600'}`} />
                        <span>{verifyingIntegrityId === report.id ? 'Verifying...' : 'Verify Hash'}</span>
                      </button>

                      <button
                        onClick={() => setActiveReport(report)}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold px-2.5 py-1.5 rounded-xl border border-slate-300 text-xs flex items-center space-x-1"
                        title="Open raw extracted document text"
                      >
                        <FileText className="w-3.5 h-3.5 text-slate-600" />
                        <span>Text</span>
                      </button>

                      <button
                        onClick={() => handleReprocess(report.id)}
                        disabled={reprocessingId === report.id}
                        className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold px-2.5 py-1.5 rounded-xl border border-slate-300 text-xs flex items-center space-x-1"
                        title="Re-analyze extraction"
                      >
                        <RefreshCw className={`w-3 h-3 ${reprocessingId === report.id ? 'animate-spin' : ''}`} />
                        <span>Retry</span>
                      </button>

                      <a
                        href={`/api/reports/${report.id}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold px-2.5 py-1.5 rounded-xl border border-slate-300 text-xs flex items-center space-x-1"
                        title="Download original document"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF</span>
                      </a>

                      <button
                        onClick={() => handleDelete(report.id)}
                        className="text-red-600 hover:bg-red-50 p-2 rounded-xl transition"
                        title="Delete report permanently from database"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Grounded Summary Preview */}
                  {report.clinical_summary || report.summary ? (
                    <div className="p-3 bg-purple-50/60 rounded-xl border border-purple-100 text-xs text-slate-800 leading-relaxed font-medium line-clamp-3">
                      <span className="font-bold text-purple-950">Clinical Summary: </span>
                      {report.clinical_summary || report.summary}
                    </div>
                  ) : null}

                  {/* Warnings pill if partially processed */}
                  {report.processing_warnings && report.processing_warnings.length > 0 && (
                    <div className="text-[11px] text-amber-800 bg-amber-50 px-2.5 py-1 rounded-lg border border-amber-200 flex items-center space-x-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                      <span>Incomplete data note: {report.processing_warnings.join('; ')}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* MODAL: REPORT FULL DETAILS & TEXT INSPECTOR */}
      {activeReport && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-4xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-5">
            <button
              onClick={() => setActiveReport(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2"
            >
              <X className="w-6 h-6" />
            </button>

            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                {renderStatusBadge(activeReport.processing_status)}
                {renderCategoryPill(activeReport.report_category, activeReport.category_name, activeReport.classification_confidence)}
                {activeReport.file_hash_sha256 && (
                  <span className="bg-slate-100 text-slate-700 font-mono text-xs px-2.5 py-0.5 rounded-full flex items-center space-x-1">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                    <span>SHA-256: {activeReport.file_hash_sha256}</span>
                  </span>
                )}
              </div>
              <h3 className="text-2xl font-black text-slate-900">{activeReport.title}</h3>
              <p className="text-xs text-slate-500 font-medium">
                Report Date: {formatISTDateOnly(activeReport.report_date)} • Uploaded: {formatIST(activeReport.created_at)} • File: {activeReport.file_name}
              </p>
            </div>

            {/* Clinical Summary */}
            <div className="p-4 bg-purple-50 border-2 border-purple-200 rounded-2xl space-y-2">
              <h4 className="text-xs font-bold text-purple-950 uppercase">Grounded Clinical Summary:</h4>
              <p className="text-sm text-slate-800 font-medium leading-relaxed whitespace-pre-line">
                {activeReport.clinical_summary || activeReport.summary || 'Summary unavailable.'}
              </p>
            </div>

            {/* Extracted Text Viewer */}
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-800">Raw Extracted Document Text:</h4>
              <div className="p-4 bg-slate-900 text-slate-100 rounded-2xl font-mono text-xs whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed border border-slate-700">
                {activeReport.extracted_text || 'No readable text could be parsed from this document.'}
              </div>
            </div>

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={() => handleReprocess(activeReport.id)}
                disabled={reprocessingId === activeReport.id}
                className="bg-purple-100 hover:bg-purple-200 text-purple-900 font-bold px-4 py-2 rounded-xl text-xs flex items-center space-x-1"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${reprocessingId === activeReport.id ? 'animate-spin' : ''}`} />
                <span>Re-analyze Document</span>
              </button>

              <button
                onClick={() => setActiveReport(null)}
                className="bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold px-6 py-2.5 rounded-xl text-sm"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: BIOMARKER REVIEW & CONFIRM (Twin Ingestion) */}
      {confirmModalReport && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-6">
            <button
              onClick={() => setConfirmModalReport(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2"
            >
              <X className="w-6 h-6" />
            </button>

            <div className="space-y-1">
              <div className="inline-flex items-center space-x-2 bg-purple-100 text-purple-900 px-3 py-1 rounded-full text-xs font-bold">
                <FileCheck className="w-3.5 h-3.5" />
                <span>Patient Review & Confirmation Protocol</span>
              </div>
              <h3 className="text-2xl font-black text-slate-900">
                Confirm Extracted Vitals for Digital Twin
              </h3>
              <p className="text-sm text-slate-600 font-medium">
                From report: <strong>{confirmModalReport.title}</strong> ({formatISTDateOnly(confirmModalReport.report_date)})
              </p>
            </div>

            <div className="p-4 bg-amber-50 border-2 border-amber-200 rounded-2xl text-xs text-amber-900 leading-relaxed">
              <strong>Clinical Safety Step:</strong> Review each extracted parameter before incorporating it into your physiological state. You can edit values or uncheck parameters if extraction was inaccurate.
            </div>

            {/* List of biomarkers to confirm */}
            <div className="space-y-3">
              {confirmModalReport.biomarkers.map((b) => {
                const item = confirmedItems[b.key] || {
                  key: b.key,
                  value: typeof b.value === 'number' ? b.value : 0,
                  unit: b.unit,
                  selected: true
                };
                return (
                  <div
                    key={b.key}
                    className={`p-4 rounded-2xl border-2 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      item.selected
                        ? 'bg-purple-50/50 border-purple-300'
                        : 'bg-slate-50 border-slate-200 opacity-60'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <input
                        type="checkbox"
                        checked={item.selected}
                        onChange={(e) =>
                          setConfirmedItems({
                            ...confirmedItems,
                            [b.key]: { ...item, selected: e.target.checked }
                          })
                        }
                        className="w-5 h-5 rounded text-purple-700 focus:ring-purple-600 cursor-pointer"
                      />
                      <div>
                        <span className="font-bold text-slate-900 text-base">{b.name}</span>
                        <div className="text-xs text-slate-500">
                          Reference: {b.reference_range} • Status: <span className="capitalize font-semibold">{b.status}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 pl-8 sm:pl-0">
                      <input
                        type="number"
                        step="any"
                        value={item.value}
                        onChange={(e) =>
                          setConfirmedItems({
                            ...confirmedItems,
                            [b.key]: { ...item, value: parseFloat(e.target.value) || 0 }
                          })
                        }
                        disabled={!item.selected}
                        className="w-24 p-2 text-base font-bold bg-white border-2 border-slate-300 rounded-xl focus:outline-none focus:border-purple-600 disabled:bg-slate-100"
                      />
                      <span className="text-sm font-semibold text-slate-600 w-16">{item.unit || b.unit}</span>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex flex-col sm:flex-row justify-end gap-3 pt-4 border-t border-slate-100">
              <button
                onClick={() => setConfirmModalReport(null)}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold px-5 py-3 rounded-xl text-sm"
              >
                Cancel
              </button>

              <button
                onClick={handleConfirmBiomarkers}
                disabled={confirmingBiomarkers}
                className="bg-purple-700 hover:bg-purple-800 text-white font-extrabold px-6 py-3 rounded-xl text-sm shadow-md transition flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                <FileCheck className="w-4 h-4" />
                <span>{confirmingBiomarkers ? 'Updating Twin State...' : 'Confirm & Feed Into Twin'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: WEB3 CRYPTOGRAPHIC PROVENANCE & INTEGRITY VERIFICATION */}
      {integrityModalData && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-2xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-6">
            <button
              onClick={() => setIntegrityModalData(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2"
            >
              <X className="w-6 h-6" />
            </button>

            <div className="space-y-1">
              <div className="inline-flex items-center space-x-2 bg-blue-100 text-blue-900 px-3 py-1 rounded-full text-xs font-bold">
                <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
                <span>Web3 Cryptographic Provenance Audit</span>
              </div>
              <h3 className="text-2xl font-black text-slate-900">
                Document Integrity & Hash Verification
              </h3>
              <p className="text-sm text-slate-600 font-medium">
                Report #{integrityModalData.report_id}: <strong>{integrityModalData.title}</strong>
              </p>
            </div>

            {/* Tamper Free or Warning Banner */}
            <div
              className={`p-4 rounded-2xl border-2 flex items-start space-x-3 ${
                integrityModalData.is_tamper_free
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                  : 'bg-red-50 border-red-300 text-red-950'
              }`}
            >
              {integrityModalData.is_tamper_free ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <h4 className="font-bold text-sm">
                  {integrityModalData.is_tamper_free
                    ? 'Cryptographic Integrity Verified: Tamper-Free'
                    : 'Cryptographic Hash Mismatch or File Missing'}
                </h4>
                <p className="text-xs mt-0.5 leading-relaxed">
                  {integrityModalData.is_tamper_free
                    ? 'The stored document in the off-chain vault exactly matches the cryptographic SHA-256 digest recorded in the Sovereign Health Twin database. No tampering or post-upload alterations detected.'
                    : `Verification status: ${integrityModalData.verification_status}. Stored document bytes do not match the expected cryptographic digest.`}
                </p>
              </div>
            </div>

            {/* Audit Details Grid */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500 uppercase block text-[10px]">Patient Reference</span>
                <span className="font-extrabold text-slate-900">{integrityModalData.patient_id}</span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500 uppercase block text-[10px]">Storage Status</span>
                <span className="font-extrabold text-slate-900">
                  {integrityModalData.file_exists ? 'Present on Disk Vault' : 'Missing File'}
                  {integrityModalData.file_size_bytes ? ` (${(integrityModalData.file_size_bytes / 1024).toFixed(1)} KB)` : ''}
                </span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500 uppercase block text-[10px]">Original Filename</span>
                <span className="font-bold text-slate-900 truncate block" title={integrityModalData.file_name}>
                  {integrityModalData.file_name}
                </span>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
                <span className="font-bold text-slate-500 uppercase block text-[10px]">Verified Timestamp (IST)</span>
                <span className="font-bold text-slate-900">{formatIST(integrityModalData.verified_at)}</span>
              </div>
            </div>

            {/* Hashes Comparison Box */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Database Anchored Hash (SHA-256):
                </label>
                <pre className="bg-slate-900 text-slate-100 p-3 rounded-xl font-mono text-xs break-all select-all">
                  {integrityModalData.stored_sha256 || 'None'}
                </pre>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Recomputed Hash from Disk Storage (SHA-256):
                </label>
                <pre className="bg-slate-900 text-slate-100 p-3 rounded-xl font-mono text-xs break-all select-all">
                  {integrityModalData.recomputed_sha256 || 'None'}
                </pre>
              </div>
            </div>

            <div className="p-3 bg-purple-50 rounded-xl border border-purple-200 text-xs text-purple-900 leading-relaxed">
              <strong>Web3 Architecture Rule:</strong> Protected Health Information (PHI) and raw document binaries remain strictly off-chain to safeguard medical privacy, while cryptographic digests anchor provenance and prevent silent alteration.
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100">
              <button
                onClick={() => setIntegrityModalData(null)}
                className="bg-slate-800 hover:bg-slate-900 text-white font-extrabold px-6 py-2.5 rounded-xl text-sm transition"
              >
                Close Audit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
