import { theme, type Theme } from '../theme';

export type CharacterId = 'calavera' | 'pinata' | 'oso' | 'girasol' | 'colibri' | 'velita' | 'tortuga';

/** Each theme's host: the one who welcomes the client, teaches most lessons and gathers the details. */
const HOST: Record<Theme, CharacterId> = { muertos: 'calavera', sol: 'girasol', huerto: 'colibri', vela: 'velita', codice: 'tortuga' };

export function host(t: Theme = theme.value): CharacterId { return HOST[t]; }

/** The lessons are written for La Calavera; outside Día de Muertos the theme's own host takes his part.
 *  Piñata and El Oso keep their parts in every theme. */
export function cast(id: CharacterId): CharacterId { return id === 'calavera' ? host() : id; }

/** The ids are also the i18n keys and the picture names. */
export const nameKey = (id: CharacterId) => `character.${id}.name` as const;
