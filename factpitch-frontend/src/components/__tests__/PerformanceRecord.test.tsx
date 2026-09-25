import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PerformanceRecord } from '../PerformanceRecord';
import type { AnalysisStats } from '../../types/api';

const stats: AnalysisStats = {
  pivot_date: '2026-01-05',
  pre: { matches: 10, wins: 3, draws: 4, losses: 3, win_rate: 30, avg_goals_for: 1.1, avg_goals_against: 1.4 },
  post: { matches: 8, wins: 6, draws: 1, losses: 1, win_rate: 75, avg_goals_for: 2.0, avg_goals_against: 0.9 },
  series: [
    { date: '2025-12-01', opponent: 'Team A', result: 'W', rolling_win_rate: 40 },
    { date: '2026-01-10', opponent: 'Team B', result: 'W', rolling_win_rate: 60 },
  ],
  chart_path: null,
};

describe('PerformanceRecord', () => {
  it('renders a no-data message when stats are null', () => {
    render(<PerformanceRecord stats={null} />);
    expect(screen.getByText('No match data was available to compare for this subject.')).toBeInTheDocument();
  });

  it('renders the pre/post ledger with a win-rate delta', () => {
    render(<PerformanceRecord stats={stats} />);
    expect(screen.getByText('Performance record')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
    expect(screen.getByText('75%')).toBeInTheDocument();
    expect(screen.getByText('+45pp')).toBeInTheDocument();
  });

  it('does not re-scale a win_rate already given as a 0-100 percentage', () => {
    render(
      <PerformanceRecord
        stats={{ ...stats, pre: { ...stats.pre, win_rate: 33.3 }, post: { ...stats.post, win_rate: 0 } }}
      />,
    );
    expect(screen.getByText('33%')).toBeInTheDocument();
    expect(screen.queryByText('3330%')).not.toBeInTheDocument();
    expect(screen.getByText('-33pp')).toBeInTheDocument();
  });

  it('surfaces a stats error instead of the ledger', () => {
    render(<PerformanceRecord stats={{ ...stats, error: 'Not enough matches to compare.' }} />);
    expect(screen.getByText('Not enough matches to compare.')).toBeInTheDocument();
  });
});
