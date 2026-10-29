import React, { useState, useEffect } from 'react';
import {
  Activity,
  PlusCircle,
  TrendingUp,
  Heart,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Trash2,
  Sparkles,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { HealthCondition, ConditionLog, DiseaseAnalytics } from '../types';
import { api } from '../services/api';
import { formatISTDateOnly, formatIST } from '../utils/dateUtils';

interface DiseaseTrackerViewProps {
  conditions: HealthCondition[];
  logs: ConditionLog[];
  analytics: DiseaseAnalytics | null;
  onDataChanged: () => void;
}

export const DiseaseTrackerView: React.FC<DiseaseTrackerViewProps> = ({
  conditions,
  logs,
  analytics,
  onDataChanged
}) => {
  // Add Condition Form
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [condName, setCondName] = useState('');
  const [diagnosedDate, setDiagnosedDate] = useState('');
  const [severity, setSeverity] = useState('monitoring');
  const [statusVal, setStatusVal] = useState('active');

  // Add Log Entry Form
  const [showAddLog, setShowAddLog] = useState(false);
  const [selectedConditionId, setSelectedConditionId] = useState<number | ''>('');
  const [logDate, setLogDate] = useState(new Date().toISOString().slice(0, 10));
  const [metricName, setMetricName] = useState('Blood Pressure (Systolic)');
  const [metricValue, setMetricValue] = useState<number | ''>(120);
  const [metricUnit, setMetricUnit] = useState('mmHg');
  const [symptoms, setSymptoms] = useState('');
  const [logNotes, setLogNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleCreateCondition = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await api.createCondition({
        condition_name: condName,
        diagnosed_date: diagnosedDate || undefined,
        severity: severity,
        status: statusVal,
      });
      setMsg({ text: `Condition "${condName}" added to tracker!`, type: 'success' });
      setCondName('');
      setShowAddCondition(false);
      onDataChanged();
    } catch (err: any) {
      setMsg({ text: 'Failed to add condition.', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleCreateLog = async (e: React.FormEvent) => {
    e.preventDefault();
    if (metricValue === '') return;
    setSaving(true);
    setMsg(null);
    try {
      await api.createConditionLog({
        condition_id: selectedConditionId ? Number(selectedConditionId) : undefined,
        log_date: logDate,
        metric_name: metricName,
        metric_value: Number(metricValue),
        metric_unit: metricUnit,
        symptoms: symptoms || undefined,
        notes: logNotes || undefined,
      });
      setMsg({ text: 'Health measurement logged to timeline!', type: 'success' });
      setSymptoms('');
      setLogNotes('');
      setShowAddLog(false);
      onDataChanged();
    } catch (err: any) {
      setMsg({ text: 'Failed to record measurement log.', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteCondition = async (id: number) => {
    if (!window.confirm('Delete this condition and associated logs?')) return;
    try {
      await api.deleteCondition(id);
      onDataChanged();
    } catch (err) {
      alert('Failed to delete condition.');
    }
  };

  const handleDeleteLog = async (id: number) => {
    try {
      await api.deleteConditionLog(id);
      onDataChanged();
    } catch (err) {
      alert('Failed to delete log entry.');
    }
  };

  // Prepare chart data from logs
  const chartData = logs.map((l) => ({
    date: formatISTDateOnly(l.log_date),
    value: l.metric_value,
    metric: `${l.metric_name} (${l.metric_unit})`,
    condition: l.condition_name
  }));

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center space-x-3">
            <Activity className="w-8 h-8 text-indigo-700" />
            <span>Disease Tracker & Health Timeline</span>
          </h1>
          <p className="text-slate-600 text-base mt-1">
            Monitor chronic conditions, record symptoms and vitals over time, and analyze clinical trends.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setShowAddCondition(!showAddCondition)}
            className="bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-bold px-4 py-2.5 rounded-xl border border-indigo-200 text-sm flex items-center space-x-1.5"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Add Condition</span>
          </button>

          <button
            onClick={() => setShowAddLog(!showAddLog)}
            className="bg-indigo-700 hover:bg-indigo-800 text-white font-bold px-5 py-2.5 rounded-xl shadow-sm text-sm flex items-center space-x-1.5"
          >
            <PlusCircle className="w-4 h-4" />
            <span>Log Measurement</span>
          </button>
        </div>
      </div>

      {msg && (
        <div
          className={`p-4 rounded-2xl text-base font-semibold flex items-center space-x-2 border-2 ${
            msg.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-900'
              : 'bg-red-50 border-red-300 text-red-900'
          }`}
        >
          {msg.type === 'success' ? (
            <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
          )}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Analytics Cards */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-2">
            <p className="text-xs font-bold text-slate-500 uppercase">Cardiovascular Indicator</p>
            <p className="text-2xl font-black text-slate-900">{analytics.cardiovascular.status}</p>
            <p className="text-sm font-semibold text-slate-600">
              Risk Level: <span className="font-bold text-indigo-700">{analytics.cardiovascular.risk_level}</span>
            </p>
            <p className="text-xs text-slate-500 pt-1">
              Resting Rate: {analytics.cardiovascular.latest_heart_rate_bpm.toFixed(1)} bpm
            </p>
          </div>

          <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-2">
            <p className="text-xs font-bold text-slate-500 uppercase">Autonomic Strain Score</p>
            <p className="text-2xl font-black text-slate-900">{analytics.stress_fatigue.score_0_to_100} / 100</p>
            <p className="text-sm font-semibold text-slate-600">
              Classification: <span className="font-bold text-emerald-700">{analytics.stress_fatigue.status}</span>
            </p>
            <p className="text-xs text-slate-500 pt-1">
              Variability Index: ±{analytics.stress_fatigue.physiological_variability.toFixed(2)} bpm
            </p>
          </div>

          <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-2">
            <p className="text-xs font-bold text-slate-500 uppercase">Body Mass Index (BMI)</p>
            <p className="text-2xl font-black text-slate-900">
              {analytics.body_mass_index.bmi ? `${analytics.body_mass_index.bmi}` : 'Not Calculated'}
            </p>
            <p className="text-sm font-semibold text-slate-600">
              {analytics.body_mass_index.category || 'Provide height & weight in profile'}
            </p>
            <p className="text-xs text-slate-500 pt-1">
              {analytics.body_mass_index.body_weight_kg ? `${analytics.body_mass_index.body_weight_kg} kg` : 'Weight unrecorded'}
            </p>
          </div>
        </div>
      )}

      {/* FORM: ADD CONDITION */}
      {showAddCondition && (
        <form onSubmit={handleCreateCondition} className="bg-slate-50 p-6 rounded-3xl border-2 border-indigo-200 shadow-sm space-y-4">
          <h3 className="text-lg font-bold text-slate-900">Add Health Condition to Monitor</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Condition Name *</label>
              <input
                type="text"
                required
                value={condName}
                onChange={(e) => setCondName(e.target.value)}
                placeholder="e.g. Hypertension, Asthma"
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Diagnosed Date</label>
              <input
                type="date"
                value={diagnosedDate}
                onChange={(e) => setDiagnosedDate(e.target.value)}
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              >
                <option value="monitoring">Monitoring / Preventative</option>
                <option value="mild">Mild</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={() => setShowAddCondition(false)}
              className="bg-slate-200 text-slate-800 font-bold px-4 py-2 rounded-xl text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-indigo-700 text-white font-bold px-5 py-2 rounded-xl text-sm shadow-sm"
            >
              {saving ? 'Saving...' : 'Save Condition'}
            </button>
          </div>
        </form>
      )}

      {/* FORM: LOG MEASUREMENT */}
      {showAddLog && (
        <form onSubmit={handleCreateLog} className="bg-slate-50 p-6 rounded-3xl border-2 border-indigo-200 shadow-sm space-y-4">
          <h3 className="text-lg font-bold text-slate-900">Record Measurement or Symptom</h3>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Linked Condition</label>
              <select
                value={selectedConditionId}
                onChange={(e) => setSelectedConditionId(e.target.value ? Number(e.target.value) : '')}
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              >
                <option value="">General Vitals</option>
                {conditions.map((c) => (
                  <option key={c.id} value={c.id}>{c.condition_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Date *</label>
              <input
                type="date"
                required
                value={logDate}
                onChange={(e) => setLogDate(e.target.value)}
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Metric Name *</label>
              <input
                type="text"
                required
                value={metricName}
                onChange={(e) => setMetricName(e.target.value)}
                placeholder="e.g. Systolic BP, Blood Glucose"
                className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Value & Unit *</label>
              <div className="flex space-x-1">
                <input
                  type="number"
                  step="any"
                  required
                  value={metricValue}
                  onChange={(e) => setMetricValue(e.target.value ? Number(e.target.value) : '')}
                  className="w-2/3 p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
                />
                <input
                  type="text"
                  required
                  value={metricUnit}
                  onChange={(e) => setMetricUnit(e.target.value)}
                  placeholder="mmHg"
                  className="w-1/3 p-2.5 bg-white border border-slate-300 rounded-xl text-sm font-semibold"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-600 mb-1">Symptoms Experienced (optional)</label>
            <input
              type="text"
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              placeholder="e.g. Mild headache, dizziness after exercise"
              className="w-full p-2.5 bg-white border border-slate-300 rounded-xl text-sm"
            />
          </div>

          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={() => setShowAddLog(false)}
              className="bg-slate-200 text-slate-800 font-bold px-4 py-2 rounded-xl text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-indigo-700 text-white font-bold px-5 py-2 rounded-xl text-sm shadow-sm"
            >
              {saving ? 'Saving...' : 'Record to Timeline'}
            </button>
          </div>
        </form>
      )}

      {/* Timeline Chart */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2 border-b border-slate-200 pb-3">
          <TrendingUp className="w-5 h-5 text-indigo-700" />
          <span>Historical Measurements Chart</span>
        </h2>

        {chartData.length < 2 ? (
          <div className="p-8 text-center bg-slate-50 rounded-2xl border border-slate-200">
            <p className="text-base font-bold text-slate-700">Need at least 2 timeline logs to render trend chart.</p>
            <p className="text-sm text-slate-500 mt-1">
              Click &quot;Log Measurement&quot; above to record health metrics across different dates.
            </p>
          </div>
        ) : (
          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 12 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', color: '#fff', border: 'none' }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="value"
                  name="Recorded Value"
                  stroke="#4f46e5"
                  strokeWidth={3}
                  dot={{ r: 5, fill: '#4f46e5' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Conditions Monitored List */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
          Active Conditions Monitored ({conditions.length})
        </h2>

        {conditions.length === 0 ? (
          <p className="text-sm text-slate-500 italic">No specific medical conditions added yet.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {conditions.map((c) => (
              <div key={c.id} className="p-4 bg-slate-50 rounded-2xl border border-slate-200 space-y-2 relative">
                <button
                  onClick={() => handleDeleteCondition(c.id)}
                  className="absolute top-3 right-3 text-slate-400 hover:text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-base text-slate-900">{c.condition_name}</span>
                  <span className="bg-indigo-100 text-indigo-800 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase">
                    {c.severity}
                  </span>
                </div>
                <p className="text-xs text-slate-500">Diagnosed: {c.diagnosed_date ? formatISTDateOnly(c.diagnosed_date) : 'Ongoing'}</p>
                <p className="text-xs font-semibold text-slate-700">{c.total_logs || 0} measurements recorded</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Log History Cards */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
          Timeline Measurement Log ({logs.length})
        </h2>

        {logs.length === 0 ? (
          <p className="text-sm text-slate-500 italic">No health log entries recorded yet.</p>
        ) : (
          <div className="space-y-2.5">
            {logs.map((l) => (
              <div key={l.id} className="p-3.5 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900 text-sm">{l.metric_name}:</span>
                    <span className="font-black text-purple-700 text-sm">{l.metric_value} {l.metric_unit}</span>
                    <span className="text-xs text-slate-500 font-semibold">• {formatISTDateOnly(l.log_date)} (Recorded: {formatIST(l.created_at)})</span>
                  </div>
                  {l.symptoms && (
                    <p className="text-xs text-slate-600 mt-0.5">Symptoms: {l.symptoms}</p>
                  )}
                </div>

                <button onClick={() => handleDeleteLog(l.id)} className="text-slate-400 hover:text-red-600 p-1">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
