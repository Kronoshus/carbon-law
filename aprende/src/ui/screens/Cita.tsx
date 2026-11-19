
import { h } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';
import { t, lang } from '../../core/i18n';
import { apiFetch } from '../../core/api';
import './datos.css';

type Slot = { start: string; local: string };
type Booking = { id: string; kind: string; start: string; local?: string };

function fmtDay(isoDate: string): string {
  const d = new Date(isoDate + 'T12:00:00Z');
  return new Intl.DateTimeFormat(lang.value === 'es' ? 'es-ES' : 'en-US', {
    weekday: 'long', day: 'numeric', month: 'long', timeZone: 'America/Los_Angeles',
  }).format(d);
}

function fmtTime(local: string): string {
  return local.slice(11, 16);
}

export function Cita({ kind = 'consultation' }: { kind?: string }) {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [booked, setBooked] = useState<Booking | null>(null);
  const [locked, setLocked] = useState<string[] | null>(null);
  const [taken, setTaken] = useState(false);
  const [selected, setSelected] = useState<Slot | null>(null);
  const [offset, setOffset] = useState(0);
  const dialogRef = useRef<HTMLDialogElement>(null);

  const k = (new URLSearchParams(window.location.hash.split('?')[1] || '')).get('kind') || kind;

  const load = async () => {
    setTaken(false);
    const from = new Date();
    from.setDate(from.getDate() + offset * 7);
    const fromStr = from.toISOString().slice(0, 10);
    const r = await apiFetch(`/booking/slots?kind=${k}&from=${fromStr}&days=7`);
    if (r.status === 409) {
      const j = await r.json();
      setLocked(j.missing || []);
      setSlots([]);
    } else if (r.ok) {
      const j = await r.json();
      setSlots(j.slots || []);
      setLocked(null);
    }
    const br = await apiFetch('/booking');
    if (br.ok) {
      const list = await br.json();
      const mine = (list || []).find((b: Booking) => b.kind === k) || null;
      setBooked(mine);
    }
  };

  useEffect(() => { void load(); }, [offset, k]);

  useEffect(() => {
    if (selected && dialogRef.current) {
      try { dialogRef.current.showModal(); } catch { /* already open */ }
    }
  }, [selected]);

  const days = Array.from(new Set(slots.map((s) => s.local.slice(0, 10))));

  const confirm = async () => {
    if (!selected) return;
    const r = await apiFetch('/booking', { method: 'POST', json: { kind: k, start: selected.start } });
    if (dialogRef.current) dialogRef.current.close();
    setSelected(null);
    if (r.status === 409) {
      const j = await r.json();
      if (j?.error === 'taken') setTaken(true);
      await load();
      return;
    }
    if (r.ok) {
      const b = await r.json();
      setBooked(b);
      await load();
    }
  };

  const cancel = async () => {
    if (!booked) return;
    await apiFetch(`/booking/${booked.id}`, { method: 'DELETE' });
    setBooked(null);
    await load();
  };

  if (locked) {
    return h('section', { class: 'screen' },
      h('h1', null, t('cita.title')),
      h('p', null, t(`cita.locked.${k}` as any)));
  }

  if (booked) {
    const when = `${fmtDay(booked.start.slice(0, 10))}, ${fmtTime(booked.local || booked.start.replace('Z', ''))}`;
    return h('section', { class: 'screen' },
      h('h1', null, t('cita.title')),
      h('p', { role: 'status' }, t('cita.booked', { when: (booked.local ? fmtTime(booked.local) : booked.start) })),
      h('p', null, t('cita.booked.note')),
      h('div', null,
        h('button', { class: 'btn', type: 'button', onClick: cancel }, t('cita.cancel')),
        h('button', { class: 'btn secondary', type: 'button' }, t('cita.reschedule'))));
  }

  return h('section', { class: 'screen' },
    h('h1', null, t('cita.title')),
    h('p', null, t('cita.kind.' + k as any)),
    taken ? h('p', { role: 'alert' }, t('cita.taken')) : null,
    days.length === 0 ? h('p', null, t('cita.none')) : null,
    days.map((day) => h('section', { key: day },
      h('h2', null, fmtDay(day)),
      h('div', null, slots.filter((s) => s.local.startsWith(day)).map((s) =>
        h('button', { key: s.start, class: 'btn secondary', type: 'button', onClick: () => setSelected(s) },
          fmtTime(s.local)))))),
    h('div', null,
      h('button', { class: 'btn secondary', type: 'button', onClick: () => setOffset(offset - 1) }, t('cita.prev')),
      h('button', { class: 'btn secondary', type: 'button', onClick: () => setOffset(offset + 1) }, t('cita.next'))),
    h('dialog', { ref: dialogRef, 'aria-labelledby': 'cita-confirm-title' },
      h('h2', { id: 'cita-confirm-title' }, t('cita.confirm.title')),
      h('p', null, selected ? fmtTime(selected.local) : ''),
      h('div', null,
        h('button', { class: 'btn', type: 'button', onClick: confirm }, t('cita.confirm.yes')),
        h('button', { class: 'btn secondary', type: 'button', onClick: () => { dialogRef.current?.close(); setSelected(null); } }, t('cita.confirm.no')))));
}
