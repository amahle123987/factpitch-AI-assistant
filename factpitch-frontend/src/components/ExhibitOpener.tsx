import { useState } from 'react';
import { useAnalysis } from '../hooks/useAnalysis';
import { StatusBox } from './StatusBox';
import { NewsExhibits } from './NewsExhibits';
import { PerformanceRecord } from './PerformanceRecord';
import type { TeamSelection } from '../types/api';

interface ExhibitOpenerProps { selection: TeamSelection | null; windowDays: number; }

/** Opens a new research exhibit and records the streaming investigation log. */
export function ExhibitOpener({ selection, windowDays }: ExhibitOpenerProps) {
  const [query, setQuery] = useState('');
  const { status, progressStages, result, errorMessage, run } = useAnalysis();
  const ready = Boolean(selection && query.trim());

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selection || !query.trim() || status === 'running') return;
    run(selection, query.trim(), windowDays);
  }

  return (
    <section className="exhibit-opener" aria-labelledby="exhibit-opener-title">
      <div className="label">Exhibit request</div>
      <h2 id="exhibit-opener-title" className="display">Open a new exhibit</h2>
      <p className="exhibit-opener-intro">Put a claim on the record. We will trace the news and compare it against the form book.</p>
      <form onSubmit={submit}>
        <label htmlFor="analysis-query" className="label">Question for the record</label>
        <textarea id="analysis-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. How has the manager change affected recent results?" disabled={!selection || status === 'running'} aria-describedby="exhibit-guidance" rows={3} />
        <div className="exhibit-action-row">
          <p id="exhibit-guidance" className="mono">{selection ? `Subject: ${selection.teamName}; ${windowDays}-day comparison window` : 'Choose a subject above before opening an exhibit.'}</p>
          <button className="open-exhibit-button" type="submit" disabled={!ready || status === 'running'}>{status === 'running' ? 'Opening exhibit...' : 'Open exhibit'}</button>
        </div>
      </form>
      <StatusBox status={status} stages={progressStages} errorMessage={errorMessage} />

      {status === 'done' && result && (
        <div className="results-file">
          <NewsExhibits news={result.news} verdict={result.verdict} />
          <PerformanceRecord stats={result.stats} />
        </div>
      )}
    </section>
  );
}
