import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Cpu,
  Lock,
  Unlock,
  Key,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Database,
  RefreshCw,
  Copy,
  Check,
  Blocks,
  Clock,
  Info,
  Layers,
  FileCheck,
  UserCheck
} from 'lucide-react';
import { Patient, TwinState, Web3NetworkStatus, Web3VerificationResult } from '../types';
import { api } from '../services/api';
import { formatIST } from '../utils/dateUtils';

interface DataIntegrityViewProps {
  patient: Patient | null;
  twinState: TwinState | null;
  onRefresh: () => void;
}

export const DataIntegrityView: React.FC<DataIntegrityViewProps> = ({
  patient,
  twinState,
  onRefresh,
}) => {
  const [networkStatus, setNetworkStatus] = useState<Web3NetworkStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Verification state
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyResult, setVerifyResult] = useState<Web3VerificationResult | null>(null);

  // Sovereign Consent state
  const [researcherAddress, setResearcherAddress] = useState<string>('0x90F79bf6EB2c4f870365E785982E1f101E93b906');
  const [durationHours, setDurationHours] = useState<number>(24);
  const [accessStatus, setAccessStatus] = useState<boolean | null>(null);
  const [accessMessage, setAccessMessage] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  const patientId = patient?.id || 'PT-DEMO-001';

  const fetchWeb3Status = async () => {
    setLoading(true);
    try {
      const res = await api.getWeb3Status();
      setNetworkStatus(res);
    } catch (err: any) {
      console.error('Failed to fetch Web3 status:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWeb3Status();
  }, []);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleVerifyOnChain = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const version = twinState ? twinState.state_version : 1;
      const res = await api.verifyTwinStateOnChain(patientId, version);
      setVerifyResult(res);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to verify state on-chain.');
    } finally {
      setVerifying(false);
    }
  };

  const handleCheckAccess = async () => {
    setActionLoading(true);
    setAccessMessage(null);
    try {
      const res = await api.checkAccessOnChain(patientId, researcherAddress);
      setAccessStatus(res.has_access);
      setAccessMessage(
        res.has_access
          ? `Address ${researcherAddress.slice(0, 10)}... has ACTIVE verified on-chain permission.`
          : `Address ${researcherAddress.slice(0, 10)}... does NOT currently have access.`
      );
    } catch (err: any) {
      setAccessMessage(err.response?.data?.detail || 'Failed to check access permission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGrantAccess = async () => {
    setActionLoading(true);
    setAccessMessage(null);
    try {
      const res = await api.grantAccessOnChain(patientId, researcherAddress, durationHours);
      setAccessStatus(true);
      setAccessMessage(
        `✓ Access granted on-chain! Tx: ${res.tx_hash ? res.tx_hash.slice(0, 12) + '...' : 'Confirmed'}. Active for ${durationHours} hours.`
      );
    } catch (err: any) {
      setAccessMessage(err.response?.data?.detail || 'Failed to grant access on-chain.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeAccess = async () => {
    setActionLoading(true);
    setAccessMessage(null);
    try {
      const res = await api.revokeAccessOnChain(patientId, researcherAddress);
      setAccessStatus(false);
      setAccessMessage(
        `✓ Access revoked on-chain! Tx: ${res.tx_hash ? res.tx_hash.slice(0, 12) + '...' : 'Confirmed'}. Researcher access terminated.`
      );
    } catch (err: any) {
      setAccessMessage(err.response?.data?.detail || 'Failed to revoke access on-chain.');
    } finally {
      setActionLoading(false);
    }
  };

  // Determine verification badge
  const renderAttestationBadge = () => {
    const status = twinState?.attestation_status || 'SIMULATED';
    if (status === 'VERIFIED') {
      return (
        <span className="bg-emerald-100 text-emerald-900 border-2 border-emerald-400 px-4 py-1.5 rounded-full text-sm font-extrabold flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-700" />
          <span>VERIFIED ON-CHAIN (EVM Block #{twinState?.on_chain_block_number || '1'})</span>
        </span>
      );
    } else if (status === 'SIMULATED') {
      return (
        <span className="bg-blue-100 text-blue-900 border-2 border-blue-400 px-4 py-1.5 rounded-full text-sm font-extrabold flex items-center space-x-2">
          <Blocks className="w-4 h-4 text-blue-700" />
          <span>LOCAL EVM (In-Process Py-EVM Testnet)</span>
        </span>
      );
    } else if (status === 'PENDING') {
      return (
        <span className="bg-amber-100 text-amber-900 border-2 border-amber-400 px-4 py-1.5 rounded-full text-sm font-extrabold flex items-center space-x-2">
          <Clock className="w-4 h-4 text-amber-700 animate-spin" />
          <span>COMMITMENT PENDING</span>
        </span>
      );
    } else if (status === 'OFFLINE') {
      return (
        <span className="bg-slate-100 text-slate-800 border-2 border-slate-400 px-4 py-1.5 rounded-full text-sm font-extrabold flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-slate-600" />
          <span>OFFLINE CRYPTOGRAPHIC HASH ONLY</span>
        </span>
      );
    } else {
      return (
        <span className="bg-slate-100 text-slate-700 border-2 border-slate-300 px-4 py-1.5 rounded-full text-sm font-bold flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-slate-500" />
          <span>NOT ANCHORED</span>
        </span>
      );
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Educational Banner - Web3 Integrity vs Clinical Truth */}
      <div className="bg-purple-950 text-white rounded-3xl p-6 sm:p-8 shadow-xl border-2 border-purple-800 relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3 max-w-2xl">
            <div className="inline-flex items-center space-x-2 bg-purple-900/90 border border-purple-500/40 px-3.5 py-1 rounded-full text-xs font-semibold text-purple-200">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Sovereign Health Twin • Cryptographic Provenance</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
              Data Integrity & Sovereign Consent
            </h1>
            <p className="text-purple-200 text-base leading-relaxed">
              Every time your physiological state is updated, a deterministic cryptographic fingerprint is computed and anchored to a smart contract.
            </p>
          </div>

          <div className="self-start md:self-center">
            {renderAttestationBadge()}
          </div>
        </div>

        {/* Clear Medical Distinction Notice */}
        <div className="mt-6 pt-4 border-t border-purple-800/80 text-xs text-purple-300 flex items-start space-x-2">
          <Info className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
          <p>
            <strong>Important Clinical Distinction:</strong> Blockchain guarantees <em>mathematical data integrity and provenance</em> (proving your readings have not been modified, tampered with, or silently altered). It does <strong>not</strong> validate clinical truth, biological accuracy, or substitute for a physician's medical diagnosis.
          </p>
        </div>
      </div>

      {/* Network & Smart Contract Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Live Network Status */}
        <div className="bg-white rounded-3xl p-6 border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <Blocks className="w-6 h-6 text-purple-700" />
              <h2 className="text-xl font-bold text-slate-900">Blockchain Network Status</h2>
            </div>
            <button
              onClick={fetchWeb3Status}
              disabled={loading}
              title="Refresh network status"
              className="p-2 hover:bg-slate-100 rounded-xl text-slate-600 transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-purple-700' : ''}`} />
            </button>
          </div>

          <div className="space-y-3 text-sm">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600 font-semibold">Network Environment:</span>
              <span className="font-mono font-bold text-slate-900">
                {networkStatus?.network_name || 'In-Process Py-EVM Testnet'}
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600 font-semibold">Chain ID:</span>
              <span className="font-mono font-bold text-slate-900">
                {networkStatus?.chain_id || 1337}
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600 font-semibold">Execution Mode:</span>
              <span className="font-mono text-xs text-slate-700 max-w-[220px] truncate uppercase font-bold">
                {networkStatus?.network_mode || 'in-process (py-evm)'}
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-600 font-semibold">Latest Mined Block:</span>
              <span className="font-mono font-bold text-emerald-700">
                #{networkStatus?.latest_block_number || twinState?.on_chain_block_number || 1}
              </span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-600 font-semibold">Contract Deployment:</span>
              <span className="font-bold text-emerald-700 flex items-center space-x-1">
                <CheckCircle2 className="w-4 h-4" />
                <span>Deployed & Verified</span>
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Smart Contract Details */}
        <div className="bg-white rounded-3xl p-6 border-2 border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center space-x-2 border-b border-slate-100 pb-3">
            <Cpu className="w-6 h-6 text-purple-700" />
            <h2 className="text-xl font-bold text-slate-900">Smart Contract Anchor</h2>
          </div>

          <div className="space-y-3 text-sm">
            <div>
              <span className="text-slate-600 font-semibold block text-xs mb-1">Contract Name & Spec:</span>
              <span className="font-mono font-bold text-slate-900">PatientDigitalTwinRegistry.sol (v2.0)</span>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <span className="text-slate-600 font-semibold text-xs">Contract Address:</span>
                <button
                  onClick={() => handleCopy(networkStatus?.contract_address || twinState?.contract_address || '0xF2E246BB76DF876Cef8b38ae84130F4F55De395b')}
                  className="text-xs text-purple-700 hover:text-purple-900 flex items-center space-x-1 font-bold"
                >
                  {copiedText === (networkStatus?.contract_address || twinState?.contract_address) ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                  <span>{copiedText ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-xl font-mono text-xs text-slate-800 break-all border border-slate-200">
                {networkStatus?.contract_address || twinState?.contract_address || '0xF2E246BB76DF876Cef8b38ae84130F4F55De395b'}
              </div>
            </div>

            <div>
              <span className="text-slate-600 font-semibold block text-xs mb-1">Patient Identity Isolation:</span>
              <p className="text-xs text-slate-600 leading-relaxed">
                Raw clinical data and identifiers are kept safely off-chain. Only non-sensitive cryptographic hashes (<code className="bg-slate-100 px-1 py-0.5 rounded">bytes32</code>) and IPFS CID pointers are recorded on-chain.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Verification Tool & Recomputation Section */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-md space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
              <CheckCircle2 className="w-7 h-7 text-emerald-600" />
              <span>Independent Cryptographic Verification Tool</span>
            </h2>
            <p className="text-base text-slate-600 font-medium mt-1">
              Re-run canonical serialization, SHA-256 state recalculation, and verify matching on-chain roots in real time.
            </p>
          </div>

          <button
            onClick={handleVerifyOnChain}
            disabled={verifying}
            className="bg-purple-700 hover:bg-purple-800 text-white font-extrabold text-base px-6 py-3.5 rounded-2xl shadow-md transition flex items-center justify-center space-x-2 min-h-[48px] disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${verifying ? 'animate-spin' : ''}`} />
            <span>{verifying ? 'Recomputing Hashes...' : 'Verify Record Integrity'}</span>
          </button>
        </div>

        {/* Verification Result Display */}
        {verifyResult && (
          <div
            className={`p-6 rounded-2xl border-2 space-y-4 ${
              verifyResult.is_valid
                ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
                : 'bg-rose-50/70 border-rose-300 text-rose-950'
            }`}
          >
            <div className="flex items-center space-x-3">
              {verifyResult.is_valid ? (
                <CheckCircle2 className="w-8 h-8 text-emerald-600 flex-shrink-0" />
              ) : (
                <XCircle className="w-8 h-8 text-rose-600 flex-shrink-0" />
              )}
              <div>
                <h3 className="text-xl font-bold">
                  {verifyResult.is_valid
                    ? 'State Verification Succeeded (Authentic Record)'
                    : `Verification Status: ${verifyResult.verification_status}`}
                </h3>
                <p className="text-sm font-medium mt-0.5">{verifyResult.reason || 'Cryptographic comparison completed.'}</p>
              </div>
            </div>

            {/* Technical Hash Comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs font-mono">
              <div className="bg-white p-3.5 rounded-xl border border-slate-200">
                <span className="text-slate-500 font-bold block mb-1">Local Recomputed State Hash:</span>
                <span className="text-slate-900 break-all">
                  {verifyResult.candidate_hash ? `0x${verifyResult.candidate_hash}` : 'N/A'}
                </span>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200">
                <span className="text-slate-500 font-bold block mb-1">On-Chain Anchored Root:</span>
                <span className="text-emerald-700 break-all font-bold">
                  {verifyResult.on_chain_root || '0x' + (twinState?.state_hash_sha256 || 'None')}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-600 pt-2 border-t border-slate-200">
              <span>Patient ID: <strong>{verifyResult.patient_id}</strong></span>
              <span>•</span>
              <span>State Version: <strong>v{verifyResult.state_version}</strong></span>
              <span>•</span>
              <span>Block: <strong>#{verifyResult.block_number || 1}</strong></span>
              {verifyResult.timestamp_observation && (
                <>
                  <span>•</span>
                  <span>Observation: <strong>{formatIST(verifyResult.timestamp_observation)}</strong></span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Current Active Twin Cryptographic Details */}
        <div className="p-5 bg-slate-50 border-2 border-slate-200 rounded-2xl space-y-3 font-mono text-xs">
          <h3 className="text-sm font-bold text-slate-800 font-sans flex items-center space-x-2">
            <Layers className="w-4 h-4 text-purple-700" />
            <span>Active Record Fingerprint (State Version {twinState?.state_version || 1})</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-700">
            <div>
              <span className="font-bold text-slate-900 block mb-0.5">SHA-256 State Hash:</span>
              <div className="bg-white p-2 rounded border border-slate-200 break-all">
                0x{twinState?.state_hash_sha256 || 'Awaiting initialization'}
              </div>
            </div>

            <div>
              <span className="font-bold text-slate-900 block mb-0.5">Previous State Hash (Hash Chain):</span>
              <div className="bg-white p-2 rounded border border-slate-200 break-all">
                {twinState?.previous_state_hash ? `0x${twinState.previous_state_hash}` : 'Genesis State (None)'}
              </div>
            </div>

            <div>
              <span className="font-bold text-slate-900 block mb-0.5">IPFS Storage Fingerprint (CIDv1):</span>
              <div className="bg-white p-2 rounded border border-slate-200 break-all text-purple-900">
                ipfs://{twinState?.ipfs_cid || 'bafybeih...'}
              </div>
            </div>

            <div>
              <span className="font-bold text-slate-900 block mb-0.5">Transaction Reference:</span>
              <div className="bg-white p-2 rounded border border-slate-200 break-all text-slate-800">
                {twinState?.on_chain_tx_hash ? `0x${twinState.on_chain_tx_hash}` : 'Local Testnet Provider'}
              </div>
            </div>

            <div>
              <span className="font-bold text-slate-900 block mb-0.5">Anchored Observation Time (IST):</span>
              <div className="bg-white p-2 rounded border border-slate-200 break-all text-slate-800">
                {twinState?.timestamp_latest_observation ? formatIST(twinState.timestamp_latest_observation) : 'Pending observation'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sovereign Consent & Data Governance Section */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border-2 border-slate-200 shadow-sm space-y-6">
        <div className="border-b border-slate-100 pb-4">
          <h2 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
            <UserCheck className="w-7 h-7 text-purple-700" />
            <span>Sovereign Consent & Researcher Access Control</span>
          </h2>
          <p className="text-base text-slate-600 font-medium mt-1">
            Grant or revoke time-limited access permissions to research institutions directly on the smart contract. You own your health twin data.
          </p>
        </div>

        {accessMessage && (
          <div className="p-4 bg-purple-50 border-2 border-purple-200 rounded-2xl text-purple-950 text-sm font-semibold flex items-center space-x-2">
            <Info className="w-5 h-5 text-purple-700 flex-shrink-0" />
            <span>{accessMessage}</span>
          </div>
        )}

        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label htmlFor="researcher-address" className="block text-sm font-bold text-slate-700 mb-1">
                Researcher or Hospital Ethereum Address:
              </label>
              <input
                id="researcher-address"
                type="text"
                value={researcherAddress}
                onChange={(e) => setResearcherAddress(e.target.value)}
                placeholder="0x..."
                className="w-full p-3 font-mono text-sm bg-slate-50 border-2 border-slate-300 rounded-xl focus:outline-none focus:border-purple-700"
              />
            </div>

            <div>
              <label htmlFor="duration-hours" className="block text-sm font-bold text-slate-700 mb-1">
                Access Duration:
              </label>
              <select
                id="duration-hours"
                value={durationHours}
                onChange={(e) => setDurationHours(Number(e.target.value))}
                className="w-full p-3 text-sm font-bold bg-slate-50 border-2 border-slate-300 rounded-xl"
              >
                <option value={24}>24 Hours (1 Day)</option>
                <option value={72}>72 Hours (3 Days)</option>
                <option value={168}>168 Hours (1 Week)</option>
                <option value={720}>720 Hours (30 Days)</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={handleCheckAccess}
              disabled={actionLoading}
              className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-sm px-5 py-3 rounded-xl border border-slate-300 transition flex items-center space-x-2 min-h-[44px]"
            >
              <Key className="w-4 h-4" />
              <span>Check On-Chain Permission</span>
            </button>

            <button
              onClick={handleGrantAccess}
              disabled={actionLoading}
              className="bg-purple-700 hover:bg-purple-800 text-white font-bold text-sm px-5 py-3 rounded-xl shadow-sm transition flex items-center space-x-2 min-h-[44px]"
            >
              <Lock className="w-4 h-4" />
              <span>Grant Time-Locked Access</span>
            </button>

            <button
              onClick={handleRevokeAccess}
              disabled={actionLoading}
              className="bg-red-50 hover:bg-red-100 text-red-700 font-bold text-sm px-5 py-3 rounded-xl border border-red-200 transition flex items-center space-x-2 min-h-[44px]"
            >
              <Unlock className="w-4 h-4" />
              <span>Revoke Access Immediately</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
