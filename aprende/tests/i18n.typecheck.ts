import { t } from '../src/core/i18n';

// @ts-expect-error intentional bad key
const _bad: string = t('no.such.key');
void _bad;
export {};
