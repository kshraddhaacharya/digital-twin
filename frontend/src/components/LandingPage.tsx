import React, { useState } from 'react';
import {
  Heart,
  ShieldCheck,
  Activity,
  FileText,
  Video,
  TrendingUp,
  Calendar,
  HelpCircle,
  Mail,
  UserPlus,
  LogIn,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  X,
  Phone,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { User } from '../types';

interface LandingPageProps {
  onLoginSuccess: (user: User) => void;
  onExploreDemo: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLoginSuccess, onExploreDemo }) => {
  const [activeModal, setActiveModal] = useState<'auth' | 'about' | 'help' | 'support' | null>(null);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register');

  // Registration form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regAge, setRegAge] = useState<number | ''>(55);
  const [regGender, setRegGender] = useState('Prefer not to say');
  const [regHeight, setRegHeight] = useState<number | ''>(168);
  const [regWeight, setRegWeight] = useState<number | ''>(70);
  const [regConditions, setRegConditions] = useState('');
  const [regAllergies, setRegAllergies] = useState('');
  const [regMedications, setRegMedications] = useState('');

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAuthError(null);
    try {
      const res = await api.register({
        full_name: regName,
        email: regEmail,
        password: regPassword,
        age: regAge ? Number(regAge) : undefined,
        gender: regGender,
        height: regHeight ? Number(regHeight) : undefined,
        body_weight: regWeight ? Number(regWeight) : undefined,
        existing_conditions: regConditions || undefined,
        allergies: regAllergies || undefined,
        medications: regMedications || undefined,
      });
      api.setToken(res.access_token);
      onLoginSuccess(res.user);
      setActiveModal(null);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Failed to register account. Please check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAuthError(null);
    try {
      const res = await api.login({
        email: loginEmail,
        password: loginPassword,
      });
      api.setToken(res.access_token);
      onLoginSuccess(res.user);
      setActiveModal(null);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-900 font-sans">
      {/* Top Header / Public Navigation */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="bg-purple-700 text-white p-2.5 rounded-2xl shadow-sm">
              <Heart className="w-7 h-7 fill-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-2xl font-black tracking-tight text-slate-900">Sovereign Health Twin</span>
                <span className="bg-purple-100 text-purple-800 text-xs font-bold px-2.5 py-0.5 rounded-full border border-purple-200">
                  Web3 Verified
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">Continuous Physiological Modeling & Patient Trust</p>
            </div>
          </div>

          {/* Nav Links */}
          <nav className="hidden md:flex items-center space-x-6 text-base font-semibold text-slate-700">
            <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="hover:text-purple-700 transition">
              Home
            </button>
            <button onClick={() => setActiveModal('about')} className="hover:text-purple-700 transition">
              About
            </button>
            <button onClick={() => {
              const el = document.getElementById('features-section');
              el?.scrollIntoView({ behavior: 'smooth' });
            }} className="hover:text-purple-700 transition">
              Features
            </button>
            <button onClick={() => setActiveModal('help')} className="hover:text-purple-700 transition">
              Help & FAQ
            </button>
            <button onClick={() => setActiveModal('support')} className="hover:text-purple-700 transition">
              Support
            </button>
          </nav>

          {/* Action Buttons */}
          <div className="flex items-center space-x-3">
            <button
              onClick={onExploreDemo}
              className="hidden sm:flex items-center space-x-1.5 text-purple-800 bg-purple-50 hover:bg-purple-100 font-bold px-4 py-2.5 rounded-xl border border-purple-200 transition min-h-[44px]"
            >
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>Explore Demo</span>
            </button>
            <button
              onClick={() => { setAuthMode('login'); setActiveModal('auth'); }}
              className="text-slate-700 hover:text-purple-800 font-bold px-4 py-2.5 rounded-xl transition min-h-[44px]"
            >
              Sign In
            </button>
            <button
              onClick={() => { setAuthMode('register'); setActiveModal('auth'); }}
              className="bg-purple-700 hover:bg-purple-800 text-white font-bold px-5 py-2.5 rounded-xl shadow-sm transition min-h-[44px]"
            >
              Create Account
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-b from-purple-50/70 to-slate-50 py-16 lg:py-24 border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center space-y-6">
          <div className="inline-flex items-center space-x-2 bg-emerald-50 text-emerald-800 border border-emerald-200 px-4 py-1.5 rounded-full text-sm font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>Cryptographically Verified on Ethereum Smart Contracts</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-tight max-w-4xl mx-auto">
            Understand Your Health <span className="text-purple-700">Over Time</span>, Not Just Snapshots
          </h1>

          <p className="text-xl sm:text-2xl text-slate-600 max-w-3xl mx-auto font-normal leading-relaxed">
            Medical decisions are often based on isolated clinical visits. Our Digital Twin maintains a living,
            continuous model of your physiological state, forecasts short-term trends, and securely protects your health records.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <button
              onClick={() => { setAuthMode('register'); setActiveModal('auth'); }}
              className="bg-purple-700 hover:bg-purple-800 text-white font-black text-lg px-8 py-4 rounded-2xl shadow-lg hover:shadow-xl transition flex items-center space-x-3 min-h-[52px]"
            >
              <span>Get Started Free</span>
              <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={onExploreDemo}
              className="bg-white hover:bg-slate-100 text-slate-800 font-bold text-lg px-8 py-4 rounded-2xl border-2 border-slate-300 shadow-sm transition min-h-[52px]"
            >
              Try Instant Demo
            </button>
          </div>

          {/* Trust badges */}
          <div className="pt-10 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto text-sm text-slate-600">
            <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="font-semibold">Senior-Friendly Design</span>
            </div>
            <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="font-semibold">No Crypto Wallet Required</span>
            </div>
            <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="font-semibold">PDF & Image Report Search</span>
            </div>
            <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-center space-x-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="font-semibold">100% Patient Privacy</span>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works (3-4 steps) */}
      <section className="py-16 bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl font-black text-slate-900">How Your Health Twin Works</h2>
            <p className="text-lg text-slate-600 mt-2">
              Four simple steps to maintain a continuous, personal representation of your vital state.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="bg-slate-50 p-6 rounded-2xl border-2 border-slate-200 space-y-3">
              <div className="w-12 h-12 bg-purple-700 text-white rounded-2xl font-black text-xl flex items-center justify-center">
                1
              </div>
              <h3 className="text-xl font-bold text-slate-900">Set Up Your Profile</h3>
              <p className="text-slate-600 leading-relaxed">
                Provide your basic details, weight, resting vitals, and conditions. Skip any optional field you prefer not to share.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl border-2 border-slate-200 space-y-3">
              <div className="w-12 h-12 bg-purple-700 text-white rounded-2xl font-black text-xl flex items-center justify-center">
                2
              </div>
              <h3 className="text-xl font-bold text-slate-900">Record or Upload Data</h3>
              <p className="text-slate-600 leading-relaxed">
                Enter readings with 1 tap, or upload lab reports in PDF or image format. Our search engine extracts key parameters.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl border-2 border-slate-200 space-y-3">
              <div className="w-12 h-12 bg-purple-700 text-white rounded-2xl font-black text-xl flex items-center justify-center">
                3
              </div>
              <h3 className="text-xl font-bold text-slate-900">Twin Evolves & Attests</h3>
              <p className="text-slate-600 leading-relaxed">
                Every measurement recalculates your rolling baseline, trend slope, and anchors a cryptographic proof on the blockchain.
              </p>
            </div>

            <div className="bg-slate-50 p-6 rounded-2xl border-2 border-slate-200 space-y-3">
              <div className="w-12 h-12 bg-purple-700 text-white rounded-2xl font-black text-xl flex items-center justify-center">
                4
              </div>
              <h3 className="text-xl font-bold text-slate-900">Forecast & Compare</h3>
              <p className="text-slate-600 leading-relaxed">
                Explore where your health trajectory is heading next, and test hypothetical scenarios (e.g. rest vs increased activity).
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Showcase Grid */}
      <section id="features-section" className="py-16 bg-slate-50 border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-12">
            <h2 className="text-3xl font-black text-slate-900">Comprehensive Health Features</h2>
            <p className="text-lg text-slate-600 mt-2">
              Designed for seniors, families, and patients seeking clarity without confusing medical jargon.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center">
                <Activity className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Physiological Digital Twin</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Continuous dynamic tracking of heart rate, rolling statistics, hourly trend slope, and vital status with automatic state versioning.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center">
                <FileText className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Medical Report Search Engine</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Upload lab test reports in PDF, JPG, or PNG. Search inside your reports using keywords and automatically extract blood pressure, glucose, and heart rate.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Web3 Blockchain Integrity</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Solidity smart contract receipts and SHA-256 state hashes guarantee your health history is tamper-proof without requiring crypto wallets.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-2xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Disease & Symptom Timeline</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Monitor chronic conditions like hypertension or asthma. Log measurements, track symptom trends, and compare readings across dates.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-pink-100 text-pink-600 rounded-2xl flex items-center justify-center">
                <Calendar className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Optional Cycle & Hormone Tracker</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Dedicated menstrual tracker for female profiles. Calculates cycle phases, next period countdown, and correlates hormonal shifts with resting heart rate.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="bg-white p-6 rounded-2xl border-2 border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-2xl flex items-center justify-center">
                <Video className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-slate-900">Personal Video Library</h3>
              <p className="text-slate-600 text-base leading-relaxed">
                Upload physical therapy, gait, or mobility videos (MP4, WebM, MOV) with secure storage, in-browser playback, and date tracking.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Bottom Banner */}
      <section className="bg-purple-900 text-white py-14">
        <div className="max-w-4xl mx-auto px-4 text-center space-y-6">
          <h2 className="text-3xl sm:text-4xl font-black">Take Control of Your Health Trajectory Today</h2>
          <p className="text-lg text-purple-200 font-medium">
            Join our research platform and see what a sovereign Patient Digital Twin can do for your personal health understanding.
          </p>
          <div className="pt-2">
            <button
              onClick={() => { setAuthMode('register'); setActiveModal('auth'); }}
              className="bg-white text-purple-900 hover:bg-purple-50 font-black text-lg px-8 py-4 rounded-2xl shadow-lg transition"
            >
              Create Your Free Twin Account
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 py-10 text-slate-600 text-sm">
        <div className="max-w-6xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Heart className="w-6 h-6 text-purple-700 fill-purple-700" />
              <span className="text-xl font-bold text-slate-900">Sovereign Health Twin</span>
            </div>
            <p className="text-slate-500 text-xs leading-relaxed">
              HackLoop 2026 Patient Digital Twin Prototype. Built to help individuals, seniors, and clinicians
              understand continuous physiological evolution backed by Web3 data integrity.
            </p>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-900">Quick Links</h4>
            <ul className="space-y-1.5 text-slate-600">
              <li><button onClick={() => setActiveModal('about')} className="hover:text-purple-700">About Our Digital Twin</button></li>
              <li><button onClick={() => setActiveModal('help')} className="hover:text-purple-700">Help & User FAQs</button></li>
              <li><button onClick={() => setActiveModal('support')} className="hover:text-purple-700">Contact & Support Desk</button></li>
              <li><button onClick={onExploreDemo} className="hover:text-purple-700">Explore Interactive Demo</button></li>
            </ul>
          </div>

          <div className="space-y-2">
            <h4 className="font-bold text-slate-900">Important Disclaimer</h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              This application is an educational and research prototype. It does not replace medical doctors,
              diagnose diseases, or prescribe medication. In case of a medical emergency, call 911 or your local emergency services immediately.
            </p>
          </div>
        </div>
      </footer>

      {/* MODAL: AUTHENTICATION (Register / Login) */}
      {activeModal === 'auth' && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setActiveModal(null)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2 rounded-full"
            >
              <X className="w-6 h-6" />
            </button>

            {/* Tabs */}
            <div className="flex border-b border-slate-200 mb-6">
              <button
                onClick={() => { setAuthMode('register'); setAuthError(null); }}
                className={`flex-1 py-3 text-lg font-bold border-b-4 transition ${
                  authMode === 'register'
                    ? 'border-purple-700 text-purple-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                Create Account
              </button>
              <button
                onClick={() => { setAuthMode('login'); setAuthError(null); }}
                className={`flex-1 py-3 text-lg font-bold border-b-4 transition ${
                  authMode === 'login'
                    ? 'border-purple-700 text-purple-700'
                    : 'border-transparent text-slate-500 hover:text-slate-800'
                }`}
              >
                Sign In
              </button>
            </div>

            {authError && (
              <div className="mb-5 p-3.5 bg-red-50 border-2 border-red-300 text-red-900 rounded-xl text-sm font-semibold">
                {authError}
              </div>
            )}

            {authMode === 'register' ? (
              <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="e.g. Alice M. Taylor"
                    className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="alice@example.com"
                    className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Password (min 6 chars) *</label>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
                  />
                </div>

                <div className="pt-2 border-t border-slate-200">
                  <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
                    Optional Health Profile Details
                  </p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-bold text-slate-600 mb-1">Age</label>
                      <input
                        type="number"
                        min={0}
                        max={130}
                        value={regAge}
                        onChange={(e) => setRegAge(e.target.value ? Number(e.target.value) : '')}
                        className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-600 mb-1">Gender</label>
                      <select
                        value={regGender}
                        onChange={(e) => setRegGender(e.target.value)}
                        className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                      >
                        <option value="Female">Female</option>
                        <option value="Male">Male</option>
                        <option value="Non-binary">Non-binary</option>
                        <option value="Prefer not to say">Prefer not to say</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-600 mb-1">Height (cm)</label>
                      <input
                        type="number"
                        min={30}
                        max={250}
                        value={regHeight}
                        onChange={(e) => setRegHeight(e.target.value ? Number(e.target.value) : '')}
                        className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-600 mb-1">Weight (kg)</label>
                      <input
                        type="number"
                        min={5}
                        max={400}
                        value={regWeight}
                        onChange={(e) => setRegWeight(e.target.value ? Number(e.target.value) : '')}
                        className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm font-semibold"
                      />
                    </div>
                  </div>

                  <div className="mt-3">
                    <label className="block text-xs font-bold text-slate-600 mb-1">Existing Conditions (optional)</label>
                    <input
                      type="text"
                      value={regConditions}
                      onChange={(e) => setRegConditions(e.target.value)}
                      placeholder="e.g. Mild Hypertension, Asthma"
                      className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-purple-700 hover:bg-purple-800 text-white font-black text-lg py-3.5 rounded-2xl shadow-md transition mt-4 min-h-[48px]"
                >
                  {loading ? 'Creating Your Twin...' : 'Register & Create Digital Twin'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Email Address</label>
                  <input
                    type="email"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="your-email@example.com"
                    className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
                  />
                </div>

                <div>
                  <label className="block text-sm font-bold text-slate-700 mb-1">Password</label>
                  <input
                    type="password"
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-purple-700 hover:bg-purple-800 text-white font-black text-lg py-3.5 rounded-2xl shadow-md transition mt-4 min-h-[48px]"
                >
                  {loading ? 'Signing In...' : 'Sign In to Your Dashboard'}
                </button>

                <div className="text-center pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setLoginEmail('demo@patient.org');
                      setLoginPassword('DemoPassword123!');
                    }}
                    className="text-xs text-purple-700 font-semibold hover:underline"
                  >
                    Use standard demo credentials
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* MODAL: ABOUT */}
      {activeModal === 'about' && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-4">
            <button onClick={() => setActiveModal(null)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2">
              <X className="w-6 h-6" />
            </button>
            <h3 className="text-2xl font-black text-slate-900">About Sovereign Health Twin</h3>
            <p className="text-slate-600 leading-relaxed">
              <strong>The Problem:</strong> Traditional healthcare relies on episodic snapshots. When you visit a clinic,
              your heart rate or blood pressure is measured once, ignoring whether you were rushed, nervous, or tired.
            </p>
            <p className="text-slate-600 leading-relaxed">
              <strong>Our Solution:</strong> A Patient Digital Twin maintains a dynamic, time-series representation of your physiological state.
              As new telemetry arrives, the model recalculates baseline trends and simulates hypothetical trajectories (e.g. resting vs exertion).
            </p>
            <p className="text-slate-600 leading-relaxed">
              <strong>Why Web3?</strong> We use smart contracts and SHA-256 state hashing to provide immutable receipts of your health evolution.
              Your data integrity cannot be silently altered or rewritten by unauthorized parties.
            </p>
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-2xl text-amber-900 text-xs">
              <strong>Research Prototype:</strong> Built for HackLoop 2026. Designed for research and educational purposes.
            </div>
          </div>
        </div>
      )}

      {/* MODAL: HELP & FAQ */}
      {activeModal === 'help' && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-xl w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-4">
            <button onClick={() => setActiveModal(null)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2">
              <X className="w-6 h-6" />
            </button>
            <h3 className="text-2xl font-black text-slate-900">Help & Frequently Asked Questions</h3>
            
            <div className="space-y-3 text-slate-700">
              <div className="border-b border-slate-200 pb-3">
                <h4 className="font-bold text-slate-900">Do I need cryptocurrency or a crypto wallet?</h4>
                <p className="text-sm text-slate-600 mt-1">
                  No. All smart contract transactions and state attestations happen automatically behind the scenes. You simply use the app with plain English labels.
                </p>
              </div>

              <div className="border-b border-slate-200 pb-3">
                <h4 className="font-bold text-slate-900">What files can I upload to the report search engine?</h4>
                <p className="text-sm text-slate-600 mt-1">
                  You can upload medical lab test reports as PDF documents or image files (PNG, JPG, JPEG). Our engine parses readable text and biomarkers.
                </p>
              </div>

              <div className="border-b border-slate-200 pb-3">
                <h4 className="font-bold text-slate-900">How does the digital twin update when I log a measurement?</h4>
                <p className="text-sm text-slate-600 mt-1">
                  When you add a measurement, the twin increments its version (e.g. v1 to v2), calculates a new SHA-256 state hash, and records the attestation on-chain.
                </p>
              </div>

              <div>
                <h4 className="font-bold text-slate-900">Is my personal health data shared publicly?</h4>
                <p className="text-sm text-slate-600 mt-1">
                  No. Only cryptographic state hashes and version anchors are recorded on-chain. Sensitive names and raw vitals stay secure in your private account.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: SUPPORT */}
      {activeModal === 'support' && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto space-y-4">
            <button onClick={() => setActiveModal(null)} className="absolute top-5 right-5 text-slate-400 hover:text-slate-700 p-2">
              <X className="w-6 h-6" />
            </button>
            <h3 className="text-2xl font-black text-slate-900">Customer Support Desk</h3>
            <p className="text-slate-600 text-sm">
              We are here to assist senior citizens, patients, and researchers with platform questions or accessibility guidance.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <Mail className="w-5 h-5 text-purple-700" />
                <div>
                  <p className="text-xs text-slate-500 font-semibold">Email Assistance</p>
                  <p className="text-sm font-bold text-slate-900">support@healthtwin.internal</p>
                </div>
              </div>

              <div className="flex items-center space-x-3 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <Phone className="w-5 h-5 text-purple-700" />
                <div>
                  <p className="text-xs text-slate-500 font-semibold">Helpline (Mon - Fri, 8 AM - 6 PM)</p>
                  <p className="text-sm font-bold text-slate-900">1-800-TWIN-MED (Demo Desk)</p>
                </div>
              </div>
            </div>

            <div className="p-4 bg-red-50 border border-red-200 rounded-2xl flex items-start space-x-3 text-red-900 text-xs">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <strong>Medical Emergency Notice:</strong> This platform is NOT a clinical emergency responder.
                If you are experiencing chest pain, shortness of breath, or any medical emergency, dial 911 or visit the nearest emergency room immediately.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
