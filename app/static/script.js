// Auto-detect API base: same origin in production, localhost in dev.
// FastAPI runs on port 8000 by default (adjust if you changed it in run.py).
const API =
  window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? `${window.location.protocol}//${window.location.hostname}:${window.location.port}`
    : "https://my-agent-1000264485672.asia-south1.run.app";

const chatWindow = document.getElementById("chat-window");
const emptyState = document.getElementById("empty-state");
const messageInput = document.getElementById("message");
const sendBtn = document.getElementById("sendBtn");
const refreshHealthBtn = document.getElementById("refreshHealthBtn");
const healthText = document.getElementById("health-text");

// Loader
const startupLoader = document.getElementById("startup-loader");
const chatContent = document.getElementById("chat-content");
const loaderText = document.getElementById("loader-text");

const dots = {
  vertex: document.getElementById("dot-vertex"),
  bigquery: document.getElementById("dot-bigquery"),
  mcp: document.getElementById("dot-mcp"),
};

// ---------- helpers ----------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

const SQL_KEYWORDS = [
  "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY",
  "LEFT JOIN", "INNER JOIN", "JOIN", "ON", "AS", "LIMIT",
  "DESC", "ASC", "AND", "OR", "NOT", "IN", "COUNT", "SUM",
  "AVG", "MAX", "MIN", "WITH", "HAVING", "DISTINCT", "BETWEEN",
];

function highlightSql(sql) {
  let escaped = escapeHtml(sql);
  for (const kw of SQL_KEYWORDS) {
    const pattern = kw.replace(" ", "\\s+");
    const re = new RegExp(`\\b${pattern}\\b`, "gi");
    escaped = escaped.replace(
      re,
      (match) => `<span class="sql-kw">${match}</span>`,
    );
  }
  return escaped;
}

function hideEmptyState() {
  if (emptyState) emptyState.style.display = "none";
}

function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ---------- rendering ----------

function addUserMessage(text) {
  hideEmptyState();
  const div = document.createElement("div");
  div.className = "message user";
  div.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  chatWindow.appendChild(div);
  scrollToBottom();
}

function addLoadingMessage() {
  hideEmptyState();
  const div = document.createElement("div");
  div.className = "message bot";
  div.innerHTML = `
    <div class="avatar">AI</div>
    <div class="card loading-card">
      <span class="thinking-dots"><span></span><span></span><span></span></span>
    </div>`;
  chatWindow.appendChild(div);
  scrollToBottom();
  return div;
}

function renderTraceSteps(toolCalls) {
  if (!toolCalls || !toolCalls.length) return "";
  return toolCalls
    .map((step) => {
      const args = escapeHtml(JSON.stringify(step.args ?? {}));
      const statusClass = step.error ? "err" : "";
      const time = step.elapsed_sec != null ? `${step.elapsed_sec}s` : "";
      return `
        <div class="trace-step ${statusClass}">
          <span class="trace-tool">${escapeHtml(step.tool)}</span>
          <span class="trace-args">${args}</span>
          <span class="trace-time">${time}</span>
        </div>`;
    })
    .join("");
}

function renderAnswer(div, data, seconds) {
  const hasTrace = (data.tool_calls && data.tool_calls.length) || data.sql;
  const traceId = "trace-" + Math.random().toString(36).slice(2, 9);

  div.innerHTML = `
    <div class="avatar">AI</div>
    <div class="card">
      <p class="insight-text">${escapeHtml(data.answer || "I didn't get a response back — try asking again.")}</p>
      <div class="card-meta">
        <span class="time-pill">${seconds.toFixed(2)}s</span>
        ${hasTrace ? `<button class="trace-toggle" type="button">View query trace ▾</button>` : ""}
      </div>
      ${
        hasTrace
          ? `<div class="trace-panel" id="${traceId}" hidden>
              ${data.sql ? `<pre class="sql-block"><code>${highlightSql(data.sql)}</code></pre>` : ""}
              <div class="trace-steps">${renderTraceSteps(data.tool_calls)}</div>
            </div>`
          : ""
      }
    </div>`;

  const toggle = div.querySelector(".trace-toggle");
  const panel = div.querySelector(`#${traceId}`);
  if (toggle && panel) {
    toggle.addEventListener("click", () => {
      const isHidden = panel.hasAttribute("hidden");
      panel.toggleAttribute("hidden");
      toggle.textContent = isHidden ? "Hide query trace ▴" : "View query trace ▾";
      if (isHidden) scrollToBottom();
    });
  }
}

function renderError(div, message) {
  div.innerHTML = `
    <div class="avatar">AI</div>
    <div class="card error-card">
      <p>${escapeHtml(message)}</p>
    </div>`;
}

// ---------- chat ----------

async function sendMessage(prefillText) {
  const text = (prefillText ?? messageInput.value).trim();
  if (!text) return;

  addUserMessage(text);
  messageInput.value = "";
  autoGrow();

  const loadingDiv = addLoadingMessage();
  const start = performance.now();

  let res;
  try {
    res = await fetch(API + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
  } catch (err) {
    renderError(
      loadingDiv,
      "Couldn't reach the assistant. Check that the backend is running.",
    );
    return;
  }

  const seconds = (performance.now() - start) / 1000;
  let data;
  try {
    data = await res.json();
  } catch (err) {
    renderError(loadingDiv, "The server sent back something that wasn't valid JSON.");
    return;
  }

  if (!res.ok) {
    // FastAPI wraps validation errors as { detail: "..." }
    // and our route raises HTTPException with detail too
    const msg = data.detail || data.error || `Request failed (${res.status}).`;
    renderError(loadingDiv, msg);
    return;
  }

  renderAnswer(loadingDiv, data, seconds);
  scrollToBottom();
}

function autoGrow() {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
}

messageInput.addEventListener("input", autoGrow);

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", () => sendMessage());

document.querySelectorAll(".suggestion-chip").forEach((chip) => {
  chip.addEventListener("click", () => sendMessage(chip.textContent.trim()));
});

// ---------- health ----------

function setDot(dot, ok) {
  if (!dot) return;
  dot.classList.remove("checking", "good", "bad");
  dot.classList.add(ok ? "good" : "bad");
}

function setAllChecking() {
  Object.values(dots).forEach((dot) => {
    if (!dot) return;
    dot.classList.remove("good", "bad");
    dot.classList.add("checking");
  });
}

async function checkHealth() {
  setAllChecking();
  healthText.textContent = "Checking…";

  try {
    const res = await fetch(API + "/health");

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();

    // FastAPI health returns { status: "ok", vertex: "connected", bigquery: "connected", mcp: "connected" }
    let allGood = true;
    for (const key of Object.keys(dots)) {
      const ok = data[key] === "connected";
      if (!ok) allGood = false;
      setDot(dots[key], ok);
    }

    if (allGood) {
      healthText.textContent = "All systems connected";
      loaderText.textContent = "System ready";
      setTimeout(() => {
        startupLoader.style.display = "none";
        chatContent.style.display = "flex";
      }, 1000);
    } else {
      healthText.textContent = "Some services unavailable";
      loaderText.textContent = "Connection issues detected — check your GCP credentials.";
      // Still show the chat UI so the user can try anyway
      setTimeout(() => {
        startupLoader.style.display = "none";
        chatContent.style.display = "flex";
      }, 2000);
    }
  } catch (err) {
    Object.values(dots).forEach((dot) => setDot(dot, false));
    healthText.textContent = "Backend unreachable";
    loaderText.textContent = "Could not connect — is the server running?";
  }
}

refreshHealthBtn.addEventListener("click", checkHealth);
document.addEventListener("DOMContentLoaded", checkHealth);
