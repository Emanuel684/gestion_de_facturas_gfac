import { useTranslation } from 'react-i18next';
import './Charts.css';

const KEYS = ['last30', 'month', 'year'];

/**
 * @param {object} props
 * @param {string | null} props.activeKey — 'last30' | 'month' | 'year' | null si el usuario editó fechas a mano
 * @param {(key: string) => void} props.onSelect
 */
export default function DateRangePresetBar({ activeKey, onSelect }) {
  const { t } = useTranslation(['dashboard']);
  const presetLabels = {
    last30: t('dashboard:last30', { defaultValue: 'Últimos 30 días' }),
    month: t('dashboard:thisMonth', { defaultValue: 'Este mes' }),
    year: t('dashboard:thisYear', { defaultValue: 'Este año' }),
  };
  return (
    <div className="sgf-presets">
      <span className="sgf-presets-label">{t('dashboard:quick', { defaultValue: 'Rápido:' })}</span>
      {KEYS.map((k) => (
        <button
          key={k}
          type="button"
          className={`sgf-preset-btn ${activeKey === k ? 'active' : ''}`}
          onClick={() => onSelect(k)}
        >
          {presetLabels[k]}
        </button>
      ))}
    </div>
  );
}
