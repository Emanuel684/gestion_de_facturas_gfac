/** @returns {{ dateFrom: string, dateTo: string }} valores para input type="date" (YYYY-MM-DD) */

function toYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export const PRESET_LABELS = {
  none: 'Personalizado',
  last30: 'Últimos 30 días',
  month: 'Este mes',
  year: 'Este año',
};

export function getDateRangePreset(presetKey) {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate());

  if (presetKey === 'last30') {
    const start = new Date(end);
    start.setDate(start.getDate() - 29);
    return { dateFrom: toYMD(start), dateTo: toYMD(end) };
  }
  if (presetKey === 'month') {
    const start = new Date(end.getFullYear(), end.getMonth(), 1);
    return { dateFrom: toYMD(start), dateTo: toYMD(end) };
  }
  if (presetKey === 'year') {
    const start = new Date(end.getFullYear(), 0, 1);
    return { dateFrom: toYMD(start), dateTo: toYMD(end) };
  }
  return { dateFrom: '', dateTo: '' };
}
