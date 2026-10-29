import React from 'react';
import {
  Heart,
  TrendingUp,
  Clock,
  Layers,
  Activity,
  AlertCircle,
  CheckCircle2,
  Cpu
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceArea
} from 'recharts';
import { Patient, TwinState, Measurement } from '../types';
import { formatIST, formatISTTimeOnly } from '../utils/dateUtils';

interface OverviewSectionProps {
  patient: Patient | null;
  twinState: TwinState | null;
  recentMeasurements: Measurement[];
  onNavigateTab: (tab: string) => void;
}

export const OverviewSection: React.FC<OverviewSectionProps> = ({
  patient,
  twinState,
  recentMeasurements,
  onNavigateTab,
}) => {
  if (!patient) {
    return (
      <div className="p-8 text-center text-slate-500 bg-white rounded-xl shadow-sm border border-slate-200">
        Loading patient overview...
      </div>
    );
  }

  // Filter heart rate observations for the mini trendline chart
  const hrData = recentMeasurements
    .filter((m) => m.measurement_type === 'heart_rate')
    .slice(0, 32)
    .reverse()
    .map((m) => ({
      time: formatISTTimeOnly(m.timestamp, false),
      value: m.value,
    }));

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'tachycardia':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'bradycardia':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'elevated':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'normal':
      default:
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
    }
  };

  const slope = twinState?.trend_slope_per_hour ?? 0;
  const isRising = slope > 0.5;
  const isFalling = slope < -0.5;

  return (
    <div className="space-y-6">
      {/* Patient Header Banner */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-slate-900">{patient.name}</h2>
            <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2.5 py-0.5 rounded-full border border-slate-300">
              {patient.id}
            </span>
            {patient.is_synthetic && (
              <span className="text-xs font-semibold bg-blue-50 text-blue-700 px-2.5 py-0.5 rounded-full border border-blue-200">
                Synthetic Benchmark
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Demographics: {patient.age} yrs • {patient.gender} • Baseline Resting HR: {patient.baseline_heart_rate} bpm
          </p>
        </div>

        {/* Current Twin State Status Badge & Web3 Anchoring */}
        <div className="flex items-center space-x-3">
          <div
            onClick={() => onNavigateTab('web3')}
            className="cursor-pointer bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg p-3 flex items-center space-x-3 transition-colors"
            title="Click to view On-Chain Attestation in Web3 tab"
          >
            <div className="bg-purple-600 text-white p-1.5 rounded-lg">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-purple-700 flex items-center space-x-1">
                <span>Web3 Anchored</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              </div>
              <div className="text-base font-extrabold text-purple-950">
                Block #{twinState?.on_chain_block_number ?? '1'} • v{twinState ? twinState.state_version : '1'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Primary Physiological Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Latest Heart Rate */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Latest Observed HR
              </span>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-black text-slate-900">
                  {twinState ? twinState.latest_heart_rate.toFixed(1) : '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">bpm</span>
              </div>
            </div>
            <div className="p-2.5 bg-rose-50 text-rose-600 rounded-lg">
              <Heart className="w-5 h-5 fill-rose-500" />
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between">
            <span
              className={`text-[11px] font-bold uppercase px-2 py-0.5 rounded-full border ${getStatusColor(
                twinState?.vital_status
              )}`}
            >
              {twinState?.vital_status || 'Unknown'}
            </span>
            <span className="text-[11px] text-slate-400">
              Target: 60-100 bpm
            </span>
          </div>
        </div>

        {/* Recent Trend Slope */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Modeled Trend (Slope)
              </span>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-black text-slate-900">
                  {twinState ? (twinState.trend_slope_per_hour ?? 0).toFixed(1) : '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">bpm/hr</span>
              </div>
            </div>
            <div
              className={`p-2.5 rounded-lg ${
                isRising
                  ? 'bg-amber-50 text-amber-600'
                  : isFalling
                  ? 'bg-blue-50 text-blue-600'
                  : 'bg-emerald-50 text-emerald-600'
              }`}
            >
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-[11px] text-slate-600">
            {isRising && 'Rising physiological trend detected'}
            {isFalling && 'Decreasing trend toward baseline'}
            {!isRising && !isFalling && 'Stable steady-state trajectory'}
          </div>
        </div>

        {/* Rolling Statistics */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                60-min Rolling Mean
              </span>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-black text-slate-900">
                  {twinState?.rolling_mean_60m ? twinState.rolling_mean_60m.toFixed(1) : '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">bpm</span>
              </div>
            </div>
            <div className="p-2.5 bg-indigo-50 text-indigo-600 rounded-lg">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 flex justify-between">
            <span>SD: ±{twinState?.rolling_std_60m?.toFixed(1) ?? '0.0'} bpm</span>
            <span>CV: {twinState?.physiological_variability_index?.toFixed(1) ?? '0.0'}%</span>
          </div>
        </div>

        {/* Data Freshness */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start">
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Data Freshness
              </span>
              <div className="mt-2 flex items-baseline space-x-2">
                <span className="text-3xl font-black text-slate-900">
                  {twinState ? Math.round(twinState.data_freshness_seconds / 60) : '--'}
                </span>
                <span className="text-xs font-medium text-slate-500">min ago</span>
              </div>
            </div>
            <div className="p-2.5 bg-slate-100 text-slate-600 rounded-lg">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 text-[11px] text-slate-500 truncate" title={twinState?.timestamp_latest_observation}>
            Obs: {twinState?.timestamp_latest_observation ? formatIST(twinState.timestamp_latest_observation) : 'N/A'}
          </div>
        </div>
      </div>

      {/* Recent Heart Rate Telemetry Chart */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Recent Heart Rate Telemetry Stream
            </h3>
            <p className="text-xs text-slate-500">
              Timestamped observations stored in patient record • Physiological safe boundaries: 60 - 100 bpm
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onNavigateTab('twin')}
              className="text-xs font-semibold text-twin-600 hover:text-twin-700 bg-twin-50 px-3 py-1.5 rounded-lg border border-twin-200"
            >
              Inspect Twin Engine →
            </button>
            <button
              onClick={() => onNavigateTab('forecast')}
              className="text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200"
            >
              Generate Forecast →
            </button>
          </div>
        </div>

        <div className="mt-6 h-64 w-full">
          {hrData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hrData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" bpm" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                {/* Physiological normal range shading (60-100 bpm) */}
                <ReferenceArea y1={60} y2={100} fill="#ecfdf5" fillOpacity={0.6} />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="Heart Rate"
                  stroke="#0284c7"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#0284c7', strokeWidth: 1, stroke: '#fff' }}
                  activeDot={{ r: 6, fill: '#0369a1' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">
              No recent heart rate observations available. Load synthetic data or submit a measurement.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
