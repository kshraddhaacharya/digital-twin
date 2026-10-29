import React, { useState } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Play,
  Clock,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  Calendar
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceArea
} from 'recharts';
import { TwinState, Forecast, Measurement } from '../types';
import { api } from '../services/api';
import { formatIST, formatISTTimeOnly } from '../utils/dateUtils';

interface ChartDataPoint {
  time: string;
  actual: number | null;
  predicted: number | null;
  lower_95: number | null;
  upper_95: number | null;
  lower_80: number | null;
  upper_80: number | null;
  band_95_height: number;
  band_95_base: number | null;
  isPrediction: boolean;
}

interface ForecastSectionProps {
  patientId: string;
  twinState: TwinState | null;
  measurements: Measurement[];
  forecasts: Forecast[];
  onForecastGenerated: () => void;
}

export const ForecastSection: React.FC<ForecastSectionProps> = ({
  patientId,
  twinState,
  measurements,
  forecasts,
  onForecastGenerated,
}) => {
  const [horizonMinutes, setHorizonMinutes] = useState(360); // 6 hours default
  const [modelType, setModelType] = useState('autoregressive_trend');
  const [loading, setLoading] = useState(false);
  const [selectedForecastIndex, setSelectedForecastIndex] = useState(0);

  // Active or selected forecast
  const currentForecast = forecasts.length > 0 ? forecasts[selectedForecastIndex] : null;

  const handleGenerateForecast = async () => {
    setLoading(true);
    try {
      await api.generateForecast(patientId, {
        horizon_minutes: horizonMinutes,
        model_type: modelType,
      });
      setSelectedForecastIndex(0);
      onForecastGenerated();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate forecast.');
    } finally {
      setLoading(false);
    }
  };

  // Combine recent actual measurements with forecast points for unified chart
  const recentActuals: ChartDataPoint[] = measurements
    .filter((m) => m.measurement_type === 'heart_rate')
    .slice(0, 32)
    .reverse()
    .map((m) => ({
      time: formatISTTimeOnly(m.timestamp, false),
      actual: m.value,
      predicted: null,
      lower_95: null,
      upper_95: null,
      lower_80: null,
      upper_80: null,
      band_95_height: 0,
      band_95_base: null,
      isPrediction: false,
    }));

  const forecastPoints: ChartDataPoint[] = currentForecast
    ? currentForecast.predicted_trajectory.map((p) => ({
        time: formatISTTimeOnly(p.timestamp, false),
        actual: null,
        predicted: p.predicted_value,
        lower_95: p.lower_bound_95,
        upper_95: p.upper_bound_95,
        lower_80: p.lower_bound_80,
        upper_80: p.upper_bound_80,
        // For uncertainty band rendering between lower and upper
        band_95_height: Math.max(0, p.upper_bound_95 - p.lower_bound_95),
        band_95_base: p.lower_bound_95,
        isPrediction: true,
      }))
    : [];

  // Bridge connection: the last actual point connects to first prediction point
  if (recentActuals.length > 0 && forecastPoints.length > 0) {
    const lastActual = recentActuals[recentActuals.length - 1];
    recentActuals[recentActuals.length - 1] = {
      ...lastActual,
      predicted: lastActual.actual,
      band_95_height: 0,
      band_95_base: lastActual.actual,
    };
  }

  const combinedData = [...recentActuals, ...forecastPoints];

  return (
    <div className="space-y-6">
      {/* Controls & Forecast Generation Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Short-Term Physiological Forecasting
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Project future trajectory using chronological historical observations anchored to the patient's active digital twin state.
            </p>
          </div>

          <button
            onClick={handleGenerateForecast}
            disabled={loading}
            className="bg-twin-600 hover:bg-twin-700 text-white font-semibold text-xs px-5 py-2.5 rounded-lg shadow-sm transition-all flex items-center space-x-2 self-start sm:self-auto disabled:opacity-50"
          >
            <Play className={`w-4 h-4 fill-white ${loading ? 'animate-pulse' : ''}`} />
            <span>{loading ? 'Forecasting...' : 'Run Forecast Pipeline'}</span>
          </button>
        </div>

        {/* Forecast Configuration Form */}
        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-6 items-center">
          {/* Horizon Slider */}
          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-slate-700 mb-2">
              <label>Forecast Horizon</label>
              <span className="text-twin-600 font-bold bg-twin-50 px-2 py-0.5 rounded border border-twin-200">
                {horizonMinutes / 60} hours ({horizonMinutes} min)
              </span>
            </div>
            <input
              type="range"
              min="60"
              max="720"
              step="30"
              value={horizonMinutes}
              onChange={(e) => setHorizonMinutes(parseInt(e.target.value))}
              className="w-full accent-twin-600 cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>1 hr</span>
              <span>6 hrs (default)</span>
              <span>12 hrs</span>
            </div>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-2">
              Forecasting Model Architecture
            </label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500 font-medium"
            >
              <option value="autoregressive_trend">
                Autoregressive Diurnal Trend (Ridge Regularized)
              </option>
              <option value="baseline_persistence">
                Baseline Persistence (Hold-Forward Extrapolation)
              </option>
            </select>
          </div>

          {/* Current State Anchor */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
            <span className="text-slate-500 font-medium">State Anchor:</span>
            <div className="font-bold text-slate-900 mt-1 flex items-center space-x-2">
              <span className="bg-twin-100 text-twin-800 px-2 py-0.5 rounded border border-twin-200">
                Twin State v{twinState?.state_version ?? 1}
              </span>
              <span className="text-slate-500">
                @ {twinState ? twinState.latest_heart_rate.toFixed(1) : '--'} bpm
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* STALE FORECAST ALERT BANNER (If current forecast is stale) */}
      {currentForecast && currentForecast.is_stale && (
        <div className="p-4 bg-amber-50 border-2 border-amber-300 rounded-xl flex items-start space-x-3 text-amber-900">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs">
            <div className="font-extrabold text-sm text-amber-800 uppercase tracking-wide">
              Stale Forecast Warning
            </div>
            <p className="mt-1">
              This forecast was generated from <strong>Twin State Version {currentForecast.twin_state_version}</strong> at{' '}
              {formatIST(currentForecast.last_observation_timestamp)}.
              The patient's digital twin has since evolved to{' '}
              <strong>State Version {twinState?.state_version}</strong>.
            </p>
            <p className="mt-1 font-semibold text-amber-800">
              {currentForecast.stale_reason} Click "Run Forecast Pipeline" to generate a fresh forecast.
            </p>
          </div>
        </div>
      )}

      {/* Unified Telemetry & Forecast Chart */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
          <div>
            <div className="flex items-center space-x-3">
              <h3 className="text-base font-bold text-slate-900">
                Modeled Trajectory & Historical Actuals
              </h3>
              {currentForecast && (
                <span
                  className={`text-[10px] font-extrabold px-2 py-0.5 rounded border uppercase tracking-wider ${
                    currentForecast.is_stale
                      ? 'bg-amber-100 text-amber-800 border-amber-300'
                      : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                  }`}
                >
                  {currentForecast.is_stale ? 'STALE' : 'FRESH'} (from v{currentForecast.twin_state_version})
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Solid line: Observed Telemetry • Dashed line: Model Forecast • Shaded area: 95% Confidence Interval
            </p>
          </div>

          {/* Historical Forecast Switcher */}
          {forecasts.length > 1 && (
            <div className="flex items-center space-x-2 text-xs">
              <span className="text-slate-500">History:</span>
              <select
                value={selectedForecastIndex}
                onChange={(e) => setSelectedForecastIndex(parseInt(e.target.value))}
                className="border border-slate-300 rounded px-2 py-1 bg-slate-50 text-slate-800 font-medium"
              >
                {forecasts.map((f, idx) => (
                  <option key={f.id} value={idx}>
                    #{f.id} - v{f.twin_state_version} {f.is_stale ? '(Stale)' : '(Active)'} -{' '}
                    {formatIST(f.created_at)}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Recharts Chart */}
        <div className="mt-6 h-80 w-full">
          {combinedData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={combinedData} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" bpm" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                
                {/* Physiological normal range shading */}
                <ReferenceArea y1={60} y2={100} fill="#ecfdf5" fillOpacity={0.4} />

                {/* 95% Confidence Interval Area Stack */}
                <Area
                  type="monotone"
                  dataKey="band_95_base"
                  stackId="ci"
                  stroke="none"
                  fill="transparent"
                  legendType="none"
                />
                <Area
                  type="monotone"
                  dataKey="band_95_height"
                  name="95% Confidence Band"
                  stackId="ci"
                  stroke="none"
                  fill="#bae6fd"
                  fillOpacity={0.45}
                />

                {/* Observed actual values */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Observed Heart Rate"
                  stroke="#0284c7"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#0284c7' }}
                  connectNulls={false}
                />

                {/* Forecast predictions */}
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Modeled Forecast"
                  stroke="#6366f1"
                  strokeWidth={2.5}
                  strokeDasharray="5 5"
                  dot={{ r: 4, fill: '#6366f1' }}
                  connectNulls={true}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">
              No forecast generated yet. Select a horizon and click "Run Forecast Pipeline".
            </div>
          )}
        </div>

        {/* Forecast Quality Warnings & Model Notes */}
        {currentForecast && (
          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 font-medium">Model Architecture</span>
              <div className="font-bold text-slate-800 mt-1">
                {currentForecast.model_name} (v{currentForecast.model_version})
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 font-medium">Anchor Observation Time</span>
              <div className="font-bold text-slate-800 mt-1 truncate">
                {formatIST(currentForecast.last_observation_timestamp)}
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
              <span className="text-slate-400 font-medium">Quality Warnings</span>
              <div className="text-slate-700 mt-1">
                {currentForecast.quality_warnings.length > 0 ? (
                  <ul className="list-disc pl-4 text-amber-700">
                    {currentForecast.quality_warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-emerald-700 font-medium flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5 inline" />
                    <span>Sufficient sample density; zero quality flags.</span>
                  </span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
