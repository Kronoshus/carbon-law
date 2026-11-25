import { h } from 'preact';
import { t } from '../core/i18n';
import type { I18nKey } from '../core/i18n-keys';

/** Why a screen could not load: the connection (fetch threw) or the server (an error status). */
export type LoadProblem = 'offline' | 'server';

/** The request's outcome as a problem, or null when it worked. */
export const problemOf = (r: Response | null): LoadProblem | null => (r === null ? 'offline' : r.ok ? null : 'server');

/** A screen that could not load: what went wrong in the client's words, and one way to try again. */
export function LoadFailed({ title, problem, retry }: { title: I18nKey; problem: LoadProblem; retry: () => void }) {
  return h('section', { class: 'screen datos-page' },
    h('h1', null, t(title)),
    h('p', { class: 'gate-error', role: 'alert' }, t(problem === 'offline' ? 'error.network' : 'error.server')),
    h('button', { class: 'btn secondary', type: 'button', onClick: retry }, t('load.retry')));
}
