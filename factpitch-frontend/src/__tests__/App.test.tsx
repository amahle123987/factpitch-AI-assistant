import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import * as apiClient from '../services/apiClient';
import { __resetCompetitionsCache } from '../hooks/useCompetitions';
import { __resetTeamsCache } from '../hooks/useTeams';

const FAKE_COMPETITIONS = [{ code: 'PL', name: 'Premier League' }];
const FAKE_TEAMS = [{ id: 57, name: 'Arsenal FC', competition: 'PL' }];

beforeEach(() => {
  __resetCompetitionsCache();
  __resetTeamsCache();
  vi.spyOn(apiClient, 'getCompetitions').mockResolvedValue(FAKE_COMPETITIONS);
  vi.spyOn(apiClient, 'getTeams').mockResolvedValue(FAKE_TEAMS);
});

describe('App (Phase 2 — case intake)', () => {
  it('renders the FactPitch masthead before any subject is selected', async () => {
    render(<App />);
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
    expect(screen.getByRole('heading', { name: 'FactPitch' })).toBeInTheDocument();
  });

  it('selecting a subject updates the masthead to the team name', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());

    await user.click(screen.getByRole('combobox', { name: 'Search for a team' }));
    await user.click(await screen.findByRole('option', { name: 'Arsenal FC' }));

    expect(screen.getByRole('heading', { name: 'Arsenal FC' })).toBeInTheDocument();
    expect(screen.getByText('Subject on file: Arsenal FC')).toBeInTheDocument();
  });

  it('the theme toggle still works alongside the intake form', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('radio', { name: 'Night Archive' }));
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});
