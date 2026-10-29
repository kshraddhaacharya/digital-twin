import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  ShieldCheck,
  AlertTriangle,
  Play,
  CheckCircle2,
  Calendar,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { ModelEvaluation } from '../types';
import { api } from '../services/api';
import { formatIST } from '../utils/dateUtils';

interface EvaluationSectionProps {
  patientId: string;
}

export const EvaluationSection: React.FC<EvaluationSectionProps> = ({ patientId }) => {
  const [evaluation, setEvaluation] = useState<ModelEvaluation | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [splitRatio, setSplitRatio] = useState<number>(0.2);

  const fetchEvaluation = async (ratio: number) => {
    setLoading(true);
    try {
      const res = await api.getEvaluation(patientId, ratio);
      setEvaluation(res);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to compute model evaluation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvaluation(splitRatio);
  }, [patientId]);

  return (
    <div className="space-y-6">
      {/* Strict Chronological Validation Guarantee Card */}
      <div className="bg-slate-900 rounded-xl p-6 text-white shadow-md">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="w-6 h-6 text-emerald-400" />
          <h2 className="text-lg font-bold">
            Strict Chronological Train / Test Validation
          </h2>
        </div>
        <p className="text-xs text-slate-300 mt-2 leading-relaxed">
          In physiological time-series analysis, random K-fold shuffling causes severe data leakage from future observations.
          Our validation pipeline strictly partitions historical observations chronologically: models are trained strictly on the past and evaluated on the subsequent held-out test window.
        </p>
      </div>

      {/* Synthetic Benchmark Disclaimer Warning */}
      <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-xs text-amber-950 flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-sm text-amber-900">
            Synthetic Benchmark Evaluation Disclaimer
          </div>
          <p className="mt-1">
            {evaluation?.disclaimer ||
              'Evaluation executed on synthetic benchmark observations. High accuracy metrics reflect adherence to synthetic generative rules and do NOT demonstrate clinical safety or diagnostic validity on real human patients.'}
          </p>
        </div>
      </div>

      {/* Metric Cards Comparison */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Autoregressive MAE */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Autoregressive Model MAE
          </span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-slate-900">
              {evaluation ? evaluation.mae.toFixed(2) : '--'}
            </span>
            <span className="text-xs font-medium text-slate-500">bpm</span>
          </div>
          <div className="mt-3 text-[11px] text-emerald-700 font-semibold flex items-center space-x-1">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>
              {evaluation ? `${evaluation.mae_improvement_pct}% improvement vs baseline` : '--'}
            </span>
          </div>
        </div>

        {/* Baseline Persistence MAE */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Baseline Persistence MAE
          </span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-slate-500">
              {evaluation ? evaluation.baseline_mae.toFixed(2) : '--'}
            </span>
            <span className="text-xs font-medium text-slate-500">bpm</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-400">
            Naive hold-forward benchmark
          </div>
        </div>

        {/* Autoregressive RMSE */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Autoregressive RMSE
          </span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-3xl font-black text-slate-900">
              {evaluation ? evaluation.rmse.toFixed(2) : '--'}
            </span>
            <span className="text-xs font-medium text-slate-500">bpm</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500">
            Baseline RMSE: {evaluation ? evaluation.baseline_rmse.toFixed(2) : '--'} bpm
          </div>
        </div>

        {/* Partition Counts */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Chronological Split
          </span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-2xl font-black text-slate-900">
              {evaluation ? `${evaluation.train_samples} / ${evaluation.test_samples}` : '--'}
            </span>
            <span className="text-xs font-medium text-slate-500">Train / Test</span>
          </div>
          <div className="mt-3 text-[11px] text-slate-500">
            Held-out Test Ratio: {Math.round(splitRatio * 100)}%
          </div>
        </div>
      </div>

      {/* Evaluation Summary & Parameters Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Evaluation Configuration & Time Horizons
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              Test partition period: {evaluation?.evaluation_period_start ? formatIST(evaluation.evaluation_period_start) : 'N/A'} to{' '}
              {evaluation?.evaluation_period_end ? formatIST(evaluation.evaluation_period_end) : 'N/A'}
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <label className="text-xs text-slate-600 font-medium">Test Split Ratio:</label>
            <select
              value={splitRatio}
              onChange={(e) => {
                const r = parseFloat(e.target.value);
                setSplitRatio(r);
                fetchEvaluation(r);
              }}
              className="text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 font-semibold"
            >
              <option value="0.15">15% Held-out Test</option>
              <option value="0.20">20% Held-out Test (Default)</option>
              <option value="0.30">30% Held-out Test</option>
            </select>

            <button
              onClick={() => fetchEvaluation(splitRatio)}
              disabled={loading}
              className="bg-twin-600 hover:bg-twin-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-all disabled:opacity-50"
            >
              {loading ? 'Evaluating...' : 'Re-run Evaluation'}
            </button>
          </div>
        </div>

        {/* Detailed Comparison Table */}
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-xs">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Model Pipeline</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Architecture / Rules</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Test MAE</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Test RMSE</th>
                <th className="px-4 py-3 text-left font-semibold text-slate-600 uppercase">Error Reduction</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              <tr className="bg-emerald-50/40 font-semibold">
                <td className="px-4 py-3 text-slate-900">Autoregressive Trend Model</td>
                <td className="px-4 py-3 text-slate-600">Ridge regularized AR(2) + 24-hr Diurnal Sin/Cos Harmonics</td>
                <td className="px-4 py-3 text-emerald-800 font-black">{evaluation?.mae.toFixed(2)} bpm</td>
                <td className="px-4 py-3 text-emerald-800 font-black">{evaluation?.rmse.toFixed(2)} bpm</td>
                <td className="px-4 py-3 text-emerald-700 font-black">-{evaluation?.mae_improvement_pct}% MAE</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-slate-700">Baseline Persistence Model</td>
                <td className="px-4 py-3 text-slate-500">Naive hold-forward of last known training observation</td>
                <td className="px-4 py-3 text-slate-600">{evaluation?.baseline_mae.toFixed(2)} bpm</td>
                <td className="px-4 py-3 text-slate-600">{evaluation?.baseline_rmse.toFixed(2)} bpm</td>
                <td className="px-4 py-3 text-slate-400">Baseline (0%)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
