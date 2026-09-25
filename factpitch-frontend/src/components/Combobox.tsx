import { useEffect, useId, useRef, useState } from 'react';

interface ComboboxProps<T> {
  options: T[];
  getKey: (option: T) => string | number;
  getLabel: (option: T) => string;
  value: T | null;
  onChange: (option: T) => void;
  placeholder?: string;
  disabled?: boolean;
  'aria-label'?: string;
}

/**
 * A searchable, keyboard-navigable dropdown — fills the gap where the
 * browser has no built-in combobox with type-to-filter. Styled here as a
 * "file drawer" lookup: typing narrows the drawer's contents.
 */
export function Combobox<T>({
  options,
  getKey,
  getLabel,
  value,
  onChange,
  placeholder = 'Search…',
  disabled = false,
  'aria-label': ariaLabel,
}: ComboboxProps<T>) {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listboxId = useId();

  const displayValue = isOpen ? query : value ? getLabel(value) : '';
  const filtered = options.filter((opt) => getLabel(opt).toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setQuery('');
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    setHighlightedIndex(0);
  }, [query]);

  function selectOption(option: T) {
    onChange(option);
    setQuery('');
    setIsOpen(false);
    inputRef.current?.blur();
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (disabled) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
        return;
      }
      setHighlightedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setHighlightedIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      if (isOpen && filtered[highlightedIndex]) {
        selectOption(filtered[highlightedIndex]);
      }
    } else if (event.key === 'Escape') {
      setIsOpen(false);
      setQuery('');
    }
  }

  const activeOptionId =
    isOpen && filtered[highlightedIndex] ? `${listboxId}-opt-${getKey(filtered[highlightedIndex])}` : undefined;

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <input
        ref={inputRef}
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-activedescendant={activeOptionId}
        aria-autocomplete="list"
        aria-label={ariaLabel}
        autoComplete="off"
        disabled={disabled}
        value={displayValue}
        placeholder={placeholder}
        onFocus={() => setIsOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value);
          setIsOpen(true);
        }}
        onKeyDown={handleKeyDown}
        className="mono"
        style={{
          width: '100%',
          padding: '9px 11px',
          background: disabled ? 'var(--bg)' : 'var(--panel)',
          color: 'var(--ink)',
          border: 'var(--border-width) solid var(--panel-border)',
          borderRadius: 2,
          fontSize: 14,
        }}
      />

      {isOpen && !disabled && (
        <ul
          id={listboxId}
          role="listbox"
          style={{
            position: 'absolute',
            zIndex: 10,
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            maxHeight: 260,
            overflowY: 'auto',
            listStyle: 'none',
            padding: 4,
            background: 'var(--panel)',
            border: 'var(--border-width) solid var(--panel-border)',
            borderRadius: 2,
            boxShadow: '0 4px 10px rgba(0, 0, 0, 0.15)',
          }}
        >
          {filtered.length === 0 && (
            <li style={{ padding: '8px 10px', color: 'var(--ink-muted)', fontSize: 13 }}>No matches on file</li>
          )}
          {filtered.map((option, index) => {
            const key = getKey(option);
            const isHighlighted = index === highlightedIndex;
            return (
              <li
                key={key}
                id={`${listboxId}-opt-${key}`}
                role="option"
                aria-selected={value ? getKey(value) === key : false}
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectOption(option);
                }}
                onMouseEnter={() => setHighlightedIndex(index)}
                style={{
                  padding: '8px 10px',
                  borderRadius: 2,
                  cursor: 'pointer',
                  fontSize: 14,
                  background: isHighlighted ? 'var(--stamp)' : 'transparent',
                  color: isHighlighted ? 'var(--stamp-text)' : 'var(--ink)',
                }}
              >
                {getLabel(option)}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
