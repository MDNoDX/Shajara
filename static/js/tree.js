/* Family tree viewer.
   The server computes the layout and every card's text (names, years and the
   Uzbek relationship name) in the active language; this file only draws it,
   handles pan / zoom / re-centring and exports a PNG. Interface messages come
   from Django's JavaScript catalogue. */
(function () {
  "use strict";

  var root = document.getElementById("tree");
  if (!root) return;

  var SVGNS = "http://www.w3.org/2000/svg";
  var view = document.getElementById("tree-view");
  var statusEl = document.getElementById("tree-status");
  var select = document.getElementById("tree-person");
  var openLink = document.getElementById("tree-open");
  var pdfLink = document.getElementById("tree-pdf");
  var addLink = document.getElementById("add-relative");
  var addTemplate = root.getAttribute("data-add-url-template");
  var dataUrl = root.getAttribute("data-url");
  var pdfUrl = root.getAttribute("data-pdf-url");

  var FONT = "'Noto Sans', system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif";
  var PAD = 10;
  var state = { data: null, vb: null, svg: null, focus: parseInt(root.getAttribute("data-focus"), 10) };
  var measureCtx = document.createElement("canvas").getContext("2d");

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  function setStatus(text) {
    statusEl.textContent = text || "";
    statusEl.hidden = !text;
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
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      lines[maxLines - 1] += "…";
    }
    return lines.map(function (line) {
      while (line.length > 1 && measureCtx.measureText(line).width > maxW) line = line.slice(0, -2) + "…";
      return line;
    });
  }

  // Positions of the texts inside a card, shared by SVG and PNG drawing.
  function cardText(n, card) {
    var inner = card.w - PAD * 2;
    var nameFont = "700 14px " + FONT, smallFont = "12px " + FONT, labelFont = "600 12px " + FONT;
    var name = wrap(n.name, nameFont, inner, 2);
    var out = [];
    var y = 24;
    name.forEach(function (line) { out.push({ t: line, y: y, cls: "t-name", font: nameFont }); y += 17; });
    if (n.years) out.push({ t: n.years, y: y + 1, cls: "t-years", font: smallFont });
    if (n.label) out.push({ t: wrap(n.label, labelFont, inner, 1)[0], y: card.h - 10, cls: "t-label", font: labelFont });
    return out;
  }

  function el(name, attrs, parent) {
    var node = document.createElementNS(SVGNS, name);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(node);
    return node;
  }

  function pathD(points) {
    return points.map(function (p, i) { return (i ? "L" : "M") + p[0] + "," + p[1]; }).join(" ");
  }

  function render(data) {
    view.querySelectorAll("svg").forEach(function (s) { s.remove(); });
    var card = data.card;
    var svg = el("svg", { role: "group", "aria-label": gettext("Family tree") });
    var g = el("g", {}, svg);
    data.lines.forEach(function (line) {
      el("path", { d: pathD(line.points), "class": "t-line " + line.kind }, g);
    });
    data.nodes.forEach(function (n) {
      var cls = ["t-card", n.gender === "female" ? "female" : "", n.focus ? "focus" : "", n.dup ? "dup" : ""].join(" ");
      var cg = el("g", { "class": cls, transform: "translate(" + n.x + "," + n.y + ")", tabindex: "0", role: "button",
        "aria-label": [n.name, n.years, n.label].filter(Boolean).join(", ") }, g);
      cg.dataset.id = n.id;
      el("rect", { "class": "box", width: card.w, height: card.h, rx: 12 }, cg);
      cardText(n, card).forEach(function (t) {
        var tx = el("text", { x: PAD, y: t.y, "class": t.cls }, cg);
        tx.textContent = t.t;
      });
      if (n.hidden_label) {
        var h = el("text", { x: card.w / 2, y: card.h + 16, "class": "t-hidden", "text-anchor": "middle" }, cg);
        h.textContent = n.hidden_label;
      }
    });
    view.appendChild(svg);
    state.svg = svg;
    state.data = data;
    fit();
  }

  // ---- pan & zoom via the viewBox -------------------------------------------
  function applyViewBox() {
    var vb = state.vb;
    state.svg.setAttribute("viewBox", [vb.x, vb.y, vb.w, vb.h].join(" "));
  }

  function fit() {
    if (!state.data) return;
    var rect = view.getBoundingClientRect();
    var w = state.data.width, h = state.data.height;
    var scale = Math.max(w / rect.width, h / rect.height, 1 / 1.4);
    var vw = rect.width * scale, vh = rect.height * scale;
    state.vb = { x: (w - vw) / 2, y: (h - vh) / 2, w: vw, h: vh };
    // Keep the focus card in view when the chart is larger than the screen.
    var f = state.data.nodes.filter(function (n) { return n.focus; })[0];
    if (f && scale > 2.5) {
      scale = 1.2;
      vw = rect.width * scale; vh = rect.height * scale;
      state.vb = { x: f.x + state.data.card.w / 2 - vw / 2, y: f.y + state.data.card.h / 2 - vh / 2, w: vw, h: vh };
    }
    applyViewBox();
  }

  function zoom(factor, cx, cy) {
    var vb = state.vb;
    if (!vb) return;
    var nw = Math.min(Math.max(vb.w * factor, 200), 20000);
    var k = nw / vb.w;
    var px = cx === undefined ? vb.x + vb.w / 2 : cx;
    var py = cy === undefined ? vb.y + vb.h / 2 : cy;
    state.vb = { x: px - (px - vb.x) * k, y: py - (py - vb.y) * k, w: nw, h: vb.h * k };
    applyViewBox();
  }

  function toChart(clientX, clientY) {
    var rect = view.getBoundingClientRect();
    var vb = state.vb;
    return { x: vb.x + (clientX - rect.left) / rect.width * vb.w, y: vb.y + (clientY - rect.top) / rect.height * vb.h };
  }

  view.addEventListener("wheel", function (e) {
    if (!state.vb) return;
    e.preventDefault();
    var p = toChart(e.clientX, e.clientY);
    zoom(e.deltaY > 0 ? 1.12 : 1 / 1.12, p.x, p.y);
  }, { passive: false });

  var drag = null;
  view.addEventListener("pointerdown", function (e) {
    if (!state.vb || e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, vb: Object.assign({}, state.vb), moved: false };
  });
  window.addEventListener("pointermove", function (e) {
    if (!drag) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
    if (!drag.moved) { drag.moved = true; view.classList.add("dragging"); }
    var rect = view.getBoundingClientRect();
    state.vb.x = drag.vb.x - dx / rect.width * drag.vb.w;
    state.vb.y = drag.vb.y - dy / rect.height * drag.vb.h;
    applyViewBox();
  });
  window.addEventListener("pointerup", function (e) {
    if (!drag) return;
    var wasDrag = drag.moved;
    drag = null;
    view.classList.remove("dragging");
    if (wasDrag) return;
    var cardEl = e.target.closest && e.target.closest(".t-card");
    if (cardEl) activate(parseInt(cardEl.dataset.id, 10));
  });
  view.addEventListener("keydown", function (e) {
    var cardEl = e.target.closest && e.target.closest(".t-card");
    if (cardEl && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      activate(parseInt(cardEl.dataset.id, 10));
    } else if (e.key === "+" || e.key === "=") zoom(1 / 1.2);
    else if (e.key === "-") zoom(1.2);
  });

  root.querySelectorAll("[data-zoom]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var what = btn.getAttribute("data-zoom");
      if (what === "in") zoom(1 / 1.25);
      else if (what === "out") zoom(1.25);
      else fit();
    });
  });

  // Clicking the person in the centre opens their profile; any other person
  // becomes the new centre.
  function activate(id) {
    if (id === state.focus) {
      var n = state.data.nodes.filter(function (x) { return x.id === id; })[0];
      if (n) window.location.href = n.url;
      return;
    }
    load(id);
  }

  function updateLinks(data) {
    var f = data.nodes.filter(function (n) { return n.focus; })[0];
    if (!f) return;
    select.value = String(f.id);
    openLink.href = f.url;
    pdfLink.href = pdfUrl + "?person=" + f.id;
    if (addLink && addTemplate) addLink.href = addTemplate.replace("/0/", "/" + f.id + "/");
    var url = new URL(window.location.href);
    url.searchParams.set("person", f.id);
    window.history.replaceState(null, "", url);
  }

  function load(id) {
    setStatus(gettext("Loading the family tree…"));
    fetch(dataUrl + "?person=" + encodeURIComponent(id), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        state.focus = data.focus;
        if (!data.nodes.length) { setStatus(gettext("The family tree is empty.")); return; }
        setStatus("");
        render(data);
        updateLinks(data);
      })
      .catch(function () { setStatus(gettext("Could not load the family tree. Please try again.")); });
  }

  select.addEventListener("change", function () { load(parseInt(select.value, 10)); });

  // ---- PNG export: drawn on a canvas so the web font is used -----------------
  document.getElementById("tree-png").addEventListener("click", function () {
    var data = state.data;
    if (!data) return;
    var scale = Math.min(2, 8000 / Math.max(data.width, data.height));
    var canvas = document.createElement("canvas");
    canvas.width = Math.round(data.width * scale);
    canvas.height = Math.round(data.height * scale);
    var ctx = canvas.getContext("2d");
    ctx.scale(scale, scale);
    ctx.fillStyle = css("--bg");
    ctx.fillRect(0, 0, data.width, data.height);
    ctx.lineJoin = "round";
    data.lines.forEach(function (line) {
      ctx.beginPath();
      ctx.setLineDash(line.kind === "divorced" || line.kind === "partners" ? [6, 4] : []);
      ctx.strokeStyle = line.kind === "child" ? css("--line-strong") : css("--accent");
      ctx.lineWidth = line.kind === "couple" ? 2 : 1.6;
      line.points.forEach(function (p, i) { if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
      ctx.stroke();
    });
    ctx.setLineDash([]);
    var card = data.card;
    data.nodes.forEach(function (n) {
      ctx.beginPath();
      ctx.roundRect(n.x, n.y, card.w, card.h, 12);
      ctx.fillStyle = n.dup ? css("--surface") : n.focus ? css("--accent-soft") : n.gender === "female" ? css("--female") : css("--male");
      ctx.fill();
      ctx.strokeStyle = n.focus ? css("--accent") : n.gender === "female" ? css("--female-line") : css("--male-line");
      ctx.lineWidth = n.focus ? 2.4 : 1.2;
      ctx.setLineDash(n.dup ? [5, 4] : []);
      ctx.stroke();
      ctx.setLineDash([]);
      cardText(n, card).forEach(function (t) {
        ctx.font = t.font;
        ctx.fillStyle = t.cls === "t-label" ? css("--accent") : t.cls === "t-years" ? css("--muted") : css("--ink");
        ctx.fillText(t.t, n.x + PAD, n.y + t.y);
      });
      if (n.hidden_label) {
        ctx.font = "11px " + FONT;
        ctx.fillStyle = css("--muted");
        ctx.textAlign = "center";
        ctx.fillText(n.hidden_label, n.x + card.w / 2, n.y + card.h + 16);
        ctx.textAlign = "left";
      }
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

  window.addEventListener("resize", function () { if (state.data) fit(); });
  (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).then(function () {
    load(state.focus);
  });
})();
