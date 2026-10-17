// The "Ask AI" panel: send a question, poll for the answer, keep the thread for this browser tab.
(function () {
  const $ = s => document.querySelector(s);
  let panel, thread, form, box, convId = null, busy = false, status = null;
  const store = {
    get() { try { return sessionStorage.getItem("hub-ask-conv"); } catch (e) { return null; } },
    set(v) { try { v ? sessionStorage.setItem("hub-ask-conv", v) : sessionStorage.removeItem("hub-ask-conv"); } catch (e) {} },
  };

  async function api(url, body) {
    const opts = { headers: { "x-hub": "1" }, credentials: "same-origin" };
    if (body) { opts.method = "POST"; opts.headers["content-type"] = "application/json"; opts.body = JSON.stringify(body); }
    const r = await fetch(url, opts);
    let data = {};
    try { data = await r.json(); } catch (e) {}
    if (!r.ok) throw new Error(data.error || (r.status === 401 ? "Your sign-in expired. Reload the page." : "Something went wrong."));
    return data;
  }

  function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }

  function addQuestion(q) { const m = el("div", "msg q"); m.appendChild(el("p", null, q)); thread.appendChild(m); scroll(); }
  function addAnswer(html, error) {
    const m = el("div", "msg a" + (error ? " err" : ""));
    if (error) m.appendChild(el("p", null, error)); else m.innerHTML = html;  // html is sanitised on the server
    thread.appendChild(m); scroll(); return m;
  }
  function scroll() { thread.scrollTop = thread.scrollHeight; }

  function emptyState() {
    thread.innerHTML = "";
    const intro = el("div", "ask-intro");
    if (!status || !status.enabled) {
      intro.appendChild(el("p", null, "The AI assistant isn't switched on yet."));
      if (status && status.admin) intro.appendChild(el("p", "muted", "Add its API key on the server with: python -m kit.manage set-secret ANTHROPIC_API_KEY_CHAT"));
      thread.appendChild(intro); return;
    }
    intro.appendChild(el("p", null, "Ask a question in plain English. Answers use the same numbers as the hub's pages, and say how they were counted."));
    const list = el("div", "chips");
    (status.suggestions || []).forEach(s => {
      const b = el("button", "chip", s); b.type = "button";
      b.addEventListener("click", () => { box.value = s; ask(); });
      list.appendChild(b);
    });
    intro.appendChild(list); thread.appendChild(intro);
  }

  async function loadThread() {
    convId = store.get();
    if (!convId) return emptyState();
    try {
      const data = await api("/ai/conversations/" + encodeURIComponent(convId));
      if (!data.turns.length) return emptyState();
      thread.innerHTML = "";
      data.turns.forEach(t => { addQuestion(t.question); addAnswer(t.answer_html, t.error); });
    } catch (e) { emptyState(); }
  }

  async function ask() {
    const q = box.value.trim();
    if (!q || busy) return;
    if (!status || !status.enabled) return;
    busy = true; form.querySelector("button").disabled = true;
    if (thread.querySelector(".ask-intro")) thread.innerHTML = "";
    addQuestion(q); box.value = "";
    const wait = el("div", "msg a pending"); const line = el("p", null, "Thinking"); wait.appendChild(line);
    thread.appendChild(wait); scroll();
    try {
      const start = await api("/ai/ask", { question: q, conversation_id: convId, page: location.pathname + location.search });
      convId = start.conversation_id; store.set(convId);
      const until = Date.now() + 5 * 60 * 1000;
      while (Date.now() < until) {
        await new Promise(r => setTimeout(r, 1500));
        const j = await api("/ai/jobs/" + encodeURIComponent(start.job_id));
        if (j.status === "running") { line.textContent = (j.progress || "Thinking"); continue; }
        wait.remove();
        addAnswer(j.answer_html, j.status === "failed" ? (j.error || "That didn't work. Try again.") : null);
        return;
      }
      wait.remove(); addAnswer(null, "That's taking too long. Try a narrower question.");
    } catch (e) {
      wait.remove(); addAnswer(null, e.message);
    } finally {
      busy = false; form.querySelector("button").disabled = false; box.focus();
    }
  }

  async function open() {
    panel.hidden = false; document.body.classList.add("ask-on");
    document.querySelectorAll("[data-ask-open]").forEach(b => b.setAttribute("aria-expanded", "true"));
    if (!status) { try { status = await api("/ai/status"); } catch (e) { status = { enabled: false }; } await loadThread(); }
    box.focus();
  }
  function close() {
    panel.hidden = true; document.body.classList.remove("ask-on");
    document.querySelectorAll("[data-ask-open]").forEach(b => { b.setAttribute("aria-expanded", "false"); });
  }

  document.addEventListener("DOMContentLoaded", () => {
    panel = $("#ask"); if (!panel) return;
    thread = $("#ask-thread"); form = $("#ask-form"); box = $("#ask-q");
    document.querySelectorAll("[data-ask-open]").forEach(b => b.addEventListener("click", () => panel.hidden ? open() : close()));
    panel.querySelector("[data-ask-close]").addEventListener("click", close);
    panel.querySelector("[data-ask-new]").addEventListener("click", () => { store.set(null); convId = null; emptyState(); box.focus(); });
    form.addEventListener("submit", e => { e.preventDefault(); ask(); });
    box.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } });
    document.addEventListener("keydown", e => { if (e.key === "Escape" && !panel.hidden) close(); });
    try { if (sessionStorage.getItem("hub-ask-open") === "1") open(); } catch (e) {}
    window.addEventListener("pagehide", () => { try { sessionStorage.setItem("hub-ask-open", panel.hidden ? "0" : "1"); } catch (e) {} });
  });
})();
