import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ExhibitOpener } from '../ExhibitOpener';
import * as apiClient from '../../services/apiClient';

const selection = { teamId: 57, teamName: 'Arsenal FC', competition: 'PL' };

describe('ExhibitOpener', () => {
  it('requires a question before an exhibit can open', async () => {
    const user = userEvent.setup();
    render(<ExhibitOpener selection={selection} windowDays={60} />);
    const button = screen.getByRole('button', { name: 'Open exhibit' });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText('Question for the record'), 'Is the form improving?');
    expect(button).toBeEnabled();
  });

  it('disables the textarea and shows guidance when no subject is selected', () => {
    render(<ExhibitOpener selection={null} windowDays={60} />);
    expect(screen.getByLabelText('Question for the record')).toBeDisabled();
    expect(screen.getByText('Choose a subject above before opening an exhibit.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Open exhibit' })).toBeDisabled();
  });

  it('shows the subject and comparison window once a subject is selected', () => {
    render(<ExhibitOpener selection={selection} windowDays={90} />);
    expect(screen.getByText('Subject: Arsenal FC; 90-day comparison window')).toBeInTheDocument();
  });

  it('streams progress into the investigation log', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'runAnalysis').mockImplementation(async ({ onProgress }) => {
      onProgress?.('Researching the claim');
      return { news: { query: 'q', key_events: [], primary_event: null, summary: '' }, stats: null, verdict: '' };
    });
    render(<ExhibitOpener selection={selection} windowDays={60} />);
    await user.type(screen.getByLabelText('Question for the record'), 'Is the form improving?');
    await user.click(screen.getByRole('button', { name: 'Open exhibit' }));
    expect(await screen.findByText('01. Researching the claim')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('News exhibits')).toBeInTheDocument());
    expect(screen.getByText('Performance record')).toBeInTheDocument();
  });

  it('shows the button label while an investigation is running', async () => {
    const user = userEvent.setup();
    let resolveRun!: (value: Awaited<ReturnType<typeof apiClient.runAnalysis>>) => void;
    vi.spyOn(apiClient, 'runAnalysis').mockReturnValue(
      new Promise((resolve) => {
        resolveRun = resolve;
      }),
    );

    render(<ExhibitOpener selection={selection} windowDays={60} />);
    await user.type(screen.getByLabelText('Question for the record'), 'Is the form improving?');
    await user.click(screen.getByRole('button', { name: 'Open exhibit' }));

    expect(await screen.findByRole('button', { name: 'Opening exhibit...' })).toBeDisabled();

    resolveRun({ news: { query: 'q', key_events: [], primary_event: null, summary: '' }, stats: null, verdict: '' });
    await waitFor(() => expect(screen.getByRole('button', { name: 'Open exhibit' })).toBeInTheDocument());
  });

  it('surfaces an error through the investigation log without crashing', async () => {
    const user = userEvent.setup();
    vi.spyOn(apiClient, 'runAnalysis').mockRejectedValue(new apiClient.ApiError('pipeline exploded'));

    render(<ExhibitOpener selection={selection} windowDays={60} />);
    await user.type(screen.getByLabelText('Question for the record'), 'Is the form improving?');
    await user.click(screen.getByRole('button', { name: 'Open exhibit' }));

    expect(await screen.findByText('Case Stalled')).toBeInTheDocument();
    expect(screen.getByText('pipeline exploded')).toBeInTheDocument();
  });
});
