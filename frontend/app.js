/**
 * CertiChain — app.js
 * Connects the static HTML frontend to the FastAPI + Neon backend.
 */

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const API = "http://localhost:8000";

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function token()  { return localStorage.getItem("cc_token"); }
function role()   { return localStorage.getItem("cc_role"); }
function ccName() { return localStorage.getItem("cc_name"); }
function uname()  { return localStorage.getItem("cc_username"); }

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
  ["cc_token","cc_role","cc_username","cc_name","cc_wallet"].forEach(k =>
    localStorage.removeItem(k)
  );
  window.location.href = "index.html";
}

function requireAuth(requiredRole) {
  if (!token() || role() !== requiredRole) {
    window.location.href =
      requiredRole === "student" ? "student-login.html" : "university-login.html";
  }
}

function escHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", {
    year: "numeric", month: "long", day: "numeric",
  });
}

// ─── BOOT ────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {

  // Mobile drawer
  $$("[data-mobile-nav-toggle]").forEach(btn => {
    btn.addEventListener("click", () => {
      const drawer = document.getElementById(btn.getAttribute("aria-controls"));
      if (!drawer) return;
      const open = drawer.getAttribute("data-open") === "true";
      drawer.setAttribute("data-open", open ? "false" : "true");
      btn.setAttribute("aria-expanded", String(!open));
    });
  });
  document.addEventListener("click", e => {
    $$("[data-mobile-drawer]").forEach(drawer => {
      const toggle = $(`[aria-controls="${drawer.id}"]`);
      if (!drawer.contains(e.target) && toggle && !toggle.contains(e.target)) {
        drawer.setAttribute("data-open", "false");
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      }
    });
  });

  // Copy buttons
  $$("[data-copy-target]").forEach(btn => {
    btn.addEventListener("click", () => {
      const el = document.getElementById(btn.dataset.copyTarget);
      if (!el) return;
      navigator.clipboard.writeText(el.value || el.textContent)
        .then(() => showToast("Copied to clipboard"));
    });
  });

  // Ripple effect
  $$("[data-ripple]").forEach(el => {
    el.addEventListener("click", e => {
      const r = document.createElement("span");
      const box = el.getBoundingClientRect();
      const sz = Math.max(box.width, box.height);
      r.style.cssText = `position:absolute;width:${sz}px;height:${sz}px;border-radius:50%;
        background:rgba(255,255,255,0.25);pointer-events:none;
        left:${e.clientX-box.left-sz/2}px;top:${e.clientY-box.top-sz/2}px;
        animation:ripple .5s ease-out forwards;`;
      if (!document.getElementById("cc-ripple-style")) {
        const s = document.createElement("style");
        s.id = "cc-ripple-style";
        s.textContent = `@keyframes ripple{from{transform:scale(0);opacity:1}to{transform:scale(2.5);opacity:0}}`;
        document.head.appendChild(s);
      }
      el.style.position = "relative";
      el.style.overflow = "hidden";
      el.appendChild(r);
      setTimeout(() => r.remove(), 600);
    });
  });

  // Logout buttons
  $$("[data-logout]").forEach(b => b.addEventListener("click", logout));

  // Route to page init
  const page = location.pathname.split("/").pop() || "index.html";
  const routes = {
    "index.html":             initIndex,
    "student-login.html":     initStudentLogin,
    "student.html":           initStudentVault,
    "university-login.html":  initUniversityLogin,
    "university.html":        initUniversityDashboard,
    "university-issue.html":  initUniversityIssue,
    "university-revoke.html": initUniversityRevoke,
    "employer.html":          initEmployerVerify,
  };
  if (routes[page]) routes[page]();
});

// ══════════════════════════════════════════════════════════════════════════════
// INDEX
// ══════════════════════════════════════════════════════════════════════════════
function initIndex() {
  const walletBtn = $("[data-ripple]");
  if (token() && walletBtn) {
    walletBtn.textContent = `${ccName() || uname()} ↗`;
    walletBtn.addEventListener("click", () => {
      window.location.href = role() === "student" ? "student.html" : "university.html";
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// STUDENT LOGIN
// ══════════════════════════════════════════════════════════════════════════════
function initStudentLogin() {
  const form  = document.getElementById("student-login-form");
  const errEl = document.getElementById("login-error");
  if (!form) return;

  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (errEl) errEl.textContent = "";
    const btn = form.querySelector("button[type='submit']");
    if (btn) { btn.disabled = true; btn.textContent = "Signing in…"; }

    try {
      const data = await apiFetch("/api/auth/student/login", {
        method: "POST",
        body: JSON.stringify({
          username: form.username.value.trim(),
          password: form.password.value,
        }),
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
      if (btn) { btn.disabled = false; btn.textContent = "Sign In"; }
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// STUDENT VAULT
// ══════════════════════════════════════════════════════════════════════════════
function initStudentVault() {
  requireAuth("student");

  const nameEl   = document.getElementById("student-name");
  const walletEl = document.getElementById("student-wallet");
  const gridEl   = document.getElementById("credentials-grid");
  const countEl  = document.getElementById("credential-count");

  if (nameEl)   nameEl.textContent   = ccName() || "";
  if (walletEl) walletEl.textContent = localStorage.getItem("cc_wallet") || "";

  loadStudentCredentials();

  async function loadStudentCredentials() {
    if (!gridEl) return;
    gridEl.innerHTML = `<div class="col-span-3 text-center py-12 font-mono text-sm text-ink/40">Loading vault…</div>`;

    try {
      const data = await apiFetch("/api/student/credentials");
      if (countEl) countEl.textContent =
        `${data.credentials.length} verified asset${data.credentials.length !== 1 ? "s" : ""} · Cryptographically secured`;
      renderCredentialCards(data.credentials, gridEl);
    } catch (err) {
      gridEl.innerHTML = `<div class="col-span-3 text-center py-12 font-mono text-sm text-[#B03A2A]">${escHtml(err.message)}</div>`;
    }
  }
}

function renderCredentialCards(creds, container) {
  if (!creds.length) {
    container.innerHTML = `
      <div class="col-span-3 text-center py-20 font-mono text-sm text-ink/35">
        No credentials found in vault.<br/>
        <span class="text-[11px] opacity-60">Ask your university to upload your credential CSV.</span>
      </div>`;
    return;
  }

  container.innerHTML = creds.map(c => {
    const sd      = c.student_data || {};
    const revoked = c.is_revoked;
    const color   = revoked ? "#B03A2A" : "#2A7A5A";
    const label   = revoked ? "REVOKED"  : "VERIFIED";
    const border  = revoked ? "" : "border-l-2 border-l-seal";
    const name    = sd.legal_name || sd.name || "—";
    const program = sd.program    || sd.major || "Certificate";
    const degree  = sd.degree_class || sd.degree || "";
    const date    = sd.graduation_date || formatDate(c.issued_at);

    return `
      <div class="interactive-surface bg-paper border border-mist/50 ${border} p-6 rounded-[6px]
                  hover:border-ink/40 flex flex-col justify-between min-h-[280px]
                  shadow-[0_1px_3px_rgba(15,15,15,0.04)]">
        <div>
          <div class="flex justify-between items-start mb-6">
            <span class="font-sans font-medium uppercase text-[11px] tracking-[0.08em] text-on-surface-variant truncate max-w-[60%]">
              ${escHtml(c.university)}
            </span>
            <span class="font-mono text-[11px] px-2 py-0.5 border shrink-0"
                  style="border-color:${color};color:${color}">${label}</span>
          </div>
          <h3 class="font-serif text-[22px] leading-tight mb-1">${escHtml(program)}</h3>
          <p class="text-on-surface-variant text-[14px]">${escHtml(degree)}</p>
          <p class="text-on-surface-variant/60 text-[13px] mt-1">${escHtml(name)}</p>
        </div>
        <div class="mt-auto pt-4">
          <!-- Hash display — click to copy -->
          <div class="mb-4 flex items-center gap-2 bg-surface-container-low rounded-[4px] px-3 py-2">
            <span class="font-mono text-[10px] text-ink/50 truncate flex-1" id="hash-${escHtml(c.hash.slice(2,10))}">
              ${escHtml(c.hash)}
            </span>
            <button type="button"
                    onclick="copyToClipboard('${escHtml(c.hash)}')"
                    class="icon-btn shrink-0 p-1 hover:text-seal" aria-label="Copy hash">
              <span class="material-symbols-outlined text-[16px]">content_copy</span>
            </button>
          </div>
          <div class="flex items-end justify-between">
            <span class="font-mono text-[11px] text-on-surface-variant opacity-60 uppercase">${escHtml(date)}</span>
            <div class="flex gap-2">
              <button type="button"
                      onclick="openVerifyWithHash('${escHtml(c.hash)}')"
                      class="icon-btn p-2 border border-mist/50 rounded-[6px] hover:bg-ink hover:text-paper"
                      aria-label="Verify on employer page">
                <span class="material-symbols-outlined text-[18px]">open_in_new</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// Copy hash and show toast
window.copyToClipboard = function(text) {
  navigator.clipboard.writeText(text).then(() =>
    showToast("Hash copied — paste on the Verify page")
  );
};

// Open employer verify page with hash pre-filled via URL param
window.openVerifyWithHash = function(hash) {
  window.open(`employer.html?hash=${encodeURIComponent(hash)}`, "_blank");
};

// ══════════════════════════════════════════════════════════════════════════════
// UNIVERSITY LOGIN
// ══════════════════════════════════════════════════════════════════════════════
function initUniversityLogin() {
  const form  = document.getElementById("university-login-form");
  const errEl = document.getElementById("login-error");
  if (!form) return;

  form.addEventListener("submit", async e => {
    e.preventDefault();
    if (errEl) errEl.textContent = "";
    const btn = form.querySelector("button[type='submit']");
    if (btn) { btn.disabled = true; btn.textContent = "Signing in…"; }

    try {
      const data = await apiFetch("/api/auth/university/login", {
        method: "POST",
        body: JSON.stringify({
          username: form.username.value.trim(),
          password: form.password.value,
        }),
        headers: {},
      });
      localStorage.setItem("cc_token",    data.token);
      localStorage.setItem("cc_role",     "university");
      localStorage.setItem("cc_username", data.username);
      localStorage.setItem("cc_name",     data.name);
      window.location.href = "university.html";
    } catch (err) {
      if (errEl) errEl.textContent = err.message;
      if (btn) { btn.disabled = false; btn.textContent = "Sign In"; }
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// UNIVERSITY DASHBOARD
// ══════════════════════════════════════════════════════════════════════════════
function initUniversityDashboard() {
  requireAuth("university");

  const nameEl = document.getElementById("uni-name");
  if (nameEl) nameEl.textContent = ccName() || "";

  loadStats();
  loadRecentAnchors();

  async function loadStats() {
    try {
      const s = await apiFetch("/api/university/stats");
      const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? "—"; };
      set("stat-total",   s.total_issued);
      set("stat-today",   s.anchored_today);
      set("stat-revoked", s.revoked);
    } catch (_) {}
  }

  async function loadRecentAnchors() {
    const list = document.getElementById("recent-anchors");
    if (!list) return;
    try {
      const data   = await apiFetch("/api/university/credentials");
      const recent = data.credentials.slice(0, 5);
      if (!recent.length) {
        list.innerHTML = `<li class="py-4 text-ink/40 font-mono text-sm">No credentials yet — upload a CSV to get started.</li>`;
        return;
      }
      list.innerHTML = recent.map(c => {
        const sd     = c.student_data || {};
        const name   = sd.legal_name || sd.name || "—";
        const prog   = sd.program    || sd.major || "Certificate";
        const color  = c.is_revoked ? "#B03A2A" : "#2A7A5A";
        const status = c.is_revoked ? "Revoked" : "Verified";
        return `
          <li class="flex flex-col gap-1 rounded-[6px] py-4 transition-colors
                     hover:bg-paper/70 sm:flex-row sm:items-baseline sm:justify-between sm:px-3">
            <span class="font-mono text-[13px] text-ink/55">${escHtml(c.hash.slice(0,18))}…</span>
            <span class="text-[15px] text-ink/85">${escHtml(prog)} · ${escHtml(name)}</span>
            <span class="font-mono text-[11px] uppercase tracking-tight" style="color:${color}">${status}</span>
          </li>`;
      }).join("");
    } catch (_) {}
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// UNIVERSITY ISSUE
// ══════════════════════════════════════════════════════════════════════════════
function initUniversityIssue() {
  requireAuth("university");

  const dropzone  = document.getElementById("csv-dropzone");
  const fileInput = document.getElementById("csv-file-input");
  const queueBtn  = document.getElementById("queue-btn");
  const resultEl  = document.getElementById("issue-result");
  let   pendingFile = null;

  if (!dropzone) return;

  // Click dropzone → open file browser
  dropzone.addEventListener("click", () => fileInput && fileInput.click());

  dropzone.addEventListener("dragover", e => {
    e.preventDefault();
    dropzone.classList.add("border-seal/80", "bg-surface-container-lowest");
  });
  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("border-seal/80", "bg-surface-container-lowest");
  });
  dropzone.addEventListener("drop", e => {
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
    if (!f.name.endsWith(".csv")) {
      showToast("Only .csv files accepted", "#B03A2A");
      return;
    }
    pendingFile = f;
    const label = dropzone.querySelector("p");
    if (label) label.textContent = `✓  ${f.name} ready`;
    dropzone.classList.add("border-seal/60");
    showToast(`${f.name} selected`);
  }

  if (queueBtn) {
    queueBtn.addEventListener("click", async () => {
      if (!pendingFile) {
        showToast("Select a CSV file first", "#B03A2A");
        return;
      }

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
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Upload failed" }));
          throw new Error(err.detail);
        }
        const data = await res.json();

        showToast(`✓ ${data.issued} credential${data.issued !== 1 ? "s" : ""} anchored on Polygon`);

        if (resultEl) {
          resultEl.hidden = false;
          resultEl.innerHTML = `
            <div class="rounded-[6px] border border-[#2A7A5A]/40 bg-[#2A7A5A]/5 p-6 mt-8">
              <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-[#2A7A5A] mb-3">
                Batch receipt · ${data.network} · Chain ID ${data.chain_id}
              </p>
              <p class="text-[15px] text-ink mb-4">${escHtml(data.message)}</p>
              <div class="space-y-2 max-h-64 overflow-y-auto">
                ${(data.results || []).map(r => `
                  <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center
                              py-2 border-b border-mist/30 gap-1">
                    <div>
                      <span class="text-sm text-ink/80 font-medium">${escHtml(r.name)}</span>
                      <span class="font-mono text-[11px] text-ink/40 ml-2">${escHtml(r.did)}</span>
                    </div>
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-[10px] text-ink/40 hidden sm:inline">${escHtml(r.hash.slice(0,20))}…</span>
                      <button onclick="copyToClipboard('${escHtml(r.hash)}')"
                              class="icon-btn text-[11px] px-2 py-1 border border-mist/50 rounded hover:bg-ink hover:text-paper">
                        Copy hash
                      </button>
                      <span class="font-mono text-[11px] ${r.status === 'issued' ? 'text-[#2A7A5A]' : 'text-ink/40'}">
                        ${r.status}
                      </span>
                    </div>
                  </div>`).join("")}
              </div>
            </div>`;
        }
      } catch (err) {
        showToast(err.message, "#B03A2A");
        if (resultEl) {
          resultEl.hidden = false;
          resultEl.innerHTML = `
            <div class="rounded-[6px] border border-[#B03A2A]/40 bg-[#B03A2A]/5 p-6 mt-8">
              <p class="font-mono text-[11px] uppercase text-[#B03A2A] mb-2">Upload error</p>
              <p class="text-sm text-ink/70">${escHtml(err.message)}</p>
            </div>`;
        }
      } finally {
        queueBtn.disabled    = false;
        queueBtn.textContent = "Queue for signing";
        pendingFile = null;
      }
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// UNIVERSITY REVOKE
// ══════════════════════════════════════════════════════════════════════════════
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

      list.innerHTML = data.credentials.map(c => {
        const sd      = c.student_data || {};
        const name    = sd.legal_name || sd.name || "—";
        const prog    = sd.program    || sd.major || "Certificate";
        const date    = sd.graduation_date || formatDate(c.issued_at);
        const revoked = c.is_revoked;
        const color   = revoked ? "#B03A2A" : "#2A7A5A";
        const status  = revoked ? "Revoked" : "Verified";

        return `
          <li class="flex flex-col gap-3 py-6 transition-colors hover:bg-paper/80
                     sm:flex-row sm:items-center sm:justify-between sm:px-4">
            <div>
              <p class="font-sans text-[15px] font-medium text-ink">${escHtml(name)}</p>
              <p class="mt-1 font-sans text-[12px] text-ink/50">${escHtml(prog)} · ${escHtml(date)}</p>
              <p class="mt-1 font-mono text-[11px] text-ink/35">${escHtml(c.hash.slice(0,26))}…</p>
            </div>
            <div class="flex items-center gap-4">
              <span class="font-mono text-[11px] uppercase tracking-tight" style="color:${color}">${status}</span>
              ${revoked
                ? `<button disabled class="rounded-[6px] border border-mist/50 px-4 py-2
                                           text-[11px] font-medium uppercase tracking-[0.08em] text-ink/30">
                     Already revoked
                   </button>`
                : `<button type="button"
                           data-revoke-hash="${escHtml(c.hash)}"
                           class="revoke-btn rounded-[6px] border border-mist px-4 py-2
                                  text-[11px] font-medium uppercase tracking-[0.08em]
                                  text-error transition-colors hover:border-error hover:bg-error/5 icon-btn">
                     Revoke
                   </button>`
              }
            </div>
          </li>`;
      }).join("");

      $$(".revoke-btn").forEach(btn => {
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
            showToast("Credential revoked — ledger state updated");
            loadRevokeList();
          } catch (err) {
            showToast(err.message, "#B03A2A");
            btn.disabled    = false;
            btn.textContent = "Revoke";
          }
        });
      });
    } catch (err) {
      list.innerHTML = `<li class="py-8 text-center font-mono text-sm text-[#B03A2A]">${escHtml(err.message)}</li>`;
    }
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// EMPLOYER VERIFY
// ══════════════════════════════════════════════════════════════════════════════
function initEmployerVerify() {

  // Tab switching (Scan QR / Paste Hash)
  $$("[data-verify-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      $$("[data-verify-tab]").forEach(b => {
        const active = b.dataset.verifyTab === btn.dataset.verifyTab;
        b.classList.toggle("bg-ink",     active);
        b.classList.toggle("text-paper", active);
        b.classList.toggle("shadow-sm",  active);
        b.classList.toggle("opacity-60", !active);
        b.setAttribute("aria-selected", String(active));
      });
      $$("[data-verify-panel]").forEach(p => {
        p.classList.toggle("hidden", p.dataset.verifyPanel !== btn.dataset.verifyTab);
      });
    });
  });

  // Find inputs and buttons — works with existing employer.html HTML
  const hashInput = document.getElementById("hash-input")
    || $("input[placeholder*='hash' i]")
    || $("input[type='text']");

  const lookupBtn = $("[data-lookup-btn]")
    || $$("button").find(b => b.textContent.trim() === "Look Up");

  const resultEl = document.getElementById("verify-result");

  // Pre-fill hash from URL param (e.g. when student clicks "open in verify")
  const urlHash = new URLSearchParams(location.search).get("hash");
  if (urlHash && hashInput) {
    hashInput.value = urlHash;
    // Auto-verify if hash came from URL
    setTimeout(() => doVerify(urlHash), 300);
  }

  // Clear default hardcoded value so box starts empty
  if (hashInput && !urlHash) hashInput.value = "";

  if (lookupBtn) {
    lookupBtn.addEventListener("click", () => doVerify(hashInput?.value.trim() || ""));
  }
  if (hashInput) {
    hashInput.addEventListener("keydown", e => {
      if (e.key === "Enter") doVerify(hashInput.value.trim());
    });
  }

  // Scan panel simulate button
  const scanBtn = $("[data-verify-panel='scan'] button");
  if (scanBtn) {
    scanBtn.addEventListener("click", () => {
      if (hashInput) doVerify(hashInput.value.trim());
    });
  }

  async function doVerify(hash) {
    if (!hash) {
      showToast("Paste a certificate hash first", "#B03A2A");
      return;
    }
    if (lookupBtn) { lookupBtn.disabled = true; lookupBtn.textContent = "Verifying…"; }
    if (resultEl)  resultEl.innerHTML = ""; // clear previous result

    try {
      const d = await apiFetch("/api/verify", {
        method:  "POST",
        body:    JSON.stringify({ hash }),
        headers: {},
      });
      renderResult(d);
    } catch (err) {
      renderError(err.message);
    } finally {
      if (lookupBtn) { lookupBtn.disabled = false; lookupBtn.textContent = "Look Up"; }
    }
  }

  function renderResult(d) {
    if (!resultEl) return;

    // ── NOT FOUND ──────────────────────────────────────────────────────────
    if (!d.found) {
      resultEl.innerHTML = `
        <div class="relative overflow-hidden bg-surface-container-lowest
                    rounded-[6px] border border-mist/50 mt-8">
          <div class="absolute top-0 left-0 w-full h-1 bg-[#B03A2A]"></div>
          <div class="p-8 text-center">
            <div class="flex items-center justify-center gap-2 mb-4">
              <span class="material-symbols-outlined text-[#B03A2A]"
                    style="font-variation-settings:'FILL' 1">cancel</span>
              <span class="font-mono text-[11px] uppercase tracking-widest text-[#B03A2A]">Not Found</span>
            </div>
            <p class="font-serif text-2xl text-ink mb-2">No matching credential</p>
            <p class="font-sans text-sm text-on-surface-variant/70 max-w-sm mx-auto">
              This hash does not exist in the CertiChain registry.
              It may be invalid, or the credential was never issued here.
            </p>
          </div>
        </div>`;
      return;
    }

    // ── VERIFIED or REVOKED ───────────────────────────────────────────────
    const revoked     = d.is_revoked;
    const statusColor = revoked ? "#B03A2A" : "#2A7A5A";
    const statusLabel = revoked ? "Revoked"  : "Verified";
    const statusIcon  = revoked ? "cancel"   : "verified_user";
    const barColor    = revoked ? "#B03A2A"  : "#C17A3A";

    resultEl.innerHTML = `
      <div class="relative overflow-hidden bg-surface-container-lowest
                  rounded-[6px] border border-mist/50 mt-8">
        <div class="absolute top-0 left-0 w-full h-1" style="background:${barColor}"></div>
        <div class="p-8">

          <!-- Status badge + chain -->
          <div class="flex justify-between items-start mb-6">
            <div class="flex items-center gap-2 px-2 py-1 border"
                 style="border-color:${statusColor}">
              <span class="material-symbols-outlined text-[14px]"
                    style="color:${statusColor};font-variation-settings:'FILL' 1">${statusIcon}</span>
              <span class="font-mono text-[11px] uppercase tracking-widest"
                    style="color:${statusColor}">${statusLabel}</span>
            </div>
            <span class="font-mono text-[12px] text-ink/30 uppercase tracking-tighter">
              Chain ID: ${d.chain_id || 137}
            </span>
          </div>

          <!-- Credential details -->
          <div class="mb-8">
            <h2 class="font-serif text-[28px] leading-tight mb-2 text-ink">
              ${escHtml(d.program || "Certificate")}
            </h2>
            <div class="space-y-1">
              <p class="font-sans text-ink font-medium">${escHtml(d.student_name)}</p>
              <p class="font-sans text-on-surface-variant text-sm">
                ${escHtml(d.university)} · Academic Ledger
              </p>
              <p class="font-sans text-on-surface-variant/60 text-sm italic">
                Issued: ${formatDate(d.issued_at)}
              </p>
              ${d.degree_class && d.degree_class !== "—"
                ? `<p class="font-mono text-[12px] text-ink/50">${escHtml(d.degree_class)}</p>`
                : ""}
              ${revoked
                ? `<p class="font-mono text-[12px] text-[#B03A2A] uppercase mt-1">
                     Revoked: ${formatDate(d.revoked_at)}
                   </p>`
                : ""}
            </div>
          </div>

          <!-- Chain metadata -->
          <div class="flex justify-between items-end pt-6 border-t border-mist/30">
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-ink/40 text-[16px]">link</span>
                <span class="font-mono text-[12px] text-on-surface-variant">
                  Block #${(d.block_number || 0).toLocaleString()}
                </span>
              </div>
              <p class="font-mono text-[12px] text-ink/40">Anchored on Polygon Mainnet</p>
              ${d.did && d.did !== "UNKNOWN"
                ? `<p class="font-mono text-[11px] text-ink/30">DID: ${escHtml(d.did)}</p>`
                : ""}
            </div>
            <p class="font-mono text-[12px] text-ink/20">${d.verification_ms || 1400}ms</p>
          </div>
        </div>
      </div>`;
  }

  function renderError(msg) {
    if (!resultEl) return;
    resultEl.innerHTML = `
      <div class="p-8 border border-mist/50 rounded-[6px] bg-surface-container-lowest text-center mt-8">
        <p class="font-mono text-[11px] text-[#B03A2A] uppercase tracking-widest mb-2">Error</p>
        <p class="text-sm text-ink/70">${escHtml(msg)}</p>
      </div>`;
  }
}