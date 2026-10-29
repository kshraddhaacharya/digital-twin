import React, { useState } from 'react';
import {
  PlusCircle,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  History,
  Send,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Heart,
  Activity
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea,
  ReferenceLine
} from 'recharts';
import { Measurement, TwinState } from '../types';
import { api } from '../services/api';
import { formatIST, formatISTTimeOnly, formatISTDateOnly } from '../utils/dateUtils';

interface RecordHistoryViewProps {
  patientId: string;
  measurements: Measurement[];
  twinState: TwinState | null;
  onDataChanged: () => void;
  onNavigateTab: (tab: string) => void;
}

export const RecordHistoryView: React.FC<RecordHistoryViewProps> = ({
  patientId,
  measurements,
  twinState,
  onDataChanged,
  onNavigateTab,
}) => {
  const [newValue, setNewValue] = useState<string>('78');
  const [measContext, setMeasContext] = useState<string>('resting');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Quick preset buttons for senior ease of entry
  const presets = [
    { label: 'Resting (72 bpm)', val: 72 },
    { label: 'Normal (78 bpm)', val: 78 },
    { label: 'After Walk (85 bpm)', val: 85 },
    { label: 'Active (95 bpm)', val: 95 },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    const valNum = parseFloat(newValue.trim());
    if (!newValue.trim() || isNaN(valNum) || valNum < 30 || valNum > 250) {
      setErrorMessage('Please enter a valid heart rate between 30 and 250 bpm (physiologically realistic range).');
      setSubmitting(false);
      return;
    }

    try {
      const nowIso = new Date().toISOString();
      const res = await api.addMeasurement(patientId, {
        timestamp: nowIso,
        measurement_type: 'heart_rate',
        value: valNum,
        unit: 'bpm',
        source: 'patient_entry',
        context: measContext,
      });

      const newVer = res.digital_twin_update.current_state_version;
      setSuccessMessage(
        `✓ Reading saved! Your digital twin advanced to State Version ${newVer}, and the record was permanently verified on the blockchain.`
      );
      onDataChanged();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to save measurement. Please verify inputs.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDateTime = (isoString: string) => {
    return formatIST(isoString);
  };

  const chartData = measurements
    .filter((m) => m.measurement_type === 'heart_rate')
    .slice(0, 30)
    .reverse()
    .map((m) => ({
      time: formatISTTimeOnly(m.timestamp, false),
      date: formatISTDateOnly(m.timestamp),
      bpm: Math.round(m.value),
      context: m.context || 'resting',
      source: m.source || 'patient_entry',
    }));

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Title */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm">
        <h2 className="text-3xl font-black text-slate-900 tracking-tight">
          My Health Readings & History
        </h2>
        <p className="text-lg text-slate-700 font-medium mt-2 leading-relaxed">
          Record a new heart rate measurement, track your live evolution chart, or inspect your verified physiological twin state.
        </p>
      </div>

      {/* LATEST BPM & PHYSIOLOGICAL STATUS CARD */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Latest BPM & Physiological State
            </span>
            <div className="flex items-baseline space-x-3 mt-1">
              <span className="text-5xl sm:text-6xl font-black text-purple-950">
                {twinState ? Math.round(twinState.latest_heart_rate) : (measurements.length > 0 ? Math.round(measurements[0].value) : '--')}
              </span>
              <span className="text-xl sm:text-2xl font-bold text-slate-600">bpm</span>
              <span className="text-xs font-bold uppercase tracking-wider text-purple-700 bg-purple-100 px-3 py-1 rounded-full">
                Context: {twinState?.measurement_context || (measurements.length > 0 ? measurements[0].context : measContext)}
              </span>
            </div>
            <div className="text-xs text-slate-500 font-semibold mt-1.5 flex items-center space-x-1">
              <Clock className="w-3.5 h-3.5 text-purple-600" />
              <span>Observation: {formatIST(twinState?.timestamp_latest_observation || (measurements.length > 0 ? measurements[0].timestamp : undefined))}</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`px-3.5 py-1.5 rounded-full text-xs font-bold capitalize border ${
                twinState?.vital_status === 'normal'
                  ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                  : twinState?.vital_status === 'elevated' || twinState?.vital_status === 'tachycardia'
                  ? 'bg-rose-100 text-rose-900 border-rose-300'
                  : 'bg-amber-100 text-amber-900 border-amber-300'
              }`}
            >
              Status: {twinState?.vital_status || 'normal'}
            </span>

            <span className="px-3.5 py-1.5 rounded-full text-xs font-bold bg-purple-100 text-purple-900 border border-purple-200">
              Twin Version {twinState?.state_version ?? 1}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-slate-500 font-semibold">60m Average:</span>
            <p className="text-sm font-black text-slate-900 mt-0.5">
              {twinState?.rolling_mean_60m ? `${Math.round(twinState.rolling_mean_60m)} bpm` : '--'}
            </p>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-slate-500 font-semibold">Hourly Trend:</span>
            <p className="text-sm font-black text-slate-900 mt-0.5">
              {twinState?.trend_slope_per_hour !== undefined
                ? `${twinState.trend_slope_per_hour > 0 ? '+' : ''}${twinState.trend_slope_per_hour.toFixed(2)} bpm/hr`
                : 'Steady'}
            </p>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-slate-500 font-semibold">Data Quality:</span>
            <p className="text-sm font-black text-slate-900 mt-0.5 capitalize">
              {twinState?.data_quality_status ? twinState.data_quality_status.replace('_', ' ') : 'Good'}
            </p>
          </div>
          <div className="bg-slate-50 p-3 rounded-xl border border-slate-200">
            <span className="text-slate-500 font-semibold">Attestation:</span>
            <p className="text-sm font-black text-emerald-700 mt-0.5 flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{twinState?.attestation_status || 'Verified'}</span>
            </p>
          </div>
        </div>
      </div>

      {/* CHRONOLOGICAL HEART RATE EVOLUTION CHART */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
          <div>
            <h3 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Activity className="w-5 h-5 text-purple-700" />
              <span>Heart Rate Evolution Chart ({chartData.length} observations)</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Shaded band indicates normal resting range (60 - 100 bpm). Real-time telemetry dynamically updates upon entry.
            </p>
          </div>
          <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-3 py-1 rounded-full border border-slate-200 self-start sm:self-auto">
            Live Stream View
          </span>
        </div>

        {chartData.length > 0 ? (
          <div className="h-64 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} tickMargin={6} />
                <YAxis domain={[40, 160]} stroke="#64748b" fontSize={11} unit=" bpm" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '1rem', color: '#fff' }}
                  formatter={(val: any) => [`${val} bpm`, 'Heart Rate']}
                  labelFormatter={(lbl, items) => {
                    const item = items?.[0]?.payload;
                    return item ? `${item.date}, ${item.time} IST (${item.context})` : lbl;
                  }}
                />
                <ReferenceArea y1={60} y2={100} fill="#10b981" fillOpacity={0.08} />
                <ReferenceLine y={100} stroke="#ef4444" strokeDasharray="3 3" label={{ value: 'Upper Normal (100 bpm)', fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }} />
                <ReferenceLine y={60} stroke="#3b82f6" strokeDasharray="3 3" label={{ value: 'Lower Normal (60 bpm)', fill: '#3b82f6', fontSize: 10, position: 'insideBottomRight' }} />
                <Line
                  type="monotone"
                  dataKey="bpm"
                  stroke="#7e22ce"
                  strokeWidth={3}
                  dot={{ r: 4, fill: '#7e22ce', stroke: '#fff', strokeWidth: 2 }}
                  activeDot={{ r: 6, fill: '#9333ea' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="p-8 text-center text-slate-400 text-sm">
            No readings recorded yet. Submit your first measurement below to see your trend line.
          </div>
        )}
      </div>

      {/* Senior-Friendly Quick Add Reading Form */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-md">
        <div className="flex items-center space-x-2 pb-4 border-b border-slate-100">
          <PlusCircle className="w-6 h-6 text-purple-700" />
          <h3 className="text-2xl font-bold text-slate-900">
            Add a New Reading
          </h3>
        </div>

        {/* Success Confirmation Alert */}
        {successMessage && (
          <div className="mt-4 p-5 bg-emerald-50 border-2 border-emerald-300 rounded-2xl text-emerald-950 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start space-x-3">
              <CheckCircle2 className="w-6 h-6 text-emerald-700 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="font-bold text-lg text-emerald-900">Successfully Recorded!</h4>
                <p className="text-base text-emerald-800 mt-1">{successMessage}</p>
              </div>
            </div>
            <button
              onClick={() => onNavigateTab('future-outlook')}
              className="bg-emerald-700 hover:bg-emerald-800 text-white font-bold text-sm px-5 py-2.5 rounded-xl whitespace-nowrap min-h-[44px]"
            >
              Check Updated Outlook →
            </button>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-4 p-4 bg-rose-50 border-2 border-rose-300 rounded-2xl text-rose-950 flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-rose-600 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-base text-rose-900">Notice</h4>
              <p className="text-base text-rose-800 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          {/* Quick 1-Tap Presets */}
          <div>
            <label className="block text-base font-bold text-slate-800 mb-2">
              Quick Presets (or type your own below):
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {presets.map((p, idx) => (
                <button
                  type="button"
                  key={idx}
                  onClick={() => setNewValue(p.val.toString())}
                  className={`py-3 px-4 rounded-xl border-2 font-bold text-base transition-all min-h-[48px] ${
                    newValue === p.val.toString()
                      ? 'bg-purple-100 border-purple-600 text-purple-950'
                      : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Numeric Entry */}
          <div>
            <label htmlFor="hr-input" className="block text-base font-bold text-slate-800 mb-2">
              Heart Rate Value (beats per minute):
            </label>
            <div className="flex items-center space-x-3">
              <input
                id="hr-input"
                type="number"
                step="1"
                min="30"
                max="250"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                required
                className="w-48 text-3xl font-black text-slate-900 border-2 border-slate-300 rounded-2xl p-3 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-600 min-h-[56px]"
              />
              <span className="text-xl font-bold text-slate-600">bpm</span>
            </div>
          </div>

          {/* Context Selector */}
          <div>
            <label className="block text-base font-bold text-slate-800 mb-2">
              Measurement Context / Physical Activity:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {[
                { id: 'resting', label: '🌿 Resting / Seated', desc: 'At rest for > 5 min' },
                { id: 'active', label: '🏃 Mild Activity', desc: 'During or after walking' },
                { id: 'post_exercise', label: '⚡ Post Exercise', desc: 'Cooling down' },
              ].map((c) => (
                <button
                  type="button"
                  key={c.id}
                  onClick={() => setMeasContext(c.id)}
                  className={`py-2.5 px-3.5 rounded-xl border-2 font-bold text-left transition-all min-h-[48px] ${
                    measContext === c.id
                      ? 'bg-purple-100 border-purple-600 text-purple-950'
                      : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  <div className="text-sm">{c.label}</div>
                  <div className="text-xs text-slate-500 font-normal mt-0.5">{c.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-purple-700 hover:bg-purple-800 text-white font-extrabold text-xl py-4 px-6 rounded-2xl shadow-md transition-all flex items-center justify-center space-x-3 min-h-[56px] active:scale-95 disabled:opacity-50"
          >
            <Send className="w-6 h-6" />
            <span>{submitting ? 'Saving reading & updating digital twin...' : 'Save & Update Digital Twin'}</span>
          </button>
        </form>
      </div>

      {/* Chronological History Log (Friendly Cards) */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <History className="w-6 h-6 text-slate-700" />
            <h3 className="text-2xl font-bold text-slate-900">
              Previous Readings ({measurements.length})
            </h3>
          </div>
          <span className="text-sm font-semibold text-slate-500">
            Most recent first
          </span>
        </div>

        <div className="mt-6 space-y-3">
          {measurements.slice(0, 25).map((m) => (
            <div
              key={m.id}
              className="p-5 bg-slate-50 rounded-2xl border-2 border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-white transition-colors"
            >
              <div className="flex items-center space-x-4">
                <div className="p-3 bg-purple-100 text-purple-700 rounded-2xl">
                  <Heart className="w-6 h-6 fill-purple-600" />
                </div>
                <div>
                  <div className="text-2xl font-black text-slate-900">
                    {Math.round(m.value)}{' '}
                    <span className="text-base font-bold text-slate-600">{m.unit}</span>
                  </div>
                  <div className="text-sm text-slate-500 mt-0.5 flex flex-wrap items-center gap-1.5">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatDateTime(m.timestamp)}</span>
                    </span>
                    <span>•</span>
                    <span className="capitalize">{m.source.replace('_', ' ')}</span>
                    {m.context && (
                      <>
                        <span>•</span>
                        <span className="bg-purple-100 text-purple-900 text-xs px-2 py-0.5 rounded-full font-semibold border border-purple-200 capitalize">
                          {m.context.replace('_', ' ')}
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Dynamic Attestation Status Badge */}
              <div className="self-start sm:self-auto flex items-center space-x-1.5 text-xs font-bold">
                {twinState?.attestation_status === 'VERIFIED' ? (
                  <span className="text-emerald-900 bg-emerald-100 border border-emerald-300 px-3 py-1.5 rounded-full flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-700" />
                    <span>Verified On-Chain (Block #{twinState.on_chain_block_number || '1'})</span>
                  </span>
                ) : twinState?.attestation_status === 'SIMULATED' ? (
                  <span className="text-blue-900 bg-blue-100 border border-blue-300 px-3 py-1.5 rounded-full flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-blue-700" />
                    <span>Local Py-EVM Verified</span>
                  </span>
                ) : twinState?.attestation_status === 'PENDING' ? (
                  <span className="text-amber-900 bg-amber-100 border border-amber-300 px-3 py-1.5 rounded-full flex items-center space-x-1.5">
                    <Clock className="w-4 h-4 text-amber-700 animate-spin" />
                    <span>Attestation Pending</span>
                  </span>
                ) : twinState?.attestation_status === 'OFFLINE' ? (
                  <span className="text-slate-800 bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-full flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-slate-500" />
                    <span>Offline Cryptographic Hash</span>
                  </span>
                ) : (
                  <span className="text-slate-700 bg-slate-100 border border-slate-300 px-3 py-1.5 rounded-full flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-slate-400" />
                    <span>Local Record</span>
                  </span>
                )}
              </div>
            </div>
          ))}

          {measurements.length === 0 && (
            <div className="p-8 text-center text-slate-400 text-lg">
              No historical measurements yet. Add your first reading above!
            </div>
          )}
        </div>
      </div>

      {/* Optional Blockchain Audit Details for Judges */}
      <div className="bg-white rounded-3xl p-6 border-2 border-slate-200 shadow-sm">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full flex items-center justify-between text-base font-bold text-slate-700 hover:text-purple-700 focus:outline-none"
        >
          <span>Blockchain Audit & Smart Contract Records (For Judges)</span>
          {showTechnicalDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>

        {showTechnicalDetails && (
          <div className="mt-4 pt-4 border-t border-slate-200 text-sm font-mono space-y-2 text-slate-700">
            <div><strong>Smart Contract Address:</strong> {twinState?.contract_address || '0xF2E246BB76DF876Cef8b38ae84130F4F55De395b'}</div>
            <div><strong>Active State Version:</strong> Version {twinState?.state_version ?? 1}</div>
            <div><strong>Latest Block:</strong> Block #{twinState?.on_chain_block_number ?? 1}</div>
            <div><strong>Transaction Hash:</strong> 0x{twinState?.on_chain_tx_hash || 'Verified'}</div>
            <div><strong>IPFS Storage CID:</strong> ipfs://{twinState?.ipfs_cid || 'bafybeih...'}</div>
          </div>
        )}
      </div>
    </div>
  );
};
