import React, { useState, useRef, useEffect } from 'react';
import {
  Heart,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  UserCheck,
  LogOut,
  LayoutDashboard,
  FileText,
  Video,
  Activity,
  Calendar,
  Home,
  Cpu,
  ChevronDown,
  Layers,
  Menu
} from 'lucide-react';
import { Patient, User } from '../types';

interface NavbarProps {
  user: User | null;
  patients: Patient[];
  selectedPatientId: string;
  onSelectPatient: (id: string) => void;
  onRefresh: () => void;
  onLoadSynthetic: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  loading: boolean;
  onLogout: () => void;
  onGoHome?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  patients,
  selectedPatientId,
  onSelectPatient,
  onRefresh,
  onLoadSynthetic,
  activeTab,
  setActiveTab,
  loading,
  onLogout,
  onGoHome,
}) => {
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const isFemale = user?.gender === 'Female';

  // Primary 4 Top-Level Tabs
  const primaryTabs = [
    { id: 'my-health', label: '1. My Health', icon: Heart },
    { id: 'digital-twin', label: '2. Digital Twin', icon: Cpu },
    { id: 'records', label: '3. Health Records', icon: FileText },
    { id: 'integrity', label: '4. Data Integrity', icon: ShieldCheck },
  ];

  // Secondary views under "More"
  const moreTabs = [
    { id: 'dashboard', label: 'Dashboard Overview', icon: LayoutDashboard },
    { id: 'videos', label: 'Personal Videos', icon: Video },
    { id: 'disease-tracker', label: 'Disease Tracker', icon: Activity },
    { id: 'cycle-tracker', label: 'Period Tracker', icon: Calendar },
    { id: 'profile', label: 'My Health Profile', icon: UserCheck },
  ];

  // Close dropdown on outside click or Escape key
  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(event.target as Node)) {
        setShowMoreMenu(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowMoreMenu(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleTabClick = (tabId: string) => {
    setActiveTab(tabId);
    setShowMoreMenu(false);
  };

  const isMoreActive = moreTabs.some((t) => t.id === activeTab);

  return (
    <header className="bg-white border-b-2 border-slate-200 sticky top-0 z-30 shadow-sm">
      {/* Top security status bar */}
      <div className="bg-slate-900 text-white px-4 py-1.5 text-xs flex flex-col sm:flex-row items-center justify-between gap-2">
        <div className="flex items-center space-x-2">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
          <span className="font-semibold text-slate-200">
            Sovereign Health Twin • Research & Educational Assistant
          </span>
        </div>
        <div className="flex items-center space-x-3 text-slate-300">
          <span className="flex items-center space-x-1.5 bg-slate-800 px-3 py-0.5 rounded-full border border-slate-700">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Web3 Blockchain Security: Active</span>
          </span>
          {user && (
            <span className="font-medium text-purple-300">
              Logged in: <strong>{user.full_name}</strong>
            </span>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          {/* Logo & Simple Title */}
          <div
            className="flex items-center space-x-3 cursor-pointer"
            onClick={onGoHome ? onGoHome : () => handleTabClick('my-health')}
          >
            <div className="bg-purple-700 text-white p-2.5 rounded-2xl shadow-sm flex items-center justify-center">
              <Heart className="w-6 h-6 fill-white" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-black text-slate-900 leading-tight">
                Sovereign Health Twin
              </h1>
              <p className="text-xs text-slate-600 font-medium">
                Continuous physiological modeling & Web3 integrity
              </p>
            </div>
          </div>

          {/* Quick Action Controls */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Home Link */}
            {onGoHome && (
              <button
                onClick={onGoHome}
                className="bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-sm px-3.5 py-2 rounded-xl transition flex items-center space-x-1.5 min-h-[44px]"
              >
                <Home className="w-4 h-4 text-slate-600" />
                <span>Home Page</span>
              </button>
            )}

            {/* Quick Demo Button */}
            <button
              onClick={onLoadSynthetic}
              disabled={loading}
              className="bg-purple-50 hover:bg-purple-100 text-purple-900 font-bold text-sm px-3.5 py-2 rounded-xl border border-purple-200 transition flex items-center space-x-1.5 min-h-[44px]"
            >
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>Load Demo Patient</span>
            </button>

            {/* Patient selector */}
            <div className="flex items-center space-x-1.5 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-300 min-h-[44px]">
              <label htmlFor="patient-select" className="text-xs font-semibold text-slate-600">
                Patient:
              </label>
              <select
                id="patient-select"
                value={selectedPatientId}
                onChange={(e) => onSelectPatient(e.target.value)}
                className="bg-transparent text-sm font-bold text-slate-900 focus:outline-none cursor-pointer"
              >
                {patients.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              disabled={loading}
              title="Refresh Health Data"
              className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-purple-700' : ''}`} />
            </button>

            {/* Logout button */}
            {user && (
              <button
                onClick={onLogout}
                title="Sign out of account"
                className="bg-red-50 hover:bg-red-100 text-red-700 font-bold text-sm px-3.5 py-2 rounded-xl border border-red-200 transition flex items-center space-x-1.5 min-h-[44px]"
              >
                <LogOut className="w-4 h-4" />
                <span>Sign Out</span>
              </button>
            )}
          </div>
        </div>

        {/* Navigation Tabs Bar: 4 Primary Destinations + More Dropdown */}
        <nav className="flex items-center space-x-1 pt-3 pb-1 border-t border-slate-100 mt-2.5 flex-wrap sm:flex-nowrap gap-y-1">
          {primaryTabs.map((tab) => {
            const Icon = tab.icon;
            // Also match legacy alias IDs
            const isActive =
              activeTab === tab.id ||
              (tab.id === 'digital-twin' && activeTab === 'future-outlook') ||
              (tab.id === 'records' && (activeTab === 'record-history' || activeTab === 'reports')) ||
              (tab.id === 'integrity' && activeTab === 'web3');

            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-bold transition whitespace-nowrap min-h-[40px] ${
                  isActive
                    ? 'bg-purple-700 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-white' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}

          {/* More Menu Dropdown */}
          <div className="relative" ref={moreMenuRef}>
            <button
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-sm font-bold transition whitespace-nowrap min-h-[40px] ${
                isMoreActive
                  ? 'bg-purple-100 text-purple-900 border border-purple-300'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <Menu className="w-4 h-4 text-slate-500" />
              <span>More Modules</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showMoreMenu ? 'rotate-180' : ''}`} />
            </button>

            {showMoreMenu && (
              <div className="absolute left-0 sm:left-auto sm:right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border-2 border-slate-200 py-2 z-50 animate-in fade-in zoom-in-95 duration-100">
                <div className="px-3.5 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Specialized Modules
                </div>
                {moreTabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => handleTabClick(tab.id)}
                      className={`w-full flex items-center space-x-2.5 px-3.5 py-2.5 text-sm font-semibold transition text-left ${
                        isActive
                          ? 'bg-purple-50 text-purple-900 font-bold'
                          : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900'
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${isActive ? 'text-purple-700' : 'text-slate-400'}`} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
};
