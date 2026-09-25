import { useId, useState, type ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTabId?: string;
}

export function Tabs({ tabs, defaultTabId }: TabsProps) {
  const [activeId, setActiveId] = useState(defaultTabId ?? tabs[0]?.id);
  const groupId = useId();
  const activeTab = tabs.find((t) => t.id === activeId) ?? tabs[0];

  function handleKeyDown(event: React.KeyboardEvent, index: number) {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const nextIndex = (index + delta + tabs.length) % tabs.length;
    setActiveId(tabs[nextIndex].id);
    document.getElementById(`${groupId}-tab-${tabs[nextIndex].id}`)?.focus();
  }

  return (
    <div>
      <div role="tablist" aria-label="Results" style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {tabs.map((tab, index) => {
          const isActive = tab.id === activeTab?.id;
          return (
            <button
              key={tab.id}
              id={`${groupId}-tab-${tab.id}`}
              role="tab"
              aria-selected={isActive}
              aria-controls={`${groupId}-panel-${tab.id}`}
              tabIndex={isActive ? 0 : -1}
              onClick={() => setActiveId(tab.id)}
              onKeyDown={(e) => handleKeyDown(e, index)}
              className="eyebrow"
              style={{
                margin: 0,
                padding: '10px 16px',
                border: 'none',
                borderBottom: `2px solid ${isActive ? 'var(--accent)' : 'transparent'}`,
                background: 'transparent',
                color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                cursor: 'pointer',
                fontSize: 12,
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          id={`${groupId}-panel-${tab.id}`}
          role="tabpanel"
          aria-labelledby={`${groupId}-tab-${tab.id}`}
          hidden={tab.id !== activeTab?.id}
        >
          {tab.id === activeTab?.id && tab.content}
        </div>
      ))}
    </div>
  );
}
