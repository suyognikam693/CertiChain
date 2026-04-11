(function () {
  "use strict";

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }
  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function showToast(message) {
    var el = qs("#cc-toast");
    if (!el) {
      el = document.createElement("div");
      el.id = "cc-toast";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add("cc-toast--show");
    clearTimeout(el._hide);
    el._hide = setTimeout(function () {
      el.classList.remove("cc-toast--show");
    }, 2200);
  }

  function initMobileNav() {
    var toggle = qs("[data-mobile-nav-toggle]");
    var drawer = qs("[data-mobile-drawer]");
    if (!toggle || !drawer) return;

    function setOpen(open) {
      drawer.setAttribute("data-open", open ? "true" : "false");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      var open = drawer.getAttribute("data-open") === "true";
      setOpen(!open);
    });

    drawer.addEventListener("click", function (e) {
      if (e.target.tagName === "A") setOpen(false);
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setOpen(false);
    });
  }

  function initCopyButtons() {
    qsa("[data-copy-target]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-copy-target");
        var input = id ? qs("#" + id) : null;
        if (!input || !input.value) return;
        navigator.clipboard.writeText(input.value).then(
          function () {
            showToast("Copied to clipboard");
          },
          function () {
            input.select();
            try {
              document.execCommand("copy");
              showToast("Copied to clipboard");
            } catch (e) {
              showToast("Copy failed");
            }
          }
        );
      });
    });
  }

  function initEmployerTabs() {
    var root = qs("[data-verify-tabs]");
    if (!root) return;
    var tabs = qsa("[data-verify-tab]", root);
    var panels = qsa("[data-verify-panel]", root);
    if (!tabs.length || !panels.length) return;

    function activate(name) {
      tabs.forEach(function (t) {
        var on = t.getAttribute("data-verify-tab") === name;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.classList.toggle("bg-ink", on);
        t.classList.toggle("text-paper", on);
        t.classList.toggle("opacity-60", !on);
        t.classList.toggle("shadow-sm", on);
      });
      panels.forEach(function (p) {
        var show = p.getAttribute("data-verify-panel") === name;
        p.classList.toggle("hidden", !show);
      });
    }

    tabs.forEach(function (t) {
      t.addEventListener("click", function () {
        activate(t.getAttribute("data-verify-tab"));
      });
    });
  }

  function initRippleButtons() {
    qsa("[data-ripple]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        var rect = btn.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;
        var ink = document.createElement("span");
        ink.style.cssText =
          "position:absolute;border-radius:9999px;pointer-events:none;background:rgba(250,250,248,0.35);transform:scale(0);animation:cc-ripple 0.55s ease-out forwards;left:" +
          (x - 10) +
          "px;top:" +
          (y - 10) +
          "px;width:20px;height:20px;";
        btn.style.position = btn.style.position || "relative";
        btn.style.overflow = "hidden";
        btn.appendChild(ink);
        setTimeout(function () {
          ink.remove();
        }, 600);
      });
    });
  }

  if (!document.getElementById("cc-ripple-style")) {
    var s = document.createElement("style");
    s.id = "cc-ripple-style";
    s.textContent =
      "@keyframes cc-ripple{to{transform:scale(18);opacity:0}}";
    document.head.appendChild(s);
  }

  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    initCopyButtons();
    initEmployerTabs();
    initRippleButtons();
  });
})();
