import type { AnalysisStats, SplitStats } from '../types/api';
import { RollingChart } from './RollingChart';

// Backend sends win_rate already as a 0-100 percentage (e.g. 33.3, not
// 0.333) — same scale as rolling_win_rate in RollingChart.
function formatRate(rate: number | undefined): string {
  return rate === undefined ? '—' : `${Math.round(rate)}%`;
}

function formatAvg(value: number | undefined): string {
  return value === undefined ? '—' : value.toFixed(2);
}

function formatRecord(split: SplitStats): string {
  if (split.wins === undefined || split.draws === undefined || split.losses === undefined) return '—';
  return `${split.wins}-${split.draws}-${split.losses}`;
}

interface LedgerRowProps {
  label: string;
  pre: string;
  post: string;
  delta?: string;
}

function LedgerRow({ label, pre, post, delta }: LedgerRowProps) {
  return (
    <div className="ledger-row">
      <span className="ledger-label label">{label}</span>
      <span className="mono ledger-value">{pre}</span>
      <span className="mono ledger-value">{post}</span>
      <span className={`mono ledger-delta${delta && delta.startsWith('-') ? ' negative' : ''}`}>{delta ?? ''}</span>
    </div>
  );
}

/** Signed win-rate delta, e.g. "+12pp" / "-4pp" (percentage points). Blank
 * when either side is missing games to compare. */
function winRateDelta(pre: SplitStats, post: SplitStats): string | undefined {
  if (pre.win_rate === undefined || post.win_rate === undefined) return undefined;
  const diff = Math.round(post.win_rate - pre.win_rate);
  return diff === 0 ? '±0pp' : `${diff > 0 ? '+' : ''}${diff}pp`;
}

interface PerformanceRecordProps {
  stats: AnalysisStats | null;
}

/** The pre/post split of the performance record either side of the pivot
 * date the news research identified — laid out like a two-column ledger. */
export function PerformanceRecord({ stats }: PerformanceRecordProps) {
  if (!stats) {
    return (
      <section className="results-section" aria-labelledby="performance-record-title">
        <div className="label">Case data</div>
        <h2 id="performance-record-title" className="display results-section-title">
          Performance record
        </h2>
        <p className="exhibit-opener-intro">No match data was available to compare for this subject.</p>
      </section>
    );
  }

  const { pre, post } = stats;

  return (
    <section className="results-section" aria-labelledby="performance-record-title">
      <div className="label">Case data</div>
      <h2 id="performance-record-title" className="display results-section-title">
        Performance record
      </h2>
      <p className="exhibit-opener-intro">
        Split at <span className="mono">{stats.pivot_date}</span> — the date the news exhibits point to.
      </p>

      {stats.error ? (
        <p className="investigation-log-error">{stats.error}</p>
      ) : (
        <div className="ledger">
          <div className="ledger-row ledger-header">
            <span className="ledger-label label">&nbsp;</span>
            <span className="mono ledger-value label">Before</span>
            <span className="mono ledger-value label">After</span>
            <span className="mono ledger-delta label">Change</span>
          </div>
          <LedgerRow label="Matches" pre={String(pre.matches)} post={String(post.matches)} />
          <LedgerRow label="Record (W-D-L)" pre={formatRecord(pre)} post={formatRecord(post)} />
          <LedgerRow
            label="Win rate"
            pre={formatRate(pre.win_rate)}
            post={formatRate(post.win_rate)}
            delta={winRateDelta(pre, post)}
          />
          <LedgerRow label="Avg goals for" pre={formatAvg(pre.avg_goals_for)} post={formatAvg(post.avg_goals_for)} />
          <LedgerRow
            label="Avg goals against"
            pre={formatAvg(pre.avg_goals_against)}
            post={formatAvg(post.avg_goals_against)}
          />
          {(pre.avg_opponent_position !== undefined || post.avg_opponent_position !== undefined) && (
            <LedgerRow
              label="Avg opponent position"
              pre={pre.avg_opponent_position !== undefined ? pre.avg_opponent_position.toFixed(1) : '—'}
              post={post.avg_opponent_position !== undefined ? post.avg_opponent_position.toFixed(1) : '—'}
            />
          )}
        </div>
      )}

      {(pre.opponent_position_note || post.opponent_position_note) && (
        <p className="ledger-note mono">{pre.opponent_position_note ?? post.opponent_position_note}</p>
      )}

      {!stats.error && (
        <div className="rolling-chart-block">
          <div className="label" style={{ marginBottom: 8 }}>
            Rolling form
          </div>
          <RollingChart series={stats.series} pivotDate={stats.pivot_date} />
        </div>
      )}
    </section>
  );
}
