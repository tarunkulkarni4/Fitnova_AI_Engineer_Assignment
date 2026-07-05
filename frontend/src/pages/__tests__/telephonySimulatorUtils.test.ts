import { describe, expect, it } from 'vitest';
import { getNextExternalCallId, shouldDisplayInSimulator } from '../telephonySimulatorUtils';

describe('telephony simulator utilities', () => {
  it('generates the next CALL-NNN id with zero padding and ignores unrelated ids', () => {
    expect(getNextExternalCallId(['CALL-001', 'CALL-002', 'CUSTOM-100'])).toBe('CALL-003');
    expect(getNextExternalCallId(['CALL-099', 'CALL-100'])).toBe('CALL-101');
    expect(getNextExternalCallId(['foo', 'bar'])).toBe('CALL-001');
  });

  it('only keeps live processing states visible in the simulator', () => {
    expect(shouldDisplayInSimulator('Uploaded')).toBe(true);
    expect(shouldDisplayInSimulator('Queued')).toBe(true);
    expect(shouldDisplayInSimulator('Processing')).toBe(true);
    expect(shouldDisplayInSimulator('Ready For Transcription')).toBe(true);
    expect(shouldDisplayInSimulator('Ready For PII Redaction')).toBe(true);
    expect(shouldDisplayInSimulator('Failed')).toBe(true);
    expect(shouldDisplayInSimulator('Completed')).toBe(false);
    expect(shouldDisplayInSimulator('Cancelled')).toBe(false);
  });
});
