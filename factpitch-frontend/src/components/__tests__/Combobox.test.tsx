import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Combobox } from '../Combobox';

interface Item {
  id: number;
  name: string;
}

const ITEMS: Item[] = [
  { id: 1, name: 'Arsenal FC' },
  { id: 2, name: 'Aston Villa FC' },
  { id: 3, name: 'AFC Bournemouth' },
  { id: 4, name: 'Liverpool FC' },
];

function renderCombobox(onChange = vi.fn(), value: Item | null = null) {
  render(
    <Combobox
      options={ITEMS}
      getKey={(i) => i.id}
      getLabel={(i) => i.name}
      value={value}
      onChange={onChange}
      aria-label="Search for a team"
    />,
  );
  return onChange;
}

describe('Combobox', () => {
  it('shows every option when opened with no query', async () => {
    const user = userEvent.setup();
    renderCombobox();
    await user.click(screen.getByRole('combobox'));

    expect(screen.getByRole('option', { name: 'Arsenal FC' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Liverpool FC' })).toBeInTheDocument();
  });

  it('filters options as the user types', async () => {
    const user = userEvent.setup();
    renderCombobox();
    await user.type(screen.getByRole('combobox'), 'A');

    expect(screen.getByRole('option', { name: 'Arsenal FC' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Aston Villa FC' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'AFC Bournemouth' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Liverpool FC' })).not.toBeInTheDocument();
  });

  it('filtering is case-insensitive', async () => {
    const user = userEvent.setup();
    renderCombobox();
    await user.type(screen.getByRole('combobox'), 'arsenal');
    expect(screen.getByRole('option', { name: 'Arsenal FC' })).toBeInTheDocument();
  });

  it('shows the "no matches" message when nothing filters in', async () => {
    const user = userEvent.setup();
    renderCombobox();
    await user.type(screen.getByRole('combobox'), 'Nonexistent');
    expect(screen.getByText('No matches on file')).toBeInTheDocument();
  });

  it('calls onChange and closes the list when an option is clicked', async () => {
    const user = userEvent.setup();
    const onChange = renderCombobox();

    await user.click(screen.getByRole('combobox'));
    await user.click(screen.getByRole('option', { name: 'Liverpool FC' }));

    expect(onChange).toHaveBeenCalledWith(ITEMS[3]);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it("displays the selected value's label when closed", () => {
    renderCombobox(vi.fn(), ITEMS[0]);
    expect(screen.getByRole('combobox')).toHaveValue('Arsenal FC');
  });

  it('supports arrow-key navigation and Enter to select', async () => {
    const user = userEvent.setup();
    const onChange = renderCombobox();
    const input = screen.getByRole('combobox');

    await user.click(input); // opens the list, highlight starts at index 0
    await user.keyboard('{ArrowDown}{Enter}'); // moves to index 1: Aston Villa FC

    expect(onChange).toHaveBeenCalledWith(ITEMS[1]);
  });

  it('Escape closes the list without selecting', async () => {
    const user = userEvent.setup();
    const onChange = renderCombobox();

    await user.click(screen.getByRole('combobox'));
    await user.keyboard('{Escape}');

    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('is disabled when the disabled prop is set', async () => {
    const user = userEvent.setup();
    render(
      <Combobox
        options={ITEMS}
        getKey={(i) => i.id}
        getLabel={(i) => i.name}
        value={null}
        onChange={vi.fn()}
        disabled
        aria-label="Search for a team"
      />,
    );

    const input = screen.getByRole('combobox');
    expect(input).toBeDisabled();

    await user.click(input);
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('closes when clicking outside', async () => {
    const user = userEvent.setup();
    render(
      <div>
        <Combobox
          options={ITEMS}
          getKey={(i) => i.id}
          getLabel={(i) => i.name}
          value={null}
          onChange={vi.fn()}
          aria-label="Search for a team"
        />
        <button>outside</button>
      </div>,
    );

    await user.click(screen.getByRole('combobox'));
    expect(screen.getByRole('listbox')).toBeInTheDocument();

    await user.click(screen.getByText('outside'));
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });
});
