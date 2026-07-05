export function shouldDisplayInSimulator(status?: string | null): boolean {
  const normalized = (status || '').trim().toLowerCase();

  if (!normalized) {
    return false;
  }

  const activeStatuses = new Set([
    'uploaded',
    'queued',
    'processing',
    'ready for transcription',
    'ready for diarization',
    'ready for transcript merge',
    'ready for pii redaction',
    'ready for ai analysis',
  ]);

  return activeStatuses.has(normalized) || normalized === 'failed';
}

export function getNextExternalCallId(existingIds: Array<string | null | undefined>): string {
  const numericSuffixes = existingIds.reduce<number[]>((acc, value) => {
    if (typeof value !== 'string') {
      return acc;
    }

    const match = value.trim().match(/^call-(\d+)$/i);
    if (!match) {
      return acc;
    }

    const parsed = Number.parseInt(match[1], 10);
    if (!Number.isNaN(parsed)) {
      acc.push(parsed);
    }

    return acc;
  }, []);

  const highest = numericSuffixes.length > 0 ? Math.max(...numericSuffixes) : 0;
  const nextValue = highest + 1;
  const width = Math.max(3, String(nextValue).length);

  return `CALL-${String(nextValue).padStart(width, '0')}`;
}
