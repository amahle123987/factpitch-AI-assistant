import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ResultsPanel } from '../ResultsPanel';
import type { AnalyzeResult } from '../../types/api';

const FULL_RESULT: AnalyzeResult = {
  news: {
    query: 'q',
    key_events: [
      { date: '2025-09-20', headline: 'Early pressure mounts', detail: 'Poor run of results' },
      { date: '2025-09-27', headline: 'Manager sacked', detail: 'Club statement issued' },
    ],
    primary_event: { date: '2025-09-27', headline: 'Manager sacked', reason: 'Clean before/after pivot' },
    summary: 'A summary of the news situation.',
  },
  stats: {
    pivot_date: '2025-09-27',
    pre: { matches: 5, wins: 1, draws: 0, losses: 4, win_rate: 20.0, avg_goals_for: 1.0, avg_goals_against: 2.6 },
    post: { matches: 7, wins: 2, draws: 2, losses: 3, win_rate: 28.6, avg_goals_for: 1.43, avg_goals_against: 1.71 },
    series: [
      { date: '2025-09-01', opponent: 'Team X', result: 'L', rolling_win_rate: 0 },
      { date: '2025-09-27', opponent: 'Team Y', result: 'W', rolling_win_rate: 33.3 },
    ],
    chart_path: null,
  },
  verdict: 'The numbers show a modest improvement after the sacking.',
};

describe('ResultsPanel', () => {
  it('shows the verdict in the Overview tab by default', () => {
    render(<ResultsPanel result={FULL_RESULT} />);
    expect(screen.getByText(/modest improvement after the sacking/)).toBeInTheDocument();
  });

  it('shows the primary (pivot) event with its reasoning', () => {
    render(<ResultsPanel result={FULL_RESULT} />);
    expect(screen.getByText('Manager sacked')).toBeInTheDocument();
    expect(screen.getByText('Clean before/after pivot')).toBeInTheDocument();
  });

  it('shows win-rate-before/after on the Overview tab', () => {
    render(<ResultsPanel result={FULL_RESULT} />);
    expect(screen.getByText('20%')).toBeInTheDocument();
    expect(screen.getByText('28.6%')).toBeInTheDocument();
  });

  it('Performance Trends tab shows the chart and opponent note when present', async () => {
    const user = userEvent.setup();
    render(<ResultsPanel result={FULL_RESULT} />);

    await user.click(screen.getByRole('tab', { name: 'Performance Trends' }));

    expect(screen.getByText('Form Over Time')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Rolling win rate/ })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Results before/ })).toBeInTheDocument();
  });

  it('News & Timeline tab marks the primary event distinctly from other events', async () => {
    const user = userEvent.setup();
    render(<ResultsPanel result={FULL_RESULT} />);

    await user.click(screen.getByRole('tab', { name: 'News & Timeline' }));

    // Both events render; only the primary one shows every field twice
    // (once in Overview's Pivot Event card, once in the News tab) —
    // check the star/bullet markers distinguish them.
    const stars = screen.getAllByText('★');
    const bullets = screen.getAllByText('●');
    expect(stars.length).toBeGreaterThanOrEqual(1);
    expect(bullets.length).toBeGreaterThanOrEqual(1);
  });

  it('handles a null stats result gracefully (no usable event found)', async () => {
    const user = userEvent.setup();
    const noStatsResult: AnalyzeResult = {
      news: { query: 'q', key_events: [], primary_event: null, summary: 'Nothing specific found.' },
      stats: null,
      verdict: 'Could not find a specific dated event to analyze against.',
    };
    render(<ResultsPanel result={noStatsResult} />);

    expect(screen.getByText(/Could not find a specific dated event/)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Performance Trends' }));
    expect(screen.getByText(/No performance data to show/)).toBeInTheDocument();
  });

  it('shows an error message on the Trends tab when stats has an error', async () => {
    const user = userEvent.setup();
    const errorResult: AnalyzeResult = {
      ...FULL_RESULT,
      stats: { ...FULL_RESULT.stats!, error: 'No finished matches found in this date range.' },
    };
    render(<ResultsPanel result={errorResult} />);

    await user.click(screen.getByRole('tab', { name: 'Performance Trends' }));
    expect(screen.getByText('No finished matches found in this date range.')).toBeInTheDocument();
  });
});
