/* The app's icon set (design doc §5): 24-unit grid, plum stroke, one fiesta fill. Rendered once as a sprite. */
export type IconName = 'mapa' | 'plan' | 'pregunta' | 'perfil' | 'sello' | 'sello-vacio';

export function IconSprite() {
  return (
    <svg width="0" height="0" style="position:absolute" aria-hidden="true">
      <defs>
        <symbol id="i-mapa" viewBox="0 0 24 24"><path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2Z" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /><path d="M9 4v14M15 6v14" stroke="currentColor" stroke-width="1.8" /></symbol>
        <symbol id="i-plan" viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" /><path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /></symbol>
        <symbol id="i-pregunta" viewBox="0 0 24 24"><path d="M4 5h16v11H10l-4 4v-4H4Z" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" /><path d="M10 9a2 2 0 1 1 2.5 2c-.4.2-.5.5-.5 1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" /><circle cx="12" cy="14" r="1" fill="currentColor" /></symbol>
        <symbol id="i-perfil" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" /><path d="M4 21a8 8 0 0 1 16 0" fill="#FFF7E6" stroke="currentColor" stroke-width="1.8" /></symbol>
        <symbol id="i-sello" viewBox="0 0 24 24"><path d="M12 2l2.4 1.8 3-.2 1 2.8 2.6 1.6-.8 2.9.8 2.9-2.6 1.6-1 2.8-3-.2L12 20l-2.4-1.8-3 .2-1-2.8L3 14l.8-2.9L3 8.2l2.6-1.6 1-2.8 3 .2Z" fill="currentColor" /><path d="m8.5 11.5 2.5 2.5 4.5-5" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" /></symbol>
        <symbol id="i-sello-vacio" viewBox="0 0 24 24"><path d="M12 2l2.4 1.8 3-.2 1 2.8 2.6 1.6-.8 2.9.8 2.9-2.6 1.6-1 2.8-3-.2L12 20l-2.4-1.8-3 .2-1-2.8L3 14l.8-2.9L3 8.2l2.6-1.6 1-2.8 3 .2Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="2 2" /></symbol>
      </defs>
    </svg>
  );
}

export function Icon({ name }: { name: IconName }) {
  return <svg class="icon" aria-hidden="true"><use href={`#i-${name}`} /></svg>;
}
