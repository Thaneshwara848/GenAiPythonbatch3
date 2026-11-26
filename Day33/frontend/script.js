"use strict";

const $ = selector => document.querySelector(selector);
let credentials = null;
let currentSession = null;
let basket = new Map();
let basketKey = crypto.randomUUID();

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}

function notify(message) {
  $("#notice").textContent = message;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (credentials) headers.set("Authorization", `Basic ${btoa(credentials.username + ":" + credentials.password)}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response;
  try { response = await fetch(path, {...options, headers}); }
  catch { throw new Error("Cannot reach the server. Please try again."); }
  if (!response.ok) {
    let error;
    try { error = await response.json(); } catch { error = {}; }
    throw new Error(error.message || `Request failed (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}

function guard(fn) {
  return async event => {
    if (event) event.preventDefault();
    try { notify(""); await fn(event); }
    catch (error) { notify(error.message); }
  };
}

function requireLogin() {
  if (!credentials) throw new Error("Please sign in first.");
}

async function loadMenu() {
  const form = new FormData($("#filters"));
  const params = new URLSearchParams();
  for (const key of ["keyword", "category", "max_price"]) if (form.get(key)) params.set(key, form.get(key));
  if (form.has("vegetarian")) params.set("vegetarian", "true");
  const items = await request("/api/menu_items?" + params);
  const grid = $("#menu-grid");
  grid.replaceChildren();
  if (!items.length) grid.append(node("p", "No dishes match your filters.", "muted"));
  for (const item of items) {
    const card = node("article", undefined, "menu-item");
    card.append(node("span", `${item.category} · ${item.vegetarian ? "VEGETARIAN" : "NON-VEGETARIAN"}`, "tag"),
                node("h3", item.title), node("span", `${item.capacity} portions available`, "muted"));
    const foot = node("div", undefined, "item-foot");
    const add = node("button", item.capacity ? "+ Add to basket" : "Sold out");
    add.disabled = !item.capacity;
    add.addEventListener("click", () => {
      const current = basket.get(item.id);
      if (current && current.quantity >= Math.min(10, item.capacity)) { notify("Maximum available quantity reached."); return; }
      basket.set(item.id, {item, quantity: current ? current.quantity + 1 : 1});
      basketKey = crypto.randomUUID();
      renderBasket();
    });
    foot.append(node("span", `₹${Number(item.price).toFixed(2)}`, "price"), add);
    card.append(foot);
    grid.append(card);
  }
}

function renderBasket() {
  const container = $("#basket");
  container.replaceChildren();
  if (!basket.size) { container.textContent = "Your basket is empty."; return; }
  for (const [id, entry] of basket) {
    const row = node("div", undefined, "basket-line");
    const quantity = node("input");
    quantity.type = "number"; quantity.min = "1"; quantity.max = "10"; quantity.value = entry.quantity;
    quantity.setAttribute("aria-label", `Quantity for ${entry.item.title}`);
    quantity.addEventListener("change", () => {
      const value = Number(quantity.value);
      if (!Number.isInteger(value) || value < 1 || value > 10) { quantity.value = entry.quantity; notify("Quantity must be between 1 and 10."); return; }
      entry.quantity = value; basketKey = crypto.randomUUID();
    });
    const remove = node("button", "Remove", "quiet");
    remove.addEventListener("click", () => { basket.delete(id); basketKey = crypto.randomUUID(); renderBasket(); });
    row.append(node("span", entry.item.title), quantity, remove);
    container.append(row);
  }
}

async function loadOrders() {
  requireLogin();
  const orders = await request("/api/orders");
  const list = $("#orders");
  list.replaceChildren();
  if (!orders.length) list.append(node("p", "No orders yet.", "muted"));
  for (const order of orders) {
    const row = node("div", undefined, "order");
    row.append(node("strong", `#${order.id} · ${order.status}`),
               node("div", `Total ₹${Number(order.total).toFixed(2)} · ${order.lines.map(line => `item #${line.item_id} × ${line.quantity}`).join(", ")}`, "muted"));
    if (order.status === "CONFIRMED") {
      const cancel = node("button", "Cancel order", "quiet");
      cancel.addEventListener("click", guard(async () => {
        if (!window.confirm(`Cancel order #${order.id}?`)) return;
        await request(`/api/orders/${order.id}/cancel`, {method: "POST", headers: {"Idempotency-Key": crypto.randomUUID()}});
        await Promise.all([loadOrders(), loadMenu()]);
      }));
      row.append(cancel);
    }
    list.append(row);
  }
}

async function loadSessions(selectId = currentSession) {
  requireLogin();
  const sessions = await request("/api/chat/sessions");
  const select = $("#sessions");
  select.replaceChildren(node("option", "Select a conversation"));
  select.firstChild.value = "";
  for (const session of sessions) {
    const option = node("option", session.title);
    option.value = session.id;
    select.append(option);
  }
  select.value = selectId || "";
}

async function loadMessages() {
  requireLogin();
  if (!currentSession) return;
  let after = 0, messages = [], data;
  do {
    data = await request(`/api/chat/sessions/${currentSession}/messages?after=${after}&limit=100`);
    messages = messages.concat(data.messages);
    if (data.messages.length) after = data.messages[data.messages.length - 1].seq_no;
  } while (data.messages.length === 100);
  const area = $("#messages");
  area.replaceChildren();
  for (const message of messages) {
    const bubble = node("div", message.content, `bubble ${message.role}`);
    if (message.metadata?.citations?.length) {
      bubble.append(node("div", message.metadata.citations.map(c => `${c.filename}, page ${c.page} (v${c.version})`).join(" · "), "sources"));
    }
    area.append(bubble);
  }
  if (!messages.length) area.append(node("div", "Say hello to your food pal.", "empty"));
  area.scrollTop = area.scrollHeight;
  const actions = $("#actions");
  actions.replaceChildren();
  for (const action of data.pending_actions) {
    const box = node("div", undefined, "action");
    const description = action.action === "create_order"
      ? action.details.preview.map(line => `${line.title} × ${line.quantity} at ₹${line.unit_price}`).join(", ")
      : `Cancel order #${action.details.order_id} (₹${action.details.total})`;
    box.append(node("strong", action.status === "PROCESSING" ? "Retry to reconcile:" : "Please confirm:"),
               node("div", description), node("small", `Expires ${new Date(action.expires_at + "Z").toLocaleString()}`));
    for (const [label, confirmed] of [["Confirm", true], ["Reject", false]]) {
      if (!confirmed && action.status === "PROCESSING") continue;
      const button = node("button", label, confirmed ? "" : "quiet");
      button.addEventListener("click", guard(async () => {
        await request(`/api/chat/actions/${action.id}/confirm`, {method: "POST", body: JSON.stringify({confirm: confirmed})});
        await Promise.all([loadMessages(), loadOrders(), loadMenu()]);
      }));
      box.append(button);
    }
    actions.append(box);
  }
}

$("#filters").addEventListener("submit", guard(loadMenu));
$("#login-form").addEventListener("submit", guard(async event => {
  const form = new FormData(event.target);
  credentials = {username: form.get("username"), password: form.get("password")};
  let user;
  try { user = await request("/api/me"); } catch (error) { credentials = null; throw error; }
  event.target.reset();
  $("#identity").textContent = `Signed in as ${user.username}`;
  $("#logout").hidden = false; $("#login-card").hidden = true; $("#admin").hidden = user.role !== "admin";
  await Promise.all([loadOrders(), loadSessions()]);
}));
$("#logout").addEventListener("click", () => {
  credentials = null; currentSession = null; $("#identity").textContent = "Browsing as guest";
  $("#logout").hidden = true; $("#login-card").hidden = false; $("#admin").hidden = true;
  $("#orders").textContent = "Sign in to see your orders."; $("#sessions").replaceChildren(node("option", "Select a conversation"));
  $("#messages").replaceChildren(node("div", "Sign in and start a conversation.", "empty")); $("#actions").replaceChildren();
});
$("#place-order").addEventListener("click", guard(async () => {
  requireLogin();
  if (!basket.size) throw new Error("Add an item to your basket first.");
  const lines = [...basket.values()].map(({item, quantity}) => ({item_id: item.id, quantity}));
  const order = await request("/api/orders", {method: "POST", headers: {"Idempotency-Key": basketKey}, body: JSON.stringify({lines})});
  basket.clear(); basketKey = crypto.randomUUID(); renderBasket();
  await Promise.all([loadOrders(), loadMenu()]); notify(`Order #${order.id} placed successfully.`);
}));
$("#refresh-orders").addEventListener("click", guard(loadOrders));
$("#new-session").addEventListener("click", guard(async () => {
  requireLogin();
  const session = await request("/api/chat/sessions", {method: "POST", body: JSON.stringify({title: "Food conversation"})});
  currentSession = session.id; await loadSessions(currentSession); await loadMessages();
}));
$("#sessions").addEventListener("change", guard(async event => {
  currentSession = Number(event.target.value) || null;
  if (currentSession) await loadMessages();
}));
$("#chat-form").addEventListener("submit", guard(async event => {
  requireLogin();
  if (!currentSession) throw new Error("Start or select a conversation first.");
  const input = $("#chat-message"), text = input.value.trim(), button = event.target.querySelector("button");
  if (!text) return;
  input.value = ""; button.disabled = true; button.textContent = "Thinking…";
  try { await request(`/api/chat/sessions/${currentSession}/messages`, {method: "POST", body: JSON.stringify({message: text})}); }
  finally { button.disabled = false; button.textContent = "Send ↑"; await loadMessages(); }
}));

function itemPayload() {
  const form = new FormData($("#item-form"));
  return {title: form.get("title"), category: form.get("category"), price: form.get("price"),
          capacity: Number(form.get("capacity")), vegetarian: form.has("vegetarian"), active: form.has("active")};
}
$("#item-form").addEventListener("submit", guard(async () => {
  await request("/api/menu_items", {method: "POST", body: JSON.stringify(itemPayload())}); await loadMenu(); notify("Menu item created.");
}));
$("#update-item").addEventListener("click", guard(async () => {
  const id = Number(new FormData($("#item-form")).get("id")); if (!id) throw new Error("Enter an item ID.");
  await request(`/api/menu_items/${id}`, {method: "PUT", body: JSON.stringify(itemPayload())}); await loadMenu(); notify("Menu item updated.");
}));
$("#disable-item").addEventListener("click", guard(async () => {
  const id = Number(new FormData($("#item-form")).get("id")); if (!id) throw new Error("Enter an item ID.");
  await request(`/api/menu_items/${id}`, {method: "DELETE"}); await loadMenu(); notify("Menu item disabled.");
}));
$("#status-form").addEventListener("submit", guard(async event => {
  const form = new FormData(event.target);
  await request(`/api/admin/orders/${Number(form.get("id"))}/status`, {method: "PATCH", body: JSON.stringify({status: form.get("status")})});
  notify("Order status updated.");
}));
$("#upload-form").addEventListener("submit", guard(async event => {
  await request("/api/documents", {method: "POST", body: new FormData(event.target)}); event.target.reset(); notify("Document indexed.");
}));
loadMenu().catch(error => notify(error.message));
