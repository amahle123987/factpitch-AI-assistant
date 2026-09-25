import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CaseFileHeader } from '../CaseFileHeader';
import { ThemeProvider } from '../../context/ThemeContext';
import * as apiClient from '../../services/apiClient';
import { __resetCompetitionsCache } from '../../hooks/useCompetitions';

const SELECTION = { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' };
const FAKE_COMPETITIONS = [
  { code: 'PL', name: 'Premier League' },
  { code: 'PD', name: 'La Liga' },
];
const FULL_HEADLINE = {
  available: true,
  position: 3,
  played: 20,
  won: 12,
  draw: 5,
  lost: 3,
  goals_for: 35,
  goals_against: 18,
  goal_difference: 17,
  points: 41,
};

function renderHeader(selection: typeof SELECTION | null) {
  return render(
    <ThemeProvider>
      <CaseFileHeader selection={selection} />
    </ThemeProvider>,
  );
}

beforeEach(() => {
  __resetCompetitionsCache();
  vi.spyOn(apiClient, 'getCrest').mockResolvedValue(null);
  vi.spyOn(apiClient, 'getHeadlineStats').mockResolvedValue(null);
  vi.spyOn(apiClient, 'getCompetitions').mockResolvedValue(FAKE_COMPETITIONS);
});

describe('CaseFileHeader', () => {
  it('shows the FactPitch masthead when no subject is selected', async () => {
    renderHeader(null);
    expect(screen.getByRole('heading', { name: 'FactPitch' })).toBeInTheDocument();
    expect(screen.getByText('Your form guide, verified.')).toBeInTheDocument();
    await waitFor(() => expect(apiClient.getCompetitions).toHaveBeenCalled());
  });

  it('shows "No Photo On File" in the frame when idle', async () => {
    renderHeader(null);
    expect(screen.getByText(/No/)).toBeInTheDocument();
    await waitFor(() => expect(apiClient.getCompetitions).toHaveBeenCalled());
  });

  it('switches to the team name, full competition name, and a case-specific tagline once selected', async () => {
    renderHeader(SELECTION);
    expect(screen.getByRole('heading', { name: 'Arsenal FC' })).toBeInTheDocument();
    expect(await screen.findByText('Case File · Premier League')).toBeInTheDocument();
    expect(screen.getByText(/Cross-referencing recent news/)).toBeInTheDocument();
  });

  it('falls back to the competition code if the full competitions list has not loaded yet', () => {
    vi.spyOn(apiClient, 'getCompetitions').mockReturnValue(new Promise(() => {})); // never resolves
    renderHeader(SELECTION);
    expect(screen.getByText('Case File · PL')).toBeInTheDocument();
  });

  it('shows a letter fallback when the team has no crest', async () => {
    vi.spyOn(apiClient, 'getCrest').mockResolvedValue(null);
    renderHeader(SELECTION);
    expect(await screen.findByText('A')).toBeInTheDocument();
  });

  it('shows the crest image when available', async () => {
    vi.spyOn(apiClient, 'getCrest').mockResolvedValue('https://example.com/crest.png');
    renderHeader(SELECTION);
    const img = await screen.findByRole('img', { name: 'Arsenal FC crest' });
    expect(img).toHaveAttribute('src', 'https://example.com/crest.png');
  });

  it('shows all five vitals chips when headline stats are available', async () => {
    vi.spyOn(apiClient, 'getHeadlineStats').mockResolvedValue(FULL_HEADLINE);
    renderHeader(SELECTION);

    expect(await screen.findByText('#3')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument(); // played
    expect(screen.getByText('12-5-3')).toBeInTheDocument();
    expect(screen.getByText('+17')).toBeInTheDocument();
    expect(screen.getByText('41')).toBeInTheDocument();
    expect(screen.getByText('Goal Diff')).toBeInTheDocument(); // full label, not truncated
  });

  it('formats a negative goal difference without an extra plus sign', async () => {
    vi.spyOn(apiClient, 'getHeadlineStats').mockResolvedValue({ ...FULL_HEADLINE, goal_difference: -4 });
    renderHeader(SELECTION);
    expect(await screen.findByText('-4')).toBeInTheDocument();
  });

  it('shows no vitals strip when headline stats are unavailable', async () => {
    renderHeader(SELECTION);
    expect(screen.queryByText('Position')).not.toBeInTheDocument();
    await waitFor(() => expect(apiClient.getCompetitions).toHaveBeenCalled());
  });

  it('shows no vitals strip when no subject is selected', async () => {
    renderHeader(null);
    expect(screen.queryByText('Position')).not.toBeInTheDocument();
    await waitFor(() => expect(apiClient.getCompetitions).toHaveBeenCalled());
  });
});

