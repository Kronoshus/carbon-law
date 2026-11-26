import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import type { I18nKey } from '../../core/i18n-keys';
import { apiFetch } from '../../core/api';
import { OFFICE, officeAddress, officeMap, officeTel } from '../../core/office';
import { LoadFailed, problemOf, type LoadProblem } from '../LoadFailed';
import './datos.css';
import './cita.css';

type Kind = 'signing' | 'consultation';
type Slot = { start: string; local: string };
type Booking = { id: string; kind: Kind; start: string };
const TZ = 'America/Los_Angeles';
const day = (iso: string) => new Intl.DateTimeFormat(lang.value, { weekday: 'long', day: 'numeric', month: 'long', timeZone: TZ }).format(new Date(iso));
const time = (iso: string) => new Intl.DateTimeFormat(lang.value, { hour: 'numeric', minute: '2-digit', timeZone: TZ }).format(new Date(iso));
const DAY = 86_400_000;

/** Book, change or cancel a signing or a consultation (spec 6.1 days 4 and 10). Times are the office's (Los Angeles). */
export function Cita() {
  const kind: Kind = new URLSearchParams(location.hash.split('?')[1] ?? '').get('kind') === 'signing' ? 'signing' : 'consultation';
  const [week, setWeek] = useState(0);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [booking, setBooking] = useState<Booking | null>(null);
  const [locked, setLocked] = useState(false);
  const [changing, setChanging] = useState(false);
  const [picked, setPicked] = useState<Slot | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [note, setNote] = useState<'taken' | 'error' | null>(null);
  const [problem, setProblem] = useState<LoadProblem | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const answered = (x: Response | null): x is Response => !!x && (x.ok || x.status === 409);       // 409: signing not open yet

  const load = async () => {
    setProblem(null);
    const from = new Date(Date.now() + week * 7 * DAY).toISOString().slice(0, 10);
    const [r, mine] = await Promise.all([apiFetch(`/booking/slots?kind=${kind}&from=${from}&days=7`), apiFetch('/booking')].map((p) => p.catch(() => null)));
    if (!answered(r) || !answered(mine)) { setProblem(problemOf(answered(r) ? mine : r)); return; }
    setLocked(r.status === 409);
    setSlots(r.ok ? (await r.json()).slots : []);
    setBooking(((await mine.json()) as Booking[]).find((b) => b.kind === kind) ?? null);
  };
  useEffect(() => { void load(); }, [week]);
  useEffect(() => { if (picked || cancelling) dialog.current?.showModal(); }, [picked, cancelling]);

  const confirm = async () => {
    if (!picked) return;
    dialog.current?.close();
    const r = await (booking
      ? apiFetch(`/booking/${booking.id}`, { method: 'PATCH', json: { start: picked.start } })
      : apiFetch('/booking', { method: 'POST', json: { kind, start: picked.start } })).catch(() => null);
    setNote(r?.status === 409 ? 'taken' : r?.ok ? null : 'error');
    if (r?.ok) setChanging(false);
    await load();
  };
  const cancel = async () => {
    dialog.current?.close();
    const r = await apiFetch(`/booking/${booking!.id}`, { method: 'DELETE' }).catch(() => null);
    setNote(r?.ok ? null : 'error');
    await load();
  };
  const ask = h('dialog', { ref: dialog, class: 'confirm', 'aria-labelledby': 'cita-confirm', onClose: () => { setPicked(null); setCancelling(false); } },
    h('h2', { id: 'cita-confirm' }, t(cancelling ? 'cita.cancel.title' : 'cita.confirm.title')),
    cancelling && booking ? h('p', null, `${day(booking.start)}, ${time(booking.start)}`) : picked ? h('p', null, `${day(picked.start)}, ${time(picked.start)}`) : null,
    h('div', { class: 'composer-actions' },
      h('button', { class: 'btn secondary', type: 'button', onClick: () => dialog.current?.close() }, t('cita.confirm.no')),
      h('button', { class: 'btn', type: 'button', onClick: () => void (cancelling ? cancel() : confirm()) }, t(cancelling ? 'cita.cancel.yes' : 'cita.confirm.yes'))));

  if (problem) return h(LoadFailed, { title: 'cita.title', problem, retry: () => void load() });
  const head = [h('h1', { key: 'h' }, t('cita.title')), h('p', { key: 'k', class: 'kind' }, t(`cita.kind.${kind}` as I18nKey))];
  if (locked && !booking) return h('section', { class: 'screen datos-page' }, head, h('p', null, t(`cita.locked.${kind}` as I18nKey)),
    kind === 'signing' ? h('a', { class: 'btn', href: '#/revisar' }, t('revisar.title')) : h('a', { class: 'btn', href: '#/aprender' }, t('empty.today')));
  const late = booking && new Date(booking.start).getTime() - Date.now() < DAY;
  const errors = note ? h('p', { class: 'gate-error', role: 'alert' }, t(note === 'taken' ? 'cita.taken' : 'datos.error')) : null;
  if (booking && !changing) {
    return h('section', { class: 'screen datos-page' }, head,
      h('p', { class: 'confirmed', role: 'status' }, t('cita.booked', { when: `${day(booking.start)}, ${time(booking.start)}` })),
      kind === 'signing' ? h('p', { class: 'place' }, t('cita.place.signing'), ' ',
        h('a', { href: officeMap, target: '_blank', rel: 'noopener noreferrer' }, officeAddress)) : null,
      errors,
      late ? h('p', null, t('cita.late'), ' ', h('a', { href: officeTel }, OFFICE.phone)) : [
        h('p', { key: 'n' }, t('cita.booked.note')),
        h('div', { key: 'a', class: 'resumen-actions' },
          h('button', { class: 'btn secondary', type: 'button', onClick: () => setChanging(true) }, t('cita.reschedule')),
          h('button', { class: 'btn secondary', type: 'button', onClick: () => setCancelling(true) }, t('cita.cancel')))], ask);
  }
  const days = [...new Set(slots.map((s) => s.local.slice(0, 10)))];
  return h('section', { class: 'screen datos-page' }, head,
    h('h2', { class: 'choose' }, t('cita.choose')),
    errors,
    days.length ? days.map((d) => h('section', { key: d, class: 'slot-day' },
      h('h3', null, day(slots.find((s) => s.local.startsWith(d))!.start)),
      h('div', { class: 'slots' }, slots.filter((s) => s.local.startsWith(d)).map((s) =>
        h('button', { key: s.start, class: 'slot', type: 'button', onClick: () => setPicked(s) }, time(s.start))))))
      : h('p', null, t('cita.none')),
    h('div', { class: 'week-nav' },
      h('button', { class: 'btn secondary', type: 'button', disabled: week === 0, onClick: () => setWeek(week - 1) }, t('cita.prev')),
      h('button', { class: 'btn secondary', type: 'button', onClick: () => setWeek(week + 1) }, t('cita.next'))),
    ask);
}
