/**
 * CertiChain — app.js
 * Connects the static HTML frontend to the FastAPI + Neon backend.
 * Drop this file next to index.html (replaces the old stub app.js).
 */

// ─── CONFIG ─────────────────────────────────────────────────────────────────
const API = "http://localhost:8000";   // change to your deployed URL in prod

// ─── HELPERS ────────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function token() { return localStorage.getItem("cc_token"); }
function role()  { return localStorage.getItem("cc_role"); }
function uname() { return localStorage.getItem("cc_username"); }

async function apiFetch(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  if (token()) headers["Authorization"] = `Bearer ${token()}`;
  const res = await fetch(`${API}${path}`, { ...opts, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

function showToast(msg, color = "#0F0F0F") {
  let t = document.getElementById("cc-toast");
  if (!t) {
    t = document.createElement("div");
    t.id = "cc-toast";
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.style.background = color;
  t.classList.add("cc-toast--show");
  setTimeout(() => t.classList.remove("cc-toast--show"), 2800);
}

function logout() {
  localStorage.removeItem("cc_token");
  localStorage.removeItem("cc_role");
  localStorage.removeItem("cc_username");
  localStorage.removeItem("cc_name");
  window.location.href = "index.html";
}

// Redirect if not logged in (call at top of protected pages)
function requireAuth(requiredRole) {
  if (!token() || role() !== requiredRole) {
    window.location.href =
      requiredRole === "student" ? "student-login.html" : "university-login.html";
  }
}

// ─── MOBILE DRAWER ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  $$("[data-mobile-nav-toggle]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id     = btn.getAttribute("aria-controls");
      const drawer = document.getElementById(id);
      if (!drawer) return;
      const open = drawer.getAttribute("data-open") === "true";
      drawer.setAttribute("data-open", open ? "false" : "true");
      btn.setAttribute("aria-expanded", open ? "false" : "true");
    });
  });

  // Close drawer on outside click
  document.addEventListener("click", (e) => {
    $$("[data-mobile-drawer]").forEach((drawer) => {
      const toggle = $(`[aria-controls="${drawer.id}"]`);
      if (!drawer.contains(e.target) && toggle && !toggle.contains(e.target)) {
        drawer.setAttribute("data-open", "false");
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }
    });
  });

  // ── Copy buttons ──────────────────────────────────────────────────────────
  $$("[data-copy-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.copyTarget);
      if (!target) return;
      navigator.clipboard.writeText(target.value).then(() =>
        showToast("Copied to clipboard")
      );
    });
  });

  // ── Ripple ────────────────────────────────────────────────────────────────
  $$("[data-ripple]").forEach((el) => {
    el.addEventListener("click", (e) => {
      const r   = document.createElement("span");
      const box = el.getBoundingClientRect();
      const sz  = Math.max(box.width, box.height);
      r.style.cssText = `
        position:absolute;width:${sz}px;height:${sz}px;border-radius:50%;
        background:rgba(255,255,255,0.25);pointer-events:none;
        left:${e.clientX - box.left - sz / 2}px;
        top:${e.clientY - box.top - sz / 2}px;
        animation:ripple .5s ease-out forwards;
      `;
      if (!document.getElementById("cc-ripple-style")) {
        const s = document.createElement("style");
        s.id = "cc-ripple-style";
        s.textContent = `@keyframes ripple{from{transform:scale(0);opacity:1}to{transform:scale(2.5);opacity:0}}`;
        document.head.appendChild(s);
      }
      el.style.position = "relative";
      el.style.overflow  = "hidden";
      el.appendChild(r);
      setTimeout(() => r.remove(), 600);
    });
  });

  // Dispatch to page-specific init
  const page = location.pathname.split("/").pop() || "index.html";
  const inits = {
    "index.html":                  initIndex,
    "student-login.html":          initStudentLogin,
    "student.html":                initStudentVault,
    "university-login.html":       initUniversityLogin,
    "university.html":             initUniversityDashboard,
    "university-issue.html":       initUniversityIssue,
    "university-revoke.html":      initUniversityRevoke,
    "employer.html":               initEmployerVerify,
  };
  if (inits[page]) inits[page]();
});

// ─── INDEX ───────────────────────────────────────────────────────────────────
function initIndex() {
  // Inject auth-aware nav changes (Connect Wallet → profile)
  const walletBtn = $("[data-ripple]");
  if (token() && walletBtn) {
    walletBtn.textContent = `${localStorage.getItem("cc_name") || uname()} ↗`;
    walletBtn.addEventListener("click", () => {
      role() === "student"
        ? (window.location.href = "student.html")
        : (window.location.href = "university.html");
    });
  }
}

// ─── STUDENT LOGIN ───────────────────────────────────────────────────────────
function initStudentLogin() {
  const form    = document.getElementById("student-login-form");
  const errEl   = document.getElementById("login-error");
  const loadEl  = document.getElementById("login-loading");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = form.username.value.trim();
    const password = form.password.value;
    if (errEl) errEl.textContent = "";
    if (loadEl) loadEl.hidden = false;

    try {
      const data = await apiFetch("/api/auth/student/login", {
        method:  "POST",
        body:    JSON.stringify({ username, password }),
        headers: {},
      });
      localStorage.setItem("cc_token",    data.token);
      localStorage.setItem("cc_role",     "student");
      localStorage.setItem("cc_username", data.username);
      localStorage.setItem("cc_name",     data.name);
      localStorage.setItem("cc_wallet",   data.wallet);
      window.location.href = "student.html";
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
    } finally {
      if (loadEl) loadEl.hidden = true;
    }
  });
}

// ─── STUDENT VAULT ───────────────────────────────────────────────────────────
function initStudentVault() {
  requireAuth("student");

  const nameEl   = document.getElementById("student-name");
  const walletEl = document.getElementById("student-wallet");
  const gridEl   = document.getElementById("credentials-grid");
  const countEl  = document.getElementById("credential-count");

  if (nameEl)   nameEl.textContent   = localStorage.getItem("cc_name") || "";
  if (walletEl) walletEl.textContent = localStorage.getItem("cc_wallet") || "";

  // Wire logout
  $$("[data-logout]").forEach((b) => b.addEventListener("click", logout));

  loadStudentCredentials();

  async function loadStudentCredentials() {
    if (!gridEl) return;
    gridEl.innerHTML = `<div class="col-span-3 text-center py-12 font-mono text-sm text-ink/40">Loading vault…</div>`;

    try {
      const data = await apiFetch("/api/student/credentials");
      if (countEl) countEl.textContent = `${data.credentials.length} verified assets · Cryptographically secured`;
      renderCredentialCards(data.credentials, gridEl);
    } catch (err) {
      gridEl.innerHTML = `<div class="col-span-3 text-center py-12 text-red-500 font-mono text-sm">${err.message}</div>`;
    }
  }
}

function renderCredentialCards(creds, container) {
  if (!creds.length) {
    container.innerHTML = `<div class="col-span-3 text-center py-20 font-mono text-sm text-ink/35">No credentials found in vault.</div>`;
    return;
  }

  container.innerHTML = creds.map((c) => {
    const sd      = c.student_data || {};
    const status  = c.is_revoked ? "REVOKED" : "VERIFIED";
    const color   = c.is_revoked ? "#B03A2A" : "#2A7A5A";
    const border  = c.is_revoked ? "" : "border-l-2 border-l-seal";

    return `
      <div class="interactive-surface bg-paper border border-mist/50 ${border} p-6 rounded-[6px]
                  hover:border-ink/40 flex flex-col justify-between min-h-[280px]
                  shadow-[0_1px_3px_rgba(15,15,15,0.04)]">
        <div>
          <div class="flex justify-between items-start mb-6">
            <span class="font-sans font-medium uppercase text-[11px] tracking-[0.08em] text-on-surface-variant">
              ${escHtml(c.university)}
            </span>
            <span class="font-mono text-[11px] px-2 py-0.5 border" style="border-color:${color};color:${color}">
              ${status}
            </span>
          </div>
          <h3 class="font-serif text-[22px] leading-tight mb-1">${escHtml(sd.program || "Certificate")}</h3>
          <p class="text-on-surface-variant text-[14px]">${escHtml(sd.degree_class || "")}</p>
        </div>
        <div class="mt-auto flex items-end justify-between">
          <span class="font-mono text-[12px] text-on-surface-variant opacity-60 uppercase">
            ${sd.graduation_date || formatDate(c.issued_at)}
          </span>
          <div class="flex gap-2">
            <button type="button" class="icon-btn p-2 border border-mist/50 rounded-[6px] hover:bg-ink hover:text-paper"
                    onclick="copyHash('${escHtml(c.hash)}')" aria-label="Copy hash">
              <span class="material-symbols-outlined text-[20px]">content_copy</span>
            </button>
            <button type="button" class="icon-btn p-2 border border-mist/50 rounded-[6px] hover:bg-ink hover:text-paper"
                    onclick="showHash('${escHtml(c.hash)}')" aria-label="Show hash">
              <span class="material-symbols-outlined text-[20px]">qr_code_2</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

window.copyHash = function (h) {
  navigator.clipboard.writeText(h).then(() => showToast("Hash copied — paste on Verify page"));
};

window.showHash = function (h) {
  showToast(`Hash: ${h.slice(0, 18)}…`);
  // Also populate the share panel input if present
  const inp = document.getElementById("share-certificate-hash-input");
  if (inp) inp.value = h;
};

// ─── UNIVERSITY LOGIN ─────────────────────────────────────────────────────────
function initUniversityLogin() {
  const form  = document.getElementById("university-login-form");
  const errEl = document.getElementById("login-error");

  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = form.username.value.trim();
    const password = form.password.value;
    if (errEl) errEl.textContent = "";

    try {
      const data = await apiFetch("/api/auth/university/login", {
        method:  "POST",
        body:    JSON.stringify({ username, password }),
        headers: {},
      });
      localStorage.setItem("cc_token",    data.token);
      localStorage.setItem("cc_role",     "university");
      localStorage.setItem("cc_username", data.username);
      localStorage.setItem("cc_name",     data.name);
      window.location.href = "university.html";
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
    }
  });
}

// ─── UNIVERSITY DASHBOARD ─────────────────────────────────────────────────────
function initUniversityDashboard() {
  requireAuth("university");

  const nameEl = document.getElementById("uni-name");
  if (nameEl) nameEl.textContent = localStorage.getItem("cc_name") || "";

  $$("[data-logout]").forEach((b) => b.addEventListener("click", logout));

  loadStats();
  loadRecentAnchors();

  async function loadStats() {
    try {
      const s = await apiFetch("/api/university/stats");
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
      set("stat-total",   s.total_issued  ?? "—");
      set("stat-today",   s.anchored_today ?? "—");
      set("stat-revoked", s.revoked       ?? "—");
    } catch (_) {}
  }

  async function loadRecentAnchors() {
    const list = document.getElementById("recent-anchors");
    if (!list) return;
    try {
      const data = await apiFetch("/api/university/credentials");
      const recent = data.credentials.slice(0, 5);
      if (!recent.length) {
        list.innerHTML = `<li class="py-4 text-ink/40 font-mono text-sm">No credentials yet.</li>`;
        return;
      }
      list.innerHTML = recent.map((c) => {
        const sd     = c.student_data || {};
        const color  = c.is_revoked ? "#B03A2A" : "#2A7A5A";
        const status = c.is_revoked ? "Revoked" : "Verified";
        return `
          <li class="flex flex-col gap-1 rounded-[6px] py-4 transition-colors
                     hover:bg-paper/70 sm:flex-row sm:items-baseline sm:justify-between sm:px-3">
            <span class="font-mono text-[13px] text-ink/55">${c.hash.slice(0, 10)}…</span>
            <span class="text-[15px] text-ink/85">${escHtml(sd.program || "Certificate")} · ${escHtml(sd.legal_name || "")}</span>
            <span class="font-mono text-[11px] uppercase tracking-tight" style="color:${color}">${status}</span>
          </li>
        `;
      }).join("");
    } catch (_) {}
  }
}

// ─── UNIVERSITY ISSUE ─────────────────────────────────────────────────────────
function initUniversityIssue() {
  requireAuth("university");

  const dropzone  = document.getElementById("csv-dropzone");
  const fileInput = document.getElementById("csv-file-input");
  const queueBtn  = document.getElementById("queue-btn");
  const resultEl  = document.getElementById("issue-result");
  let   pendingFile = null;

  if (!dropzone) return;

  // Click to browse
  dropzone.addEventListener("click", () => fileInput && fileInput.click());
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("border-seal/80", "bg-surface-container-lowest");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-seal/80", "bg-surface-container-lowest");
  });
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("border-seal/80", "bg-surface-container-lowest");
    const f = e.dataTransfer.files[0];
    if (f) selectFile(f);
  });

  if (fileInput) {
    fileInput.addEventListener("change", () => {
      if (fileInput.files[0]) selectFile(fileInput.files[0]);
    });
  }

  function selectFile(f) {
    if (!f.name.endsWith(".csv")) { showToast("Only .csv files accepted", "#B03A2A"); return; }
    pendingFile = f;
    const label = dropzone.querySelector("p");
    if (label) label.textContent = `✓ ${f.name} selected — click "Queue for signing"`;
    showToast(`${f.name} ready to upload`);
  }

  if (queueBtn) {
    queueBtn.addEventListener("click", async () => {
      if (!pendingFile) { showToast("Please select a CSV file first", "#B03A2A"); return; }

      queueBtn.disabled    = true;
      queueBtn.textContent = "Signing + anchoring…";

      const fd = new FormData();
      fd.append("file", pendingFile);

      try {
        const res = await fetch(`${API}/api/university/upload-csv`, {
          method:  "POST",
          headers: { Authorization: `Bearer ${token()}` },
          body:    fd,
        });
        if (!res.ok) throw new Error((await res.json()).detail);
        const data = await res.json();

        showToast(`✓ ${data.issued} credentials anchored on Polygon`);

        if (resultEl) {
          resultEl.hidden = false;
          resultEl.innerHTML = `
            <div class="rounded-[6px] border border-[#2A7A5A]/40 bg-[#2A7A5A]/5 p-6 mt-8">
              <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-[#2A7A5A] mb-3">Batch receipt</p>
              <p class="text-[15px] text-ink">${data.message}</p>
              <p class="font-mono text-[12px] text-ink/50 mt-2">Network: ${data.network} · Chain ID: ${data.chain_id}</p>
              <div class="mt-4 space-y-2 max-h-52 overflow-y-auto">
                ${(data.results || []).map(r => `
                  <div class="flex justify-between items-center py-1 border-b border-mist/30">
                    <span class="text-sm text-ink/80">${escHtml(r.name)}</span>
                    <span class="font-mono text-[11px] ${r.status === 'issued' ? 'text-[#2A7A5A]' : 'text-ink/40'}">${r.status}</span>
                  </div>
                `).join("")}
              </div>
            </div>
          `;
        }
      } catch (err) {
        showToast(err.message, "#B03A2A");
      } finally {
        queueBtn.disabled    = false;
        queueBtn.textContent = "Queue for signing";
        pendingFile = null;
      }
    });
  }
}

// ─── UNIVERSITY REVOKE ────────────────────────────────────────────────────────
function initUniversityRevoke() {
  requireAuth("university");

  const list = document.getElementById("revoke-list");
  if (!list) return;

  loadRevokeList();

  async function loadRevokeList() {
    list.innerHTML = `<li class="py-8 text-center font-mono text-sm text-ink/40">Loading credentials…</li>`;
    try {
      const data = await apiFetch("/api/university/credentials");
      if (!data.credentials.length) {
        list.innerHTML = `<li class="py-8 text-center font-mono text-sm text-ink/40">No credentials issued yet.</li>`;
        return;
      }
      list.innerHTML = data.credentials.map((c) => {
        const sd      = c.student_data || {};
        const revoked = c.is_revoked;
        const color   = revoked ? "#B03A2A" : "#2A7A5A";
        const status  = revoked ? "Revoked" : "Verified";

        return `
          <li class="flex flex-col gap-3 py-6 transition-colors hover:bg-paper/80
                     sm:flex-row sm:items-center sm:justify-between sm:px-4" data-hash="${escHtml(c.hash)}">
            <div>
              <p class="font-sans text-[15px] font-medium text-ink">${escHtml(sd.legal_name || "—")}</p>
              <p class="mt-1 font-sans text-[12px] text-ink/50">${escHtml(sd.program || "")} · ${escHtml(sd.graduation_date || "")}</p>
              <p class="mt-2 font-mono text-[13px] text-ink/45">${c.hash.slice(0, 18)}…</p>
            </div>
            <div class="flex items-center gap-4">
              <span class="font-mono text-[11px] uppercase tracking-tight" style="color:${color}">${status}</span>
              ${revoked
                ? `<button disabled class="rounded-[6px] border border-mist/50 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.08em] text-ink/35">Already revoked</button>`
                : `<button type="button" data-revoke-hash="${escHtml(c.hash)}"
                          class="revoke-btn rounded-[6px] border border-mist px-4 py-2 text-[11px]
                                 font-medium uppercase tracking-[0.08em] text-error transition-colors
                                 hover:border-error hover:bg-error/5 icon-btn">
                     Revoke
                   </button>`
              }
            </div>
          </li>
        `;
      }).join("");

      // Wire revoke buttons
      $$(".revoke-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const h = btn.dataset.revokeHash;
          if (!confirm("Revoke this credential? This cannot be undone.")) return;
          btn.disabled    = true;
          btn.textContent = "Revoking…";
          try {
            await apiFetch("/api/university/revoke", {
              method: "POST",
              body:   JSON.stringify({ hash: h }),
            });
            showToast("Credential revoked and ledger state updated");
            loadRevokeList();
          } catch (err) {
            showToast(err.message, "#B03A2A");
            btn.disabled    = false;
            btn.textContent = "Revoke";
          }
        });
      });
    } catch (err) {
      list.innerHTML = `<li class="py-8 text-center text-red-500 font-mono text-sm">${err.message}</li>`;
    }
  }
}

// ─── EMPLOYER VERIFY ──────────────────────────────────────────────────────────
function initEmployerVerify() {
  // Tab switching
  $$("[data-verify-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$("[data-verify-tab]").forEach((b) => {
        const active = b.dataset.verifyTab === btn.dataset.verifyTab;
        b.classList.toggle("bg-ink",    active);
        b.classList.toggle("text-paper", active);
        b.classList.toggle("shadow-sm",  active);
        b.classList.toggle("opacity-60", !active);
        b.setAttribute("aria-selected", active);
      });
      $$("[data-verify-panel]").forEach((p) => {
        p.classList.toggle("hidden", p.dataset.verifyPanel !== btn.dataset.verifyTab);
      });
    });
  });

  // Look Up button
  const lookupBtn = $("[data-lookup-btn]") || (() => {
    // fallback: find the Look Up button by text
    return $$("button").find(b => b.textContent.trim() === "Look Up");
  })();

  const hashInput = $("input[placeholder*='hash' i]") || $("input[type='text']");
  const resultEl  = document.getElementById("verify-result");

  if (lookupBtn && hashInput) {
    lookupBtn.addEventListener("click", () => doVerify(hashInput.value.trim()));
  }

  // Also allow Enter in input
  if (hashInput) {
    hashInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") doVerify(hashInput.value.trim());
    });
  }

  // Simulate scan button
  const scanBtn = $("[data-verify-panel='scan'] button");
  if (scanBtn) {
    scanBtn.addEventListener("click", () => {
      // Copy the pre-filled hash from paste panel as demo
      if (hashInput) doVerify(hashInput.value.trim());
    });
  }

  async function doVerify(hash) {
    if (!hash) { showToast("Paste a certificate hash first", "#B03A2A"); return; }
    if (lookupBtn) { lookupBtn.disabled = true; lookupBtn.textContent = "Verifying…"; }

    try {
      const d = await apiFetch("/api/verify", {
        method: "POST",
        body:   JSON.stringify({ hash }),
        headers: {},
      });
      renderVerifyResult(d);
    } catch (err) {
      renderVerifyError(err.message);
    } finally {
      if (lookupBtn) { lookupBtn.disabled = false; lookupBtn.textContent = "Look Up"; }
    }
  }

  function renderVerifyResult(d) {
    if (!resultEl) return;

    if (!d.found) {
      resultEl.innerHTML = `
        <div class="interactive-surface relative overflow-hidden bg-surface-container-lowest
                    rounded-[6px] border border-mist/50">
          <div class="absolute top-0 left-0 w-full h-1 bg-[#B03A2A]"></div>
          <div class="p-8 text-center">
            <p class="font-mono text-[11px] uppercase tracking-widest text-[#B03A2A] mb-3">Not Found</p>
            <p class="font-serif text-2xl text-ink mb-2">No matching credential</p>
            <p class="font-sans text-sm text-on-surface-variant/70">
              This hash does not exist in the CertiChain registry.
            </p>
          </div>
        </div>`;
      return;
    }

    const isRevoked = d.is_revoked;
    const statusColor = isRevoked ? "#B03A2A" : "#2A7A5A";
    const statusLabel = isRevoked ? "Revoked" : "Verified";
    const statusIcon  = isRevoked ? "cancel"  : "verified_user";
    const barColor    = isRevoked ? "#B03A2A" : "#C17A3A";

    resultEl.innerHTML = `
      <div class="interactive-surface relative overflow-hidden bg-surface-container-lowest
                  rounded-[6px] border border-mist/50">
        <div class="absolute top-0 left-0 w-full h-1" style="background:${barColor}"></div>
        <div class="p-8">
          <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-2 px-2 py-1 border" style="border-color:${statusColor}">
              <span class="material-symbols-outlined text-[14px]"
                    style="color:${statusColor};font-variation-settings:'FILL' 1">${statusIcon}</span>
              <span class="font-mono text-[11px] uppercase tracking-widest" style="color:${statusColor}">
                ${statusLabel}
              </span>
            </div>
            <div class="text-right">
              <span class="font-mono text-[12px] text-ink/30 uppercase tracking-tighter">
                Chain ID: ${d.chain_id || 137}
              </span>
            </div>
          </div>
          <div class="mb-8">
            <h2 class="font-serif text-[28px] leading-tight mb-2 text-ink">
              ${escHtml(d.program || "Certificate")}
            </h2>
            <div class="space-y-1">
              <p class="font-body text-ink font-medium">${escHtml(d.student_name || "—")}</p>
              <p class="font-body text-on-surface-variant text-sm">
                ${escHtml(d.university)} · Academic Ledger
              </p>
              <p class="font-body text-on-surface-variant/60 text-sm italic">
                Issued: ${formatDate(d.issued_at)}
              </p>
              ${isRevoked ? `<p class="font-mono text-[11px] text-[#B03A2A] uppercase mt-1">
                Revoked: ${formatDate(d.revoked_at)}
              </p>` : ""}
            </div>
          </div>
          <div class="flex justify-between items-end pt-6 border-t border-mist/30">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-ink/40 text-[16px]">link</span>
                <span class="font-mono text-[12px] text-on-surface-variant">
                  Block #${(d.block_number || 0).toLocaleString()}
                </span>
              </div>
              <p class="font-mono text-[12px] text-ink/40">Anchored on Polygon</p>
            </div>
            <div class="text-right">
              <p class="font-mono text-[12px] text-ink/20">${d.verification_ms || 1400}ms</p>
            </div>
          </div>
        </div>
      </div>`;
  }

  function renderVerifyError(msg) {
    if (!resultEl) return;
    resultEl.innerHTML = `
      <div class="p-8 border border-mist/50 rounded-[6px] bg-surface-container-lowest text-center">
        <p class="font-mono text-[11px] text-[#B03A2A] uppercase tracking-widest mb-2">Error</p>
        <p class="text-sm text-ink/70">${escHtml(msg)}</p>
      </div>`;
  }
}

// ─── UTILS ───────────────────────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    year: "numeric", month: "long", day: "numeric",
  });
}