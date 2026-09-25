import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { NewsExhibits } from '../NewsExhibits';
import type { NewsResearch } from '../../types/api';

const news: NewsResearch = {
  query: 'How has the manager change affected results?',
  key_events: [
    { date: '2026-01-05', headline: 'New manager appointed', detail: 'The club confirmed a new head coach.' },
    { date: '2026-01-20', headline: 'Key striker returns from injury', detail: 'Back in training this week.' },
  ],
  primary_event: {
    date: '2026-01-05',
    headline: 'New manager appointed',
    reason: 'This is the clearest inflection point in the timeline.',
  },
  summary: 'The managerial change looks like the main driver of the shift in form.',
};

describe('NewsExhibits', () => {
  it('numbers the primary event first, then the remaining key events', () => {
    render(<NewsExhibits news={news} verdict="The form change tracks the managerial appointment." />);

    expect(screen.getByText('Exhibit 01')).toBeInTheDocument();
    expect(screen.getByText('Primary evidence')).toBeInTheDocument();
    expect(screen.getByText('Exhibit 02')).toBeInTheDocument();
    expect(screen.getByText('Key striker returns from injury')).toBeInTheDocument();
    expect(screen.getAllByText('New manager appointed')).toHaveLength(1);
  });

  it('renders the summary and verdict stamp', () => {
    render(<NewsExhibits news={news} verdict="The form change tracks the managerial appointment." />);
    expect(screen.getByText(news.summary)).toBeInTheDocument();
    expect(screen.getByText('The form change tracks the managerial appointment.')).toBeInTheDocument();
    expect(screen.getByText('On the record')).toBeInTheDocument();
  });

  it('shows a quiet-record message when there are no key events', () => {
    render(<NewsExhibits news={{ ...news, key_events: [], primary_event: null }} verdict="Inconclusive." />);
    expect(screen.getByText('No news events turned up for this window — the record is quiet.')).toBeInTheDocument();
  });
});
