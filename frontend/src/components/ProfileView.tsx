import React, { useState } from 'react';
import {
  UserCheck,
  Save,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Heart,
  Scale,
  Ruler,
  Calendar,
  Pill,
  ShieldAlert,
  Phone
} from 'lucide-react';
import { User } from '../types';
import { api } from '../services/api';
import { formatISTDateOnly, formatIST } from '../utils/dateUtils';

interface ProfileViewProps {
  user: User;
  onProfileUpdated: (updatedUser: User) => void;
  onLogout: () => void;
}

export const ProfileView: React.FC<ProfileViewProps> = ({
  user,
  onProfileUpdated,
  onLogout
}) => {
  const [fullName, setFullName] = useState(user.full_name || '');
  const [age, setAge] = useState<number | ''>(user.age !== undefined && user.age !== null ? user.age : '');
  const [dateOfBirth, setDateOfBirth] = useState(user.date_of_birth || '');
  const [gender, setGender] = useState(user.gender || 'Prefer not to say');
  const [height, setHeight] = useState<number | ''>(user.height || '');
  const [bodyWeight, setBodyWeight] = useState<number | ''>(user.body_weight || '');
  const [conditions, setConditions] = useState(user.existing_conditions || '');
  const [allergies, setAllergies] = useState(user.allergies || '');
  const [medications, setMedications] = useState(user.medications || '');
  const [emergencyContact, setEmergencyContact] = useState(user.emergency_contact || '');
  const [healthNotes, setHealthNotes] = useState(user.health_notes || '');

  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const updated = await api.updateProfile({
        full_name: fullName.trim(),
        age: age ? Number(age) : undefined,
        date_of_birth: dateOfBirth || undefined,
        gender: gender,
        height: height ? Number(height) : undefined,
        body_weight: bodyWeight ? Number(bodyWeight) : undefined,
        existing_conditions: conditions.trim() || undefined,
        allergies: allergies.trim() || undefined,
        medications: medications.trim() || undefined,
        emergency_contact: emergencyContact.trim() || undefined,
        health_notes: healthNotes.trim() || undefined,
      });
      onProfileUpdated(updated);
      setSuccessMsg('Your profile and health records have been saved successfully.');
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await api.deleteAccount();
      api.setToken(null);
      onLogout();
    } catch (err: any) {
      alert('Failed to delete account. Please try again.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-900 flex items-center space-x-3">
            <UserCheck className="w-8 h-8 text-purple-700" />
            <span>My Health Profile</span>
          </h1>
          <p className="text-slate-600 text-base mt-1">
            Manage your personal metrics, medical conditions, and clinical notes. All data is securely stored.
          </p>
        </div>

        <div className="text-right">
          <div className="text-sm font-semibold text-slate-500 bg-slate-100 px-4 py-2 rounded-2xl border border-slate-300">
            Digital Twin ID: <span className="font-mono font-bold text-slate-800">{user.patient_id}</span>
          </div>
          {user.created_at && (
            <div className="text-xs text-slate-400 mt-1">
              Registered: {formatIST(user.created_at)}
            </div>
          )}
        </div>
      </div>

      {successMsg && (
        <div className="p-4 bg-emerald-50 border-2 border-emerald-300 text-emerald-900 rounded-2xl text-base font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-4 bg-red-50 border-2 border-red-300 text-red-900 rounded-2xl text-base font-semibold flex items-center space-x-2">
          <AlertTriangle className="w-6 h-6 text-red-600 flex-shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Main Profile Form */}
      <form onSubmit={handleSave} className="bg-white p-6 sm:p-8 rounded-3xl border-2 border-slate-200 shadow-sm space-y-6">
        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
          1. Personal Information
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Full Name</label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold focus:outline-none focus:border-purple-700"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Email Address</label>
            <input
              type="email"
              disabled
              value={user.email}
              className="w-full p-3 bg-slate-100 border border-slate-300 rounded-xl text-base text-slate-600 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Age (Years)</label>
            <input
              type="number"
              min={0}
              max={130}
              value={age}
              onChange={(e) => setAge(e.target.value ? Number(e.target.value) : '')}
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Date of Birth</label>
            <input
              type="date"
              value={dateOfBirth}
              onChange={(e) => setDateOfBirth(e.target.value)}
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Gender Identification</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            >
              <option value="Female">Female</option>
              <option value="Male">Male</option>
              <option value="Non-binary">Non-binary</option>
              <option value="Prefer not to say">Prefer not to say</option>
              <option value="Self-described">Self-described</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">Emergency Contact</label>
            <input
              type="text"
              value={emergencyContact}
              onChange={(e) => setEmergencyContact(e.target.value)}
              placeholder="e.g. Son: Mark (555-0199)"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3 pt-4">
          2. Physical Measurements
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center space-x-1">
              <Ruler className="w-4 h-4 text-purple-700" />
              <span>Height (cm)</span>
            </label>
            <input
              type="number"
              min={30}
              max={250}
              value={height}
              onChange={(e) => setHeight(e.target.value ? Number(e.target.value) : '')}
              placeholder="e.g. 165"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center space-x-1">
              <Scale className="w-4 h-4 text-purple-700" />
              <span>Body Weight (kg)</span>
            </label>
            <input
              type="number"
              min={5}
              max={400}
              value={bodyWeight}
              onChange={(e) => setBodyWeight(e.target.value ? Number(e.target.value) : '')}
              placeholder="e.g. 68.5"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>
        </div>

        <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3 pt-4">
          3. Health Conditions, Allergies & Medications
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center space-x-1">
              <Heart className="w-4 h-4 text-red-600" />
              <span>Known Medical Conditions</span>
            </label>
            <input
              type="text"
              value={conditions}
              onChange={(e) => setConditions(e.target.value)}
              placeholder="e.g. Mild Hypertension, Type 2 Diabetes, Arthritis"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center space-x-1">
              <ShieldAlert className="w-4 h-4 text-amber-600" />
              <span>Allergies</span>
            </label>
            <input
              type="text"
              value={allergies}
              onChange={(e) => setAllergies(e.target.value)}
              placeholder="e.g. Penicillin, Sulfa drugs, Peanuts"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1 flex items-center space-x-1">
              <Pill className="w-4 h-4 text-blue-600" />
              <span>Current Medications</span>
            </label>
            <input
              type="text"
              value={medications}
              onChange={(e) => setMedications(e.target.value)}
              placeholder="e.g. Lisinopril 10mg daily, Metformin 500mg"
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-1">
              Personal Health Notes
            </label>
            <textarea
              rows={3}
              value={healthNotes}
              onChange={(e) => setHealthNotes(e.target.value)}
              placeholder="Any additional instructions or observations for your health record..."
              className="w-full p-3 bg-slate-50 border-2 border-slate-300 rounded-xl text-base font-semibold"
            />
          </div>
        </div>

        <div className="pt-4 flex flex-wrap items-center justify-between gap-4">
          <button
            type="submit"
            disabled={saving}
            className="bg-purple-700 hover:bg-purple-800 text-white font-black text-lg px-8 py-3.5 rounded-2xl shadow-md transition flex items-center space-x-2 min-h-[48px]"
          >
            <Save className="w-5 h-5" />
            <span>{saving ? 'Saving Changes...' : 'Save Profile Changes'}</span>
          </button>

          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="text-red-600 hover:text-red-800 hover:bg-red-50 font-bold px-4 py-2.5 rounded-xl border border-red-200 transition text-sm flex items-center space-x-1.5"
          >
            <Trash2 className="w-4 h-4" />
            <span>Delete Account & Data</span>
          </button>
        </div>
      </form>

      {/* MODAL: DELETE ACCOUNT CONFIRMATION */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 sm:p-8 shadow-2xl space-y-4">
            <div className="w-12 h-12 bg-red-100 text-red-600 rounded-2xl flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h3 className="text-2xl font-black text-slate-900">Delete Account & Health Data?</h3>
            <p className="text-slate-600 text-sm leading-relaxed">
              This action is permanent and irreversible. All your profile information, digital twin history,
              uploaded reports, and videos will be completely removed from the database.
            </p>
            <div className="flex items-center space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold py-3 rounded-xl transition text-base"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-bold py-3 rounded-xl transition text-base"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
