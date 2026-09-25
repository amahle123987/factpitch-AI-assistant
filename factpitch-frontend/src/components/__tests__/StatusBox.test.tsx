import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { StatusBox } from '../StatusBox';

describe('StatusBox', () => {
  it('renders nothing when idle', () => {
    const { container } = render(<StatusBox status="idle" stages={[]} errorMessage={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows numbered stage lines while running', () => {
    render(
      <StatusBox
        status="running"
        stages={['Researching: recent injury news', 'Validating the narrative']}
        errorMessage={null}
      />,
    );

    expect(screen.getByText('Investigating…')).toBeInTheDocument();
    expect(screen.getByText('01. Researching: recent injury news')).toBeInTheDocument();
    expect(screen.getByText('02. Validating the narrative')).toBeInTheDocument();
  });

  it('shows "Case Processed" when done, and can be collapsed', async () => {
    const user = userEvent.setup();
    render(<StatusBox status="done" stages={['Researching', 'Done']} errorMessage={null} />);

    expect(screen.getByText('Case Processed')).toBeInTheDocument();
    expect(screen.getByText('01. Researching')).toBeInTheDocument();

    await user.click(screen.getByText('Case Processed'));
    expect(screen.queryByText('01. Researching')).not.toBeInTheDocument();
  });

  it('shows "Case Stalled" and the error detail on failure', () => {
    render(<StatusBox status="error" stages={['Researching']} errorMessage="pipeline exploded" />);

    expect(screen.getByText('Case Stalled')).toBeInTheDocument();
    expect(screen.getByText('pipeline exploded')).toBeInTheDocument();
  });
});
