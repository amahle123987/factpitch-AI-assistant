import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Sidebar } from '../Sidebar';
import * as apiClient from '../../services/apiClient';
import { __resetCompetitionsCache } from '../../hooks/useCompetitions';
import { __resetTeamsCache } from '../../hooks/useTeams';

const FAKE_COMPETITIONS = [
  { code: 'PL', name: 'Premier League' },
  { code: 'PD', name: 'La Liga' },
];
const FAKE_TEAMS = [{ id: 57, name: 'Arsenal FC', competition: 'PL' }];

function renderSidebar(overrides: Partial<React.ComponentProps<typeof Sidebar>> = {}) {
  const onCompetitionChange = vi.fn();
  const onSelectionChange = vi.fn();
  const onWindowDaysChange = vi.fn();

  render(
    <Sidebar
      competition={null}
      onCompetitionChange={onCompetitionChange}
      selection={null}
      onSelectionChange={onSelectionChange}
      windowDays={60}
      onWindowDaysChange={onWindowDaysChange}
      {...overrides}
    />,
  );

  return { onCompetitionChange, onSelectionChange, onWindowDaysChange };
}

beforeEach(() => {
  __resetCompetitionsCache();
  __resetTeamsCache();
  vi.spyOn(apiClient, 'getCompetitions').mockResolvedValue(FAKE_COMPETITIONS);
  vi.spyOn(apiClient, 'getTeams').mockResolvedValue(FAKE_TEAMS);
});

describe('Sidebar', () => {
  it('loads and displays competitions', async () => {
    renderSidebar();
    expect(await screen.findByText('Premier League')).toBeInTheDocument();
    expect(screen.getByText('La Liga')).toBeInTheDocument();
  });

  it('shows the empty-state message before a team is selected', async () => {
    renderSidebar();
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
    expect(screen.getByText('Select a team above to get started.')).toBeInTheDocument();
  });

  it('shows the team name once selected', async () => {
    renderSidebar({ selection: { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' } });
    expect(screen.getByText('Team: Arsenal FC')).toBeInTheDocument();
  });

  it('selecting a team in the combobox calls onSelectionChange with id/name/competition', async () => {
    const user = userEvent.setup();
    const { onSelectionChange } = renderSidebar();

    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
    const teamCombobox = screen.getByRole('combobox', { name: 'Search for a team' });
    await user.click(teamCombobox);
    await user.click(await screen.findByRole('option', { name: 'Arsenal FC' }));

    expect(onSelectionChange).toHaveBeenCalledWith({ teamId: 57, teamName: 'Arsenal FC', competition: 'PL' });
  });

  it('changing competition clears the current selection', async () => {
    const user = userEvent.setup();
    const { onSelectionChange } = renderSidebar({
      selection: { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' },
    });

    await screen.findByText('Premier League');
    await user.selectOptions(screen.getByLabelText('Restrict to a competition (optional)'), 'La Liga');

    expect(onSelectionChange).toHaveBeenCalledWith(null);
  });

  it('shows an error and disables inputs when the API is unreachable', async () => {
    vi.spyOn(apiClient, 'getCompetitions').mockRejectedValue(new apiClient.ApiError('Could not reach the API'));

    renderSidebar();

    expect(await screen.findByText(/Can't reach the API backend/)).toBeInTheDocument();
    expect(screen.getByLabelText('Restrict to a competition (optional)')).toBeDisabled();
    expect(screen.getByRole('combobox', { name: 'Search for a team' })).toBeDisabled();
  });

  it('the days slider reflects and reports its value', async () => {
    const { onWindowDaysChange } = renderSidebar({ windowDays: 60 });

    expect(screen.getByText('60')).toBeInTheDocument();

    // jsdom doesn't implement native range-input keyboard stepping, so we
    // simulate what the browser would eventually dispatch: a change event
    // carrying the new value, and confirm our handler reads it correctly.
    const slider = screen.getByLabelText('Days before/after to compare');
    fireEvent.change(slider, { target: { value: '105' } });

    expect(onWindowDaysChange).toHaveBeenCalledWith(105);
  });
});
