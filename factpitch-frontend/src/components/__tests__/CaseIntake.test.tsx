import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CaseIntake } from '../CaseIntake';
import * as apiClient from '../../services/apiClient';
import { __resetCompetitionsCache } from '../../hooks/useCompetitions';
import { __resetTeamsCache } from '../../hooks/useTeams';

const FAKE_COMPETITIONS = [
  { code: 'PL', name: 'Premier League' },
  { code: 'PD', name: 'La Liga' },
];
const FAKE_TEAMS = [{ id: 57, name: 'Arsenal FC', competition: 'PL' }];

function renderCaseIntake(overrides: Partial<React.ComponentProps<typeof CaseIntake>> = {}) {
  const onCompetitionChange = vi.fn();
  const onSelectionChange = vi.fn();
  const onWindowDaysChange = vi.fn();

  render(
    <CaseIntake
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

describe('CaseIntake', () => {
  it('loads and lists competitions in the jurisdiction select', async () => {
    renderCaseIntake();
    expect(await screen.findByText('Premier League')).toBeInTheDocument();
    expect(screen.getByText('La Liga')).toBeInTheDocument();
  });

  it('shows "No subject selected" before a team is chosen', async () => {
    renderCaseIntake();
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
    expect(screen.getByText('No subject selected.')).toBeInTheDocument();
  });

  it('shows "Subject on file" once a team is selected', async () => {
    renderCaseIntake({ selection: { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' } });
    expect(screen.getByText('Subject on file: Arsenal FC')).toBeInTheDocument();
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
  });

  it('selecting a team calls onSelectionChange with id/name/competition', async () => {
    const user = userEvent.setup();
    const { onSelectionChange } = renderCaseIntake();

    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
    const teamCombobox = screen.getByRole('combobox', { name: 'Search for a team' });
    await user.click(teamCombobox);
    await user.click(await screen.findByRole('option', { name: 'Arsenal FC' }));

    expect(onSelectionChange).toHaveBeenCalledWith({ teamId: 57, teamName: 'Arsenal FC', competition: 'PL' });
  });

  it('changing jurisdiction clears the current selection', async () => {
    const user = userEvent.setup();
    const { onSelectionChange } = renderCaseIntake({
      selection: { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' },
    });

    await screen.findByText('Premier League');
    await user.selectOptions(screen.getByLabelText('Jurisdiction (optional)'), 'La Liga');

    expect(onSelectionChange).toHaveBeenCalledWith(null);
  });

  it('shows the unreachable message and disables inputs when the API fails', async () => {
    vi.spyOn(apiClient, 'getCompetitions').mockRejectedValue(new apiClient.ApiError('Could not reach the API'));

    renderCaseIntake();

    expect(await screen.findByText('Case file unreachable.')).toBeInTheDocument();
    expect(screen.getByLabelText('Jurisdiction (optional)')).toBeDisabled();
    expect(screen.getByRole('combobox', { name: 'Search for a team' })).toBeDisabled();
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());
  });

  it('the investigation-window slider reports its value', async () => {
    const { onWindowDaysChange } = renderCaseIntake({ windowDays: 60 });
    await waitFor(() => expect(apiClient.getTeams).toHaveBeenCalled());

    expect(screen.getByText('Investigation window — 60 days either side')).toBeInTheDocument();

    // jsdom doesn't implement native range-input keyboard stepping, so we
    // simulate what the browser would eventually dispatch: a change event
    // carrying the new value.
    const slider = screen.getByLabelText('Investigation window — 60 days either side');
    fireEvent.change(slider, { target: { value: '105' } });

    expect(onWindowDaysChange).toHaveBeenCalledWith(105);
  });
});
