import { h } from 'preact';
import { render } from 'preact';
import { describe, it, expect } from 'vitest';
import { App } from '../src/ui/App';

describe('App', () => {
  it('renders', () => {
    const container = document.createElement('div');
    document.body.appendChild(container);
    render(h(App, null), container);
    expect(container.textContent).toContain('Memento Mori');
  });
});
