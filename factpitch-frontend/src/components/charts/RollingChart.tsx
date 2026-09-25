import type { RollingPoint } from '../../types/api';

interface RollingChartProps {
  series: RollingPoint[];
  pivotDate: string;
}

const WIDTH = 480;
const HEIGHT = 200;
const PADDING = { top: 20, right: 20, bottom: 24, left: 34 };

export function RollingChart({ series, pivotDate }: RollingChartProps) {
  if (series.length === 0) return null;

  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;

  const xFor = (index: number) =>
    series.length === 1 ? PADDING.left : PADDING.left + (index / (series.length - 1)) * plotWidth;
  const yFor = (value: number) => PADDING.top + (1 - value / 100) * plotHeight;

  const points = series.map((p, i) => `${xFor(i)},${yFor(p.rolling_win_rate)}`).join(' ');

  // Locate the pivot on the x-axis: the first point on/after the pivot
  // date, or the end of the series if the pivot is after every match.
  const pivotIndex = series.findIndex((p) => p.date >= pivotDate);
  const pivotX = xFor(pivotIndex === -1 ? series.length - 1 : pivotIndex);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Rolling win rate over time, ${series.length} matches, pivot date ${pivotDate}`}
      style={{ width: '100%', height: 'auto' }}
    >
      {[0, 25, 50, 75, 100].map((tick) => (
        <g key={tick}>
          <line
            x1={PADDING.left}
            y1={yFor(tick)}
            x2={WIDTH - PADDING.right}
            y2={yFor(tick)}
            stroke="var(--panel-border)"
            strokeWidth={0.5}
          />
          <text x={PADDING.left - 6} y={yFor(tick) + 3} textAnchor="end" fontSize={9} fill="var(--ink-muted)">
            {tick}
          </text>
        </g>
      ))}

      <line
        x1={pivotX}
        y1={PADDING.top}
        x2={pivotX}
        y2={HEIGHT - PADDING.bottom}
        stroke="var(--ink-muted)"
        strokeWidth={1.5}
        strokeDasharray="4 3"
      />
      <text x={pivotX} y={PADDING.top - 6} textAnchor="middle" fontSize={9} fill="var(--ink-muted)" className="mono">
        {pivotDate}
      </text>

      <polyline points={points} fill="none" stroke="var(--stamp)" strokeWidth={2} />
      {series.map((p, i) => (
        <circle key={p.date + i} cx={xFor(i)} cy={yFor(p.rolling_win_rate)} r={3} fill="var(--stamp)">
          <title>{`${p.date} vs ${p.opponent} (${p.result}) — ${p.rolling_win_rate}%`}</title>
        </circle>
      ))}
    </svg>
  );
}
