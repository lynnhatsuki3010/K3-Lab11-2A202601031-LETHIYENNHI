// Lab 11 demo client — vanilla JS, no build step.
// Talks to client/server.py (FastAPI) at /api/*.

const state = {
  activeTarget: "unsafe",
  sessionIds: {}, // target -> random browser session id (kept per page load)
  targets: [],
  history: {}, // target -> [{role, text, badge}]
};

function uuid() {
  return "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function ensureSession(target) {
  if (!state.sessionIds[target]) {
    state.sessionIds[target] = uuid();
  }
  if (!state.history[target]) {
    state.history[target] = [];
  }
}

async function loadTargets() {
  const res = await fetch("/api/targets");
  const data = await res.json();
  state.targets = data.targets;
  const list = document.getElementById("target-list");
  list.innerHTML = "";
  data.targets.forEach((t) => {
    ensureSession(t.id);
    const btn = document.createElement("button");
    btn.className = "target-btn" + (t.id === state.activeTarget ? " active" : "");
    btn.dataset.target = t.id;
    btn.innerHTML = `<strong>${t.label}</strong><span>${t.description}</span>`;
    btn.onclick = () => selectTarget(t.id);
    list.appendChild(btn);
  });
  updateHeader();
}

async function loadPresets() {
  const res = await fetch("/api/presets");
  const data = await res.json();
  const list = document.getElementById("preset-list");
  list.innerHTML = "";
  data.presets.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "preset-btn";
    btn.innerHTML = `<span class="preset-cat">${p.category}</span><span class="preset-text">${escapeHtml(
      p.input.slice(0, 90)
    )}${p.input.length > 90 ? "..." : ""}</span>`;
    btn.onclick = () => {
      document.getElementById("chat-input").value = p.input;
      document.getElementById("chat-input").focus();
    };
    list.appendChild(btn);
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function selectTarget(targetId) {
  state.activeTarget = targetId;
  ensureSession(targetId);
  document.querySelectorAll(".target-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.target === targetId);
  });
  updateHeader();
  renderMessages();
}

function updateHeader() {
  const t = state.targets.find((x) => x.id === state.activeTarget);
  document.getElementById("active-target-label").textContent = t
    ? t.label
    : state.activeTarget;
}

function renderMessages() {
  const box = document.getElementById("messages");
  box.innerHTML = "";
  const hist = state.history[state.activeTarget] || [];
  if (hist.length === 0) {
    const empty = document.createElement("div");
    empty.className = "msg system";
    empty.textContent = "Chưa có tin nhắn nào — thử một prompt mẫu bên trái, hoặc tự gõ câu hỏi.";
    box.appendChild(empty);
    return;
  }
  hist.forEach((m) => {
    const div = document.createElement("div");
    div.className = "msg " + m.role;
    if (m.badge) {
      const badge = document.createElement("span");
      badge.className = "badge " + m.badge.cls;
      badge.textContent = m.badge.text;
      div.appendChild(badge);
      div.appendChild(document.createElement("br"));
    }
    div.appendChild(document.createTextNode(m.text));
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
}

function badgeFor(result) {
  if (result.leaked) {
    return { cls: "badge-leaked", text: "LEAKED" };
  }
  if (result.blocked) {
    return { cls: "badge-blocked", text: "BLOCKED (" + (result.layer || "?") + ")" };
  }
  return { cls: "badge-ok", text: "OK" };
}

async function sendMessage(text) {
  const target = state.activeTarget;
  ensureSession(target);
  state.history[target].push({ role: "user", text });
  renderMessages();

  const sendBtn = document.getElementById("send-btn");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        target,
        session_id: state.sessionIds[target],
        message: text,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || res.statusText);
    }
    const data = await res.json();
    state.history[target].push({
      role: "agent",
      text: data.response,
      badge: badgeFor(data),
    });
  } catch (e) {
    state.history[target].push({
      role: "system",
      text: "Lỗi: " + e.message,
    });
  } finally {
    sendBtn.disabled = false;
    renderMessages();
  }
}

async function resetActive() {
  const target = state.activeTarget;
  await fetch("/api/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target, session_id: state.sessionIds[target] }),
  });
  state.sessionIds[target] = uuid();
  state.history[target] = [];
  renderMessages();
}

document.getElementById("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  sendMessage(text);
});

document.getElementById("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("chat-form").requestSubmit();
  }
});

document.getElementById("reset-btn").addEventListener("click", resetActive);

loadTargets();
loadPresets();
