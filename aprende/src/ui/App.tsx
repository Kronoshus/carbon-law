import { h } from 'preact';
import '@fontsource/work-sans/400.css';
import '@fontsource/work-sans/600.css';
import '@fontsource/work-sans/700.css';
import '@fontsource/league-spartan/700.css';
import '@fontsource/league-spartan/800.css';
import './tokens.css';
import './shell.css';
import { useEffect, useState } from 'preact/hooks';
import { route, navigate } from '../core/router';
import { getToken } from '../core/api';
import { Shell } from './Shell';
import { Bienvenida } from './screens/Bienvenida';
import { CuentaNueva } from './screens/CuentaNueva';
import { Entrar } from './screens/Entrar';
import { Placeholder } from './screens/Placeholder';

const PUBLIC = new Set(['/bienvenida', '/cuenta-nueva', '/entrar']);

export function App() {
  const r = route.value;
  const [ready, setReady] = useState(true);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tok = await getToken();
      if (cancelled) return;
      setAuthed(!!tok);
      setReady(true);
      const isPublic = PUBLIC.has(r);
      if (!tok && !isPublic) {
        navigate('/bienvenida');
      } else if (tok && isPublic) {
        // landing route
        try {
          const res = await fetch('/journey', { headers: { Authorization: `Bearer ${tok}` } });
          if (res.ok) {
            const j = await res.json();
            const facts = j.facts || {};
            navigate(facts.ai_disclosed ? '/aprender' : '/inicio/ia');
          } else {
            navigate('/inicio/ia');
          }
        } catch {
          navigate('/inicio/ia');
        }
      }
    })();
    return () => { cancelled = true; };
  }, [r]);

  if (!ready) return null;

  let screen;
  if (r === '/bienvenida') screen = h(Bienvenida, null);
  else if (r === '/cuenta-nueva') screen = h(CuentaNueva, null);
  else if (r === '/entrar') screen = h(Entrar, null);
  else screen = h(Placeholder, null);

  if (PUBLIC.has(r)) return screen;
  if (!authed) return h(Bienvenida, null);
  return h(Shell, null, screen);
}
