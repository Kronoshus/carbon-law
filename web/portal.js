const status = document.getElementById("status");
status.innerHTML = "<p>Loading...</p>";
try { document.getElementById("status").innerHTML = "<p>Your matter is currently in: Attorney Review (sample).</p>"; } catch(e) {}
document.getElementById("changeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    matter_id: document.getElementById("matter").value,
    requested_by: "client",
    change_type: document.getElementById("changeType").value,
    affected_documents: document.getElementById("docs").value
  };
  document.getElementById("out").textContent = JSON.stringify(body, null, 2);
});
document.getElementById("cancel").addEventListener("click", () => { document.getElementById("out").textContent = "Cancellation request recorded."; });
document.getElementById("reschedule").addEventListener("click", () => { document.getElementById("out").textContent = "Reschedule request recorded."; });
