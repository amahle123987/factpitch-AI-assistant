import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResultsBarChart } from '../ResultsBarChart';

describe('ResultsBarChart', () => {
  it('describes the before/after counts in the accessible name', () => {
    render(
      <ResultsBarChart pre={{ wins: 1, draws: 0, losses: 4 }} post={{ wins: 2, draws: 2, losses: 3 }} />,
    );
    expect(
      screen.getByRole('img', {
        name: 'Results before: 1 wins, 0 draws, 4 losses. After: 2 wins, 2 draws, 3 losses.',
      }),
    ).toBeInTheDocument();
  });

  it('does not crash when every count is zero', () => {
    render(<ResultsBarChart pre={{ wins: 0, draws: 0, losses: 0 }} post={{ wins: 0, draws: 0, losses: 0 }} />);
    expect(screen.getByRole('img')).toBeInTheDocument();
  });

  it('renders value labels only for non-zero bars', () => {
    render(<ResultsBarChart pre={{ wins: 0, draws: 3, losses: 0 }} post={{ wins: 0, draws: 0, losses: 0 }} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
