import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EvidenceDossier } from '../EvidenceDossier';
import type { AnalyzeResult } from '../../types/api';

const result: AnalyzeResult = {
  news: {
    query: 'manager change',
    summary: 'The club changed manager after a poor run.',
    primary_event: { date: '2025-09-27', headline: 'Manager sacked', reason: 'Clear pivot date' },
    key_events: [
      { date: '2025-09-20', headline: 'Pressure mounts', detail: 'Reports of unrest.' },
      { date: '2025-09-27', headline: 'Manager sacked', detail: 'Club announcement.' },
    ],
  },
  stats: {
    pivot_date: '2025-09-27',
    pre: { matches: 5, wins: 1, draws: 1, losses: 3, win_rate: 20, avg_goals_for: 1, avg_goals_against: 2 },
    post: { matches: 5, wins: 3, draws: 1, losses: 1, win_rate: 60, avg_goals_for: 2, avg_goals_against: 1 },
    series: [], chart_path: null,
  },
  verdict: 'Form improved after the change.',
};

describe('EvidenceDossier', () => {
  it('files a verdict, numbered news exhibits, and the performance split', () => {
    render(<EvidenceDossier result={result} />);
    expect(screen.getByText('Form improved after the change.')).toBeInTheDocument();
    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('Before pivot')).toBeInTheDocument();
    expect(screen.getByText('After pivot')).toBeInTheDocument();
  });
});
