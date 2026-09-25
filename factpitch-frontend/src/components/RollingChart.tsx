import type { RollingPoint } from '../types/api';

const WIDTH = 680;
const HEIGHT = 220;
const PAD_LEFT = 40;
const PAD_RIGHT = 16;
const PAD_TOP = 16;
const PAD_BOTTOM = 30;
const MARKER_SIZE = 4;

const RESULT_COLOR: Record<RollingPoint['result'], string> = {
  W: 'var(--win)',
  D: 'var(--draw)',
  L: 'var(--loss)',
};

function xFor(index: number, count: number): number {
  const innerWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  if (count <= 1) return PAD_LEFT + innerWidth / 2;
  return PAD_LEFT + (innerWidth * index) / (count - 1);
}

// rolling_win_rate arrives as a 0-100 percentage (same scale as
// SplitStats.win_rate), not a 0-1 fraction.
function yFor(rate: number): number {
  const innerHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  return PAD_TOP + innerHeight * (1 - rate / 100);
}

/** Index of the first point on or after the pivot date, used to place the
 * pivot marker between two plotted points rather than on a specific one. */
function pivotIndex(series: RollingPoint[], pivotDate: string): number | null {
  const idx = series.findIndex((p) => p.date >= pivotDate);
  if (idx <= 0) return null;
  return idx;
}

interface MarkerProps {
  result: RollingPoint['result'];
  x: number;
  y: number;
  size?: number;
}

/** A win/draw/loss result is never conveyed by color alone here — each gets
 * its own shape (circle / diamond / triangle) so the chart still reads for
 * colorblind viewers, not just via the <title> tooltip. */
function Marker({ result, x, y, size = MARKER_SIZE }: MarkerProps) {
  const fill = RESULT_COLOR[result];
  const stroke = 'var(--panel)';
  if (result === 'W') {
    return <circle cx={x} cy={y} r={size} fill={fill} stroke={stroke} strokeWidth={1} />;
  }
  if (result === 'D') {
    const points = [
      [x, y - size * 1.15],
      [x + size * 1.15, y],
      [x, y + size * 1.15],
      [x - size * 1.15, y],
    ]
      .map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`)
      .join(' ');
    return <polygon points={points} fill={fill} stroke={stroke} strokeWidth={1} />;
  }
  const points = [
    [x, y - size * 1.25],
    [x + size * 1.15, y + size * 0.85],
    [x - size * 1.15, y + size * 0.85],
  ]
    .map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`)
    .join(' ');
  return <polygon points={points} fill={fill} stroke={stroke} strokeWidth={1} />;
}

interface RollingChartProps {
  series: RollingPoint[];
  pivotDate: string;
}

/** A case-file take on a rolling-form line chart: the win-rate trend as a
 * single ink line, each match plotted as a shaped, W/D/L-colored marker,
 * with a dashed "pivot" rule marking the date the news exhibits point to. */
export function RollingChart({ series, pivotDate }: RollingChartProps) {
  if (series.length === 0) {
    return <p className="exhibit-opener-intro">No rolling form data to chart for this window.</p>;
  }

  const linePath = series
    .map((point, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i, series.length).toFixed(1)} ${yFor(point.rolling_win_rate).toFixed(1)}`)
    .join(' ');

  const pivotIdx = pivotIndex(series, pivotDate);
  const pivotX = pivotIdx !== null ? (xFor(pivotIdx - 1, series.length) + xFor(pivotIdx, series.length)) / 2 : null;

  return (
    <div className="rolling-chart">
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Rolling win rate over the investigation window">
        {[0, 50, 100].map((tick) => (
          <g key={tick}>
            <line
              x1={PAD_LEFT}
              x2={WIDTH - PAD_RIGHT}
              y1={yFor(tick)}
              y2={yFor(tick)}
              stroke="var(--panel-border)"
              strokeWidth={1}
              strokeDasharray={tick === 0 ? undefined : '2 3'}
            />
            <text x={PAD_LEFT - 8} y={yFor(tick) + 4} textAnchor="end" className="chart-axis-label">
              {tick}%
            </text>
          </g>
        ))}

        {pivotX !== null && (
          <>
            <line x1={pivotX} x2={pivotX} y1={PAD_TOP} y2={HEIGHT - PAD_BOTTOM} stroke="var(--stamp)" strokeWidth={1.5} strokeDasharray="4 3" />
            <text x={pivotX} y={PAD_TOP - 4} textAnchor="middle" className="chart-axis-label" fill="var(--stamp)">
              Pivot
            </text>
          </>
        )}

        <path d={linePath} fill="none" stroke="var(--ink)" strokeWidth={1.5} />

        {series.map((point, i) => (
          <g key={`${point.date}-${i}`}>
            <Marker result={point.result} x={xFor(i, series.length)} y={yFor(point.rolling_win_rate)} />
            <title>
              {point.date} vs {point.opponent} — {point.result} · {Math.round(point.rolling_win_rate)}% rolling
            </title>
          </g>
        ))}
      </svg>

      <div className="chart-legend">
        <span className="chart-legend-item">
          <svg className="chart-legend-icon" viewBox="0 0 10 10" aria-hidden="true">
            <circle cx="5" cy="5" r="4" fill="var(--win)" />
          </svg>
          Win
        </span>
        <span className="chart-legend-item">
          <svg className="chart-legend-icon" viewBox="0 0 10 10" aria-hidden="true">
            <polygon points="5,0.5 9.5,5 5,9.5 0.5,5" fill="var(--draw)" />
          </svg>
          Draw
        </span>
        <span className="chart-legend-item">
          <svg className="chart-legend-icon" viewBox="0 0 10 10" aria-hidden="true">
            <polygon points="5,0.5 9.5,9 0.5,9" fill="var(--loss)" />
          </svg>
          Loss
        </span>
      </div>
    </div>
  );
}
