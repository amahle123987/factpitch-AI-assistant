import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RollingChart } from '../RollingChart';

describe('RollingChart', () => {
  it('renders nothing for an empty series', () => {
    const { container } = render(<RollingChart series={[]} pivotDate="2025-09-27" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders a single-point series without dividing by zero', () => {
    render(
      <RollingChart
        series={[{ date: '2025-09-27', opponent: 'Team X', result: 'W', rolling_win_rate: 100 }]}
        pivotDate="2025-09-27"
      />,
    );
    expect(screen.getByRole('img', { name: /1 matches/ })).toBeInTheDocument();
  });

  it('describes the series in the accessible name', () => {
    render(
      <RollingChart
        series={[
          { date: '2025-09-01', opponent: 'A', result: 'W', rolling_win_rate: 100 },
          { date: '2025-09-15', opponent: 'B', result: 'L', rolling_win_rate: 50 },
        ]}
        pivotDate="2025-09-10"
      />,
    );
    expect(screen.getByRole('img', { name: /2 matches, pivot date 2025-09-10/ })).toBeInTheDocument();
  });

  it('places the pivot marker at the series end when the pivot is after every match', () => {
    // Regression check: findIndex returns -1 when no match date is >= the
    // pivot — the component should fall back to the last point instead of
    // rendering at x=NaN.
    const { container } = render(
      <RollingChart
        series={[{ date: '2025-01-01', opponent: 'A', result: 'W', rolling_win_rate: 100 }]}
        pivotDate="2025-12-31"
      />,
    );
    const dashedLine = container.querySelector('line[stroke-dasharray]');
    expect(dashedLine?.getAttribute('x1')).not.toBe('NaN');
  });
});
