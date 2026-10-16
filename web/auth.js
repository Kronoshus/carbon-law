const API = localStorage.getItem("carbon_api") || "https://carbon-law.onrender.com";
async function api(path, method="GET", body=null, token=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (token) opts.headers.Authorization = "Bearer " + token;
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
function getToken() { return localStorage.getItem("carbon_token"); }
function setToken(t) { localStorage.setItem("carbon_token", t); }
function clearToken() { localStorage.removeItem("carbon_token"); }
function getUser() { try { return JSON.parse(localStorage.getItem("carbon_user")||"null"); } catch(e){return null;} }
function setUser(u) { localStorage.setItem("carbon_user", JSON.stringify(u)); }
