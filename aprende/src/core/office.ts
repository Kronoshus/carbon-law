import office from './office.json';

/** The office where signings happen, and its phone. The backend reads the same file for its emails and reminders. */
export const OFFICE = office;
export const officeAddress = `${office.name}, ${office.street}, ${office.city}`;
export const officeTel = `tel:+1${office.phone.replace(/\D/g, '')}`;
export const officeMap = `https://maps.google.com/?q=${`${office.street} ${office.city}`.replace(/,/g, '').split(/\s+/).join('+')}`;
