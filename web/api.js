const API_BASE = "https://carbon-law.onrender.com";
async function carbonApi(path, method="GET", body=null) {
  const opts = { method, headers: {"Content-Type":"application/json"} };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
window.CarbonAPI = { api: carbonApi };
