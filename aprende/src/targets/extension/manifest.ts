export function makeManifest(origin: string) {
  const host = origin.replace(/\/+$/, '');
  return {
    manifest_version: 3 as const,
    name: 'Aprende y Planea',
    version: '0.0.1',
    permissions: ['sidePanel', 'storage', 'alarms', 'notifications', 'offscreen'],
    host_permissions: [`${host}/*`],
    background: { service_worker: 'background.js', type: 'module' as const },
    side_panel: { default_path: 'sidepanel.html' },
    action: { default_popup: 'popup.html' },
  };
}
