export interface Platform {
  storage: {
    get(key: string): Promise<string | null>;
    set(key: string, value: string): Promise<void>;
    remove(key: string): Promise<void>;
  };
  getMicrophone(): Promise<MediaStream | null>;
  notify(title: string, body: string): Promise<void>;
  openUrl(url: string): void;
  scheduleReminder(when: number | Date, message: string): Promise<void>;
}

let current: Platform | null = null;

export function setPlatform(p: Platform): void {
  current = p;
}

export function getPlatform(): Platform {
  if (!current) throw new Error('platform not initialized');
  return current;
}

export const platform = new Proxy({} as Platform, {
  get(_target, prop) {
    const p = getPlatform() as Record<string, unknown>;
    return p[prop as string];
  },
});
