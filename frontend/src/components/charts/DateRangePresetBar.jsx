import { PRESET_LABELS } from '../../utils/dateRangePresets';
import './Charts.css';

const KEYS = ['last30', 'month', 'year'];

/**
 * @param {object} props
 * @param {string | null} props.activeKey — 'last30' | 'month' | 'year' | null si el usuario editó fechas a mano
 * @param {(key: string) => void} props.onSelect
 */
export default function DateRangePresetBar({ activeKey, onSelect }) {
  return (
    <div className="sgf-presets">
      <span className="sgf-presets-label">Rápido:</span>
      {KEYS.map((k) => (
        <button
          key={k}
          type="button"
          className={`sgf-preset-btn ${activeKey === k ? 'active' : ''}`}
          onClick={() => onSelect(k)}
        >
          {PRESET_LABELS[k]}
        </button>
      ))}
    </div>
  );
}
