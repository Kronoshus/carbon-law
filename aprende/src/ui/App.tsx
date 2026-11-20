import { h, Fragment } from 'preact';
import { IconSprite } from './Icons';
import '@fontsource/work-sans/400.css';
import '@fontsource/work-sans/600.css';
import '@fontsource/work-sans/700.css';
import '@fontsource/league-spartan/700.css';
import '@fontsource/league-spartan/800.css';
import './tokens.css';
import './shell.css';
import { useEffect, useState } from 'preact/hooks';
import { route, navigate } from '../core/router';
import { getToken, extensionOff, apiFetch } from '../core/api';
import { Shell } from './Shell';
import { Bienvenida } from './screens/Bienvenida';
import { Privacidad } from './screens/Privacidad';
import { InicioIa, InicioConsentimiento, InicioNoAcepto, InicioNombres, InicioEspera } from './screens/Inicio';
import { CuentaNueva } from './screens/CuentaNueva';
import { Entrar } from './screens/Entrar';
import { Placeholder } from './screens/Placeholder';
import { NoDisponible } from './screens/NoDisponible';
import { Plan } from './screens/Plan';
import { Aprender } from './screens/Aprender';
import { Leccion } from './screens/Leccion';
import { Datos } from './screens/Datos';
import { Documentos } from './screens/Documentos';
import { Resumen } from './screens/Resumen';
import { Firmados } from './screens/Firmados';
import { Revisar } from './screens/Revisar';
import { Preguntas } from './screens/Preguntas';
import { Acuerdo } from './screens/Acuerdo';
import { Cita } from './screens/Cita';
import { Pago, PagoListo } from './screens/Pago';
import { DevCharacter } from './DevCharacter';

const PUBLIC = new Set(['/bienvenida', '/cuenta-nueva', '/entrar']);
const OPEN = new Set(['/privacidad']);

function Screens() {
  const r = route.value;
  const leccionMatch = r.match(/^\/leccion\/(.+)$/);
  const datosMatch = r.match(/^\/datos\/(.+)$/);
  const pagoListo = r.startsWith('/pago/listo');
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
      const isOpen = OPEN.has(r);
      if (!tok && !isPublic && !isOpen) {
        navigate('/bienvenida');
      } else if (tok && isPublic) {
        try {
          const res = await apiFetch('/journey');
          if (res.ok) {
            const j = await res.json();
            const facts = j.facts || {};
            let target = '/inicio/ia';
            if (facts.ai_disclosed) {
              if (facts.consent_answer === 'no') target = '/inicio/no-acepto';
              else if (!facts.consent) target = '/inicio/consentimiento';
              else if (!facts.names_submitted) target = '/inicio/nombres';
              else if (j.conflict !== 'clear') target = '/inicio/espera';
              else target = '/aprender';
            }
            navigate(target);
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

  if (ready && import.meta.env?.DEV && r === '/dev/personaje') {
    return h(DevCharacter, null);
  }

  if (extensionOff.value) return h(NoDisponible, null);

  if (!ready) return null;

  let screen;
  if (r === '/bienvenida') screen = h(Bienvenida, null);
  else if (r === '/privacidad') screen = h(Privacidad, null);
  else if (r === '/cuenta-nueva') screen = h(CuentaNueva, null);
  else if (r === '/entrar') screen = h(Entrar, null);
  else if (r === '/plan') screen = h(Plan, null);
  else if (r === '/inicio/ia') screen = h(InicioIa, null);
  else if (r === '/inicio/consentimiento') screen = h(InicioConsentimiento, null);
  else if (r === '/inicio/no-acepto') screen = h(InicioNoAcepto, null);
  else if (r === '/inicio/nombres') screen = h(InicioNombres, null);
  else if (r === '/inicio/espera') screen = h(InicioEspera, null);
  else if (r === '/aprender') screen = h(Aprender, null);
  else if (leccionMatch) screen = h(Leccion, { id: decodeURIComponent(leccionMatch[1]) });
  else if (r === '/documentos') screen = h(Documentos, null);
  else if (r === '/resumen') screen = h(Resumen, null);
  else if (r === '/firmados') screen = h(Firmados, null);
  else if (r === '/revisar') screen = h(Revisar, null);
  else if (r === '/preguntas') screen = h(Preguntas, null);
  else if (r === '/acuerdo') screen = h(Acuerdo, null);
  else if (r === '/cita') screen = h(Cita, null);
  else if (r === '/pago') screen = h(Pago, null);
  else if (pagoListo) screen = h(PagoListo, null);
  else if (datosMatch) screen = h(Datos, { group: decodeURIComponent(datosMatch[1]) });
  else screen = h(Placeholder, null);

  if (leccionMatch) {
    if (!authed) return h(Bienvenida, null);
    return screen;
  }
  if (r.startsWith('/inicio/') || datosMatch) return authed ? h(Shell, { bare: true }, screen) : h(Bienvenida, null);   // one thing at a time
  if (r === '/privacidad') return authed ? h(Shell, null, screen) : screen;
  if (PUBLIC.has(r)) return screen;
  if (!authed) return h(Bienvenida, null);
  return h(Shell, null, screen);
}

/** The icon sprite is drawn once for every screen (the shell and the full-screen lesson player). */
export function App() {
  return h(Fragment, null, h(IconSprite, null), h(Screens, null));
}
