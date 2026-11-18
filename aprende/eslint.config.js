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
    files: ['scripts/**/*.{mjs,js}'],
    languageOptions: { globals: { console: 'readonly', process: 'readonly' } },
  },
);