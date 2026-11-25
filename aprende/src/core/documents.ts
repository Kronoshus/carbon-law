import { t } from './i18n';
import type { I18nKey } from './i18n-keys';

/** The office's document names (the backend's WORKFLOW_DOCUMENTS) in the reader's language; a name not listed is shown as sent. */
const NAMES: Record<string, I18nKey> = {
  'Revocable living trust': 'doc.trust',
  'Pour-over will': 'doc.pourover',
  'Advance health care directive': 'doc.ahcd',
  'Financial power of attorney': 'doc.poa',
};

export const documentName = (name: string): string => (NAMES[name] ? t(NAMES[name]) : name);
