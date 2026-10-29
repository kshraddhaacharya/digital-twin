import React, { useState } from 'react';
import {
  Calendar,
  Heart,
  Activity,
  PlusCircle,
  Sparkles,
  Info,
  CheckCircle2,
  AlertTriangle,
  Trash2,
  Clock
} from 'lucide-react';
import { CycleSummary, CycleLog } from '../types';
import { api } from '../services/api';
import { formatISTDateOnly, formatIST } from '../utils/dateUtils';

interface CycleTrackerViewProps {
  summary: CycleSummary | null;
  history: CycleLog[];
  onDataChanged: () => void;
}

export const CycleTrackerView: React.FC<CycleTrackerViewProps> = ({
  summary,
  history,
  onDataChanged
}) => {
  const [showLogForm, setShowLogForm] = useState(false);
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState('');
  const [cycleLength, setCycleLength] = useState(28);
  const [periodLength, setPeriodLength] = useState(5);
  const [flow, setFlow] = useState('medium');
  const [symptoms, setSymptoms] = useState('Mild cramps, energy low');
  const [notes, setNotes] = useState('');

  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const handleLogPeriod = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      await api.logCycle({
        start_date: startDate,
        end_date: endDate || undefined,
        cycle_length_days: cycleLength,
        period_length_days: periodLength,
        flow_intensity: flow,
        symptoms: symptoms || undefined,
        notes: notes || undefined,
      });
      setMsg({ text: 'Period cycle logged successfully!', type: 'success' });
      setShowLogForm(false);
      onDataChanged();
    } catch (err: any) {
      setMsg({ text: 'Failed to record period log.', type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteCycle(id);
      onDataChanged();
    } catch (err) {
      alert('Failed to delete cycle record.');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center space-x-3">
            <Calendar className="w-8 h-8 text-pink-600" />
            <span>Menstrual & Hormonal Cycle Tracker</span>
          </h1>
          <p className="text-slate-600 text-base mt-1">
            Track your cycle phases, predict future periods, and understand how progesterone and estrogen
            naturally influence your resting heart rate.
          </p>
        </div>

        <button
          onClick={() => setShowLogForm(!showLogForm)}
          className="bg-pink-600 hover:bg-pink-700 text-white font-bold px-6 py-3 rounded-2xl shadow-sm text-base flex items-center space-x-2 min-h-[48px]"
        >
          <PlusCircle className="w-5 h-5" />
          <span>Log Period Dates</span>
        </button>
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

      {/* Cycle Phase & Countdown Wheel */}
      {summary && summary.has_data ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Phase Badge */}
          <div className="bg-gradient-to-br from-pink-500 to-rose-600 text-white p-6 rounded-3xl shadow-lg space-y-3">
            <span className="bg-white/20 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
              Current Cycle Day {summary.current_cycle_day} of {summary.cycle_length_days}
            </span>
            <h2 className="text-3xl font-black">{summary.current_phase}</h2>
            <p className="text-pink-100 text-sm leading-relaxed">{summary.phase_description}</p>
          </div>

          {/* Next Period Countdown */}
          <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-3">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Next Period Prediction</span>
            <div className="flex items-baseline space-x-2">
              <span className="text-5xl font-black text-slate-900">{summary.days_until_next_period}</span>
              <span className="text-base font-bold text-slate-500">days away</span>
            </div>
            <p className="text-sm font-semibold text-slate-700">
              Expected on: <span className="text-pink-600 font-bold">{formatISTDateOnly(summary.predicted_next_period)}</span>
            </p>
            <p className="text-xs text-slate-500">
              Fertile Window: {formatISTDateOnly(summary.fertile_window?.start)} to {formatISTDateOnly(summary.fertile_window?.end)}
            </p>
          </div>

          {/* Biological Heart Rate Link */}
          <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-3">
            <div className="flex items-center space-x-2 text-purple-700">
              <Heart className="w-5 h-5 fill-purple-700" />
              <span className="font-bold text-base">Digital Twin Vital Link</span>
            </div>
            <p className="text-2xl font-black text-slate-900">
              {summary.physiological_correlation?.current_twin_heart_rate_bpm.toFixed(1)} bpm
            </p>
            <p className="text-xs text-slate-600 leading-relaxed">
              <strong>Hormonal Trend:</strong> {summary.physiological_correlation?.expected_phase_shift}
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-white p-8 rounded-3xl border-2 border-slate-200 text-center space-y-3">
          <p className="text-lg font-bold text-slate-800">No cycle records logged yet.</p>
          <p className="text-sm text-slate-600 max-w-md mx-auto">
            Click &quot;Log Period Dates&quot; above to record your most recent period start date and calculate your active cycle phase.
          </p>
        </div>
      )}

      {/* FORM: LOG PERIOD */}
      {showLogForm && (
        <form onSubmit={handleLogPeriod} className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-pink-200 shadow-sm space-y-4">
          <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
            Record Period Cycle Dates
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Period Start Date *</label>
              <input
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Period End Date (optional)</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Average Cycle Length (Days)</label>
              <input
                type="number"
                min={20}
                max={45}
                value={cycleLength}
                onChange={(e) => setCycleLength(Number(e.target.value))}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Flow Intensity</label>
              <select
                value={flow}
                onChange={(e) => setFlow(e.target.value)}
                className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
              >
                <option value="light">Light</option>
                <option value="medium">Medium</option>
                <option value="heavy">Heavy</option>
                <option value="spotting">Spotting</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-600 mb-1">Symptoms (Cramps, Fatigue, Mood, Bloating)</label>
            <input
              type="text"
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              placeholder="e.g. Lower back cramps, mild headache"
              className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
            />
          </div>

          <div className="flex justify-end space-x-2 pt-2">
            <button
              type="button"
              onClick={() => setShowLogForm(false)}
              className="bg-slate-200 text-slate-800 font-bold px-4 py-2 rounded-xl text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="bg-pink-600 hover:bg-pink-700 text-white font-bold px-6 py-2 rounded-xl text-sm shadow-sm"
            >
              {saving ? 'Saving...' : 'Save Period Log'}
            </button>
          </div>
        </form>
      )}

      {/* Cycle History Table / Cards */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
          Cycle History Log ({history.length})
        </h2>

        {history.length === 0 ? (
          <p className="text-sm text-slate-500 italic">No historical cycles logged.</p>
        ) : (
          <div className="space-y-3">
            {history.map((item) => (
              <div
                key={item.id}
                className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-base text-slate-900">Period Start: {formatISTDateOnly(item.start_date)}</span>
                    <span className="bg-pink-100 text-pink-800 text-xs font-bold px-2.5 py-0.5 rounded-full capitalize">
                      {item.flow_intensity} Flow
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Cycle duration: {item.cycle_length_days} days • Period: {item.period_length_days} days
                    {item.end_date ? ` • Ended: ${formatISTDateOnly(item.end_date)}` : ''}
                    {item.created_at ? ` • Logged: ${formatIST(item.created_at)}` : ''}
                  </p>
                  {item.symptoms && (
                    <p className="text-xs text-slate-700 mt-1">Symptoms: {item.symptoms}</p>
                  )}
                </div>

                <button onClick={() => handleDelete(item.id)} className="text-slate-400 hover:text-red-600 p-2">
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
