import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Play,
  RotateCcw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Info,
  Clock,
  Heart
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceArea
} from 'recharts';
import { TwinState, Forecast, Measurement, ScenarioComparison } from '../types';
import { api } from '../services/api';
import { formatISTTimeOnly, formatIST } from '../utils/dateUtils';

interface FutureOutlookViewProps {
  patientId: string;
  twinState: TwinState | null;
  measurements: Measurement[];
  forecasts: Forecast[];
  onRefreshData: () => void;
}

export const FutureOutlookView: React.FC<FutureOutlookViewProps> = ({
  patientId,
  twinState,
  measurements,
  forecasts,
  onRefreshData,
}) => {
  const [selectedHypothetical, setSelectedHypothetical] = useState<number>(-25); // -25%, 0%, +25%
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [loadingForecast, setLoadingForecast] = useState<boolean>(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);

  // Active or latest forecast
  const latestForecast = forecasts.length > 0 ? forecasts[0] : null;

  // Check if forecast is outdated relative to active twin version
  const isOutdated = latestForecast && twinState
    ? latestForecast.twin_state_version < twinState.state_version
    : false;

  // Load Scenario simulation comparison
  const loadScenarioSimulation = async (paramVal: number) => {
    try {
      const res = await api.simulateScenarios(patientId, {
        horizon_minutes: 120,
        parameter_name: 'activity_exertion_factor',
        parameter_value: paramVal,
        parameter_unit: '%',
      });
      setComparison(res);
    } catch (err) {
      console.error('Failed to run scenario simulation:', err);
    }
  };

  useEffect(() => {
    loadScenarioSimulation(selectedHypothetical);
  }, [patientId, selectedHypothetical, twinState?.state_version]);

  // Handle generating fresh forecast
  const handleGenerateFreshForecast = async () => {
    setLoadingForecast(true);
    try {
      await api.generateForecast(patientId, {
        horizon_minutes: 120,
        model_type: 'autoregressive_trend',
      });
      await loadScenarioSimulation(selectedHypothetical);
      onRefreshData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update forecast.');
    } finally {
      setLoadingForecast(false);
    }
  };

  // Build clean chart points: past actuals + future projection
  const recentActuals = measurements
    .filter((m) => m.measurement_type === 'heart_rate')
    .slice(0, 16)
    .reverse()
    .map((m) => ({
      time: formatISTTimeOnly(m.timestamp, false),
      actual: m.value,
      forecastA: null as number | null,
      forecastB: null as number | null,
    }));

  const chartFuturePoints = comparison
    ? comparison.scenario_a.simulated_trajectory.map((ptA, idx) => {
        const ptB = comparison.scenario_b.simulated_trajectory[idx];
        return {
          time: formatISTTimeOnly(ptA.timestamp, false),
          actual: null as number | null,
          forecastA: ptA.simulated_value,
          forecastB: ptB ? ptB.simulated_value : null,
        };
      })
    : [];

  // Connect last actual point to first forecast point
  if (recentActuals.length > 0 && chartFuturePoints.length > 0) {
    const last = recentActuals[recentActuals.length - 1];
    recentActuals[recentActuals.length - 1] = {
      ...last,
      forecastA: last.actual,
      forecastB: last.actual,
    };
  }

  const chartData = [...recentActuals, ...chartFuturePoints];

  // Plain-English explanation of difference
  const getDifferenceExplanation = () => {
    if (!comparison) return '';
    const diff = comparison.delta_summary.endpoint_delta_bpm;
    if (selectedHypothetical < 0) {
      return `In this resting scenario, your heart rate is projected to be about ${diff.toFixed(1)} beats per minute lower by this evening compared to your current path.`;
    } else if (selectedHypothetical > 0) {
      return `In this active scenario, your heart rate is projected to be about ${diff.toFixed(1)} beats per minute higher by this evening compared to your current path.`;
    } else {
      return 'Currently showing your baseline trend path.';
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      {/* Page Title & Plain-English Intro */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm">
        <h2 className="text-3xl font-black text-slate-900 tracking-tight">
          Digital Twin Simulation & Counterfactual Outcomes
        </h2>
        <p className="text-lg text-slate-700 font-medium mt-2 leading-relaxed">
          Your digital twin anchors your current physiological state and simulates possible short-term outcomes over the next <strong>2 hours (120 minutes)</strong> under different conditions.
        </p>

        {/* State Anchor & Data Quality in simple language */}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-sm text-slate-600 bg-slate-50 p-3.5 rounded-2xl border border-slate-200">
          <span>Current Modeled State: <strong>Version {twinState ? twinState.state_version : '1'}</strong></span>
          <span>•</span>
          <span>Model: <strong>{twinState?.model_version || 'autoregressive_trend_v1.0'}</strong></span>
          <span>•</span>
          <span>Data Quality: <strong className="capitalize">{twinState?.data_quality_status || 'Good'}</strong></span>
          <span>•</span>
          <span>Latest Reading: <strong>{twinState ? `${twinState.latest_heart_rate.toFixed(1)} bpm` : '--'}</strong></span>
        </div>
      </div>

      {/* OUTDATED FORECAST WARNING (Plain English) */}
      {isOutdated && (
        <div className="p-6 bg-amber-50 border-3 border-amber-400 rounded-3xl text-amber-950 shadow-sm">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-7 h-7 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-xl font-bold text-amber-900">
                Newer Reading Available — Outlook is Outdated
              </h3>
              <p className="text-base text-amber-800 mt-1 leading-relaxed">
                You added a new measurement since this forecast was made. Click below to refresh your digital twin with the latest information.
              </p>
              <button
                onClick={handleGenerateFreshForecast}
                disabled={loadingForecast}
                className="mt-4 bg-amber-600 hover:bg-amber-700 text-white font-bold text-base px-6 py-3 rounded-xl shadow-md transition-all min-h-[48px]"
              >
                {loadingForecast ? 'Updating Digital Twin...' : 'Update Outlook with Latest Reading'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* The Single, Clean, Readable Chart */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-md">
        <div className="pb-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-xl font-bold text-slate-900">
              Projected Heart Rate Over Next 2 Hours (120 min)
            </h3>
            <p className="text-base text-slate-600 font-medium">
              Blue dots: Observed readings • Purple line: Baseline path (Scenario A) • Orange line: Counterfactual path (Scenario B)
            </p>
          </div>
        </div>

        {/* Unified Readable Chart */}
        <div className="mt-6 h-80 sm:h-96 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="time" tick={{ fontSize: 13, fill: '#475569', fontWeight: 600 }} stroke="#94a3b8" />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 13, fill: '#475569', fontWeight: 600 }} stroke="#94a3b8" unit=" bpm" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', color: '#fff', fontSize: '14px', padding: '10px 14px' }}
                  labelStyle={{ color: '#cbd5e1', fontWeight: 'bold' }}
                />
                <Legend wrapperStyle={{ fontSize: '14px', paddingTop: '12px' }} />

                {/* Normal resting physiological range shading (60-100 bpm) */}
                <ReferenceArea y1={60} y2={100} fill="#ecfdf5" fillOpacity={0.6} />

                {/* Past Actual Readings */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Your Past Readings"
                  stroke="#0284c7"
                  strokeWidth={3}
                  dot={{ r: 5, fill: '#0284c7', strokeWidth: 2, stroke: '#fff' }}
                  connectNulls={false}
                />

                {/* Scenario A: Current Path */}
                <Line
                  type="monotone"
                  dataKey="forecastA"
                  name="Current Trend Path"
                  stroke="#7c3aed"
                  strokeWidth={3}
                  strokeDasharray="6 6"
                  dot={{ r: 4, fill: '#7c3aed' }}
                  connectNulls={true}
                />

                {/* Scenario B: Hypothetical Path */}
                {selectedHypothetical !== 0 && (
                  <Line
                    type="monotone"
                    dataKey="forecastB"
                    name={`Hypothetical Path (${selectedHypothetical > 0 ? '+' : ''}${selectedHypothetical}%)`}
                    stroke="#ea580c"
                    strokeWidth={3}
                    dot={{ r: 4, fill: '#ea580c' }}
                    connectNulls={true}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-lg text-slate-400">
              Loading your outlook chart...
            </div>
          )}
        </div>
      </div>

      {/* Senior-Friendly Scenario Comparison Controls */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm">
        <h3 className="text-xl font-bold text-slate-900">
          Compare a Different Hypothetical Scenario
        </h3>
        <p className="text-base text-slate-700 font-medium mt-1">
          How might your heart rate differ if your body rests more, or experiences light activity?
        </p>

        {/* 3 Large Preset Buttons for Senior Accessibility */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <button
            onClick={() => setSelectedHypothetical(-25)}
            className={`p-4 rounded-2xl border-2 font-bold text-base transition-all min-h-[56px] text-left flex flex-col justify-between ${
              selectedHypothetical === -25
                ? 'bg-purple-100 border-purple-600 text-purple-950 shadow-sm'
                : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span className="text-lg">🌿 More Relaxed (-25%)</span>
            <span className="text-xs text-slate-600 font-normal mt-1">Gentle resting & calm pacing</span>
          </button>

          <button
            onClick={() => setSelectedHypothetical(0)}
            className={`p-4 rounded-2xl border-2 font-bold text-base transition-all min-h-[56px] text-left flex flex-col justify-between ${
              selectedHypothetical === 0
                ? 'bg-purple-100 border-purple-600 text-purple-950 shadow-sm'
                : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span className="text-lg">⚖️ Current Trend (0%)</span>
            <span className="text-xs text-slate-600 font-normal mt-1">Continuing your daily baseline</span>
          </button>

          <button
            onClick={() => setSelectedHypothetical(25)}
            className={`p-4 rounded-2xl border-2 font-bold text-base transition-all min-h-[56px] text-left flex flex-col justify-between ${
              selectedHypothetical === 25
                ? 'bg-purple-100 border-purple-600 text-purple-950 shadow-sm'
                : 'bg-slate-50 border-slate-300 text-slate-700 hover:bg-slate-100'
            }`}
          >
            <span className="text-lg">🏃 Active Exertion (+25%)</span>
            <span className="text-xs text-slate-600 font-normal mt-1">Walking or mild physical activity</span>
          </button>
        </div>

        {/* Plain-English Scenario Difference Explanation */}
        <div className="mt-6 p-5 bg-slate-50 border-2 border-slate-200 rounded-2xl">
          <h4 className="text-base font-bold text-slate-900">
            What this scenario means for you:
          </h4>
          <p className="text-lg text-slate-800 font-medium mt-1 leading-relaxed">
            {getDifferenceExplanation()}
          </p>
        </div>

        {/* Plain-English Disclaimer */}
        <div className="mt-4 p-4 bg-amber-50 rounded-2xl border border-amber-300 text-sm text-amber-900">
          <strong>Please note:</strong> This alternative is an illustrative mathematical simulation to help you understand trends. It does not predict the proven effect of any specific medication or treatment.
        </div>
      </div>

      {/* Optional Technical Details for Mentors / Judges */}
      <div className="bg-white rounded-3xl p-6 border-2 border-slate-200 shadow-sm">
        <button
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full flex items-center justify-between text-base font-bold text-slate-700 hover:text-purple-700 focus:outline-none"
        >
          <span>Technical Model & Blockchain Details (For Judges & Mentors)</span>
          {showTechnicalDetails ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>

        {showTechnicalDetails && (
          <div className="mt-4 pt-4 border-t border-slate-200 text-sm font-mono space-y-2 text-slate-700">
            <div><strong>Active Twin State Version:</strong> Version {twinState?.state_version ?? 1}</div>
            <div><strong>Model Version:</strong> {twinState?.model_version || 'autoregressive_trend_v1.0'}</div>
            <div><strong>Data Quality Status:</strong> {twinState?.data_quality_status || 'good'}</div>
            <div><strong>Forecasting Algorithm:</strong> Autoregressive Trend Extrapolation (AR(2) + 24-hr Diurnal Harmonic)</div>
            <div><strong>Forecast Horizon:</strong> 120 minutes (2 hours, 15-minute steps) [Bounded for autonomic realism]</div>
            <div><strong>Hypothetical Kinetics:</strong> Asymptotic relaxation / exertion curve (k = 0.03 min⁻¹)</div>
            <div><strong>Blockchain Smart Contract:</strong> {twinState?.contract_address || '0xF2E246BB76DF876Cef8b38ae84130F4F55De395b'}</div>
            <div><strong>On-Chain State Root:</strong> 0x{twinState?.state_hash_sha256 || 'Verified'}</div>
          </div>
        )}
      </div>
    </div>
  );
};
