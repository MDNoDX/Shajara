/* Small progressive enhancements. All messages go through Django's
   JavaScript catalogue (gettext / interpolate from /jsi18n/), so they appear
   in the user's language: Uzbek Latin or Uzbek Cyrillic. */
(function () {
  "use strict";

  // Confirm destructive actions.
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-confirm]");
    if (!el) return;
    if (!window.confirm(gettext("Are you sure you want to delete this?"))) {
      e.preventDefault();
    }
  });

  // Photo size check before upload (the server checks again).
  document.addEventListener("change", function (e) {
    var input = e.target;
    if (input.type !== "file" || !input.files || !input.files[0]) return;
    var form = input.closest("[data-photo-limit]");
    if (!form) return;
    var limitMb = parseInt(form.getAttribute("data-photo-limit"), 10);
    if (input.files[0].size > limitMb * 1024 * 1024) {
      window.alert(interpolate(gettext("The photo is too large. The maximum size is %(size)s MB."), { size: limitMb }, true));
      input.value = "";
    }
  });

  // Show the death fields only for deceased people.
  document.querySelectorAll("[data-show-if]").forEach(function (block) {
    var box = document.getElementById(block.getAttribute("data-show-if"));
    if (!box) return;
    var sync = function () { block.hidden = !box.checked; };
    box.addEventListener("change", sync);
    sync();
  });

  // "Add relative": hide new-person fields when linking an existing person,
  // the gender choice for father/mother, and "other parent" unless adding a child.
  var relation = document.getElementById("id_relation");
  var existing = document.getElementById("id_existing");
  if (relation) {
    var newPerson = document.querySelector("[data-new-person]");
    var otherParent = document.querySelector("[data-show-if-relation]");
    var genderField = document.getElementById("id_gender") && document.getElementById("id_gender").closest(".field");
    var syncRelation = function () {
      if (newPerson && existing) newPerson.hidden = !!existing.value;
      if (otherParent) otherParent.hidden = relation.value !== otherParent.getAttribute("data-show-if-relation");
      if (genderField) genderField.hidden = relation.value === "father" || relation.value === "mother";
    };
    relation.addEventListener("change", syncRelation);
    if (existing) existing.addEventListener("change", syncRelation);
    syncRelation();
  }

  // Buttons disabled by the submit handler come back when the page is
  // restored from the back/forward cache.
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted) return;
    document.querySelectorAll("button[data-label]").forEach(function (b) {
      b.disabled = false; b.textContent = b.getAttribute("data-label"); b.removeAttribute("data-label");
    });
  });

  // Prevent double submission and show progress.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (form.method.toLowerCase() !== "post" || form.classList.contains("langsw")) return;
    var btn = e.submitter;
    if (!btn || btn.name === "delete") return;
    window.setTimeout(function () {
      btn.disabled = true;
      btn.setAttribute("data-label", btn.textContent);
      btn.textContent = gettext("Saving…");
    }, 0);
  });

  // Close open menus when clicking elsewhere or choosing an item.
  document.addEventListener("click", function (e) {
    document.querySelectorAll("details.usermenu[open], details.dropdown[open]").forEach(function (d) {
      var summary = d.querySelector("summary");
      if (!d.contains(e.target) || (!summary.contains(e.target) && e.target.closest(".menu a, .menu button"))) {
        d.removeAttribute("open");
      }
    });
  });

  // Colour theme: auto → light → dark, remembered in this browser.
  var themeBtn = document.querySelector("[data-theme-toggle]");
  function applyTheme(mode) {
    if (mode === "light" || mode === "dark") document.documentElement.setAttribute("data-theme", mode);
    else document.documentElement.removeAttribute("data-theme");
    if (themeBtn) {
      themeBtn.setAttribute("data-mode", mode);
      var names = { auto: gettext("Automatic"), light: gettext("Light"), dark: gettext("Dark") };
      themeBtn.title = gettext("Colour theme") + ": " + names[mode];
    }
  }
  var themeChoice = document.querySelector("[data-theme-choice]");
  function setTheme(mode) {
    try { localStorage.setItem("theme", mode); } catch (e) {}
    applyTheme(mode);
    if (themeChoice) themeChoice.querySelectorAll("[data-theme-value]").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-theme-value") === mode));
    });
  }
  var savedTheme = "light";
  try { savedTheme = localStorage.getItem("theme") || "light"; } catch (e) {}
  setTheme(savedTheme);
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      setTheme({ light: "dark", dark: "auto", auto: "light" }[themeBtn.getAttribute("data-mode")] || "light");
    });
  }
  if (themeChoice) themeChoice.addEventListener("click", function (e) {
    var b = e.target.closest("[data-theme-value]");
    if (b) setTheme(b.getAttribute("data-theme-value"));
  });

  // Copy a code to the clipboard.
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = document.getElementById(btn.getAttribute("data-copy")).textContent.trim();
      var done = function () {
        btn.classList.add("copied");
        btn.title = gettext("Copied");
        window.setTimeout(function () { btn.classList.remove("copied"); }, 1600);
      };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () {});
    });
  });

  // Connecting Telegram: the page notices by itself when the bot linked the account.
  var tgWait = document.querySelector("[data-telegram-wait]");
  if (tgWait) {
    var started = Date.now();
    var poll = function () {
      if (Date.now() - started > 15 * 60 * 1000) return;
      if (document.hidden) { window.setTimeout(poll, 3000); return; }
      fetch(tgWait.getAttribute("data-telegram-wait"), { credentials: "same-origin", headers: { Accept: "application/json" } })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.connected) { window.location.hash = "telegram"; window.location.reload(); }
          else window.setTimeout(poll, 3000);
        })
        .catch(function () { window.setTimeout(poll, 6000); });
    };
    window.setTimeout(poll, 3000);
  }

  // Toast messages close themselves after a few seconds.
  document.querySelectorAll(".toast").forEach(function (toast, i) {
    var close = function () { toast.classList.add("hide"); window.setTimeout(function () { toast.remove(); }, 350); };
    toast.querySelector(".toast-close").addEventListener("click", close);
    window.setTimeout(close, 6000 + i * 600);
  });

  // A search box above long multiple-choice lists (people in an event).
  document.querySelectorAll("select[data-filterable]").forEach(function (select) {
    var box = document.createElement("input");
    box.type = "search";
    box.className = "filter-box";
    box.placeholder = gettext("Type a name to filter…");
    select.parentNode.insertBefore(box, select);
    box.addEventListener("input", function () {
      var q = box.value.trim().toLowerCase();
      Array.prototype.forEach.call(select.options, function (o) {
        o.hidden = q && o.text.toLowerCase().indexOf(q) === -1 && !o.selected;
      });
    });
  });

  // New son: suggest the surname made from the paternal grandfather's name.
  var surnameHint = document.querySelector("[data-son-surname]");
  if (surnameHint) {
    var lastName = document.getElementById("id_last_name");
    var suggested = surnameHint.getAttribute("data-son-surname");
    var fatherSurname = surnameHint.getAttribute("data-father-surname");
    document.querySelectorAll("input[name=gender]").forEach(function (radio) {
      radio.addEventListener("change", function () {
        var rel = document.getElementById("id_relation");
        if (!lastName || !rel || rel.value !== "child" || !suggested) return;
        var untouched = !lastName.value || lastName.value === suggested || lastName.value === fatherSurname;
        if (radio.value === "male" && radio.checked && untouched) lastName.value = suggested;
        if (radio.value === "female" && radio.checked && lastName.value === suggested) lastName.value = "";
      });
    });
  }

  // ---- Live search: results while typing, no Enter needed ------------------
  function debounce(fn, ms) {
    var t;
    return function () { var args = arguments; clearTimeout(t); t = setTimeout(function () { fn.apply(null, args); }, ms); };
  }

  document.querySelectorAll("input[data-live-search]").forEach(function (input) {
    var box = input.parentNode.querySelector(".live-results");
    var mode = input.getAttribute("data-mode") || "navigate";
    var url = input.getAttribute("data-live-search");
    var items = [], active = -1, lastQuery = null, request = 0;

    function hide() { box.hidden = true; input.setAttribute("aria-expanded", "false"); active = -1; }
    function mark() {
      box.querySelectorAll(".live-item").forEach(function (el, i) {
        el.classList.toggle("active", i === active);
        el.setAttribute("aria-selected", String(i === active));
        if (i === active) el.scrollIntoView({ block: "nearest" });
      });
    }
    function choose(item) {
      hide();
      if (mode === "pick") {
        input.value = item.name;
        input.blur();
        input.dispatchEvent(new CustomEvent("livesearch:pick", { detail: item, bubbles: true }));
      } else {
        window.location.href = item.url;
      }
    }
    function render(data, q) {
      items = data.results;
      active = items.length ? 0 : -1;
      box.innerHTML = "";
      if (!items.length) {
        var none = document.createElement("div");
        none.className = "live-empty";
        none.textContent = gettext("No results found.");
        box.appendChild(none);
      }
      items.forEach(function (item, i) {
        var a = document.createElement("a");
        a.className = "live-item";
        a.href = item.url;
        a.setAttribute("role", "option");
        var av = document.createElement("span");
        av.className = "avatar sm" + (item.gender === "female" ? " female" : "");
        if (item.photo) { var img = document.createElement("img"); img.src = item.photo; img.alt = ""; av.appendChild(img); }
        else av.textContent = item.initials;
        var who = document.createElement("span");
        who.className = "live-who";
        var name = document.createElement("b");
        name.textContent = item.name;
        who.appendChild(name);
        var meta = [item.years, item.label].filter(Boolean).join(" · ");
        if (meta) { var m = document.createElement("small"); m.textContent = meta; who.appendChild(m); }
        a.appendChild(av);
        a.appendChild(who);
        a.addEventListener("mousedown", function (e) { e.preventDefault(); });
        a.addEventListener("click", function (e) { e.preventDefault(); choose(item); });
        a.addEventListener("mousemove", function () { if (active !== i) { active = i; mark(); } });
        box.appendChild(a);
      });
      if (mode === "navigate" && items.length) {
        var all = document.createElement("a");
        all.className = "live-all";
        all.href = data.all_url;
        all.textContent = gettext("All results");
        box.appendChild(all);
      }
      box.hidden = false;
      input.setAttribute("aria-expanded", "true");
      mark();
    }
    var run = debounce(function () {
      var q = input.value.trim();
      if (!q) { hide(); lastQuery = null; return; }
      if (q === lastQuery && !box.hidden) return;
      lastQuery = q;
      var mine = ++request;
      box.classList.add("loading");
      fetch(url + (url.indexOf("?") === -1 ? "?" : "&") + "q=" + encodeURIComponent(q), {
        credentials: "same-origin", headers: { Accept: "application/json" },
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (mine !== request) return;
        box.classList.remove("loading");
        render(data, q);
      }).catch(function () { box.classList.remove("loading"); });
    }, 150);

    input.addEventListener("input", run);
    input.addEventListener("focus", function () {
      if (mode === "pick") input.select();
      else if (input.value.trim()) run();
    });
    input.addEventListener("keydown", function (e) {
      if (box.hidden) { if (e.key === "ArrowDown") run(); return; }
      if (e.key === "ArrowDown") { e.preventDefault(); active = Math.min(active + 1, items.length - 1); mark(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); active = Math.max(active - 1, 0); mark(); }
      else if (e.key === "Enter" && active >= 0 && items[active]) { e.preventDefault(); choose(items[active]); }
      else if (e.key === "Escape") { hide(); }
    });
    input.addEventListener("blur", function () { setTimeout(hide, 150); });
    // In "pick" mode Enter in the box must never submit the surrounding form
    // (the form's own buttons still do).
    if (mode === "pick") input.addEventListener("keydown", function (e) {
      if (e.key === "Enter") e.preventDefault();
    });
  });

  // A picked person fills a hidden field; a form marked data-autosubmit is
  // sent as soon as every hidden field has a value ("Who is who?").
  document.addEventListener("livesearch:pick", function (e) {
    var target = e.target.getAttribute("data-pick-target");
    var field = target && document.getElementById(target);
    if (!field) return;
    field.value = e.detail.id;
    field.dispatchEvent(new Event("change", { bubbles: true }));
    var form = field.form;
    if (form && form.hasAttribute("data-autosubmit")) {
      var ready = Array.prototype.every.call(form.querySelectorAll("input[type=hidden]"), function (h) { return h.value; });
      if (ready) HTMLFormElement.prototype.submit.call(form);
    }
  });
  // Emptying a picker marked data-pick-clear clears its hidden field too.
  document.querySelectorAll("input[data-pick-clear]").forEach(function (input) {
    input.addEventListener("input", function () {
      var field = document.getElementById(input.getAttribute("data-pick-target"));
      if (field && field.value && !input.value.trim()) {
        field.value = "";
        field.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });
  document.querySelectorAll("[data-swap]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var ids = btn.getAttribute("data-swap").split(" ");
      var a = document.getElementById(ids[0]), b = document.getElementById(ids[1]);
      var an = document.getElementById(ids[0] + "-name"), bn = document.getElementById(ids[1] + "-name");
      var v = a.value; a.value = b.value; b.value = v;
      v = an.value; an.value = bn.value; bn.value = v;
      if (a.value && b.value) HTMLFormElement.prototype.submit.call(a.form);
    });
  });

  // Search pages: the results below update while typing.
  document.querySelectorAll("form[data-live-page]").forEach(function (form) {
    var input = form.querySelector("input[type=search]");
    var target = document.getElementById(form.getAttribute("data-target"));
    var base = form.getAttribute("data-live-page");
    var request = 0;
    var update = debounce(function () {
      var q = input.value.trim();
      var mine = ++request;
      target.classList.add("updating");
      var sep = base.indexOf("?") === -1 ? "?" : "&";
      fetch(base + sep + "partial=1&q=" + encodeURIComponent(q), { credentials: "same-origin" })
        .then(function (r) { return r.text(); })
        .then(function (html) {
          if (mine !== request) return;
          target.innerHTML = html;
          target.classList.remove("updating");
          window.history.replaceState(null, "", base + (q ? sep + "q=" + encodeURIComponent(q) : ""));
        })
        .catch(function () { target.classList.remove("updating"); });
    }, 200);
    input.addEventListener("input", update);
    form.addEventListener("submit", function (e) { e.preventDefault(); update(); });
  });

  // Colour palettes: preview immediately when a palette is chosen.
  document.querySelectorAll("[data-palette-form] input[type=radio][name$=palette]").forEach(function (radio) {
    radio.addEventListener("change", function () {
      document.documentElement.setAttribute("data-palette", radio.value);
      try { document.cookie = "palette=" + radio.value + ";path=/;max-age=31536000;samesite=lax"; } catch (e) {}
    });
  });
})();
