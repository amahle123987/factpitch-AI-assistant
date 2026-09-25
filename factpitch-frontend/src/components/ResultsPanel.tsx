import { Tabs } from './Tabs';
import { ResultsBarChart } from './charts/ResultsBarChart';
import { RollingChart } from './charts/RollingChart';
import type { AnalyzeResult, SplitStats } from '../types/api';

function SplitCard({ label, stats, delta }: { label: string; stats: SplitStats; delta?: number }) {
  const deltaColor = delta === undefined ? undefined : delta > 0 ? 'var(--win)' : delta < 0 ? 'var(--loss)' : 'var(--text-muted)';
  const arrow = delta === undefined ? '' : delta > 0 ? '▲' : delta < 0 ? '▼' : '—';

  return (
    <div className="card" style={{ flex: 1 }}>
      <div className="eyebrow">{label}</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 2 }}>
        Win rate{' '}
        {delta !== undefined && (
          <span style={{ color: deltaColor }}>
            {arrow} {Math.abs(delta)}%
          </span>
        )}
      </div>
      <div className="mono" style={{ fontSize: 28, fontWeight: 600 }}>
        {stats.win_rate ?? 0}%
      </div>
      <div className="mono" style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>
        {stats.wins ?? 0}W {stats.draws ?? 0}D {stats.losses ?? 0}L &nbsp;·&nbsp; {stats.avg_goals_for ?? '—'} GF /{' '}
        {stats.avg_goals_against ?? '—'} GA
      </div>
    </div>
  );
}

export function ResultsPanel({ result }: { result: AnalyzeResult }) {
  const { news, stats, verdict } = result;
  const primaryHeadline = news.primary_event?.headline;
  const hasValidStats = Boolean(stats && !stats.error);
  const winRateDelta =
    hasValidStats && stats ? Math.round(((stats.post.win_rate ?? 0) - (stats.pre.win_rate ?? 0)) * 10) / 10 : undefined;

  const overviewTab = (
    <div>
      <div className="eyebrow">Verdict</div>
      <div className="card" style={{ marginBottom: 20 }}>
        <p style={{ fontStyle: 'italic', margin: 0, lineHeight: 1.55 }}>{verdict}</p>
      </div>

      {news.primary_event && (
        <>
          <div className="eyebrow">Pivot Event</div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {news.primary_event.date}
            </div>
            <div style={{ fontSize: 16, margin: '4px 0' }}>{news.primary_event.headline}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{news.primary_event.reason}</div>
          </div>
        </>
      )}

      {hasValidStats && stats && (
        <>
          <div className="eyebrow">At a Glance</div>
          <div style={{ display: 'flex', gap: 12 }}>
            <SplitCard label="Before" stats={stats.pre} />
            <SplitCard label="After" stats={stats.post} delta={winRateDelta} />
          </div>
        </>
      )}
    </div>
  );

  const trendsTab = (
    <div>
      {!hasValidStats && (
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          {stats?.error ?? 'No performance data to show — see the News & Timeline tab for what was found.'}
        </p>
      )}

      {hasValidStats && stats && (
        <>
          {stats.series.length > 0 && (
            <>
              <div className="eyebrow">Form Over Time</div>
              <div className="card" style={{ marginBottom: 20 }}>
                <RollingChart series={stats.series} pivotDate={stats.pivot_date} />
                <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '8px 0 0 0' }}>
                  Rolling win rate over a trailing 5-match window. Dashed line marks the pivot date.
                </p>
              </div>
            </>
          )}

          <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
            <SplitCard label="Before" stats={stats.pre} />
            <SplitCard label="After" stats={stats.post} delta={winRateDelta} />
          </div>

          <div className="card" style={{ marginBottom: 12 }}>
            <ResultsBarChart pre={stats.pre as never} post={stats.post as never} />
          </div>

          {stats.pre.avg_opponent_position !== undefined && stats.post.avg_opponent_position !== undefined && (
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              Avg opponent league position — before: <strong>{stats.pre.avg_opponent_position}</strong>, after:{' '}
              <strong>{stats.post.avg_opponent_position}</strong> (lower number = tougher opponent; based on{' '}
              <strong>current</strong> standings, not standings at the time each match was played)
            </p>
          )}
        </>
      )}
    </div>
  );

  const newsTab = (
    <div>
      <p style={{ fontSize: 14, marginTop: 0 }}>{news.summary}</p>
      {news.key_events.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No dated events found for this query.</p>
      )}
      {news.key_events.map((event, i) => {
        const isPrimary = event.headline === primaryHeadline;
        return (
          <div
            key={i}
            className="card"
            style={{ marginBottom: 10, borderColor: isPrimary ? 'var(--accent)' : 'var(--panel-border)' }}
          >
            <div style={{ display: 'flex', gap: 10 }}>
              <span style={{ color: isPrimary ? 'var(--accent)' : 'var(--panel-border)', fontSize: 16 }}>
                {isPrimary ? '★' : '●'}
              </span>
              <div>
                <div className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {event.date}
                </div>
                <div style={{ fontSize: 14 }}>{event.headline}</div>
                {event.detail && (
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>{event.detail}</div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <Tabs
      tabs={[
        { id: 'overview', label: 'Overview', content: overviewTab },
        { id: 'trends', label: 'Performance Trends', content: trendsTab },
        { id: 'news', label: 'News & Timeline', content: newsTab },
      ]}
    />
  );
}
