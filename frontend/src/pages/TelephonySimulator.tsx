import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Webhook,
  User,
  FileAudio,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  FileCheck,
  Layout,
  ExternalLink,
  Wifi,
  RefreshCw,
  PhoneIncoming,
  Activity
} from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { listAdvisors, listTeams } from '../api/lookups';
import { simulateTelephonyCall } from '../api/calls';
import { getPipelineStatus, cancelPipeline, startPipeline } from '../api/pipeline';
import { apiClient } from '../api/client';
import { PipelineStageStatus, PipelineStatusResponse } from '../types/pipeline';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import StatusBadge from '../components/common/StatusBadge';
import ScoreBadge from '../components/common/ScoreBadge';
import { getNextExternalCallId, shouldDisplayInSimulator } from './telephonySimulatorUtils';

const PIPELINE_STAGES = [
  'Audio Processing',
  'Transcription',
  'Speaker Diarization',
  'Transcript Building',
  'PII Redaction',
  'AI Analysis'
];

const POLL_INTERVAL_MS = 2500;
const POLL_BACKOFF_MS = 5000;
const POLL_MAX_MS = 10000;
const SOFT_ERROR_HINT_THRESHOLD = 3;

// Interface for tracking submitted calls
interface SubmittedCall {
  id: string; // The backend Call ID
  externalCallId: string;
  vendor: string;
  advisorName: string;
  timestamp: number;
}

// ----------------------------------------------------------------------------
// Tracker Component: Isolated Polling for a Single Call
// ----------------------------------------------------------------------------
function CallProcessingTracker({
  call,
  onDuplicateSubmit,
  onTerminalState
}: {
  call: SubmittedCall;
  onDuplicateSubmit: (externalCallId: string, vendor: string) => void;
  onTerminalState?: (callId: string, state: 'completed' | 'cancelled') => void;
}) {
  const navigate = useNavigate();
  type PipelineUIState = 'idle' | 'starting' | 'polling' | 'completed' | 'failed' | 'cancelled';
  const [pipelineUIState, setPipelineUIState] = useState<PipelineUIState>('polling');
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [consecutivePollErrors, setConsecutivePollErrors] = useState(0);

  const cancelMutation = useMutation({
    mutationFn: () => cancelPipeline(call.id),
    onSuccess: () => {
      setPipelineUIState('cancelled');
      stopPolling();
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => startPipeline(call.id),
    onSuccess: () => {
      setPipelineUIState('polling');
      // Wait a moment for uvicorn dispatch before scheduling poll
      setTimeout(() => schedulePoll(call.id), 200);
    },
  });

  const handleCancelClick = () => {
    cancelMutation.mutate();
  };

  const handleRetryClick = () => {
    retryMutation.mutate();
  };

  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isPollActiveRef = useRef(false);
  const isPollingRef = useRef(true); // Start polling immediately on mount

  const stopPolling = () => {
    isPollingRef.current = false;
    if (pollTimeoutRef.current !== null) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  useEffect(() => {
    schedulePoll(call.id);
    return () => stopPolling();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [call.id]);

  useEffect(() => {
    if (pipelineUIState === 'completed' || pipelineUIState === 'cancelled') {
      onTerminalState?.(call.id, pipelineUIState);
    }
  }, [call.id, onTerminalState, pipelineUIState]);

  const nextPollDelay = (errCount: number): number => {
    if (errCount === 0) return POLL_INTERVAL_MS;
    const backoff = POLL_BACKOFF_MS * Math.pow(1.5, errCount - 1);
    return Math.min(backoff, POLL_MAX_MS);
  };

  const schedulePoll = (cId: string) => {
    if (!isPollingRef.current) return;
    if (isPollActiveRef.current) return;

    isPollActiveRef.current = true;

    getPipelineStatus(cId)
      .then((serverStatus) => {
        setPipelineStatus(serverStatus);
        setConsecutivePollErrors(0);

        if (serverStatus.pipeline_status === 'completed') {
          stopPolling();
          setPipelineUIState('completed');
          return;
        }
        if (serverStatus.pipeline_status === 'failed') {
          stopPolling();
          setPipelineUIState('failed');
          return;
        }
        if (serverStatus.pipeline_status === 'cancelled') {
          stopPolling();
          setPipelineUIState('cancelled');
          return;
        }

        if (isPollingRef.current) {
          pollTimeoutRef.current = setTimeout(() => schedulePoll(cId), POLL_INTERVAL_MS);
        }
      })
      .catch(() => {
        setConsecutivePollErrors((prev) => {
          const newCount = prev + 1;
          if (isPollingRef.current) {
            const delay = nextPollDelay(newCount);
            pollTimeoutRef.current = setTimeout(() => schedulePoll(cId), delay);
          }
          return newCount;
        });
      })
      .finally(() => {
        isPollActiveRef.current = false;
      });
  };

  const getInitialStages = (): PipelineStageStatus[] =>
    PIPELINE_STAGES.map((name) => ({ stage: name, status: 'Waiting', error: null }));

  const displayStages: PipelineStageStatus[] = pipelineStatus?.stages ?? getInitialStages();

  const stageIcon = (stageStatus: PipelineStageStatus['status']) => {
    switch (stageStatus) {
      case 'Completed': return <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />;
      case 'Failed': return <AlertCircle className="w-3 h-3 text-red-500 shrink-0" />;
      case 'Cancelled': return <X className="w-3 h-3 text-neutral-400 shrink-0" />;
      case 'Processing': return <Loader2 className="w-3 h-3 text-brand-600 animate-spin shrink-0" />;
      default: return <span className="w-3 h-3 shrink-0 rounded-full border border-neutral-300 inline-block" />;
    }
  };

  const stageLabelClass = (stageStatus: PipelineStageStatus['status']) => {
    switch (stageStatus) {
      case 'Completed': return 'text-emerald-700 font-semibold';
      case 'Failed': return 'text-red-700 font-semibold';
      case 'Cancelled': return 'text-neutral-500 line-through';
      case 'Processing': return 'text-brand-700 font-semibold';
      default: return 'text-neutral-400';
    }
  };

  const stageBadge = (st: PipelineStageStatus) => {
    switch (st.status) {
      case 'Completed': return <span className="text-[9px] font-bold uppercase tracking-wider text-emerald-600">Completed</span>;
      case 'Failed': return <span className="text-[9px] font-bold uppercase tracking-wider text-red-600">Failed</span>;
      case 'Cancelled': return <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-400">Cancelled</span>;
      case 'Processing': return (
        <span className="text-[9px] font-bold uppercase tracking-wider text-brand-600 flex items-center gap-1">
          <Loader2 className="w-2 h-2 animate-spin" /> Processing
        </span>
      );
      default: return <span className="text-[9px] font-bold uppercase tracking-wider text-neutral-400">Waiting</span>;
    }
  };

  const overallStatusLabel = () => {
    if (pipelineUIState === 'starting') return 'Starting pipeline…';
    if (pipelineUIState === 'polling') return 'Pipeline in Progress';
    if (pipelineUIState === 'completed') return 'Analysis Completed';
    if (pipelineUIState === 'failed') return 'Pipeline Failed';
    if (pipelineUIState === 'cancelled') return 'Cancelled';
    return '';
  };

  const connectionLost = consecutivePollErrors >= SOFT_ERROR_HINT_THRESHOLD;

  return (
    <div className="bg-white border border-neutral-200 rounded-lg shadow-sm flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-neutral-50 px-4 py-3 border-b border-neutral-200 flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-xs font-bold text-neutral-900">{call.vendor}</span>
          <span className="text-[10px] text-neutral-500 font-mono">EXT: {call.externalCallId}</span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] uppercase font-bold text-neutral-500">Call ID</span>
          <span className="text-xs font-mono text-neutral-700">{call.id.substring(0, 8)}</span>
        </div>
      </div>
      
      {/* Status & Stages */}
      <div className="p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <User className="w-3.5 h-3.5 text-neutral-400" />
            <span className="text-xs font-medium text-neutral-700">{call.advisorName}</span>
          </div>
          <div className="flex items-center gap-1.5">
            {pipelineUIState === 'polling' && <Loader2 className="w-3.5 h-3.5 text-brand-600 animate-spin" />}
            {pipelineUIState === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
            {pipelineUIState === 'failed' && <AlertCircle className="w-3.5 h-3.5 text-red-500" />}
            {pipelineUIState === 'cancelled' && <X className="w-3.5 h-3.5 text-neutral-400" />}
            <span className="text-xs font-bold text-neutral-800">{overallStatusLabel()}</span>
          </div>
        </div>

        {connectionLost && pipelineUIState === 'polling' && (
          <div className="bg-neutral-100 border border-neutral-200 rounded px-3 py-2 text-[10px] text-neutral-600 flex items-center gap-2">
            <Loader2 className="w-3 h-3 shrink-0 animate-spin text-neutral-400" />
            <span>Polling temporarily unavailable. Server processing continues.</span>
          </div>
        )}

        <div className="border border-neutral-100 rounded overflow-hidden divide-y divide-neutral-100 mt-1">
          {displayStages.map((st, idx) => (
            <div
              key={idx}
              className={`px-3 py-2 flex items-center justify-between text-[10px] transition-colors ${
                st.status === 'Processing' ? 'bg-brand-50' :
                st.status === 'Completed' ? 'bg-white' :
                st.status === 'Failed' ? 'bg-red-50' :
                st.status === 'Cancelled' ? 'bg-neutral-50' :
                'bg-white'
              }`}
            >
              <div className="flex items-center gap-2">
                {stageIcon(st.status)}
                <span className={`font-medium ${stageLabelClass(st.status)}`}>{st.stage}</span>
              </div>
              <div className="flex flex-col items-end gap-0.5">
                {stageBadge(st)}
                {st.status === 'Failed' && st.error && (
                  <span className="text-[9px] text-red-500 max-w-[150px] text-right truncate" title={st.error}>
                    {st.error}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="bg-neutral-50 px-4 py-3 border-t border-neutral-200 flex justify-between items-center">
        <button
          onClick={() => onDuplicateSubmit(call.externalCallId, call.vendor)}
          className="px-3 py-1.5 text-[10px] font-semibold text-neutral-600 hover:text-neutral-900 border border-neutral-200 bg-white hover:bg-neutral-100 rounded transition-colors flex items-center gap-1 shadow-sm"
        >
          <RefreshCw className="w-3 h-3" />
          Re-Send Duplicate
        </button>

        {(pipelineUIState === 'polling' || pipelineUIState === 'starting' || pipelineUIState === 'idle') && (
          <button
            onClick={handleCancelClick}
            disabled={cancelMutation.isPending}
            className="px-3 py-1.5 text-[10px] font-semibold text-white bg-red-600 hover:bg-red-700 rounded transition-colors flex items-center gap-1 shadow-sm disabled:opacity-50"
          >
            {cancelMutation.isPending && <Loader2 className="w-3 h-3 animate-spin shrink-0" />}
            Cancel Processing
          </button>
        )}

        {pipelineUIState === 'completed' && (
          <button
            onClick={() => navigate(`/calls/${call.id}`)}
            className="px-3 py-1.5 text-[10px] font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded transition-colors flex items-center gap-1 shadow-sm"
          >
            <Layout className="w-3 h-3" />
            Open Review <ExternalLink className="w-2.5 h-2.5 shrink-0" />
          </button>
        )}

        {pipelineUIState === 'cancelled' && (
          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">Cancelled</span>
        )}

        {pipelineUIState === 'failed' && (
          <button
            onClick={handleRetryClick}
            disabled={retryMutation.isPending}
            className="px-3 py-1.5 text-[10px] font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded transition-colors flex items-center gap-1 shadow-sm disabled:opacity-50"
          >
            {retryMutation.isPending && <Loader2 className="w-3 h-3 animate-spin shrink-0" />}
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Main Page Component
// ----------------------------------------------------------------------------
export default function TelephonySimulator() {
  const { selectedOrgId } = useAppGlobalContext();

  // Ingestion form state
  const [advisorId, setAdvisorId] = useState('');
  const [vendor, setVendor] = useState('FITNOVA_DIALER');
  const [externalCallId, setExternalCallId] = useState('CALL-001');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isCustomExternalIdMode, setIsCustomExternalIdMode] = useState(false);

  // Active trackable calls state
  const [submittedCalls, setSubmittedCalls] = useState<SubmittedCall[]>([]);
  const [restoredOrgId, setRestoredOrgId] = useState<string | null>(null);
  const [restorationStatus, setRestorationStatus] = useState<string>('idle');
  const [restorationError, setRestorationError] = useState<string>('');
  const restorationRequestIdRef = useRef(0);
  
  // Feedback state for the form itself
  const [validationError, setValidationError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch persisted calls from backend and restore only active processing calls into the simulator.
  useEffect(() => {
    if (!selectedOrgId || selectedOrgId === restoredOrgId) return;

    const requestId = restorationRequestIdRef.current + 1;
    restorationRequestIdRef.current = requestId;

    console.log(`[TELEPHONY_SIMULATOR] Starting restoration from backend for org: ${selectedOrgId}...`);
    setRestorationStatus('loading');

    apiClient.get('/dashboard/calls', {
      params: {
        has_source_reference: true,
        organization_id: selectedOrgId,
        page_size: 100,
        sort: 'newest'
      }
    }).then((res) => {
      console.log('[TELEPHONY_SIMULATOR] API response status:', res.status);
      console.log('[TELEPHONY_SIMULATOR] Raw API response data:', res.data);
      const items = res.data.items || [];
      console.log('[TELEPHONY_SIMULATOR] Items extracted:', items.length);

      const mappedCalls: SubmittedCall[] = items
        .filter((c: any) => shouldDisplayInSimulator(c.processing_status))
        .map((c: any) => {
          const parsedDate = new Date(c.upload_time);
          const timestamp = isNaN(parsedDate.getTime()) ? Date.now() : parsedDate.getTime();
          return {
            id: c.call_id,
            externalCallId: c.source_reference || 'UNKNOWN',
            vendor: c.source_type,
            advisorName: c.advisor_name,
            timestamp
          };
        });
      console.log('[TELEPHONY_SIMULATOR] Mapped active calls:', mappedCalls);

      if (requestId !== restorationRequestIdRef.current) {
        return;
      }

      setSubmittedCalls((prev) => {
        const merged = [...prev.filter((c) => !mappedCalls.some((mc) => mc.id === c.id))];
        mappedCalls.forEach((mc) => {
          if (!merged.find((existing) => existing.id === mc.id)) {
            merged.push(mc);
          }
        });
        const sorted = merged.sort((a, b) => b.timestamp - a.timestamp);
        console.log('[TELEPHONY_SIMULATOR] Merged & sorted active calls:', sorted);
        return sorted;
      });

      const persistedExternalIds = items.map((c: any) => c.source_reference).filter(Boolean);
      const nextAutoId = getNextExternalCallId(persistedExternalIds);
      setExternalCallId(nextAutoId);
      setIsCustomExternalIdMode(false);
      setRestorationStatus('success');
      setRestoredOrgId(selectedOrgId);
    }).catch(err => {
      if (requestId !== restorationRequestIdRef.current) {
        return;
      }
      console.error('[TELEPHONY_SIMULATOR] Failed to restore simulator calls:', err);
      setRestorationError(err.message || String(err));
      setRestorationStatus('failed');
      setRestoredOrgId(selectedOrgId);
    });
  }, [selectedOrgId, restoredOrgId]);

  const { data: advisors = [], isLoading: loadingAdvisors } = useQuery({
    queryKey: QUERY_KEYS.advisorsLookup(undefined, selectedOrgId),
    queryFn: () => listAdvisors({
      organization_id: selectedOrgId,
      status: 'Active'
    }),
    enabled: !!selectedOrgId,
  });

  const ingestMutation = useMutation({
    mutationFn: ({ file, advId, extId, srcVendor, requestToken }: { file: File, advId: string, extId: string, srcVendor: string, requestToken: number }) => {
      void requestToken;
      return simulateTelephonyCall(file, advId, extId, srcVendor);
    },
    onSuccess: (res, variables) => {
      if (variables.requestToken !== restorationRequestIdRef.current) {
        return;
      }
      if (res.success && res.call_id) {
        // Resolve advisor name for tracker display
        const advName = advisors.find((a) => a.id === variables.advId)?.name || 'Unknown Advisor';
        
        // Add to tracking array (deduplicated)
        setSubmittedCalls((prev) => {
          const newCall = {
            id: res.call_id!,
            externalCallId: variables.extId,
            vendor: variables.srcVendor,
            advisorName: advName,
            timestamp: Date.now()
          };
          if (prev.find(c => c.id === newCall.id)) {
            return prev;
          }
          return [newCall, ...prev];
        });

        setSuccessMessage(`Accepted! Background processing started for ${variables.extId}.`);
        setValidationError('');

        setAudioFile(null);

        const persistedExternalIds = [variables.extId, ...submittedCalls.map((call) => call.externalCallId).filter(Boolean)];
        const nextAutoId = getNextExternalCallId(persistedExternalIds);
        setExternalCallId(nextAutoId);
        setIsCustomExternalIdMode(false);

        // Hide success message after a few seconds
        setTimeout(() => setSuccessMessage(''), 4000);
      } else {
        setValidationError(res.message || 'Ingestion failed.');
      }
    },
    onError: (err: any) => {
      setValidationError(err.message || 'An error occurred during ingestion.');
      setSuccessMessage('');
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValidationError('');
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();

    if (!['.wav', '.mp3', '.m4a'].includes(extension)) {
      setValidationError('Unsupported file format. Please upload .wav, .mp3, or .m4a.');
      return;
    }

    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      setValidationError('Audio file size exceeds the 50 MB limit.');
      return;
    }

    setAudioFile(file);
    setValidationError('');
  };

  const handleIngestSubmit = () => {
    setValidationError('');
    setSuccessMessage('');
    if (!audioFile || !advisorId || !externalCallId || !vendor) return;

    const requestToken = restorationRequestIdRef.current + 1;
    restorationRequestIdRef.current = requestToken;
    
    ingestMutation.mutate({
      file: audioFile,
      advId: advisorId,
      extId: externalCallId,
      srcVendor: vendor,
      requestToken
    });
  };

  // Helper function for the tracker cards to trigger a duplicate intentionally
  const handleDuplicateSubmit = (extId: string, srcVendor: string) => {
    // We'll resubmit with whatever audio file is currently in the form (or require them to pick one)
    if (!audioFile) {
      setValidationError(`Please select an audio file in the form above first to resend ${extId}.`);
      return;
    }
    if (!advisorId) {
      setValidationError(`Please select an advisor first to resend ${extId}.`);
      return;
    }
    
    setValidationError('');
    setSuccessMessage('');
    
    const requestToken = restorationRequestIdRef.current + 1;
    restorationRequestIdRef.current = requestToken;

    ingestMutation.mutate({
      file: audioFile,
      advId: advisorId,
      extId: extId,
      srcVendor: srcVendor,
      requestToken
    });
  };

  const handleTrackableCallStateChange = (callId: string, state: 'completed' | 'cancelled') => {
    if (state === 'completed' || state === 'cancelled') {
      setSubmittedCalls((prev) => prev.filter((call) => call.id !== callId));
    }
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <PageHeader
        title="Telephony Simulator"
        subtitle="Simulate inbound webhooks and monitor decoupled background pipeline processing."
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: The Ingestion Form */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white border border-neutral-200 rounded-lg p-5 shadow-sm space-y-5 sticky top-6">
            <div className="flex items-center gap-2 font-semibold text-sm text-neutral-900 border-b border-neutral-100 pb-3">
              <Webhook className="w-5 h-5 text-brand-600" />
              <span>Simulate New Incoming Call</span>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-neutral-600">Source / Vendor</label>
                <input
                  type="text"
                  value={vendor}
                  onChange={(e) => setVendor(e.target.value)}
                  disabled={ingestMutation.isPending}
                  className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-neutral-600">External Call ID</label>
                  <button
                    type="button"
                    onClick={() => {
                      setIsCustomExternalIdMode(true);
                      setExternalCallId('');
                    }}
                    className="text-[10px] font-semibold text-brand-600 hover:text-brand-700"
                  >
                    Custom ID / Test duplicate
                  </button>
                </div>
                <input
                  type="text"
                  value={externalCallId}
                  onChange={(e) => setExternalCallId(e.target.value)}
                  disabled={ingestMutation.isPending}
                  readOnly={!isCustomExternalIdMode}
                  placeholder="CALL-001"
                  className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-neutral-600">Mapped Advisor</label>
                <select
                  value={advisorId}
                  onChange={(e) => setAdvisorId(e.target.value)}
                  disabled={ingestMutation.isPending || loadingAdvisors}
                  className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500 disabled:opacity-50"
                >
                  <option value="" disabled>Select an Advisor</option>
                  {advisors.map((adv) => (
                    <option key={adv.id} value={adv.id}>{adv.name} ({adv.team_name})</option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5 pt-1">
                <label className="text-xs font-semibold text-neutral-600">Audio File (.wav, .mp3, .m4a)</label>
                {!audioFile ? (
                  <div className="border-2 border-dashed border-neutral-300 rounded-lg p-4 text-center flex flex-col items-center justify-center space-y-2 hover:border-brand-500 transition-colors bg-neutral-50 cursor-pointer relative">
                    <input
                      type="file"
                      accept=".wav,.mp3,.m4a"
                      onChange={handleFileChange}
                      disabled={ingestMutation.isPending}
                      className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <div className="p-2 bg-white border border-neutral-200 rounded-full shadow-sm text-neutral-400">
                      <FileAudio className="w-4 h-4" />
                    </div>
                    <p className="text-[10px] font-bold text-neutral-600">Select Audio File to Simulate</p>
                  </div>
                ) : (
                  <div className="border border-neutral-200 rounded-lg p-3 bg-neutral-50 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileCheck className="w-4 h-4 text-brand-600 shrink-0" />
                      <div className="min-w-0">
                        <p className="font-semibold text-neutral-900 truncate">{audioFile.name}</p>
                        <p className="text-[9px] text-neutral-400 mt-0.5">
                          {formatFileSize(audioFile.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => setAudioFile(null)}
                      disabled={ingestMutation.isPending}
                      className="p-1 rounded-full text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 disabled:opacity-50"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>

            {validationError && (
              <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span className="font-medium">{validationError}</span>
              </div>
            )}

            {successMessage && (
              <div className="bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md p-3 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span className="font-medium">{successMessage}</span>
              </div>
            )}

            <div className="pt-2 border-t border-neutral-100">
              <button
                onClick={handleIngestSubmit}
                disabled={!audioFile || !advisorId || !vendor || !externalCallId || ingestMutation.isPending}
                className="w-full py-2.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-sm"
              >
                {ingestMutation.isPending ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Calling Webhook...</>
                ) : (
                  <><PhoneIncoming className="w-4 h-4" /> Simulate Incoming Call</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Active / Recent Processing */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-neutral-200">
            <div className="flex items-center gap-2 font-semibold text-sm text-neutral-900">
              <Activity className="w-5 h-5 text-neutral-500" />
              <span>Recent Incoming Calls</span>
            </div>
            <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">
              {submittedCalls.length} Active Sessions
            </span>
          </div>

          {restorationStatus === 'loading' && (
            <div className="bg-blue-50 text-blue-700 border border-blue-200 rounded-md p-3 text-xs flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin shrink-0" />
              <span>Restoring previous simulator calls from backend...</span>
            </div>
          )}

          {restorationStatus === 'failed' && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Failed to restore previous calls:</span>
                <p className="mt-0.5 font-mono text-[10px]">{restorationError}</p>
              </div>
            </div>
          )}

          {restorationStatus === 'success' && (
            <div className="bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md px-3 py-1.5 text-[10px] flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
              <span>Successfully synchronized with backend database.</span>
            </div>
          )}

          {submittedCalls.length === 0 ? (
            <div className="border-2 border-dashed border-neutral-200 rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-3 bg-neutral-50/50">
              <div className="w-12 h-12 bg-white rounded-full shadow-sm flex items-center justify-center border border-neutral-100">
                <PhoneIncoming className="w-5 h-5 text-neutral-300" />
              </div>
              <div>
                <p className="text-sm font-semibold text-neutral-600">No active calls</p>
                <p className="text-xs text-neutral-400 mt-1 max-w-[250px] mx-auto">
                  Simulate an incoming call on the left. It will appear here and process in the background.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
              {submittedCalls.map((call) => (
                <CallProcessingTracker
                  key={call.id}
                  call={call}
                  onDuplicateSubmit={handleDuplicateSubmit}
                  onTerminalState={handleTrackableCallStateChange}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
