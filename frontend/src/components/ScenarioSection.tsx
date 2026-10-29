import React, { useState, useEffect } from 'react';
import {
  Sliders,
  RotateCcw,
  AlertTriangle,
  Play,
  ArrowRight,
  TrendingDown,
  TrendingUp,
  HelpCircle,
  FileText
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ReferenceArea
} from 'recharts';
import { TwinState, ScenarioComparison } from '../types';
import { api } from '../services/api';
import { formatISTTimeOnly } from '../utils/dateUtils';

interface ScenarioSectionProps {
  patientId: string;
  twinState: TwinState | null;
}

export const ScenarioSection: React.FC<ScenarioSectionProps> = ({
  patientId,
  twinState,
}) => {
  const [paramValue, setParamValue] = useState<number>(-25.0);
  const [horizonMinutes, setHorizonMinutes] = useState<number>(360);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const runSimulation = async (val: number, horizon: number) => {
    setLoading(true);
    try {
      const res = await api.simulateScenarios(patientId, {
        horizon_minutes: horizon,
        parameter_name: 'trend_damping_pct',
        parameter_value: val,
        parameter_unit: '%',
      });
      setComparison(res);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to run scenario simulation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runSimulation(paramValue, horizonMinutes);
  }, [patientId]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVal = parseFloat(e.target.value);
    setParamValue(newVal);
  };

  const handleSliderCommit = () => {
    runSimulation(paramValue, horizonMinutes);
  };

  const handleResetBaseline = () => {
    setParamValue(0.0);
    runSimulation(0.0, horizonMinutes);
  };

  // Build dual-trajectory dataset for chart
  const chartData = comparison
    ? comparison.scenario_a.simulated_trajectory.map((ptA, idx) => {
        const ptB = comparison.scenario_b.simulated_trajectory[idx];
        const timeLabel = formatISTTimeOnly(ptA.timestamp, false);
        return {
          time: timeLabel,
          scenario_a: ptA.simulated_value,
          scenario_b: ptB ? ptB.simulated_value : null,
          delta: ptB ? Math.abs(ptB.simulated_value - ptA.simulated_value).toFixed(1) : 0,
        };
      })
    : [];

  return (
    <div className="space-y-6">
      {/* Educational & Mathematical Simulation Warning */}
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs text-amber-950 flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-sm text-amber-900">
            Transparent Mathematical Simulation — Not a Validated Clinical Intervention
          </div>
          <p className="mt-1">
            Scenario B computes a transparent counterfactual mathematical variation from the patient's current modeled twin state.
            This demonstration does not simulate validated pharmaceutical, surgical, or clinical treatment outcomes.
          </p>
        </div>
      </div>

      {/* Interactive Scenario Parameter Controls Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <h2 className="text-lg font-bold text-slate-900">
              Hypothetical Altered Condition Simulator
            </h2>
            <p className="text-xs text-slate-500 mt-1">
              Compare <strong>Scenario A (Current Trajectory)</strong> against{' '}
              <strong>Scenario B (Hypothetical Altered Condition)</strong>. Both scenarios originate from identical Twin State v{twinState?.state_version}.
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleResetBaseline}
              disabled={loading}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-2 rounded-lg transition-colors flex items-center space-x-1 border border-slate-200"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset to Baseline (0%)</span>
            </button>

            <button
              onClick={() => runSimulation(paramValue, horizonMinutes)}
              disabled={loading}
              className="bg-twin-600 hover:bg-twin-700 text-white font-semibold text-xs px-4 py-2 rounded-lg shadow-sm transition-all flex items-center space-x-1.5 disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 fill-white ${loading ? 'animate-pulse' : ''}`} />
              <span>{loading ? 'Simulating...' : 'Recompute'}</span>
            </button>
          </div>
        </div>

        {/* Interactive Parameter Slider */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
          <div>
            <div className="flex justify-between items-center text-xs font-semibold text-slate-700 mb-2">
              <label>Hypothetical Heart-Rate Trend Damping</label>
              <span className={`font-mono font-bold px-2.5 py-0.5 rounded text-xs border ${
                paramValue < 0
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : paramValue > 0
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : 'bg-slate-100 text-slate-700 border-slate-300'
              }`}>
                {paramValue > 0 ? `+${paramValue}` : paramValue}%
              </span>
            </div>

            <input
              type="range"
              min="-80"
              max="80"
              step="5"
              value={paramValue}
              onChange={handleSliderChange}
              onMouseUp={handleSliderCommit}
              onTouchEnd={handleSliderCommit}
              className="w-full accent-twin-600 cursor-pointer"
            />

            <div className="flex justify-between text-[10px] text-slate-400 mt-1">
              <span>-80% (Substantial Damping)</span>
              <span>0% (Baseline)</span>
              <span>+80% (Amplification)</span>
            </div>
          </div>

          {/* Delta Metrics Cards */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <span className="text-[10px] font-semibold uppercase text-slate-500">Max Delta</span>
              <div className="text-lg font-bold text-slate-900 mt-1">
                ±{comparison ? comparison.delta_summary.max_absolute_delta_bpm.toFixed(1) : '--'}{' '}
                <span className="text-xs font-normal text-slate-500">bpm</span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <span className="text-[10px] font-semibold uppercase text-slate-500">Mean Delta</span>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {comparison ? comparison.delta_summary.mean_absolute_delta_bpm.toFixed(1) : '--'}{' '}
                <span className="text-xs font-normal text-slate-500">bpm</span>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
              <span className="text-[10px] font-semibold uppercase text-slate-500">Endpoint Delta</span>
              <div className="text-lg font-bold text-slate-900 mt-1">
                {comparison ? comparison.delta_summary.endpoint_delta_bpm.toFixed(1) : '--'}{' '}
                <span className="text-xs font-normal text-slate-500">bpm</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dual Trajectory Chart */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="pb-4 border-b border-slate-100">
          <h3 className="text-base font-bold text-slate-900">
            Scenario Trajectory Comparison
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Blue: Scenario A (Current Trajectory) • Orange: Scenario B (Hypothetical Altered Condition)
          </p>
        </div>

        <div className="mt-6 h-80 w-full">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 15, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} stroke="#cbd5e1" unit=" bpm" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />

                <ReferenceArea y1={60} y2={100} fill="#ecfdf5" fillOpacity={0.4} />

                {/* Scenario A Line */}
                <Line
                  type="monotone"
                  dataKey="scenario_a"
                  name="Scenario A: Current Trajectory"
                  stroke="#0284c7"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: '#0284c7' }}
                />

                {/* Scenario B Line */}
                <Line
                  type="monotone"
                  dataKey="scenario_b"
                  name={`Scenario B: Altered Trend (${paramValue > 0 ? `+${paramValue}` : paramValue}%)`}
                  stroke="#f97316"
                  strokeWidth={2.5}
                  strokeDasharray="4 4"
                  dot={{ r: 4, fill: '#f97316' }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">
              Loading simulation comparison...
            </div>
          )}
        </div>

        {/* Structured Scenario Record & Assumptions Breakdown */}
        {comparison && (
          <div className="mt-6 pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                Mathematical Rule
              </span>
              <p className="font-mono text-slate-800 text-[11px] mt-2 leading-relaxed">
                {comparison.scenario_b.mathematical_rule}
              </p>
            </div>

            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                Stated Assumptions
              </span>
              <p className="text-slate-700 mt-2 leading-relaxed">
                {comparison.scenario_b.assumptions}
              </p>
            </div>

            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
              <span className="text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                Model Limitations
              </span>
              <p className="text-slate-700 mt-2 leading-relaxed">
                {comparison.scenario_b.limitations}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
