import { useTheme, type Theme } from '../context/ThemeContext';

const OPTIONS: { value: Theme; label: string }[] = [
  { value: 'light', label: 'Day Desk' },
  { value: 'dark', label: 'Night Archive' },
  { value: 'high-contrast', label: 'High Contrast' },
];

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <div
      role="radiogroup"
      aria-label="Color theme"
      style={{
        display: 'inline-flex',
        border: 'var(--border-width) solid var(--panel-border)',
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      {OPTIONS.map((opt) => {
        const active = theme === opt.value;
        return (
          <button
            key={opt.value}
            role="radio"
            aria-checked={active}
            onClick={() => setTheme(opt.value)}
            className="label"
            style={{
              margin: 0,
              padding: '8px 12px',
              border: 'none',
              cursor: 'pointer',
              background: active ? 'var(--stamp)' : 'var(--panel)',
              color: active ? 'var(--stamp-text)' : 'var(--ink-muted)',
              fontSize: 10,
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
