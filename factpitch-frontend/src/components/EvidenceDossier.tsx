import { ResultsBarChart } from './charts/ResultsBarChart';
import { RollingChart } from './charts/RollingChart';
import type { AnalyzeResult, SplitStats } from '../types/api';

function SplitDocket({ label, stats }: { label: string; stats: SplitStats }) {
  return (
    <section className="split-docket" aria-label={`${label} performance`}>
      <div className="label">{label}</div>
      <strong className="mono">{stats.win_rate ?? 0}%</strong>
      <span>win rate · {stats.matches} matches</span>
      <span className="mono">{stats.wins ?? 0}W · {stats.draws ?? 0}D · {stats.losses ?? 0}L</span>
      <span className="mono">{stats.avg_goals_for ?? '—'} GF / {stats.avg_goals_against ?? '—'} GA</span>
    </section>
  );
}

export function EvidenceDossier({ result }: { result: AnalyzeResult }) {
  const { news, stats, verdict } = result;
  const hasStats = Boolean(stats && !stats.error);
  const primaryHeadline = news.primary_event?.headline;

  return (
    <section className="evidence-dossier" aria-labelledby="evidence-title">
      <div className="label">Filed evidence</div>
      <h2 id="evidence-title" className="display">Results docket</h2>

      <section className="verdict-sheet" aria-labelledby="verdict-title">
        <div><div className="label">Finding</div><h3 id="verdict-title" className="display">Verdict</h3></div>
        <span className="stamp">Verified</span>
        <p>{verdict}</p>
      </section>

      <section aria-labelledby="news-exhibits-title">
        <div className="results-section-heading"><div><div className="label">News record</div><h3 id="news-exhibits-title" className="display">Numbered exhibits</h3></div><p>{news.summary}</p></div>
        {news.key_events.length === 0 ? <p className="results-empty">No dated exhibits were found for this query.</p> : (
          <ol className="news-exhibits">
            {news.key_events.map((event, index) => {
              const primary = event.headline === primaryHeadline;
              return <li key={`${event.date}-${event.headline}`} className={primary ? 'is-primary' : ''}>
                <div className="exhibit-number mono">{String(index + 1).padStart(2, '0')}</div>
                <div><div className="exhibit-date mono">{event.date}{primary ? ' · pivot event' : ''}</div><h4>{event.headline}</h4>{event.detail && <p>{event.detail}</p>}{primary && news.primary_event?.reason && <p className="pivot-reason">Why this pivot: {news.primary_event.reason}</p>}</div>
              </li>;
            })}
          </ol>
        )}
      </section>

      <section className="performance-dossier" aria-labelledby="performance-title">
        <div className="results-section-heading"><div><div className="label">Performance record</div><h3 id="performance-title" className="display">Before and after</h3></div></div>
        {!hasStats && <p className="results-empty">{stats?.error ?? 'No performance data was available for this investigation.'}</p>}
        {hasStats && stats && <>
          <div className="split-dockets"><SplitDocket label="Before pivot" stats={stats.pre} /><SplitDocket label="After pivot" stats={stats.post} /></div>
          {stats.series.length > 0 && <figure className="case-chart"><figcaption><span className="label">Exhibit A</span> Rolling win rate · dashed line marks {stats.pivot_date}</figcaption><RollingChart series={stats.series} pivotDate={stats.pivot_date} /></figure>}
          <figure className="case-chart"><figcaption><span className="label">Exhibit B</span> Result count before and after the pivot</figcaption><ResultsBarChart pre={{ wins: stats.pre.wins ?? 0, draws: stats.pre.draws ?? 0, losses: stats.pre.losses ?? 0 }} post={{ wins: stats.post.wins ?? 0, draws: stats.post.draws ?? 0, losses: stats.post.losses ?? 0 }} /></figure>
        </>}
      </section>
    </section>
  );
}
