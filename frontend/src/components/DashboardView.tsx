import React from 'react';
import {
  Heart,
  ShieldCheck,
  TrendingUp,
  FileText,
  Video,
  Activity,
  PlusCircle,
  Search,
  UserCheck,
  Calendar,
  AlertCircle,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { User, TwinState, Measurement, MedicalReport, UserVideo, DiseaseAnalytics } from '../types';

interface DashboardViewProps {
  user: User;
  twinState: TwinState | null;
  recentMeasurements: Measurement[];
  reports: MedicalReport[];
  videos: UserVideo[];
  diseaseAnalytics: DiseaseAnalytics | null;
  onNavigate: (tab: string) => void;
  onQuickLoadDemo?: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  user,
  twinState,
  recentMeasurements,
  reports,
  videos,
  diseaseAnalytics,
  onNavigate,
  onQuickLoadDemo
}) => {
  // Calculate profile completion percentage
  const fields = [
    user.full_name,
    user.email,
    user.age,
    user.gender && user.gender !== 'Prefer not to say',
    user.height,
    user.body_weight,
    user.existing_conditions,
    user.emergency_contact
  ];
  const filledCount = fields.filter(Boolean).length;
  const completionPct = Math.round((filledCount / fields.length) * 100);

  // Latest measurement
  const latestMeas = recentMeasurements.length > 0 ? recentMeasurements[0] : null;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Welcome & Profile Summary Header */}
      <div className="bg-gradient-to-r from-purple-900 via-indigo-900 to-slate-900 text-white rounded-3xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center space-x-2 bg-purple-800/60 border border-purple-400/30 px-3.5 py-1 rounded-full text-xs font-semibold text-purple-200">
              <Sparkles className="w-3.5 h-3.5 text-purple-300" />
              <span>Personalized Sovereign Health Twin</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
              Welcome back, {user.full_name}
            </h1>
            <p className="text-purple-200 text-base leading-relaxed">
              Your digital twin is tracking your continuous vital signs, verifying integrity on-chain,
              and simulating future trajectories.
            </p>
          </div>

          {/* Quick Profile Meter */}
          <div className="bg-white/10 backdrop-blur-md border border-white/20 p-4 rounded-2xl w-full md:w-64 space-y-2">
            <div className="flex justify-between items-center text-sm font-bold">
              <span className="text-slate-200">Profile Completion</span>
              <span className="text-emerald-400">{completionPct}%</span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-2.5 overflow-hidden">
              <div
                className="bg-emerald-400 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${completionPct}%` }}
              ></div>
            </div>
            {completionPct < 100 && (
              <button
                onClick={() => onNavigate('profile')}
                className="text-xs text-purple-200 hover:text-white font-semibold underline block text-right pt-1"
              >
                Complete health profile →
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Quick Action Buttons */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <button
          onClick={() => onNavigate('reports')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <FileText className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Upload Report</span>
        </button>

        <button
          onClick={() => onNavigate('videos')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <Video className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Upload Video</span>
        </button>

        <button
          onClick={() => onNavigate('record-history')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <PlusCircle className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Add Measurement</span>
        </button>

        <button
          onClick={() => onNavigate('future-outlook')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <TrendingUp className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Future Outlook</span>
        </button>

        <button
          onClick={() => onNavigate('disease-tracker')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <Activity className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Disease Tracker</span>
        </button>

        <button
          onClick={() => onNavigate('profile')}
          className="bg-white hover:bg-purple-50 p-4 rounded-2xl border-2 border-slate-200 hover:border-purple-300 shadow-sm transition text-left flex flex-col justify-between space-y-2 min-h-[90px]"
        >
          <UserCheck className="w-6 h-6 text-purple-700" />
          <span className="font-bold text-slate-800 text-sm">Update Profile</span>
        </button>
      </div>

      {/* Main Dashboard Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Current Digital Twin Vital State */}
        <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Heart className="w-5 h-5 text-red-600 fill-red-600" />
              <span>Current Vital Twin</span>
            </h2>
            <span className="bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-bold px-2.5 py-1 rounded-full flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Verified On-Chain</span>
            </span>
          </div>

          <div className="pt-2 flex items-baseline space-x-2">
            <span className="text-5xl font-black text-slate-900">
              {twinState ? twinState.latest_heart_rate.toFixed(1) : (latestMeas ? latestMeas.value.toFixed(1) : '72.0')}
            </span>
            <span className="text-lg font-bold text-slate-500">bpm</span>
          </div>

          <p className="text-sm text-slate-600 font-medium">
            Status: <span className="font-bold text-slate-800 capitalize">{twinState?.vital_status || 'Normal Resting Range'}</span>
          </p>

          <div className="p-3.5 bg-slate-50 rounded-2xl text-xs text-slate-600 space-y-1">
            <p><strong>Digital Twin Version:</strong> v{twinState?.state_version || 1}</p>
            <p><strong>Hourly Trend:</strong> {twinState?.trend_slope_per_hour ? `${twinState.trend_slope_per_hour.toFixed(2)} bpm/hr` : 'Steady (0.00 bpm/hr)'}</p>
          </div>

          <button
            onClick={() => onNavigate('my-health')}
            className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 rounded-xl transition text-sm flex items-center justify-center space-x-2"
          >
            <span>View Full Health Screen</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Card 2: Physical Metrics & Health Profile */}
        <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
          <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
            <UserCheck className="w-5 h-5 text-purple-700" />
            <span>Health Profile Summary</span>
          </h2>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="bg-purple-50/50 p-3.5 rounded-2xl border border-purple-100">
              <p className="text-xs text-slate-500 font-bold">Body Weight</p>
              <p className="text-2xl font-black text-slate-900 mt-1">
                {user.body_weight ? `${user.body_weight} kg` : 'Not Set'}
              </p>
            </div>

            <div className="bg-purple-50/50 p-3.5 rounded-2xl border border-purple-100">
              <p className="text-xs text-slate-500 font-bold">Height</p>
              <p className="text-2xl font-black text-slate-900 mt-1">
                {user.height ? `${user.height} cm` : 'Not Set'}
              </p>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200">
              <p className="text-xs text-slate-500 font-bold">Age / Gender</p>
              <p className="text-base font-bold text-slate-800 mt-1">
                {user.age || '—'} yrs • {user.gender || '—'}
              </p>
            </div>

            <div className="bg-slate-50 p-3.5 rounded-2xl border border-slate-200">
              <p className="text-xs text-slate-500 font-bold">Body Mass Index</p>
              <p className="text-base font-bold text-slate-800 mt-1">
                {diseaseAnalytics?.body_mass_index.bmi ? `${diseaseAnalytics.body_mass_index.bmi} (${diseaseAnalytics.body_mass_index.category})` : '—'}
              </p>
            </div>
          </div>

          <div className="text-xs text-slate-600 truncate">
            <strong>Known Conditions:</strong> {user.existing_conditions || 'None recorded'}
          </div>

          <button
            onClick={() => onNavigate('profile')}
            className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-3 rounded-xl transition text-sm flex items-center justify-center space-x-2"
          >
            <span>Edit My Profile</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Card 3: Disease Tracker & Risk Status */}
        <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-slate-900 flex items-center space-x-2">
              <Activity className="w-5 h-5 text-indigo-700" />
              <span>Disease & Risk Monitor</span>
            </h2>
            <span className="bg-indigo-50 text-indigo-800 border border-indigo-200 text-xs font-bold px-2 py-0.5 rounded-full">
              {diseaseAnalytics?.cardiovascular.risk_level || 'Low'} Risk
            </span>
          </div>

          <div className="p-3.5 bg-slate-50 rounded-2xl space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600 font-medium">Cardiovascular:</span>
              <span className="font-bold text-slate-900">{diseaseAnalytics?.cardiovascular.status || 'Optimal Resting'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600 font-medium">Autonomic Strain:</span>
              <span className="font-bold text-slate-900">{diseaseAnalytics?.stress_fatigue.status || 'Calm & Rested'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600 font-medium">Conditions Monitored:</span>
              <span className="font-bold text-purple-700">{diseaseAnalytics?.tracking_summary.monitored_conditions_count || 0} active</span>
            </div>
          </div>

          <p className="text-xs text-slate-500 italic">
            Continuous evaluation of rolling physiological variability and trend variance.
          </p>

          <button
            onClick={() => onNavigate('disease-tracker')}
            className="w-full bg-indigo-50 hover:bg-indigo-100 text-indigo-900 font-bold py-3 rounded-xl transition text-sm flex items-center justify-center space-x-2 border border-indigo-200"
          >
            <span>Open Disease Timeline</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Reports & Videos Quick Previews */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Uploaded Reports Preview */}
        <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <span>Recent Medical Reports ({reports.length})</span>
            </h3>
            <button
              onClick={() => onNavigate('reports')}
              className="text-xs font-bold text-purple-700 hover:underline"
            >
              View all & search →
            </button>
          </div>

          {reports.length === 0 ? (
            <div className="p-6 bg-slate-50 rounded-2xl border border-dashed border-slate-300 text-center space-y-2">
              <p className="text-sm font-semibold text-slate-600">No medical reports uploaded yet.</p>
              <button
                onClick={() => onNavigate('reports')}
                className="bg-purple-700 text-white font-bold text-xs px-4 py-2 rounded-xl"
              >
                Upload PDF or Lab Photo
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {reports.slice(0, 3).map((r) => (
                <div
                  key={r.id}
                  onClick={() => onNavigate('reports')}
                  className="p-3 bg-slate-50 hover:bg-purple-50/50 rounded-xl border border-slate-200 cursor-pointer transition flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <p className="font-bold text-sm text-slate-900">{r.title}</p>
                    <p className="text-xs text-slate-500">{r.report_date} • {r.file_type.toUpperCase()} • {r.biomarkers.length} vitals detected</p>
                  </div>
                  <span className="text-xs text-purple-700 font-bold">Search →</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Uploaded Videos Preview */}
        <div className="bg-white p-6 rounded-3xl border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
              <Video className="w-5 h-5 text-amber-600" />
              <span>Personal Video Library ({videos.length})</span>
            </h3>
            <button
              onClick={() => onNavigate('videos')}
              className="text-xs font-bold text-purple-700 hover:underline"
            >
              View all videos →
            </button>
          </div>

          {videos.length === 0 ? (
            <div className="p-6 bg-slate-50 rounded-2xl border border-dashed border-slate-300 text-center space-y-2">
              <p className="text-sm font-semibold text-slate-600">No exercise or mobility videos uploaded.</p>
              <button
                onClick={() => onNavigate('videos')}
                className="bg-amber-600 text-white font-bold text-xs px-4 py-2 rounded-xl"
              >
                Upload Video (MP4 / WebM)
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {videos.slice(0, 3).map((v) => (
                <div
                  key={v.id}
                  onClick={() => onNavigate('videos')}
                  className="p-3 bg-slate-50 hover:bg-amber-50/50 rounded-xl border border-slate-200 cursor-pointer transition flex items-center justify-between"
                >
                  <div className="space-y-0.5">
                    <p className="font-bold text-sm text-slate-900">{v.title}</p>
                    <p className="text-xs text-slate-500">{v.video_date} • {v.file_type.toUpperCase()}</p>
                  </div>
                  <span className="text-xs text-amber-700 font-bold">Play →</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
