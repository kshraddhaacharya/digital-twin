import React, { useState } from 'react';
import {
  Cpu,
  Layers,
  ArrowRight,
  Send,
  History,
  CheckCircle,
  AlertTriangle,
  Clock,
  Sparkles,
  RefreshCw,
  PlusCircle
} from 'lucide-react';
import { TwinState, Measurement } from '../types';
import { api } from '../services/api';
import { formatIST } from '../utils/dateUtils';

interface DigitalTwinSectionProps {
  patientId: string;
  twinState: TwinState | null;
  twinHistory: TwinState[];
  onTwinUpdated: () => void;
}

export const DigitalTwinSection: React.FC<DigitalTwinSectionProps> = ({
  patientId,
  twinState,
  twinHistory,
  onTwinUpdated,
}) => {
  // New measurement form state
  const [measType, setMeasType] = useState('heart_rate');
  const [measValue, setMeasValue] = useState('78.5');
  const [measUnit, setMeasUnit] = useState('bpm');
  const [measSource, setMeasSource] = useState('bedside_monitor');
  const [measTime, setMeasTime] = useState(new Date().toISOString().slice(0, 16));
  
  const [submitting, setSubmitting] = useState(false);
  const [updateFeedback, setUpdateFeedback] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmitMeasurement = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    setUpdateFeedback(null);

    const valNum = parseFloat(measValue);
    if (isNaN(valNum)) {
      setErrorMessage('Please enter a valid numeric value.');
      setSubmitting(false);
      return;
    }

    try {
      const isoTimestamp = new Date(measTime).toISOString();
      const res = await api.addMeasurement(patientId, {
        timestamp: isoTimestamp,
        measurement_type: measType,
        value: valNum,
        unit: measUnit,
        source: measSource,
      });

      setUpdateFeedback(res);
      onTwinUpdated();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setErrorMessage(detail);
      } else if (Array.isArray(detail)) {
        setErrorMessage(detail.map((d: any) => d.msg).join('; '));
      } else {
        setErrorMessage('Failed to submit measurement. Check connection or values.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleInitializeTwin = async () => {
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await api.initializeTwin(patientId);
      onTwinUpdated();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to initialize digital twin.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* State Version Banner */}
      <div className="bg-gradient-to-r from-twin-800 to-slate-900 rounded-xl p-6 text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="bg-white/10 p-3 rounded-xl border border-white/20 backdrop-blur-sm">
            <Cpu className="w-8 h-8 text-twin-300" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs uppercase font-bold tracking-widest text-twin-300">
                Core Digital Twin Engine
              </span>
              <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-400/30 uppercase">
                Active Continuous State
              </span>
            </div>
            <h2 className="text-2xl font-black tracking-tight mt-0.5">
              Twin State Version {twinState ? twinState.state_version : 'Uninitialized'}
            </h2>
            <p className="text-xs text-slate-300 mt-1">
              Maintains an explicit mathematical representation of patient physiology. Increments deterministically on new valid observations.
            </p>
          </div>
        </div>

        <button
          onClick={handleInitializeTwin}
          disabled={submitting}
          className="bg-white/10 hover:bg-white/20 border border-white/25 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-all flex items-center space-x-2 self-start md:self-auto"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Reinitialize Twin from History</span>
        </button>
      </div>

      {/* Two-Column Comparison: Raw Observed Values vs Inferred Twin State Features */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Raw Observations */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-700">
                Latest Observed Measurement
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              The direct telemetry sensor reading captured from the patient.
            </p>

            <div className="mt-5 space-y-4">
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <span className="text-xs text-slate-500 font-medium">Observed Heart Rate</span>
                <div className="text-3xl font-black text-slate-900 mt-1">
                  {twinState ? twinState.latest_heart_rate.toFixed(1) : '--'}{' '}
                  <span className="text-sm font-normal text-slate-500">bpm</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 font-medium">Observation Time</span>
                  <div className="font-semibold text-slate-800 mt-1 truncate">
                    {twinState?.timestamp_latest_observation
                      ? formatIST(twinState.timestamp_latest_observation)
                      : 'N/A'}
                  </div>
                </div>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                  <span className="text-slate-400 font-medium">Sensor Source</span>
                  <div className="font-semibold text-slate-800 mt-1">
                    Telemetry Stream
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
            <span>Measurement ID: #{twinState?.last_processed_measurement_id ?? 'None'}</span>
            <span>Data Freshness: {twinState ? Math.round(twinState.data_freshness_seconds / 60) : '--'} min ago</span>
          </div>
        </div>

        {/* Column 2: Inferred Twin Features */}
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
              <span className="w-2.5 h-2.5 rounded-full bg-twin-600 animate-pulse"></span>
              <h3 className="text-sm font-bold uppercase tracking-wider text-twin-700">
                Derived Physiological Twin State
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Continuous latent features inferred by the Digital Twin Engine from chronological observation history.
            </p>

            <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-twin-50/60 rounded-lg border border-twin-100">
                <span className="text-twin-600 font-medium">Rolling Mean (60 min)</span>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  {twinState?.rolling_mean_60m ? twinState.rolling_mean_60m.toFixed(1) : '--'}{' '}
                  <span className="text-xs font-normal text-slate-500">bpm</span>
                </div>
              </div>

              <div className="p-3 bg-twin-50/60 rounded-lg border border-twin-100">
                <span className="text-twin-600 font-medium">Rolling Std Dev (60 min)</span>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  ±{twinState?.rolling_std_60m ? twinState.rolling_std_60m.toFixed(1) : '0.0'}{' '}
                  <span className="text-xs font-normal text-slate-500">bpm</span>
                </div>
              </div>

              <div className="p-3 bg-twin-50/60 rounded-lg border border-twin-100">
                <span className="text-twin-600 font-medium">Rate of Change (Slope)</span>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  {twinState?.trend_slope_per_hour ? twinState.trend_slope_per_hour.toFixed(1) : '0.0'}{' '}
                  <span className="text-xs font-normal text-slate-500">bpm/hr</span>
                </div>
              </div>

              <div className="p-3 bg-twin-50/60 rounded-lg border border-twin-100">
                <span className="text-twin-600 font-medium">Circadian Harmonic Offset</span>
                <div className="text-xl font-bold text-slate-900 mt-1">
                  {twinState?.circadian_phase_estimate ? `${twinState.circadian_phase_estimate > 0 ? '+' : ''}${twinState.circadian_phase_estimate.toFixed(1)}` : '0.0'}{' '}
                  <span className="text-xs font-normal text-slate-500">bpm</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500">Physiological Variability Index:</span>
            <span className="font-bold text-slate-800">
              {twinState?.physiological_variability_index ? twinState.physiological_variability_index.toFixed(1) : '0.0'}%
            </span>
          </div>
        </div>
      </div>

      {/* Submit New Observation Form & Dynamic Update */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-2 pb-4 border-b border-slate-100">
          <PlusCircle className="w-5 h-5 text-twin-600" />
          <h3 className="text-base font-bold text-slate-900">
            Submit New Patient Observation (Simulate Live Bedside Feed)
          </h3>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Demonstrates how the Digital Twin dynamically ingests observations, increments its state version, recalculates physiological features, and marks older forecasts as stale.
        </p>

        {/* Update Confirmation Feedback Alert */}
        {updateFeedback && (
          <div className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start space-x-3">
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-emerald-900">
              <div className="font-bold text-sm text-emerald-800">
                Digital Twin Successfully Updated!
              </div>
              <p className="mt-1">
                State Version advanced from <strong>v{updateFeedback.digital_twin_update.previous_version}</strong> to{' '}
                <strong className="text-emerald-700 font-black">v{updateFeedback.digital_twin_update.current_state_version}</strong>.
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="bg-white px-2 py-0.5 rounded border border-emerald-200 font-mono">
                  New HR: {updateFeedback.digital_twin_update.latest_heart_rate} bpm
                </span>
                <span className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300 font-semibold">
                  {updateFeedback.digital_twin_update.stale_forecasts_invalidated} older forecast(s) flagged as STALE
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {errorMessage && (
          <div className="mt-4 p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-rose-900">
              <div className="font-bold text-sm text-rose-800">Observation Rejected</div>
              <p className="mt-1">{errorMessage}</p>
              <p className="mt-1 text-[11px] text-rose-700">
                The Digital Twin state was preserved without modification.
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmitMeasurement} className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Measurement Type
            </label>
            <select
              value={measType}
              onChange={(e) => setMeasType(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500"
            >
              <option value="heart_rate">Heart Rate (bpm)</option>
              <option value="systolic_bp">Systolic BP (mmHg)</option>
              <option value="diastolic_bp">Diastolic BP (mmHg)</option>
              <option value="body_temperature">Body Temperature (°C)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Observed Value
            </label>
            <input
              type="number"
              step="0.1"
              value={measValue}
              onChange={(e) => setMeasValue(e.target.value)}
              required
              className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500"
              placeholder="e.g. 78.5"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Observation Timestamp
            </label>
            <input
              type="datetime-local"
              value={measTime}
              onChange={(e) => setMeasTime(e.target.value)}
              required
              className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Source Tag
            </label>
            <select
              value={measSource}
              onChange={(e) => setMeasSource(e.target.value)}
              className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500"
            >
              <option value="bedside_monitor">Bedside Monitor</option>
              <option value="manual_nurse_entry">Manual Nurse Entry</option>
              <option value="telemetry_patch">Wearable Patch</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-twin-600 hover:bg-twin-700 text-white font-semibold text-sm py-2 px-4 rounded-lg shadow-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{submitting ? 'Updating...' : 'Update Twin'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* State Version History Audit Log */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex items-center space-x-2 pb-4 border-b border-slate-100">
          <History className="w-5 h-5 text-slate-600" />
          <h3 className="text-base font-bold text-slate-900">
            Twin State Version History & Audit Ledger
          </h3>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Immutable ledger of every state version produced for patient {patientId}. Explains the exact historical snapshot associated with each forecast.
        </p>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Version</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Status</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Latest HR</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">60m Mean</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Trend Slope</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Observation Time</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Created UTC</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {twinHistory.map((s) => (
                <tr key={s.id} className={s.is_active_version ? 'bg-twin-50/40 font-semibold' : ''}>
                  <td className="px-4 py-3 font-mono">
                    <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded border border-slate-200">
                      v{s.state_version}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {s.is_active_version ? (
                      <span className="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-200">
                        ACTIVE
                      </span>
                    ) : (
                      <span className="text-slate-400 text-[11px]">Archived</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-900 font-bold">{s.latest_heart_rate.toFixed(1)} bpm</td>
                  <td className="px-4 py-3 text-slate-600">{s.rolling_mean_60m ? `${s.rolling_mean_60m.toFixed(1)} bpm` : '--'}</td>
                  <td className="px-4 py-3 text-slate-600">{s.trend_slope_per_hour ? `${s.trend_slope_per_hour.toFixed(1)} bpm/hr` : '0.0'}</td>
                  <td className="px-4 py-3 text-slate-500">{formatIST(s.timestamp_latest_observation)}</td>
                  <td className="px-4 py-3 text-slate-400">{formatIST(s.created_at)}</td>
                </tr>
              ))}
              {twinHistory.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                    No state history found. Initialize the digital twin to start version tracking.
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
