export const SCORE_DIMENSIONS = [
  { key: 'rapport', label: 'Rapport' },
  { key: 'needs_discovery', label: 'Needs Discovery' },
  { key: 'product_knowledge', label: 'Product Knowledge' },
  { key: 'objection_handling', label: 'Objection Handling' },
  { key: 'compliance', label: 'Compliance' },
  { key: 'trial_booking', label: 'Trial Booking' },
  { key: 'closing', label: 'Closing' }
] as const;

export type DimensionKey = typeof SCORE_DIMENSIONS[number]['key'];

export const DIMENSION_LABELS: Record<string, string> = {
  rapport: 'Rapport',
  needs_discovery: 'Needs Discovery',
  product_knowledge: 'Product Knowledge',
  objection_handling: 'Objection Handling',
  compliance: 'Compliance',
  trial_booking: 'Trial Booking',
  closing: 'Closing',
  overall: 'Overall Quality'
};
