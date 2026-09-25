import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RollingChart } from '../RollingChart';
import type { RollingPoint } from '../../types/api';

const series: RollingPoint[] = [
  { date: '2025-12-01', opponent: 'Team A', result: 'W', rolling_win_rate: 40 },
  { date: '2026-01-10', opponent: 'Team B', result: 'L', rolling_win_rate: 55 },
];

describe('RollingChart', () => {
  it('renders a message when there is no series data', () => {
    render(<RollingChart series={[]} pivotDate="2026-01-05" />);
    expect(screen.getByText('No rolling form data to chart for this window.')).toBeInTheDocument();
  });

  it('renders a point for every match plus the W/D/L legend', () => {
    render(<RollingChart series={series} pivotDate="2026-01-05" />);
    expect(screen.getByRole('img', { name: 'Rolling win rate over the investigation window' })).toBeInTheDocument();
    expect(screen.getByText('Win')).toBeInTheDocument();
    expect(screen.getByText('Draw')).toBeInTheDocument();
    expect(screen.getByText('Loss')).toBeInTheDocument();
  });
});
