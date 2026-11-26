let authorization = null;
let currentSession = null;
let currentRole = null;
const $ = (selector) => document.querySelector(selector);

function notice(message) { $("#notice").textContent = message; }
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (authorization) headers.set("Authorization", authorization);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response;
  try { response = await fetch(path, {...options, headers}); }
  catch { throw new Error("Cannot reach the server."); }
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try { message = (await response.json()).message || message; } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
function button(text, handler, className) {
  const element = node("button", text, className);
  element.type = "button";
  element.addEventListener("click", async () => {
    element.disabled = true;
    try { notice(""); await handler(); } catch (error) { notice(error.message); }
    finally { element.disabled = false; }
  });
  return element;
}
async function loadPackages() {
  const params = new URLSearchParams(new FormData($("#filters")));
  for (const [key, value] of [...params]) if (!value) params.delete(key);
  const packages = await api(`/api/packages?${params}`);
  const container = $("#packages");
  container.replaceChildren();
  if (!packages.length) container.append(node("p", "No trips match your search."));
  for (const item of packages) {
    const card = node("article", undefined, "card");
    card.append(node("div", item.destination.toUpperCase(), "card-art"));
    const body = node("div", undefined, "card-body");
    body.append(node("h3", item.title), node("p", `${item.duration_days} days · Departs ${item.start_date}`),
      node("p", `${item.capacity} seats available`));
    const bottom = node("div", undefined, "card-bottom");
    bottom.append(node("strong", `₹${Number(item.price).toLocaleString("en-IN")}`),
      button("Book trip", async () => {
        if (!authorization) throw new Error("Please sign in to book.");
        const quantity = prompt("Number of travellers (1–10):", "1");
        if (quantity === null) return;
        if (!/^(?:[1-9]|10)$/.test(quantity)) throw new Error("Enter a quantity from 1 to 10.");
        const booking = await api("/api/bookings", {method:"POST", headers:{"Idempotency-Key":crypto.randomUUID()}, body:JSON.stringify({lines:[{item_id:item.id,quantity:Number(quantity)}]})});
        notice(`Booking #${booking.id} confirmed.`);
        await Promise.all([loadPackages(), loadBookings()]);
      }));
    body.append(bottom); card.append(body); container.append(card);
    if (currentRole === "admin") {
      const controls = node("div", undefined, "card-bottom");
      controls.append(button("Edit", async () => {
        const form = $("#package-form");
        for (const key of ["id", "title", "destination", "duration_days", "price", "capacity", "start_date"]) form.elements[key].value = item[key];
        form.scrollIntoView({behavior: "smooth"});
      }, "secondary"), button("Disable", async () => {
        if (!confirm(`Disable ${item.title}?`)) return;
        await api(`/api/packages/${item.id}`, {method:"DELETE"});
        notice("Package disabled.");
        await loadPackages();
      }, "secondary"));
      body.append(controls);
    }
  }
}
async function loadBookings() {
  const container = $("#bookings");
  container.replaceChildren();
  if (!authorization) { container.append(node("p", "Sign in to see your bookings.")); return; }
  const bookings = await api("/api/bookings");
  if (!bookings.length) container.append(node("p", "No bookings yet."));
  for (const booking of bookings) {
    const row = node("div", undefined, "list-item");
    row.append(node("span", `Booking #${booking.id} · ${booking.status} · ₹${booking.total}${booking.refund !== null ? ` · Refund ₹${booking.refund}` : ""}`));
    if (booking.status === "CONFIRMED") row.append(button("Cancel booking", async () => {
      if (!confirm("Cancel this booking? The refund depends on the departure date.")) return;
      const result = await api(`/api/bookings/${booking.id}/cancel`, {method:"POST"});
      notice(`Booking cancelled. Simulated refund: ₹${result.refund}.`);
      await Promise.all([loadBookings(), loadPackages()]);
    }, "secondary"));
    container.append(row);
  }
}
async function loadSessions() {
  $("#sessions").replaceChildren();
  if (!authorization) return;
  for (const session of await api("/api/chat/sessions")) {
    $("#sessions").append(button(session.title, async () => { currentSession = session.id; await loadMessages(); }));
  }
}
function renderMessage(message) {
  const bubble = node("div", undefined, `bubble ${message.role}`);
  bubble.append(node("div", message.content));
  if (message.metadata?.mode) bubble.append(node("small", message.metadata.mode));
  for (const source of message.metadata?.citations || []) {
    bubble.append(node("small", `Source: ${source.filename} · page/section ${source.page} · v${source.version} · ${source.chunk_id}`));
  }
  for (const action of message.metadata?.actions || []) {
    const box = node("div", undefined, "action");
    box.append(node("strong", "Confirmation required"), node("pre", JSON.stringify(action.terms, null, 2)),
      node("small", `Expires ${action.expires_at} UTC`));
    for (const [label, accepted] of [["Confirm", true], ["Reject", false]]) {
      box.append(button(label, async () => {
        const result = await api(`/api/chat/actions/${action.pending_action_id}/confirm`, {method:"POST", body:JSON.stringify({confirm:accepted})});
        notice(`Action ${result.status.toLowerCase()}.`);
        await Promise.all([loadMessages(), loadBookings(), loadPackages()]);
      }, accepted ? "" : "secondary"));
    }
    bubble.append(box);
  }
  $("#messages").append(bubble);
}
async function loadMessages() {
  if (!currentSession) return;
  const messages = [];
  let after = 0;
  while (true) {
    const page = await api(`/api/chat/sessions/${currentSession}/messages?after=${after}&limit=200`);
    messages.push(...page);
    if (page.length < 200) break;
    after = page[page.length - 1].seq_no;
  }
  $("#messages").replaceChildren();
  messages.forEach(renderMessage);
  $("#messages").scrollTop = $("#messages").scrollHeight;
}
$("#filters").addEventListener("submit", async (event) => {
  event.preventDefault(); try { await loadPackages(); } catch (error) { notice(error.message); }
});
$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    authorization = `Basic ${btoa(`${form.get("username")}:${form.get("password")}`)}`;
    const user = await api("/api/me");
    currentRole = user.role;
    $("#identity").textContent = `${user.username} · ${user.role}`;
    $("#admin").classList.toggle("hidden", user.role !== "admin");
    event.currentTarget.reset(); notice("Signed in successfully.");
    currentSession = null;
    $("#messages").replaceChildren(node("p", "Start or select a conversation."));
    await Promise.all([loadBookings(), loadSessions(), loadPackages()]);
  } catch (error) {
    authorization = null; currentSession = null; currentRole = null; $("#identity").textContent = "Browsing as guest";
    $("#admin").classList.add("hidden"); $("#sessions").replaceChildren();
    $("#messages").replaceChildren(node("p", "Sign in and start a conversation."));
    await loadBookings(); notice(error.message);
  }
});
$("#logout").addEventListener("click", () => {
  authorization = null; currentSession = null; currentRole = null; $("#identity").textContent = "Browsing as guest";
  $("#admin").classList.add("hidden"); $("#sessions").replaceChildren();
  $("#messages").replaceChildren(node("p", "Sign in and start a conversation."));
  loadBookings(); loadPackages().catch(error => notice(error.message)); notice("Signed out.");
});
$("#refresh-bookings").addEventListener("click", () => loadBookings().catch(error => notice(error.message)));
$("#package-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget));
  const id = data.id; delete data.id; data.active = true;
  try { await api(id ? `/api/packages/${id}` : "/api/packages", {method:id ? "PUT" : "POST",body:JSON.stringify(data)}); notice("Package saved."); event.currentTarget.reset(); await loadPackages(); }
  catch (error) { notice(error.message); }
});
$("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { const result = await api("/api/documents", {method:"POST",body:new FormData(event.currentTarget)}); notice(`Indexed ${result.filename}, version ${result.version}.`); event.currentTarget.reset(); }
  catch (error) { notice(error.message); }
});
$("#new-chat").addEventListener("click", async () => {
  try {
    if (!authorization) throw new Error("Please sign in first.");
    currentSession = (await api("/api/chat/sessions", {method:"POST"})).id;
    await Promise.all([loadSessions(), loadMessages()]);
  } catch (error) { notice(error.message); }
});
$("#chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const field = $("#chat-input"); const message = field.value;
  if (!currentSession) { notice("Start or select a conversation first."); return; }
  const send = event.currentTarget.querySelector("button");
  send.disabled = true; $("#chat-loading").classList.remove("hidden");
  try {
    await api(`/api/chat/sessions/${currentSession}/messages`, {method:"POST",body:JSON.stringify({message})});
    field.value = ""; await Promise.all([loadMessages(), loadSessions()]);
  } catch (error) { notice(error.message); await loadMessages(); }
  finally { send.disabled = false; $("#chat-loading").classList.add("hidden"); }
});
loadPackages().catch(error => notice(error.message));
