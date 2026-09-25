import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { Tabs } from '../Tabs';

const TABS = [
  { id: 'a', label: 'Overview', content: <div>Overview content</div> },
  { id: 'b', label: 'Trends', content: <div>Trends content</div> },
  { id: 'c', label: 'News', content: <div>News content</div> },
];

describe('Tabs', () => {
  it('shows the first tab by default', () => {
    render(<Tabs tabs={TABS} />);
    expect(screen.getByText('Overview content')).toBeVisible();
    expect(screen.queryByText('Trends content')).not.toBeInTheDocument();
  });

  it('respects defaultTabId', () => {
    render(<Tabs tabs={TABS} defaultTabId="b" />);
    expect(screen.getByText('Trends content')).toBeVisible();
  });

  it('switches content when a tab is clicked', async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} />);

    await user.click(screen.getByRole('tab', { name: 'News' }));

    expect(screen.getByText('News content')).toBeVisible();
    expect(screen.queryByText('Overview content')).not.toBeInTheDocument();
  });

  it('marks only the active tab as aria-selected', async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} />);

    await user.click(screen.getByRole('tab', { name: 'Trends' }));

    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'false');
    expect(screen.getByRole('tab', { name: 'Trends' })).toHaveAttribute('aria-selected', 'true');
  });

  it('ArrowRight moves to the next tab and wraps around', async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} />);

    const firstTab = screen.getByRole('tab', { name: 'Overview' });
    firstTab.focus();
    await user.keyboard('{ArrowRight}');
    expect(screen.getByText('Trends content')).toBeVisible();

    await user.keyboard('{ArrowRight}{ArrowRight}'); // wraps: News -> back to Overview
    expect(screen.getByText('Overview content')).toBeVisible();
  });

  it('ArrowLeft moves to the previous tab', async () => {
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} defaultTabId="b" />);

    screen.getByRole('tab', { name: 'Trends' }).focus();
    await user.keyboard('{ArrowLeft}');

    expect(screen.getByText('Overview content')).toBeVisible();
  });
});
