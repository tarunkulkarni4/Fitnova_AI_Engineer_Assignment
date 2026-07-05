import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Upload,
  User,
  FileAudio,
  CheckCircle2,
  Play,
  AlertCircle,
  Loader2,
  X,
  FileCheck,
  Layout,
  ExternalLink,
  RefreshCw,
  Search,
  Wifi
} from 'lucide-react';

import { useAppGlobalContext } from '../contexts/AppContext';
import { listAdvisors, listTeams } from '../api/lookups';
import { uploadCall } from '../api/calls';
import { startPipeline, getPipelineStatus } from '../api/pipeline';
import { PipelineStageStatus, PipelineStatusResponse } from '../types/pipeline';
import { QUERY_KEYS } from '../constants/queryKeys';
import PageHeader from '../components/common/PageHeader';
import StatusBadge from '../components/common/StatusBadge';
import ScoreBadge from '../components/common/ScoreBadge';

const PIPELINE_STAGES = [
  'Audio Processing',
  'Transcription',
  'Speaker Diarization',
  'Transcript Building',
  'PII Redaction',
  'AI Analysis'
];

const POLL_INTERVAL_MS = 2500;         // normal interval
const POLL_BACKOFF_MS  = 5000;         // after first failure
const POLL_MAX_MS      = 10000;        // cap for backoff
// After this many soft failures we show a neutral "status temporarily unavailable" hint.
// We NEVER stop polling due to network errors — only server-confirmed status stops polling.
const SOFT_ERROR_HINT_THRESHOLD = 3;

export default function UploadPage() {
  const navigate = useNavigate();
  const { selectedOrgId } = useAppGlobalContext();

  // Wizard state
  const [step, setStep] = useState(1);
  const [advisorId, setAdvisorId] = useState('');
  const [teamFilterId, setTeamFilterId] = useState('');
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [sourceType, setSourceType] = useState('Manual Ingest');
  const [advisorSearch, setAdvisorSearch] = useState('');

  // Post-upload state
  const [callId, setCallId] = useState<string | null>(null);

  // File validation errors
  const [validationError, setValidationError] = useState('');

  // ── Async pipeline polling state ──────────────────────────────────────────
  type PipelineUIState = 'idle' | 'starting' | 'polling' | 'completed' | 'failed';
  const [pipelineUIState, setPipelineUIState] = useState<PipelineUIState>('idle');
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [consecutivePollErrors, setConsecutivePollErrors] = useState(0);

  // Refs for poll management (stable across renders, no stale closure issues)
  // We use a self-scheduling setTimeout loop instead of setInterval to guarantee
  // that a new poll only starts AFTER the previous request finishes.
  const pollTimeoutRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isPollActiveRef  = useRef(false);   // true while a request is in-flight
  const isPollingRef     = useRef(false);   // true while the loop is alive
  const pollCallIdRef    = useRef<string | null>(null);
  const pollErrorCountRef = useRef(0);      // mirror of state for use inside closures

  const stopPolling = () => {
    isPollingRef.current = false;
    if (pollTimeoutRef.current !== null) {
      clearTimeout(pollTimeoutRef.current);
      pollTimeoutRef.current = null;
    }
  };

  // Clear timeout on unmount to prevent memory leaks
  useEffect(() => {
    return () => stopPolling();
  }, []);

  // Compute next poll delay based on consecutive error count
  const nextPollDelay = (errCount: number): number => {
    if (errCount === 0) return POLL_INTERVAL_MS;
    const backoff = POLL_BACKOFF_MS * Math.pow(1.5, errCount - 1);
    return Math.min(backoff, POLL_MAX_MS);
  };

  // ── Data fetching ─────────────────────────────────────────────────────────

  const { data: teams = [] } = useQuery({
    queryKey: QUERY_KEYS.teamsLookup(selectedOrgId),
    queryFn: () => listTeams(selectedOrgId),
    enabled: !!selectedOrgId,
  });

  const { data: advisors = [], isLoading: loadingAdvisors } = useQuery({
    queryKey: QUERY_KEYS.advisorsLookup(teamFilterId || undefined, selectedOrgId),
    queryFn: () => listAdvisors({
      organization_id: selectedOrgId,
      team_id: teamFilterId || undefined,
      status: 'Active'
    }),
    enabled: !!selectedOrgId,
  });

  const filteredAdvisors = advisors.filter((adv) =>
    adv.name.toLowerCase().includes(advisorSearch.toLowerCase().trim())
  );

  // ── Navigation guard ──────────────────────────────────────────────────────

  const isUploading = false; // set by upload mutation below
  const isBusy = pipelineUIState === 'starting' || pipelineUIState === 'polling';

  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isBusy) {
        e.preventDefault();
        e.returnValue = 'Analysis in progress — you can safely leave this page. Processing continues on the server.';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isBusy]);

  // ── Upload mutation ───────────────────────────────────────────────────────

  const uploadMutation = useMutation({
    mutationFn: ({ file, advId, srcType }: { file: File; advId: string; srcType: string }) =>
      uploadCall(file, advId, srcType),
    onSuccess: (res) => {
      if (res.success && res.call_id) {
        setCallId(res.call_id);
        setStep(3);
      } else {
        setValidationError(res.message || 'Upload failed.');
      }
    },
    onError: (err: any) => {
      setValidationError(err.message || 'An error occurred during upload.');
    }
  });

  // ── Pipeline: start + self-scheduling poll loop ───────────────────────────

  /**
   * Execute a single status poll, then schedule the next one.
   * A new request is only scheduled after the previous one completes,
   * preventing overlapping requests even if a poll takes longer than the
   * interval (e.g. when the server is momentarily busy with CPU work).
   *
   * Error contract:
   *   - Network / transient errors: increment error counter, apply backoff,
   *     keep polling. NEVER mark pipeline stages as Failed.
   *   - Server-confirmed 'failed': stop polling, enter failed UI state.
   *   - Server-confirmed 'completed': stop polling, enter completed UI state.
   */
  const schedulePoll = (cId: string) => {
    if (!isPollingRef.current) return;   // loop was stopped
    if (isPollActiveRef.current) return; // prior request still in-flight (safety)

    isPollActiveRef.current = true;

    getPipelineStatus(cId)
      .then((serverStatus) => {
        // Successful response — update UI and reset error counter
        setPipelineStatus(serverStatus);
        pollErrorCountRef.current = 0;
        setConsecutivePollErrors(0);

        if (serverStatus.pipeline_status === 'completed') {
          stopPolling();
          setPipelineUIState('completed');
          return; // do not schedule next poll
        }
        if (serverStatus.pipeline_status === 'failed') {
          stopPolling();
          setPipelineUIState('failed');
          return; // do not schedule next poll
        }

        // Still running — schedule next poll at normal interval
        if (isPollingRef.current) {
          pollTimeoutRef.current = setTimeout(
            () => schedulePoll(cId),
            POLL_INTERVAL_MS
          );
        }
      })
      .catch(() => {
        // Network / transient error.
        // IMPORTANT: do NOT mark any stage as Failed.
        // Apply exponential backoff and keep polling.
        const newCount = pollErrorCountRef.current + 1;
        pollErrorCountRef.current = newCount;
        setConsecutivePollErrors(newCount);

        if (isPollingRef.current) {
          const delay = nextPollDelay(newCount);
          pollTimeoutRef.current = setTimeout(
            () => schedulePoll(cId),
            delay
          );
        }
      })
      .finally(() => {
        isPollActiveRef.current = false;
      });
  };

  const startPolling = (cId: string) => {
    stopPolling();
    isPollActiveRef.current = false;
    isPollingRef.current = true;
    pollCallIdRef.current = cId;
    pollErrorCountRef.current = 0;
    setConsecutivePollErrors(0);

    // Fire the first poll immediately; subsequent polls are self-scheduled.
    schedulePoll(cId);
  };

  const handleRunPipeline = async () => {
    if (!callId) return;
    setStartError(null);
    setPipelineUIState('starting');

    try {
      await startPipeline(callId);
      // 202 accepted — begin polling regardless of already_processing
      setPipelineUIState('polling');
      startPolling(callId);
    } catch (err: any) {
      setStartError(err.message || 'Failed to start pipeline.');
      setPipelineUIState('idle');
    }
  };

  // ── File helpers ──────────────────────────────────────────────────────────

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

  const handleUploadSubmit = () => {
    if (!audioFile || !advisorId) return;
    uploadMutation.mutate({ file: audioFile, advId: advisorId, srcType: sourceType });
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const selectedAdvisor = advisors.find(a => a.id === advisorId);

  // ── Stage status helpers ──────────────────────────────────────────────────

  /** Derive per-stage display state when actively polling but no server data yet */
  const getInitialStages = (): PipelineStageStatus[] =>
    PIPELINE_STAGES.map((name) => ({ stage: name, status: 'Waiting', error: null }));

  const displayStages: PipelineStageStatus[] =
    pipelineStatus?.stages ?? getInitialStages();

  const stageIcon = (stageStatus: PipelineStageStatus['status']) => {
    switch (stageStatus) {
      case 'Completed': return <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />;
      case 'Failed':    return <AlertCircle className="w-4 h-4 text-red-500 shrink-0" />;
      case 'Processing': return <Loader2 className="w-4 h-4 text-brand-600 animate-spin shrink-0" />;
      default:          return <span className="w-4 h-4 shrink-0 rounded-full border-2 border-neutral-300 inline-block" />;
    }
  };

  const stageLabelClass = (stageStatus: PipelineStageStatus['status']) => {
    switch (stageStatus) {
      case 'Completed': return 'text-emerald-700 font-semibold';
      case 'Failed':    return 'text-red-700 font-semibold';
      case 'Processing': return 'text-brand-700 font-semibold';
      default:          return 'text-neutral-400';
    }
  };

  const stageBadge = (st: PipelineStageStatus) => {
    switch (st.status) {
      case 'Completed':  return <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Completed</span>;
      case 'Failed':     return <span className="text-[10px] font-bold uppercase tracking-wider text-red-600">Failed</span>;
      case 'Processing': return (
        <span className="text-[10px] font-bold uppercase tracking-wider text-brand-600 flex items-center gap-1">
          <Loader2 className="w-2.5 h-2.5 animate-spin" /> Processing
        </span>
      );
      default: return <span className="text-[10px] font-bold uppercase tracking-wider text-neutral-400">Waiting</span>;
    }
  };

  const overallStatusLabel = () => {
    if (pipelineUIState === 'starting') return 'Starting pipeline…';
    if (pipelineUIState === 'polling')  return 'AI Analysis Pipeline in Progress — processing on server…';
    if (pipelineUIState === 'completed') return 'Analysis Completed';
    if (pipelineUIState === 'failed')   return 'Pipeline Stage Failed';
    return '';
  };

  const connectionLost = consecutivePollErrors >= SOFT_ERROR_HINT_THRESHOLD;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <PageHeader
        title="Ingest Audio Call"
        subtitle="Upload a raw customer interaction recording to run compliance scorecard pipelines"
      />

      {/* Stepper Header */}
      <div className="grid grid-cols-3 gap-2 border-b border-neutral-200 pb-4">
        {[
          { num: 1, label: 'Configure Metadata' },
          { num: 2, label: 'Upload Recording' },
          { num: 3, label: 'Process Intelligence' }
        ].map((s) => (
          <div
            key={s.num}
            className={`flex items-center gap-2 border-b-2 pb-2 text-xs font-semibold ${
              step >= s.num ? 'border-brand-600 text-brand-600' : 'border-transparent text-neutral-400'
            }`}
          >
            <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] border ${
              step >= s.num ? 'bg-brand-600 text-white border-brand-600' : 'border-neutral-300'
            }`}>
              {s.num}
            </span>
            <span className="hidden sm:inline">{s.label}</span>
          </div>
        ))}
      </div>

      {/* STEP 1: CONFIGURE METADATA */}
      {step === 1 && (
        <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2 font-semibold text-sm text-neutral-900 border-b border-neutral-100 pb-3">
            <User className="w-5 h-5 text-brand-600" />
            <span>Select Assisting Advisor &amp; Metadata</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-600">Filter by Team</label>
              <select
                value={teamFilterId}
                onChange={(e) => { setTeamFilterId(e.target.value); setAdvisorId(''); }}
                className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
              >
                <option value="">All Teams</option>
                {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-600">Ingestion Source Type</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="text-xs border-neutral-200 rounded-md bg-white py-2 px-3 w-full hover:border-neutral-300 focus:ring-1 focus:ring-brand-500"
              >
                <option value="Manual Ingest">Manual Ingest</option>
                <option value="REST API">REST API</option>
                <option value="Integration Hub">Integration Hub</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-neutral-600 block">Select Active Advisor</label>
            <div className="relative">
              <Search className="w-4 h-4 text-neutral-400 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search active advisors by name..."
                value={advisorSearch}
                onChange={(e) => setAdvisorSearch(e.target.value)}
                className="text-xs border-neutral-200 rounded-md pl-9 pr-4 py-2 w-full bg-white shadow-sm focus:ring-1 focus:ring-brand-500"
              />
            </div>

            {loadingAdvisors ? (
              <div className="text-center py-6 text-xs text-neutral-400">Loading advisors...</div>
            ) : filteredAdvisors.length === 0 ? (
              <div className="text-center py-6 text-xs text-neutral-400">No active advisors found</div>
            ) : (
              <div className="max-h-48 overflow-y-auto border border-neutral-200 rounded-md divide-y divide-neutral-100 bg-white">
                {filteredAdvisors.map((adv) => (
                  <div
                    key={adv.id}
                    onClick={() => setAdvisorId(adv.id)}
                    className={`p-3 text-xs flex items-center justify-between cursor-pointer transition-colors ${
                      advisorId === adv.id ? 'bg-brand-50 text-brand-700 font-semibold' : 'hover:bg-neutral-50 text-neutral-700'
                    }`}
                  >
                    <div>
                      <p className="font-semibold text-neutral-900">{adv.name}</p>
                      <p className="text-[10px] text-neutral-400 mt-0.5">{adv.email} • {adv.team_name}</p>
                    </div>
                    {advisorId === adv.id && <CheckCircle2 className="w-4 h-4 text-brand-600" />}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={() => setStep(2)}
              disabled={!advisorId}
              className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors shadow-sm"
            >
              Continue to Upload
            </button>
          </div>
        </div>
      )}

      {/* STEP 2: UPLOAD RECORDING */}
      {step === 2 && (
        <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm space-y-6">
          <div className="flex items-center gap-2 font-semibold text-sm text-neutral-900 border-b border-neutral-100 pb-3">
            <FileAudio className="w-5 h-5 text-brand-600" />
            <span>Select Call Audio Recording</span>
          </div>

          {selectedAdvisor && (
            <div className="bg-neutral-50 p-4 rounded-md border border-neutral-100 text-xs flex items-center justify-between">
              <div>
                <p className="text-[10px] uppercase font-bold text-neutral-400">Assigned Advisor</p>
                <p className="font-semibold text-neutral-800 mt-0.5">{selectedAdvisor.name} ({selectedAdvisor.team_name})</p>
              </div>
              <button
                onClick={() => setStep(1)}
                disabled={uploadMutation.isPending}
                className="text-xs font-semibold text-brand-600 hover:text-brand-700 disabled:opacity-50 hover:underline"
              >
                Change Metadata
              </button>
            </div>
          )}

          {!audioFile ? (
            <div className="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center flex flex-col items-center justify-center space-y-3 hover:border-brand-500 transition-colors bg-neutral-50 cursor-pointer relative">
              <input
                type="file"
                accept=".wav,.mp3,.m4a"
                onChange={handleFileChange}
                disabled={uploadMutation.isPending}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="p-3 bg-white border border-neutral-200 rounded-full shadow-sm text-neutral-400">
                <Upload className="w-6 h-6" />
              </div>
              <div>
                <p className="text-xs font-bold text-neutral-700">Drag your audio file here, or click to browse</p>
                <p className="text-[10px] text-neutral-400 mt-1">Supports wav, mp3, m4a up to 50 MB</p>
              </div>
            </div>
          ) : (
            <div className="border border-neutral-200 rounded-lg p-4 bg-neutral-50 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 bg-brand-50 rounded-lg text-brand-600">
                  <FileCheck className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <p className="font-semibold text-neutral-900 truncate">{audioFile.name}</p>
                  <p className="text-[10px] text-neutral-400 mt-0.5">
                    {formatFileSize(audioFile.size)} • {audioFile.name.substring(audioFile.name.lastIndexOf('.')).toUpperCase()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setAudioFile(null)}
                disabled={uploadMutation.isPending}
                className="p-1 rounded-full text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 disabled:opacity-50"
                title="Remove file"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {validationError && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{validationError}</span>
            </div>
          )}

          <div className="flex items-center justify-between pt-2 border-t border-neutral-100">
            <button
              onClick={() => setStep(1)}
              disabled={uploadMutation.isPending}
              className="px-4 py-2 text-xs font-semibold text-neutral-700 hover:text-neutral-900 bg-white border border-neutral-200 rounded-md disabled:opacity-50 transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleUploadSubmit}
              disabled={!audioFile || uploadMutation.isPending}
              className="px-5 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              {uploadMutation.isPending ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Ingesting Audio...</>
              ) : (
                'Upload and Ingest Call'
              )}
            </button>
          </div>
        </div>
      )}

      {/* STEP 3: PIPELINE */}
      {step === 3 && callId && (
        <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-neutral-100 pb-3">
            <div className="flex items-center gap-2 font-semibold text-sm text-neutral-900">
              <Play className="w-5 h-5 text-brand-600" />
              <span>Pipeline Stage Execution</span>
            </div>
            <span className="text-[10px] text-neutral-400 font-bold font-mono">
              CALL ID: {callId.substring(0, 8)}
            </span>
          </div>

          {/* ── Idle: trigger button ── */}
          {pipelineUIState === 'idle' && (
            <div className="text-center py-8 space-y-4">
              <div className="p-4 bg-brand-50 rounded-full w-14 h-14 flex items-center justify-center text-brand-600 mx-auto border border-brand-200 shadow-inner">
                <Play className="w-6 h-6 fill-brand-600" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-sm font-semibold text-neutral-900">Ingestion Succeeded</h3>
                <p className="text-xs text-neutral-500">
                  Audio call uploaded. Ready to enter the AI analysis pipeline.
                </p>
              </div>
              {startError && (
                <div className="bg-red-50 text-red-700 border border-red-200 rounded-md p-3 text-xs flex items-start gap-2 max-w-md mx-auto">
                  <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                  <span>{startError}</span>
                </div>
              )}
              <button
                onClick={handleRunPipeline}
                className="px-6 py-2.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors shadow-sm"
              >
                Run AI Pipeline
              </button>
            </div>
          )}

          {/* ── Starting spinner ── */}
          {pipelineUIState === 'starting' && (
            <div className="text-center py-8 space-y-3">
              <Loader2 className="w-8 h-8 text-brand-600 animate-spin mx-auto" />
              <p className="text-xs text-neutral-500">Initiating pipeline…</p>
            </div>
          )}

          {/* ── Polling / Completed / Failed ── */}
          {(pipelineUIState === 'polling' || pipelineUIState === 'completed' || pipelineUIState === 'failed') && (
            <div className="space-y-5">

              {/* ── "Safe to leave" banner (only while polling) ── */}
              {pipelineUIState === 'polling' && (
                <div className="bg-brand-50 border border-brand-200 rounded-lg px-4 py-3 text-xs text-brand-700 flex items-center gap-2">
                  <Wifi className="w-4 h-4 shrink-0" />
                  <span>
                    Analysis in progress — you can safely leave this page. Processing continues on the server.
                  </span>
                </div>
              )}

              {/* ── Soft status-unavailable notice (never red, never says "failed") ── */}
              {connectionLost && pipelineUIState === 'polling' && (
                <div className="bg-neutral-100 border border-neutral-300 rounded-lg px-4 py-3 text-xs text-neutral-600 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 shrink-0 animate-spin text-neutral-400" />
                  <span>
                    Live status temporarily unavailable. Analysis is still processing on the server.
                  </span>
                </div>
              )}

              {/* ── Overall status bar ── */}
              <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4 text-xs flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {pipelineUIState === 'polling' && <Loader2 className="w-4 h-4 text-brand-600 animate-spin" />}
                  {pipelineUIState === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                  {pipelineUIState === 'failed' && <AlertCircle className="w-4 h-4 text-red-500" />}
                  <span className="font-semibold text-neutral-800">{overallStatusLabel()}</span>
                </div>
                {pipelineUIState === 'completed' && <StatusBadge status="Completed" />}
              </div>

              {/* ── Per-stage list ── */}
              <div className="border border-neutral-100 rounded-lg overflow-hidden divide-y divide-neutral-100">
                {displayStages.map((st, idx) => (
                  <div
                    key={idx}
                    className={`p-4 flex items-center justify-between text-xs transition-colors ${
                      st.status === 'Processing' ? 'bg-brand-50' :
                      st.status === 'Completed'  ? 'bg-white' :
                      st.status === 'Failed'     ? 'bg-red-50' :
                      'bg-white'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {stageIcon(st.status)}
                      <span className={`font-medium ${stageLabelClass(st.status)}`}>{st.stage}</span>
                    </div>
                    <div className="flex flex-col items-end gap-0.5">
                      {stageBadge(st)}
                      {st.status === 'Failed' && st.error && (
                        <span className="text-[10px] text-red-500 max-w-[220px] text-right truncate" title={st.error}>
                          {st.error}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* ── Success outcome ── */}
              {pipelineUIState === 'completed' && pipelineStatus && (
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-5 text-xs grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div>
                    <p className="text-[10px] text-emerald-600 uppercase font-bold">Overall score</p>
                    <div className="flex items-center gap-1.5 mt-1">
                      <ScoreBadge score={pipelineStatus.overall_score} size="md" />
                    </div>
                  </div>
                  <div>
                    <p className="text-[10px] text-emerald-600 uppercase font-bold">Detected issues</p>
                    <p className="text-sm font-semibold text-neutral-800 mt-1.5">
                      {pipelineStatus.issue_tags_count ?? 0} Compliance Issues
                    </p>
                  </div>
                  <div className="flex items-center sm:justify-end">
                    <button
                      onClick={() => navigate(`/calls/${callId}`)}
                      className="px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors flex items-center gap-1"
                    >
                      <Layout className="w-3.5 h-3.5" />
                      Open Call Review <ExternalLink className="w-3 h-3 shrink-0" />
                    </button>
                  </div>
                </div>
              )}

              {/* ── Failure outcome ── */}
              {pipelineUIState === 'failed' && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-5 text-xs space-y-4">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-neutral-900">A pipeline stage failed</p>
                      <p className="text-neutral-500 mt-0.5">
                        {pipelineStatus?.error_message || 'Check the stage list above for details.'}
                      </p>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 border-t border-red-100 pt-3">
                    <button
                      onClick={() => { setPipelineUIState('idle'); setStep(2); }}
                      className="px-3.5 py-1.5 border border-neutral-200 rounded text-neutral-700 bg-white text-xs font-semibold hover:bg-neutral-50"
                    >
                      Upload Another
                    </button>
                    <button
                      onClick={handleRunPipeline}
                      className="px-4 py-1.5 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded flex items-center gap-1"
                    >
                      <RefreshCw className="w-3 h-3" /> Retry Pipeline
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
