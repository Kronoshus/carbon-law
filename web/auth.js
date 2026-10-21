const CARBON_API_BASE = "https://carbon-law.onrender.com";
async function api(path, method="GET", body=null, token=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (token) opts.headers.Authorization = "Bearer " + token;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(CARBON_API_BASE + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
function getToken() { return localStorage.getItem("carbon_token"); }
function getUser() { const user = localStorage.getItem("carbon_user"); return user ? JSON.parse(user) : null; }
function setUser(user) { localStorage.setItem("carbon_user", JSON.stringify(user)); }
function setToken(t) { localStorage.setItem("carbon_token", t); }
function clearToken() { localStorage.removeItem("carbon_token"); }
function logout() { clearToken(); localStorage.removeItem("carbon_user"); window.location.href = "login.html"; }
function requireAuth(roles) {
  const u = getUser();
  if (!getToken() || !u) { window.location.href = "login.html"; return null; }
  if (roles && !roles.includes(u.role)) { window.location.href = "index.html"; return null; }
  return u;
}
function authHeader() { const t=getToken(); return t ? "Bearer "+t : null; }
window.CarbonAuth = { logout, requireAuth, authHeader, getToken, setToken, clearToken, getUser, setUser };
