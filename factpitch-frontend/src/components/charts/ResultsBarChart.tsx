interface ResultsBarChartProps {
  pre: { wins: number; draws: number; losses: number };
  post: { wins: number; draws: number; losses: number };
}

const WIDTH = 480;
const HEIGHT = 220;
const PADDING = { top: 30, right: 20, bottom: 30, left: 30 };
const CATEGORIES: { key: 'wins' | 'draws' | 'losses'; label: string; color: string }[] = [
  { key: 'wins', label: 'Wins', color: 'var(--win)' },
  { key: 'draws', label: 'Draws', color: 'var(--draw)' },
  { key: 'losses', label: 'Losses', color: 'var(--loss)' },
];

export function ResultsBarChart({ pre, post }: ResultsBarChartProps) {
  const max = Math.max(1, pre.wins, pre.draws, pre.losses, post.wins, post.draws, post.losses);
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;
  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const groupWidth = plotWidth / CATEGORIES.length;
  const barWidth = groupWidth * 0.32;

  function barHeight(value: number) {
    return (value / max) * plotHeight;
  }

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Results before: ${pre.wins} wins, ${pre.draws} draws, ${pre.losses} losses. After: ${post.wins} wins, ${post.draws} draws, ${post.losses} losses.`}
      style={{ width: '100%', height: 'auto' }}
    >
      <text x={PADDING.left} y={16} className="eyebrow" fill="var(--ink-muted)" fontSize={10}>
        BEFORE
      </text>
      <text x={WIDTH - PADDING.right} y={16} textAnchor="end" className="eyebrow" fill="var(--stamp)" fontSize={10}>
        AFTER
      </text>

      {CATEGORIES.map((cat, i) => {
        const groupX = PADDING.left + i * groupWidth;
        const preH = barHeight(pre[cat.key]);
        const postH = barHeight(post[cat.key]);
        const baseline = HEIGHT - PADDING.bottom;

        return (
          <g key={cat.key}>
            <rect
              x={groupX + groupWidth * 0.15}
              y={baseline - preH}
              width={barWidth}
              height={preH}
              fill={cat.color}
              opacity={0.55}
            />
            {pre[cat.key] > 0 && (
              <text
                x={groupX + groupWidth * 0.15 + barWidth / 2}
                y={baseline - preH - 6}
                textAnchor="middle"
                className="mono"
                fontSize={11}
                fill="var(--ink)"
              >
                {pre[cat.key]}
              </text>
            )}

            <rect
              x={groupX + groupWidth * 0.53}
              y={baseline - postH}
              width={barWidth}
              height={postH}
              fill={cat.color}
            />
            {post[cat.key] > 0 && (
              <text
                x={groupX + groupWidth * 0.53 + barWidth / 2}
                y={baseline - postH - 6}
                textAnchor="middle"
                className="mono"
                fontSize={11}
                fill="var(--ink)"
              >
                {post[cat.key]}
              </text>
            )}

            <text
              x={groupX + groupWidth / 2}
              y={baseline + 18}
              textAnchor="middle"
              fontSize={12}
              fill="var(--ink-muted)"
            >
              {cat.label}
            </text>
          </g>
        );
      })}

      <line
        x1={PADDING.left}
        y1={HEIGHT - PADDING.bottom}
        x2={WIDTH - PADDING.right}
        y2={HEIGHT - PADDING.bottom}
        stroke="var(--panel-border)"
      />
    </svg>
  );
}
