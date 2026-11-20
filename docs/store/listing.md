# Chrome Web Store listing — DRAFT

**Borrador / Draft. Not published.** Publishing waits for Kevin's yes (brief section 7). The privacy wording needs the
attorney's approval (#52). Written by the Opus test writer (p8-tests), 2026-11-20. Screenshots: `screenshots/` (1280 × 800 PNG).

## Item
- Name: Aprende y Planea
- Category: Education
- Language: Spanish (primary), English
- Privacy policy URL: https://carbon.bailment.tech/aprende/#/privacidad
- Homepage URL: https://carbon.bailment.tech/aprende/
- Support email: info@carbonlaw.com

## Spanish (es)
Short description (es): Aprenda sobre testamentos y fideicomisos en California, a su ritmo, con Carbon Law Group.

Detailed description (es):
Aprende y Planea es la aplicación de Carbon Law Group para aprender, en español y en inglés, qué es un testamento, un
fideicomiso en vida, un poder para finanzas y una directiva de salud.

- Cuatro lecciones cortas, una al día, con La Calavera, la Piñata y El Oso.
- Los personajes son programas de inteligencia artificial: no son el abogado y no dan asesoría legal.
- Cuando usted quiera, prepara su plan con el despacho: el abogado revisa y decide todo.
- La extensión abre la aplicación en el panel lateral de Chrome. Guarda solo su sesión y la borra cuando cierra Chrome.

Información general, no asesoría legal.

## English (en)
Short description (en): Learn about wills and trusts in California, at your own pace, with Carbon Law Group.

Detailed description (en):
Aprende y Planea is Carbon Law Group's app for learning, in Spanish and English, what a will, a living trust, a
financial power of attorney and a health care directive are.

- Four short lessons, one a day, with La Calavera, the Piñata and El Oso.
- The characters are artificial intelligence programs: they are not the attorney and they do not give legal advice.
- When you are ready, you prepare your plan with the firm: the attorney reviews and decides everything.
- The extension opens the app in Chrome's side panel. It keeps only your session and clears it when you close Chrome.

General information, not legal advice.

## Single purpose
Open Carbon Law Group's estate-planning lessons (Aprende y Planea) in Chrome's side panel, with a toolbar popup that
shows today's step.

## Permission justifications
- `sidePanel`: the app runs in Chrome's side panel; the popup's "Abrir" button opens it.
- `storage`: keeps the sign-in session in `chrome.storage.session` (memory only, cleared when Chrome closes). Nothing is
  written to `chrome.storage.local` or `sync`.
- Host `https://carbon-law.onrender.com/*`: the firm's own server, the only one the extension talks to.

## Remote code
No. Every script is in the package; the content security policy allows only the package's own scripts.

## Data use (the Store's privacy practices form)
- Collected: personally identifiable information (name, email), authentication information (the session), user activity
  (lesson progress), website content the user writes (answers and questions to the firm).
- To confirm with the attorney: health information (the answers for the health care directive may name wishes about
  care) and financial information (the trust answers name property). Card data is never collected: payment is on
  Stripe's page.
- Not collected: location, web history, personal communications outside the app, immigration status.
- Certifications to tick: not sold to third parties; not used or transferred for purposes unrelated to the item's single
  purpose; not used or transferred to determine creditworthiness or for lending.
