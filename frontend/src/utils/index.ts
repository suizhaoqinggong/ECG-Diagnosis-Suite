export function formatConfidence(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}
