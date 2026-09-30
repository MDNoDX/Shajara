/* Family tree viewer.
   The server computes the layout and every card's text (names, years, the
   Uzbek relationship name) in the active language; this file draws it,
   handles pan / zoom, opening and closing branches, re-centring and PNG
   export. Interface messages come from Django's JavaScript catalogue. */
(function () {
  "use strict";

  var root = document.getElementById("tree");
  if (!root) return;

  var SVGNS = "http://www.w3.org/2000/svg";
  var view = document.getElementById("tree-view");
  var statusEl = document.getElementById("tree-status");
  var picker = document.getElementById("tree-person");
  var openLink = document.getElementById("tree-open");
  var pdfLink = document.getElementById("tree-pdf");
  var addLink = document.getElementById("add-relative");
  var addTemplate = root.getAttribute("data-add-url-template");
  var dataUrl = root.getAttribute("data-url");
  var pdfUrl = root.getAttribute("data-pdf-url");

  var FONT = "'Noto Sans', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif";
  // Card geometry (the same numbers are used in apps/genealogy/pdf.py).
  var AV = { cx: 34, cy: 34, r: 20 }, TX = 64, PADR = 10;

  var params = new URLSearchParams(window.location.search);
  function idSet(name) {
    return new Set((params.get(name) || "").split(",").filter(Boolean).map(Number));
  }
  var state = {
    data: null, vb: null, svg: null,
    focus: parseInt(root.getAttribute("data-focus"), 10),
    all: params.get("all") === "1",
    opened: idSet("open"), closed: idSet("closed"), folded: idSet("folded"), unfolded: idSet("kids"),
  };
  var measureCtx = document.createElement("canvas").getContext("2d");

  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  function setStatus(text) {
    statusEl.textContent = text || "";
    statusEl.hidden = !text;
  }

  function query() {
    var q = new URLSearchParams();
    q.set("person", state.focus);
    if (state.all) q.set("all", "1");
    [["open", state.opened], ["closed", state.closed], ["folded", state.folded], ["kids", state.unfolded]].forEach(function (p) {
      if (p[1].size) q.set(p[0], Array.from(p[1]).join(","));
    });
    return q.toString();
  }

  // Wrap text to at most `maxLines` lines of width `maxW`, adding "…" if cut.
  function wrap(text, font, maxW, maxLines) {
    measureCtx.font = font;
    var words = String(text || "").split(/\s+/).filter(Boolean);
    var lines = [], cur = "";
    words.forEach(function (w) {
      var trial = cur ? cur + " " + w : w;
      if (!cur || measureCtx.measureText(trial).width <= maxW) cur = trial;
      else { lines.push(cur); cur = w; }
    });
    if (cur) lines.push(cur);
    if (lines.length > maxLines) { lines = lines.slice(0, maxLines); lines[maxLines - 1] += "…"; }
    return lines.map(function (line) {
      while (line.length > 1 && measureCtx.measureText(line).width > maxW) line = line.slice(0, -2) + "…";
      return line;
    });
  }

  // Everything written on a card, with positions; shared by SVG and PNG.
  function cardText(n, card) {
    var inner = card.w - TX - PADR;
    var nameFont = "700 13.5px " + FONT, smallFont = "11.5px " + FONT, labelFont = "600 11px " + FONT;
    var out = [], y = 25;
    wrap(n.name, nameFont, inner, 2).forEach(function (line) {
      out.push({ t: line, x: TX, y: y, cls: "t-name", font: nameFont }); y += 16;
    });
    if (n.years) out.push({ t: n.years, x: TX, y: y + 1, cls: "t-years", font: smallFont });
    var label = null;
    if (n.label) {
      var t = wrap(n.label, labelFont, inner - 12, 1)[0];
      measureCtx.font = labelFont;
      label = { t: t, x: TX + 6, y: card.h - 13, w: measureCtx.measureText(t).width + 12, font: labelFont };
    }
    return { lines: out, label: label };
  }

  function el(name, attrs, parent) {
    var node = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(node);
    return node;
  }

  // Polyline with softly rounded corners.
  function pathD(points) {
    var R = 12, d = "M" + points[0][0] + "," + points[0][1];
    for (var i = 1; i < points.length - 1; i++) {
      var p = points[i - 1], c = points[i], n = points[i + 1];
      var l1 = Math.hypot(c[0] - p[0], c[1] - p[1]), l2 = Math.hypot(n[0] - c[0], n[1] - c[1]);
      var r = Math.min(R, l1 / 2, l2 / 2);
      if (r < 1) { d += " L" + c[0] + "," + c[1]; continue; }
      var a = [c[0] + (p[0] - c[0]) * r / l1, c[1] + (p[1] - c[1]) * r / l1];
      var b = [c[0] + (n[0] - c[0]) * r / l2, c[1] + (n[1] - c[1]) * r / l2];
      d += " L" + a[0] + "," + a[1] + " Q" + c[0] + "," + c[1] + " " + b[0] + "," + b[1];
    }
    var last = points[points.length - 1];
    return d + " L" + last[0] + "," + last[1];
  }

  // Small rounded button on a card: open/close brothers and sisters or children.
  function toggle(parent, x, y, text, title, action, id, isOpen) {
    var g = el("g", { "class": "t-toggle" + (isOpen ? " open" : ""), transform: "translate(" + x + "," + y + ")",
      tabindex: "0", role: "button", "aria-label": title, "aria-expanded": String(isOpen) }, parent);
    g.dataset.action = action;
    g.dataset.id = id;
    g.dataset.open = isOpen ? "1" : "";
    el("title", {}, g).textContent = title;
    var w = Math.max(24, text.length * 7.5 + 14);
    el("rect", { x: -w / 2, y: -11, width: w, height: 22, rx: 11 }, g);
    el("text", { x: 0, y: 4, "text-anchor": "middle" }, g).textContent = text;
  }

  var positions = {};
  function key(n) { return n.id + (n.dup ? "d" : ""); }

  function render(data, anchor) {
    var card = data.card;
    var old = positions;
    positions = {};
    var svg = el("svg", { role: "group", "aria-label": gettext("Family tree") });
    var defs = el("defs", {}, svg);
    var g = el("g", {}, svg);
    var lines = el("g", { "class": "t-lines" }, g);
    data.lines.forEach(function (line) {
      el("path", { d: pathD(line.points), "class": "t-line " + line.kind }, lines);
    });
    var cards = [];
    data.nodes.forEach(function (n) {
      positions[key(n)] = { x: n.x, y: n.y };
      var cls = ["t-card", n.gender === "female" ? "female" : "male", n.focus ? "focus" : "", n.dup ? "dup" : ""].join(" ");
      var cg = el("g", { "class": cls, transform: "translate(" + n.x + "," + n.y + ")" }, g);
      cards.push([cg, n]);
      var body = el("g", { "class": "t-body", tabindex: "0", role: "button",
        "aria-label": [n.name, n.years, n.label].filter(Boolean).join(", ") }, cg);
      body.dataset.id = n.id;
      el("rect", { "class": "box", width: card.w, height: card.h, rx: 14 }, body);
      el("rect", { "class": "stripe", x: 0, y: 12, width: 4, height: card.h - 24, rx: 2 }, body);
      el("circle", { "class": "avatar", cx: AV.cx, cy: AV.cy, r: AV.r }, body);
      if (n.photo) {
        var clipId = "clip-" + key(n);
        el("circle", { cx: AV.cx, cy: AV.cy, r: AV.r - 1 }, el("clipPath", { id: clipId }, defs));
        el("image", { href: n.photo, x: AV.cx - AV.r, y: AV.cy - AV.r, width: AV.r * 2, height: AV.r * 2,
          preserveAspectRatio: "xMidYMid slice", "clip-path": "url(#" + clipId + ")" }, body);
      } else {
        el("text", { "class": "t-initials", x: AV.cx, y: AV.cy + 4.5, "text-anchor": "middle" }, body).textContent = n.initials;
      }
      var text = cardText(n, card);
      text.lines.forEach(function (t) { el("text", { x: t.x, y: t.y, "class": t.cls }, body).textContent = t.t; });
      if (text.label) {
        el("rect", { "class": "t-pill", x: text.label.x - 6, y: text.label.y - 12, width: text.label.w, height: 17, rx: 8.5 }, body);
        el("text", { x: text.label.x, y: text.label.y, "class": "t-label" }, body).textContent = text.label.t;
      }
      if (n.sibs) {
        toggle(cg, n.sibs.side === "left" ? 18 : card.w - 18, 0, n.sibs.open ? "−" : "+" + n.sibs.count,
          (n.sibs.open ? gettext("Hide brothers and sisters") : gettext("Show brothers and sisters")) + " (" + n.sibs_label + ")",
          "sibs", n.id, n.sibs.open);
      }
      if (n.kids) {
        toggle(cg, card.w - 24, card.h, n.kids.open ? "−" : "+" + n.kids.count,
          (n.kids.open ? gettext("Hide children") : gettext("Show children")) + " (" + n.kids_label + ")",
          "kids", n.id, n.kids.open);
      }
    });

    // Keep the clicked card where it was on screen and let the other cards
    // glide from their old places to the new ones.
    var shift = { x: 0, y: 0 };
    var animate = anchor && state.vb && old[anchor] && positions[anchor];
    if (animate) {
      shift.x = positions[anchor].x - old[anchor].x;
      shift.y = positions[anchor].y - old[anchor].y;
    }
    view.querySelectorAll("svg").forEach(function (s) { s.remove(); });
    view.appendChild(svg);
    state.svg = svg;
    state.data = data;
    if (!animate) { fit(true); return; }
    state.vb.x += shift.x;
    state.vb.y += shift.y;
    applyViewBox();
    lines.classList.add("t-appear");
    // FLIP: each card starts where it was and glides to its new place. The
    // CSS transform replaces the transform attribute while it is set.
    var moving = [];
    cards.forEach(function (c) {
      var from = old[key(c[1])];
      if (!from) { c[0].classList.add("t-appear"); return; }
      var fx = from.x + shift.x, fy = from.y + shift.y;
      if (Math.abs(fx - c[1].x) < 0.5 && Math.abs(fy - c[1].y) < 0.5) return;
      c[0].style.transform = "translate(" + fx + "px," + fy + "px)";
      moving.push(c);
    });
    if (!moving.length) return;
    svg.getBoundingClientRect(); // commit the starting positions
    moving.forEach(function (c) {
      c[0].classList.add("t-move");
      c[0].style.transform = "translate(" + c[1].x + "px," + c[1].y + "px)";
    });
    window.setTimeout(function () {
      moving.forEach(function (c) { c[0].classList.remove("t-move"); c[0].style.transform = ""; });
    }, 600);
  }

  // ---- pan & zoom via the viewBox -------------------------------------------
  function applyViewBox() {
    var vb = state.vb;
    state.svg.setAttribute("viewBox", [vb.x, vb.y, vb.w, vb.h].join(" "));
  }

  // The whole chart; with `nearFocus`, large charts open around the centre person.
  function fit(nearFocus) {
    if (!state.data) return;
    var rect = view.getBoundingClientRect();
    var w = state.data.width, h = state.data.height;
    var scale = Math.max(w / rect.width, h / rect.height, 1 / 1.3);
    var vw = rect.width * scale, vh = rect.height * scale;
    state.vb = { x: (w - vw) / 2, y: (h - vh) / 2, w: vw, h: vh };
    var f = state.data.nodes.filter(function (n) { return n.focus && !n.dup; })[0];
    if (nearFocus && f && scale > 1.4) {
      scale = 1.05;
      vw = rect.width * scale; vh = rect.height * scale;
      state.vb = { x: f.x + state.data.card.w / 2 - vw / 2, y: f.y + state.data.card.h / 2 - vh * 0.62, w: vw, h: vh };
    }
    applyViewBox();
  }

  function zoom(factor, cx, cy) {
    var vb = state.vb;
    if (!vb) return;
    var nw = Math.min(Math.max(vb.w * factor, 240), 40000);
    var k = nw / vb.w;
    var px = cx === undefined ? vb.x + vb.w / 2 : cx;
    var py = cy === undefined ? vb.y + vb.h / 2 : cy;
    state.vb = { x: px - (px - vb.x) * k, y: py - (py - vb.y) * k, w: nw, h: vb.h * k };
    applyViewBox();
  }

  function toChart(clientX, clientY) {
    var rect = view.getBoundingClientRect(), vb = state.vb;
    return { x: vb.x + (clientX - rect.left) / rect.width * vb.w, y: vb.y + (clientY - rect.top) / rect.height * vb.h };
  }

  // Mouse wheel and trackpad pinch zoom; two-finger trackpad scrolling pans.
  view.addEventListener("wheel", function (e) {
    if (!state.vb) return;
    e.preventDefault();
    var mouseWheel = e.deltaMode === 1 || (e.deltaX === 0 && Math.abs(e.deltaY) >= 50 && Number.isInteger(e.deltaY));
    if (e.ctrlKey || e.metaKey || mouseWheel) {
      var p = toChart(e.clientX, e.clientY);
      var step = e.ctrlKey && !mouseWheel ? Math.exp(e.deltaY / 100) : (e.deltaY > 0 ? 1.15 : 1 / 1.15);
      zoom(step, p.x, p.y);
      return;
    }
    var rect = view.getBoundingClientRect();
    state.vb.x += e.deltaX / rect.width * state.vb.w;
    state.vb.y += e.deltaY / rect.height * state.vb.h;
    applyViewBox();
  }, { passive: false });

  // Drag to pan (mouse or one finger), pinch with two fingers.
  var pointers = new Map(), drag = null, pinch = null;
  view.addEventListener("pointerdown", function (e) {
    if (!state.vb) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointers.size === 1) {
      drag = { x: e.clientX, y: e.clientY, vb: Object.assign({}, state.vb), moved: false, target: e.target };
    } else if (pointers.size === 2) {
      var pts = Array.from(pointers.values());
      pinch = { d: Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y), vb: Object.assign({}, state.vb) };
      drag = null;
    }
  });
  window.addEventListener("pointermove", function (e) {
    if (!pointers.has(e.pointerId)) return;
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pinch && pointers.size === 2) {
      var pts = Array.from(pointers.values());
      var d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      state.vb = Object.assign({}, pinch.vb);
      var p = toChart((pts[0].x + pts[1].x) / 2, (pts[0].y + pts[1].y) / 2);
      zoom(pinch.d / Math.max(d, 1), p.x, p.y);
      return;
    }
    if (!drag) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
    if (!drag.moved) { drag.moved = true; view.classList.add("dragging"); }
    var rect = view.getBoundingClientRect();
    state.vb.x = drag.vb.x - dx / rect.width * drag.vb.w;
    state.vb.y = drag.vb.y - dy / rect.height * drag.vb.h;
    applyViewBox();
  });
  function endPointer(e) {
    if (!pointers.has(e.pointerId)) return;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (pointers.size) return;
    var d = drag;
    drag = null;
    view.classList.remove("dragging");
    if (d && !d.moved) activate(d.target);
  }
  window.addEventListener("pointerup", endPointer);
  window.addEventListener("pointercancel", endPointer);

  view.addEventListener("keydown", function (e) {
    var target = e.target.closest && e.target.closest(".t-toggle, .t-body");
    if ((e.key === "Enter" || e.key === " ") && target) {
      e.preventDefault();
      activate(target);
    } else if (e.key === "+" || e.key === "=") zoom(1 / 1.2);
    else if (e.key === "-") zoom(1.2);
  });

  root.querySelectorAll("[data-zoom]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var what = btn.getAttribute("data-zoom");
      if (what === "in") zoom(1 / 1.25);
      else if (what === "out") zoom(1.25);
      else fit(false);
    });
  });

  // A toggle opens or closes a branch; a card becomes the new centre (a
  // click on the centre person opens their profile).
  function activate(target) {
    var t = target.closest && target.closest(".t-toggle");
    if (t) {
      var id = parseInt(t.dataset.id, 10);
      if (t.dataset.action === "sibs") {
        if (t.dataset.open) { state.closed.add(id); state.opened.delete(id); }
        else { state.opened.add(id); state.closed.delete(id); }
      } else if (t.dataset.open) { state.folded.add(id); state.unfolded.delete(id); }
      else { state.unfolded.add(id); state.folded.delete(id); }
      load(String(id));
      return;
    }
    var body = target.closest && target.closest(".t-body");
    if (!body) return;
    var pid = parseInt(body.dataset.id, 10);
    if (pid === state.focus) {
      var n = state.data.nodes.filter(function (x) { return x.id === pid; })[0];
      if (n) window.location.href = n.url;
      return;
    }
    state.focus = pid;
    load(String(pid));
  }

  function updateLinks(data) {
    var f = data.nodes.filter(function (n) { return n.focus && !n.dup; })[0];
    if (!f) return;
    if (document.activeElement !== picker) picker.value = f.name;
    openLink.href = f.url;
    pdfLink.href = pdfUrl + "?" + query();
    if (addLink && addTemplate) addLink.href = addTemplate.replace("/0/", "/" + f.id + "/");
    window.history.replaceState(null, "", window.location.pathname + "?" + query());
    root.querySelectorAll("[data-expand]").forEach(function (b) {
      b.setAttribute("aria-pressed", String((b.getAttribute("data-expand") === "all") === state.all));
    });
  }

  function load(anchor) {
    if (!state.data) setStatus(gettext("Loading the family tree…"));
    view.classList.add("loading");
    fetch(dataUrl + "?" + query(), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        view.classList.remove("loading");
        state.focus = data.focus;
        if (!data.nodes.length) { setStatus(gettext("The family tree is empty.")); return; }
        setStatus("");
        render(data, anchor);
        updateLinks(data);
      })
      .catch(function () {
        view.classList.remove("loading");
        setStatus(gettext("Could not load the family tree. Please try again."));
      });
  }

  // The name picker (live search) puts the chosen person in the centre.
  picker.addEventListener("livesearch:pick", function (e) { state.focus = e.detail.id; load(null); });

  root.querySelectorAll("[data-expand]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      state.all = btn.getAttribute("data-expand") === "all";
      state.opened.clear(); state.closed.clear(); state.folded.clear(); state.unfolded.clear();
      load(String(state.focus));
    });
  });

  // ---- PNG export: drawn on a canvas so the web font is used -----------------
  document.getElementById("tree-png").addEventListener("click", function () {
    var data = state.data;
    if (!data) return;
    var scale = Math.min(2, 16000 / Math.max(data.width, data.height));
    var canvas = document.createElement("canvas");
    canvas.width = Math.round(data.width * scale);
    canvas.height = Math.round(data.height * scale);
    var ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    ctx.fillStyle = css("--tree-bg");
    ctx.fillRect(0, 0, data.width, data.height);
    ctx.lineJoin = "round";
    data.lines.forEach(function (line) {
      ctx.beginPath();
      ctx.setLineDash(line.kind === "divorced" || line.kind === "partners" ? [6, 4] : []);
      ctx.strokeStyle = line.kind === "child" ? css("--tree-line") : css("--accent");
      ctx.lineWidth = line.kind === "child" ? 1.6 : 2.2;
      line.points.forEach(function (p, i) { if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
      ctx.stroke();
    });
    ctx.setLineDash([]);
    var card = data.card;
    data.nodes.forEach(function (n) {
      var female = n.gender === "female";
      ctx.save();
      ctx.translate(n.x, n.y);
      ctx.shadowColor = "rgba(0,0,0,.08)"; ctx.shadowBlur = 8; ctx.shadowOffsetY = 2;
      ctx.beginPath(); ctx.roundRect(0, 0, card.w, card.h, 14);
      ctx.fillStyle = n.focus ? css("--accent-soft") : css("--surface"); ctx.fill();
      ctx.shadowColor = "transparent";
      ctx.setLineDash(n.dup ? [5, 4] : []);
      ctx.strokeStyle = n.focus ? css("--accent") : css("--line-strong"); ctx.lineWidth = n.focus ? 2.4 : 1; ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = female ? css("--female-line") : css("--male-line");
      ctx.beginPath(); ctx.roundRect(0, 12, 4, card.h - 24, 2); ctx.fill();
      ctx.beginPath(); ctx.arc(AV.cx, AV.cy, AV.r, 0, Math.PI * 2);
      ctx.fillStyle = female ? css("--female") : css("--male"); ctx.fill();
      ctx.fillStyle = css("--ink-2"); ctx.font = "700 13px " + FONT; ctx.textAlign = "center";
      ctx.fillText(n.initials || "", AV.cx, AV.cy + 4.5);
      ctx.textAlign = "left";
      var text = cardText(n, card);
      text.lines.forEach(function (t) {
        ctx.font = t.font;
        ctx.fillStyle = t.cls === "t-years" ? css("--muted") : css("--ink");
        ctx.fillText(t.t, t.x, t.y);
      });
      if (text.label) {
        ctx.fillStyle = css("--accent-soft");
        ctx.beginPath(); ctx.roundRect(text.label.x - 6, text.label.y - 12, text.label.w, 17, 8.5); ctx.fill();
        ctx.font = text.label.font; ctx.fillStyle = css("--accent");
        ctx.fillText(text.label.t, text.label.x, text.label.y);
      }
      ctx.restore();
    });
    canvas.toBlob(function (blob) {
      if (!blob) { window.alert(gettext("An error occurred.")); return; }
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = pgettext("file name", "family-tree") + ".png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    }, "image/png");
  });

  window.addEventListener("resize", function () { if (state.data) fit(true); });
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () { load(null); });
})();
