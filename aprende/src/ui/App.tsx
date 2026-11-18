import { h } from 'preact';
import './tokens.css';
import { route } from '../core/router';
import { Shell } from './Shell';
import { Bienvenida } from './screens/Bienvenida';
import { CuentaNueva } from './screens/CuentaNueva';
import { Entrar } from './screens/Entrar';
import { Placeholder } from './screens/Placeholder';

const PUBLIC = new Set(['/bienvenida', '/cuenta-nueva', '/entrar']);

export function App() {
  const r = route.value;
  let screen;
  if (r === '/bienvenida') screen = h(Bienvenida, null);
  else if (r === '/cuenta-nueva') screen = h(CuentaNueva, null);
  else if (r === '/entrar') screen = h(Entrar, null);
  else screen = h(Placeholder, null);

  if (PUBLIC.has(r)) return screen;
  return h(Shell, null, screen);
}
