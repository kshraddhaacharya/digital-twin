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
  Database,
  RefreshCw,
  Copy,
  Check,
  Blocks,
  Wallet
} from 'lucide-react';
import { TwinState, Web3NetworkStatus, Web3VerificationResult } from '../types';
import { api } from '../services/api';

interface Web3SectionProps {
  patientId: string;
  twinState: TwinState | null;
  twinHistory: TwinState[];
}

export const Web3Section: React.FC<Web3SectionProps> = ({
  patientId,
  twinState,
  twinHistory,
}) => {
  const [networkStatus, setNetworkStatus] = useState<Web3NetworkStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Verification state
  const [selectedVersion, setSelectedVersion] = useState<number>(twinState ? twinState.state_version : 1);
  const [verifying, setVerifying] = useState<boolean>(false);
  const [verifyResult, setVerifyResult] = useState<Web3VerificationResult | null>(null);

  // Sovereign Consent state
  const [researcherAddress, setResearcherAddress] = useState<string>('0x90F79bf6EB2c4f870365E785982E1f101E93b906');
  const [durationHours, setDurationHours] = useState<number>(24);
  const [accessStatus, setAccessStatus] = useState<boolean | null>(null);
  const [accessMessage, setAccessMessage] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);

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

  useEffect(() => {
    if (twinState) {
      setSelectedVersion(twinState.state_version);
    }
  }, [twinState]);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const handleVerifyOnChain = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await api.verifyTwinStateOnChain(patientId, selectedVersion);
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
          ? `Address ${researcherAddress.slice(0, 8)}... has ACTIVE verified on-chain permission.`
          : `Address ${researcherAddress.slice(0, 8)}... does NOT currently have access.`
      );
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to check permission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGrantAccess = async () => {
    setActionLoading(true);
    setAccessMessage(null);
    try {
      const res = await api.grantAccessOnChain(patientId, researcherAddress, durationHours * 3600);
      setAccessStatus(true);
      setAccessMessage(`Access GRANTED on-chain. Transaction: ${res.tx_hash.slice(0, 16)}...`);
      fetchWeb3Status();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to grant access on-chain.');
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
      setAccessMessage(`Access REVOKED on-chain. Transaction: ${res.tx_hash.slice(0, 16)}...`);
      fetchWeb3Status();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to revoke access on-chain.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Web3 Banner */}
      <div className="bg-gradient-to-r from-purple-900 via-slate-900 to-twin-900 rounded-xl p-6 text-white shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="bg-purple-500/20 p-3 rounded-xl border border-purple-400/30 backdrop-blur-sm">
              <Blocks className="w-8 h-8 text-purple-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs uppercase font-bold tracking-widest text-purple-300">
                  Web3 Decentralized Architecture
                </span>
                <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded border border-emerald-400/30 uppercase">
                  Smart Contract Anchored
                </span>
              </div>
              <h2 className="text-2xl font-black tracking-tight mt-0.5">
                Patient Digital Twin Sovereign Registry
              </h2>
              <p className="text-xs text-slate-300 mt-1 max-w-2xl">
                Every state version is cryptographically hashed (SHA-256), content-addressed on IPFS, and anchored to an EVM Smart Contract (`PatientDigitalTwinRegistry.sol`) ensuring immutable audit trails and sovereign patient consent.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={fetchWeb3Status}
              disabled={loading}
              className="bg-white/10 hover:bg-white/20 border border-white/25 text-white text-xs font-semibold px-3 py-2 rounded-lg transition-all flex items-center space-x-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh Node</span>
            </button>
          </div>
        </div>
      </div>

      {/* EVM Blockchain Network Telemetry Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Smart Contract Address */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Deployed Smart Contract
          </span>
          <div className="mt-2 flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-purple-800 bg-purple-50 px-2 py-1 rounded border border-purple-200 truncate max-w-[180px]">
              {networkStatus ? networkStatus.contract_address : 'Loading...'}
            </span>
            {networkStatus && networkStatus.contract_address && (
              <button
                onClick={() => handleCopy(networkStatus.contract_address!)}
                title="Copy Contract Address"
                className="text-slate-400 hover:text-purple-600 p-1"
              >
                {copiedText === networkStatus.contract_address ? (
                  <Check className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            )}
          </div>
          <div className="mt-3 text-[11px] text-slate-400">
            EVM Registry: <code className="font-mono">PatientDigitalTwinRegistry</code>
          </div>
        </div>

        {/* Transacting Account */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Active Wallet Identity
          </span>
          <div className="mt-2 flex items-center justify-between">
            <span className="font-mono text-xs font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded border border-slate-200 truncate max-w-[180px]">
              {networkStatus ? networkStatus.active_wallet_address : 'Loading...'}
            </span>
            {networkStatus && networkStatus.active_wallet_address && (
              <button
                onClick={() => handleCopy(networkStatus.active_wallet_address!)}
                title="Copy Wallet Address"
                className="text-slate-400 hover:text-slate-700 p-1"
              >
                {copiedText === networkStatus.active_wallet_address ? (
                  <Check className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            )}
          </div>
          <div className="mt-3 text-[11px] text-slate-500">
            Balance: <strong>{networkStatus ? networkStatus.wallet_balance_eth.toLocaleString() : '--'} ETH</strong>
          </div>
        </div>

        {/* EVM Chain & Network */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            EVM Network & Chain ID
          </span>
          <div className="mt-2 text-lg font-bold text-slate-900">
            Chain ID: <span className="font-mono text-twin-600">{networkStatus ? networkStatus.chain_id : '--'}</span>
          </div>
          <div className="mt-3 text-[11px] text-emerald-700 font-semibold flex items-center space-x-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{networkStatus?.network_name || 'EVM Connected'}</span>
          </div>
        </div>

        {/* Latest Block Height */}
        <div className="bg-white rounded-xl p-5 border border-slate-200 shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Current Block Height
          </span>
          <div className="mt-2 text-2xl font-black text-slate-900 font-mono">
            #{networkStatus ? networkStatus.latest_block_number : '--'}
          </div>
          <div className="mt-3 text-[11px] text-slate-400">
            Real-time consensus confirmation
          </div>
        </div>
      </div>

      {/* Cryptographic On-Chain State Verification Panel */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <h3 className="text-base font-bold text-slate-900">
                On-Chain Cryptographic State Integrity Verifier
              </h3>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Validates that the active digital twin state matches the immutable cryptographic hash anchored in the smart contract.
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <label className="text-xs text-slate-600 font-semibold">Verify Version:</label>
            <select
              value={selectedVersion}
              onChange={(e) => setSelectedVersion(parseInt(e.target.value))}
              className="text-xs border border-slate-300 rounded-lg p-2 bg-slate-50 font-bold"
            >
              {twinHistory.map((s) => (
                <option key={s.id} value={s.state_version}>
                  Version {s.state_version} ({s.is_active_version ? 'Active' : 'Archived'})
                </option>
              ))}
            </select>

            <button
              onClick={handleVerifyOnChain}
              disabled={verifying}
              className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-all disabled:opacity-50 flex items-center space-x-1.5"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{verifying ? 'Querying Blockchain...' : 'Verify On-Chain'}</span>
            </button>
          </div>
        </div>

        {/* Verification Result Card */}
        {verifyResult && (
          <div className={`mt-5 p-5 rounded-xl border ${
            verifyResult.is_valid
              ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
              : 'bg-rose-50 border-rose-300 text-rose-950'
          }`}>
            <div className="flex items-center space-x-3">
              {verifyResult.is_valid ? (
                <CheckCircle2 className="w-6 h-6 text-emerald-600 flex-shrink-0" />
              ) : (
                <XCircle className="w-6 h-6 text-rose-600 flex-shrink-0" />
              )}
              <div>
                <h4 className="text-sm font-extrabold uppercase tracking-wide">
                  {verifyResult.is_valid
                    ? 'Cryptographic On-Chain Parity Confirmed'
                    : 'Integrity Check Failed — State Tampering Detected'}
                </h4>
                <p className="text-xs mt-0.5">
                  {verifyResult.is_valid
                    ? 'Candidate digital twin features match the immutable SHA-256 state root committed to the smart contract.'
                    : 'Candidate features do NOT match the on-chain hash for this state version!'}
                </p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
              <div className="bg-white/80 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">On-Chain State Root</span>
                <div className="text-slate-800 font-bold truncate mt-1">
                  0x{verifyResult.on_chain_root}
                </div>
              </div>

              <div className="bg-white/80 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">Decentralized IPFS CIDv1</span>
                <div className="text-purple-800 font-bold truncate mt-1">
                  ipfs://{verifyResult.ipfs_cid}
                </div>
              </div>

              <div className="bg-white/80 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">Block Anchor</span>
                <div className="text-slate-800 font-bold mt-1">
                  Block #{verifyResult.block_number}
                </div>
              </div>

              <div className="bg-white/80 p-3 rounded-lg border border-emerald-200">
                <span className="text-[10px] uppercase font-bold text-slate-500">Smart Contract</span>
                <div className="text-slate-800 font-bold truncate mt-1">
                  {verifyResult.contract_address}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Current Active State On-Chain Attestation Preview */}
        {!verifyResult && twinState && (
          <div className="mt-5 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
            <span className="font-bold text-slate-700">Active Twin State Attestation Record:</span>
            <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <span className="text-slate-400">Transaction Hash:</span>
                <div className="font-mono font-bold text-purple-700 truncate">
                  {twinState.on_chain_tx_hash ? `0x${twinState.on_chain_tx_hash}` : 'Committed'}
                </div>
              </div>
              <div>
                <span className="text-slate-400">Committed Block:</span>
                <div className="font-mono font-bold text-slate-800">
                  Block #{twinState.on_chain_block_number ?? '1'}
                </div>
              </div>
              <div>
                <span className="text-slate-400">IPFS CID:</span>
                <div className="font-mono font-bold text-slate-800 truncate">
                  {twinState.ipfs_cid ? `ipfs://${twinState.ipfs_cid}` : '--'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sovereign Patient Consent & Decentralized Access Control */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
        <div className="pb-4 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Key className="w-5 h-5 text-twin-600" />
            <h3 className="text-base font-bold text-slate-900">
              Sovereign Patient Consent & Access Control (Smart Contract Permissioning)
            </h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            The patient's Ethereum wallet owns their Digital Twin. Only authorized researcher or clinician wallets with an unexpired on-chain permission grant can access the state.
          </p>
        </div>

        {accessMessage && (
          <div className={`mt-4 p-3 rounded-lg border text-xs font-semibold ${
            accessStatus
              ? 'bg-emerald-50 border-emerald-300 text-emerald-800'
              : 'bg-amber-50 border-amber-300 text-amber-800'
          }`}>
            {accessMessage}
          </div>
        )}

        <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Clinician / Researcher Ethereum Wallet Address
            </label>
            <input
              type="text"
              value={researcherAddress}
              onChange={(e) => setResearcherAddress(e.target.value)}
              className="w-full text-xs font-mono border border-slate-300 rounded-lg p-2.5 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-twin-500"
              placeholder="0x..."
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Access Duration
            </label>
            <select
              value={durationHours}
              onChange={(e) => setDurationHours(parseInt(e.target.value))}
              className="w-full text-xs border border-slate-300 rounded-lg p-2.5 bg-slate-50 font-medium"
            >
              <option value="1">1 Hour</option>
              <option value="24">24 Hours (1 Day)</option>
              <option value="168">7 Days (1 Week)</option>
              <option value="720">30 Days</option>
            </select>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={handleGrantAccess}
            disabled={actionLoading}
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-all flex items-center space-x-1.5 disabled:opacity-50"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>Grant Access On-Chain</span>
          </button>

          <button
            onClick={handleRevokeAccess}
            disabled={actionLoading}
            className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm transition-all flex items-center space-x-1.5 disabled:opacity-50"
          >
            <Unlock className="w-3.5 h-3.5" />
            <span>Revoke Access On-Chain</span>
          </button>

          <button
            onClick={handleCheckAccess}
            disabled={actionLoading}
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold px-4 py-2 rounded-lg border border-slate-300 transition-all flex items-center space-x-1.5"
          >
            <Key className="w-3.5 h-3.5" />
            <span>Verify Address Permission</span>
          </button>
        </div>
      </div>
    </div>
  );
};
