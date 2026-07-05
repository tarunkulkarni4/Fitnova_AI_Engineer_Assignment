/**
 * Format score (0-100) safely.
 */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '--';
  return `${Math.round(score)}`;
}

/**
 * Format duration in seconds (e.g. 125 -> 2:05).
 */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format timestamp in seconds (e.g. 12.5 -> 0:12).
 */
export function formatTimestamp(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Format datetime strings into human-readable local dates.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '--';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Helper to fall back category snake_case to Title Case.
 */
export function formatCategoryLabel(category: string | null | undefined): string {
  if (!category) return '--';
  return category
    .toLowerCase()
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Human-friendly labels for ProcessingStatus enums.
 */
export function formatProcessingStatus(status: string | null | undefined): string {
  if (!status) return 'Unknown';
  const mapping: Record<string, string> = {
    Uploaded: 'Uploaded',
    Processing: 'Processing',
    Ready_For_Transcription: 'Ready for Transcription',
    Ready_For_Diarization: 'Ready for Diarization',
    Ready_For_Transcript_Merge: 'Ready for Transcript Merge',
    Ready_For_PII_Redaction: 'Ready for PII Redaction',
    Ready_For_AI_Analysis: 'Ready for AI Analysis',
    Completed: 'Completed',
    Failed: 'Failed',
    Cancelled: 'Cancelled',
  };
  // Handle case differences or raw enums
  const normalized = status.replace(/\s+/g, '_');
  return mapping[normalized] || mapping[status] || status;
}
