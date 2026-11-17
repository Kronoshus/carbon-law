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
      }]
    }
  }
);
