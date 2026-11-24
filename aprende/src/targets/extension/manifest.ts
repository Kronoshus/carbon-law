export function makeManifest(origin: string) {
  const host = origin.replace(/\/+$/, '');
  const icons = { '16': 'icons/icon-16.png', '48': 'icons/icon-48.png', '128': 'icons/icon-128.png' };
  return {
    manifest_version: 3 as const,
    name: 'Memento Mori',
    version: '0.1.0',
    description: 'Lecciones de planificación patrimonial de Carbon Law Group. Estate-planning lessons.',
    icons,
    action: { default_popup: 'popup.html', default_icon: icons },
    permissions: ['sidePanel', 'storage'],
    host_permissions: [`${host}/*`],
    content_security_policy: { extension_pages: `script-src 'self'; object-src 'self'; connect-src 'self' ${host}` },
    background: { service_worker: 'background.js', type: 'module' as const },
    side_panel: { default_path: 'sidepanel.html' },
  };
}
