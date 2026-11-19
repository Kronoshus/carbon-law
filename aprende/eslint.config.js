import js from '@eslint/js';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist/**', 'node_modules/**', 'tests/fixtures/**'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/core/**/*.{ts,tsx}', 'src/ui/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-imports': ['error', {
        patterns: [{ group: ['**/targets/**'], message: 'core/ui must not import targets' }]
      }],
      'no-restricted-syntax': ['error', {
        selector: 'JSXText[value=/\\S/]',
        message: 'No hard-coded text in JSX; use t(key).',
      }],
    }
  }
,
  {
    // Spec 10 / T5-06: the browser's speech recognition sends the client's audio to a third party. Voice input, when the
    // firm approves hosting, goes through the firm's own servers only.
    files: ['src/**/*.{ts,tsx}'],
    rules: {
      'no-restricted-globals': ['error',
        { name: 'SpeechRecognition', message: 'Browser speech recognition sends audio to a third party (spec 10).' },
        { name: 'webkitSpeechRecognition', message: 'Browser speech recognition sends audio to a third party (spec 10).' }],
      'no-restricted-properties': ['error',
        { object: 'window', property: 'SpeechRecognition', message: 'Browser speech recognition sends audio to a third party (spec 10).' },
        { object: 'window', property: 'webkitSpeechRecognition', message: 'Browser speech recognition sends audio to a third party (spec 10).' }],
    },
  },
  {
    files: ['scripts/**/*.{mjs,js}'],
    languageOptions: { globals: { console: 'readonly', process: 'readonly' } },
  },
);