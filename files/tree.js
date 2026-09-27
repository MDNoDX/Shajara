/* =====================================================================
   FAMILY TREE ENGINE
   Layout model: "family units" — a person plus partners — laid out as a
   tidy tree. Children hang from the union they belong to. A person who
   would appear twice (e.g. cousins who married) is drawn once; the second
   place shows a dashed reference card that jumps to the first.
   ===================================================================== */
const CW = 204, CH = 86, HG = 26, CG = 70, VG = 74, RH = CH + VG;
const T = { mode:"family", focusId:null, depthUp:3, depthDown:3, branchId:"", unionId:"", collapsed:new Set(), k:1, x:0, y:0, layout:null, showLegend:true };

function byBirth(a,b){ const da=dSort((vital(a,"birth").chosen||{}).date), db=dSort((vital(b,"birth").chosen||{}).date); return (da??9e9)-(db??9e9); }
function unionSort(a,b){ return (dSort(a.rel.start)??9e9)-(dSort(b.rel.start)??9e9); }
function unionLabel(r){ const yr = yearLabel(r.start)||"?"; return t(r.unionType==="partnership" ? "p. {y}" : "m. {y}", {y:yr}) + (r.endReason==="divorce" ? " · "+t("div.") : ""); }
const doubtful = (st) => st==="unverified" || st==="family_tradition" || st==="contradicted";

/* ---------- descendant units ---------- */
function descUnit(pid, depth, ctx){
  const u = {pid, dup:false, groups:[], hasKids:false, hidden:0};
  if(ctx.seen.has(pid)){ u.dup = true; return u; }
  ctx.seen.add(pid);
  const groups = new Map();
  unionsOf(pid).sort(unionSort).forEach(un=>groups.set(un.partnerId, {partnerId:un.partnerId, union:un.rel, kids:[]}));
  for(const k of childrenOf(pid)){
    const others = parentsOf(k.person.id).filter(x=>x.person.id!==pid).map(x=>x.person.id);
    let key = others.find(o=>groups.has(o));
    if(key===undefined){ key = others[0] || "__none"; if(!groups.has(key)) groups.set(key, {partnerId: key==="__none"? null : key, union:null, kids:[]}); }
    groups.get(key).kids.push(k);
  }
  let gl = [...groups.values()];
  if(ctx.onlyPartner!==undefined && ctx.rootId===pid) gl = gl.filter(g=>g.partnerId===ctx.onlyPartner);
  u.collapsed = ctx.collapsed.has(pid);
  u.hasKids = gl.some(g=>g.kids.length);
  gl.forEach(g=>{
    g.partnerDup = g.partnerId ? ctx.seen.has(g.partnerId) : false;
    if(g.partnerId) ctx.seen.add(g.partnerId);
  });
  gl.forEach(g=>{
    const show = depth>0 && !u.collapsed;
    g.children = show ? g.kids.sort((a,b)=>byBirth(a.person.id,b.person.id)).map(k=>({rel:k.rel, unit:descUnit(k.person.id, depth-1, ctx)})) : [];
    if(!show) u.hidden += g.kids.length;
  });
  // partner sides: 1st right, 2nd left, 3rd right (outer)…; parentless-group sits under the person
  const withP = gl.filter(g=>g.partnerId), noP = gl.filter(g=>!g.partnerId);
  withP.forEach((g,i)=>{ g.side = i%2===0 ? "R" : "L"; g.rank = Math.floor(i/2); });
  const left = withP.filter(g=>g.side==="L").sort((a,b)=>b.rank-a.rank);
  const right = withP.filter(g=>g.side==="R").sort((a,b)=>a.rank-b.rank);
  u.order = [...left, ...noP, ...right];
  u.cards = [...left.map(g=>({g})), {self:true}, ...right.map(g=>({g}))];
  return u;
}
function measureDesc(u){
  if(u.dup){ u.w = CW; u.ownW = CW; return u.w; }
  u.ownW = u.cards.length*CW + (u.cards.length-1)*CG;
  let cw = 0, n = 0;
  u.order.forEach((g,gi)=>{ g.children.forEach(c=>{ measureDesc(c.unit); cw += c.unit.w; n++; }); });
  const groupsWithKids = u.order.filter(g=>g.children.length).length;
  u.childW = n ? cw + HG*(n-1) + HG*0.8*Math.max(0,groupsWithKids-1) : 0;
  u.w = Math.max(u.ownW, u.childW);
  return u.w;
}
function placeDesc(u, x0, y, out){
  if(u.dup){ out.nodes.push({pid:u.pid, x:x0, y, dup:true}); u.selfX = x0; return; }
  const bx = x0 + (u.w - u.ownW)/2;
  const pos = new Map();
  u.cards.forEach((c,i)=>{ const x = bx + i*(CW+CG); if(c.self){ u.selfX = x; out.nodes.push({pid:u.pid, x, y, unitHasKids:u.hasKids, collapsed:u.collapsed, hidden:u.hidden}); } else { pos.set(c.g, x); out.nodes.push({pid:c.g.partnerId, x, y, dup:c.g.partnerDup, partner:true}); } });
  // couple lines
  u.order.forEach(g=>{
    if(!g.partnerId) { g.ux = u.selfX + CW/2; g.uy = y + CH; return; }
    const px = pos.get(g); const adjacent = Math.abs(px - u.selfX) === CW+CG;
    const cls = ["t-couple", g.union && g.union.unionType==="partnership" ? "partnership" : "", g.union && doubtful(g.union.status) ? "doubt" : ""].join(" ");
    const yl = y + CH/2;
    const x1 = Math.min(px, u.selfX) + CW, x2 = Math.max(px, u.selfX);
    if(adjacent){
      out.edges.push({cls, d:`M${x1},${yl} H${x2}`});
      if(g.union && g.union.endReason==="divorce"){ const mx=(x1+x2)/2; out.edges.push({cls:"t-couple", d:`M${mx-5},${yl+7} L${mx-1},${yl-7} M${mx+1},${yl+7} L${mx+5},${yl-7}`}); }
      g.ux = (x1+x2)/2; g.uy = yl;
    } else {
      const top = y - 14, sx = u.selfX + CW/2, pxm = px + CW/2;
      out.edges.push({cls, d:`M${sx},${y} V${top} H${pxm} V${y}`});
      g.ux = pxm; g.uy = y + CH;
    }
    if(g.union){
      const lab = unionLabel(g.union);
      out.labels.push({x: adjacent? g.ux : (u.selfX+CW/2 + px+CW/2)/2, y: adjacent? yl-8 : y-20, t:lab, cls:"t-ulabel"});
    } else {
      out.labels.push({x: adjacent? g.ux : (u.selfX+CW/2 + px+CW/2)/2, y: adjacent? yl-8 : y-20, t:"no union recorded", cls:"t-ulabel"});
    }
  });
  if(u.hasKids) out.toggles.push({pid:u.pid, x:u.selfX + CW/2, y:y+CH+ (u.collapsed? 16 : 0), collapsed:u.collapsed, hidden:u.hidden, only: u.collapsed});
  if(!u.childW) return;
  let cx = x0 + (u.w - u.childW)/2; const cy = y + RH; let first = true;
  u.order.forEach(g=>{
    if(!g.children.length) return;
    if(!first) cx += HG*0.8; first = false;
    const centers = [];
    g.children.forEach(c=>{ placeDesc(c.unit, cx, cy, out); centers.push({x:c.unit.selfX + CW/2, rel:c.rel}); cx += c.unit.w + HG; });
    const barY = cy - VG/2;
    const minX = Math.min(g.ux, ...centers.map(c=>c.x)), maxX = Math.max(g.ux, ...centers.map(c=>c.x));
    out.edges.push({cls:"t-edge", d:`M${g.ux},${g.uy} V${barY}`});
    out.edges.push({cls:"t-edge", d:`M${minX},${barY} H${maxX}`});
    centers.forEach(c=>{
      const nat = c.rel.nature; const cls = ["t-edge", nat==="adoptive"?"adopt": (["step","guardian","foster"].includes(nat)? nat : ""), doubtful(c.rel.status)?"doubt":""].join(" ");
      out.edges.push({cls, d:`M${c.x},${barY} V${cy}`});
      if(nat!=="biological") out.labels.push({x:c.x+6, y:cy-8, t: nat==="unknown" ? t("link type unknown") : PC_NATURE[nat].toLowerCase(), cls:"t-elabel", anchor:"start"});
    });
  });
}

/* ---------- ancestor nodes ---------- */
function ancNode(pid, depth, ctx){
  const n = {pid, parents:[]};
  if(depth<=0) return n;
  const ps = parentsOf(pid);
  let chosen = ps.filter(x=>x.rel.nature==="biological" || x.rel.nature==="unknown");
  if(!chosen.length) chosen = ps;
  chosen = chosen.sort((a,b)=>(a.person.sex==="male"?0:a.person.sex==="female"?1:2)-(b.person.sex==="male"?0:b.person.sex==="female"?1:2)).slice(0,2);
  n.more = ps.length - chosen.length;
  n.parents = chosen.map(x=>{
    if(ctx.seen.has(x.person.id)) return {rel:x.rel, node:{pid:x.person.id, dup:true, parents:[]}};
    ctx.seen.add(x.person.id);
    return {rel:x.rel, node:ancNode(x.person.id, depth-1, ctx)};
  });
  if(ctx.ghosts && n.parents.length<2 && !(P(pid).noParentSearch)){
    const have = n.parents.map(x=>x.node.pid && P(x.node.pid) ? P(x.node.pid).sex : null);
    const need = n.parents.length===0 ? ["male","female"] : [have[0]==="male"?"female":have[0]==="female"?"male":"unknown"];
    need.forEach(sx=>n.parents.push({ghost:true, node:{ghost:true, forPid:pid, sex:sx, parents:[]}}));
  }
  return n;
}
function measureAnc(n){ if(!n.parents.length){ n.w = CW; return CW; } let s = 0; n.parents.forEach(p=>{ s += measureAnc(p.node); }); s += HG*(n.parents.length-1); n.w = Math.max(CW, s); return n.w; }
function placeAnc(n, x0, y, out, skipSelf){
  const x = x0 + (n.w - CW)/2; n.x = x;
  if(!skipSelf){ if(n.ghost) out.nodes.push({ghost:true, forPid:n.forPid, sex:n.sex, x, y}); else out.nodes.push({pid:n.pid, x, y, dup:n.dup}); }
  if(!n.parents.length) return;
  const pw = n.parents.reduce((s,p)=>s+p.node.w,0) + HG*(n.parents.length-1);
  let px = x0 + (n.w - pw)/2; const py = y - RH;
  const pts = [];
  n.parents.forEach(p=>{ placeAnc(p.node, px, py, out); pts.push({x:p.node.x, p}); px += p.node.w + HG; });
  const barY = y - VG/2, cx = x + CW/2;
  // couple line between the two parents when a union is recorded
  if(pts.length===2 && !pts[0].p.ghost && !pts[1].p.ghost){
    const u = unionsOf(pts[0].p.node.pid).find(u=>u.partnerId===pts[1].p.node.pid);
    if(u){
      const a = pts[0].x + CW, b = pts[1].x;
      if(b - a < 400){ out.edges.push({cls:"t-couple "+(doubtful(u.rel.status)?"doubt":""), d:`M${a},${py+CH/2} H${b}`}); out.labels.push({x:(a+b)/2, y:py+CH/2-8, t:unionLabel(u.rel), cls:"t-ulabel"}); }
    }
  }
  pts.forEach(({x:pxx, p})=>{
    const top = pxx + CW/2;
    const nat = p.ghost ? "" : p.rel.nature;
    const cls = p.ghost ? "t-edge doubt" : ["t-edge", nat==="adoptive"?"adopt":(["step","guardian","foster"].includes(nat)?nat:""), doubtful(p.rel.status)?"doubt":""].join(" ");
    out.edges.push({cls, d:`M${top},${py+CH} V${barY} H${cx} V${y}`});
    if(!p.ghost && nat!=="biological") out.labels.push({x:top+6, y:barY-6, t: nat==="unknown"?t("link type unknown"):PC_NATURE[nat].toLowerCase(), cls:"t-elabel", anchor:"start"});
  });
  if(n.more) out.labels.push({x:cx, y:y-6, t:tn(n.more,"+{n} other parent link — see profile","+{n} other parent links — see profile"), cls:"t-elabel"});
}

/* ---------- compose a view ---------- */
function rootsForFull(set){
  const ppl = Object.values(S.people).filter(p=>!set || set.has(p.id));
  const hasParentsIn = (id) => parentsOf(id).some(x=>!set || set.has(x.person.id));
  let roots = ppl.filter(p=>!hasParentsIn(p.id));
  roots = roots.filter(r=>!unionsOf(r.id).some(u=>(!set||set.has(u.partnerId)) && hasParentsIn(u.partnerId)));
  const sizeOf = (id)=>{ let n=0; const st=[id], s=new Set(); while(st.length){ const c=st.pop(); if(s.has(c)) continue; s.add(c); n++; childrenOf(c).forEach(x=>st.push(x.person.id)); } return n; };
  return roots.sort((a,b)=>sizeOf(b.id)-sizeOf(a.id) || byBirth(a.id,b.id)).map(r=>r.id);
}
function computeLayout(){
  const out = {nodes:[], edges:[], labels:[], toggles:[], title:""};
  const f = T.focusId && P(T.focusId) ? T.focusId : null;
  const mode = T.mode;
  if(!Object.keys(S.people).length) return null;
  const descFrom = (rootId, depth, extra={}) => { const ctx = {seen:new Set(), collapsed:T.collapsed, rootId, ...extra}; const u = descUnit(rootId, depth, ctx); measureDesc(u); return {u, ctx}; };

  if(mode==="descendants" || mode==="couple" || mode==="branch"){
    let rootId = f, extra = {}, depth = T.depthDown;
    if(mode==="couple"){ const r = S.rels[T.unionId]; if(!r) return {empty:"Choose a couple to show their children and grandchildren."}; rootId = r.aId; extra.onlyPartner = r.bId; out.title = `${nameById(r.aId)} & ${nameById(r.bId)}`; }
    if(mode==="branch"){ const b = S.branches[T.branchId]; if(!b) return {empty: Object.keys(S.branches).length ? "Choose a branch to show." : "No branches yet. Use “Branches” to define one by its founder."}; if(!P(b.founderId)) return {empty:"This branch's founder was deleted. Edit the branch to choose a new founder."}; rootId = b.founderId; depth = 99; out.title = b.name; }
    if(!rootId) return {empty:"Choose a person to start from."};
    const {u} = descFrom(rootId, depth, extra); placeDesc(u, 0, 0, out);
  } else if(mode==="ancestors"){
    if(!f) return {empty:"Choose a person to trace their ancestors."};
    const n = ancNode(f, T.depthUp, {seen:new Set([f]), ghosts:true}); measureAnc(n); placeAnc(n, 0, 0, out);
  } else if(mode==="family"){
    if(!f) return {empty:"Choose a person to centre the tree on."};
    const n = ancNode(f, T.depthUp, {seen:new Set([f]), ghosts:true}); measureAnc(n);
    const up = {nodes:[], edges:[], labels:[], toggles:[]}; placeAnc(n, 0, 0, up, true);
    const {u} = descFrom(f, T.depthDown); const down = {nodes:[], edges:[], labels:[], toggles:[]}; placeDesc(u, 0, 0, down);
    const dx = n.x - u.selfX;
    down.nodes.forEach(o=>o.x+=dx); down.toggles.forEach(o=>o.x+=dx); down.labels.forEach(o=>o.x+=dx);
    down.edges.forEach(e=>{ e.d = shiftPath(e.d, dx); });
    ["nodes","edges","labels","toggles"].forEach(k=>out[k].push(...up[k], ...down[k]));
  } else { // full
    const ids = rootsForFull(null); const ctx = {seen:new Set(), collapsed:T.collapsed}; let x = 0;
    for(const r of ids){ if(ctx.seen.has(r)) continue; ctx.rootId = r; const u = descUnit(r, 99, ctx); measureDesc(u); placeDesc(u, x, 0, out); x += u.w + CW*0.6; }
  }
  out.nodes.forEach(nd=>{ if(nd.pid===f) nd.focus = true; });
  const xs = out.nodes.map(n=>n.x), ys = out.nodes.map(n=>n.y);
  out.box = {x0:Math.min(...xs), y0:Math.min(...ys)-30, x1:Math.max(...xs)+CW, y1:Math.max(...ys)+CH+30};
  return out;
}
function shiftPath(d, dx){ return d.replace(/([MLH])(-?[\d.]+)/g, (m,c,n)=>c+(parseFloat(n)+dx)); }

/* ---------- render ---------- */
function wrapName(s, max=20){
  const words = s.split(/\s+/); const lines=[""]; for(const w of words){ const cur = lines[lines.length-1]; if((cur+" "+w).trim().length<=max) lines[lines.length-1]=(cur+" "+w).trim(); else lines.push(w); }
  if(lines.length>2){ lines[1] = (lines.slice(1).join(" ")).slice(0,max-1)+"…"; lines.length=2; }
  return lines.map(l=>l.length>max? l.slice(0,max-1)+"…" : l);
}
function cardSVG(nd, focusId, forExport){
  if(nd.ghost){
    const lbl = nd.sex==="male"?"Father":nd.sex==="female"?"Mother":"Parent"; const role = nd.sex==="male"?"father":nd.sex==="female"?"mother":"parent";
    return `<g class="t-card ghost" transform="translate(${nd.x},${nd.y})" ${forExport?"":`tabindex="0" role="button" data-ghost="${nd.forPid}" data-sex="${nd.sex}" aria-label="${esc(t("Add "+role+" of {name}",{name:nameById(nd.forPid)}))}"`}>
      <rect class="bg" width="${CW}" height="${CH}" rx="6"/>
      <text class="nm" x="16" y="34">${t(lbl+" not recorded")}</text>
      <text class="lb" x="16" y="56">${forExport?"Not yet researched":"＋ Add what you know"}</text></g>`;
  }
  const p = P(nd.pid); if(!p) return "";
  const yl = yearsLine(p); const name = nameOf(p); const lines = wrapName(name);
  const kin = nd.dup ? t("Shown elsewhere — select to jump") : kinLabel(focusId, p.id);
  const cls = ["t-card", nd.focus?"focus":"", nd.dup?"dup":"", p.living==="living"?"living":""].join(" ");
  const aria = `${name}, ${yl.text}${kin? ", "+kin:""}${yl.conflict?", "+t("conflicting dates"):""}`;
  const ny = lines.length===1 ? 34 : 27;
  return `<g class="${cls}" transform="translate(${nd.x},${nd.y})" ${forExport?"":`tabindex="0" role="button" data-pid="${p.id}" ${nd.dup?'data-dup="1"':""} aria-label="${esc(aria)}"`}>
    <rect class="bg" width="${CW}" height="${CH}" rx="6"/>
    <rect class="stripe" x="0" y="10" width="3" height="${CH-20}" rx="1.5"/>
    <circle class="mono" cx="34" cy="${CH/2}" r="21"/><text class="mono-t" x="34" y="${CH/2}">${esc(initials(p))}</text>
    ${lines.map((l,i)=>`<text class="nm" x="64" y="${ny+i*17}">${esc(l)}</text>`).join("")}
    <text class="yr${yl.conflict?" yr-warn":""}" x="64" y="${ny+lines.length*17+2}">${yl.conflict?"⚠ ":""}${esc(yl.text)}</text>
    ${kin?`<text class="lb" x="64" y="${CH-9}">${esc(kin.length>26?kin.slice(0,25)+"…":kin)}</text>`:""}
  </g>`;
}
function treeContentSVG(L, forExport){
  const edges = L.edges.map(e=>`<path class="${e.cls}" d="${e.d}"/>`).join("");
  const labels = L.labels.map(l=>`<text class="${l.cls}" x="${l.x}" y="${l.y}" ${l.anchor?`text-anchor="${l.anchor}"`:""}>${esc(l.t)}</text>`).join("");
  const cards = L.nodes.map(n=>cardSVG(n, T.focusId, forExport)).join("");
  const toggles = forExport ? "" : L.toggles.map(t=>`<g class="t-tog" data-toggle="${t.pid}" transform="translate(${t.x},${t.y+12})" tabindex="0" role="button" aria-label="${esc(tg(t.collapsed?"Expand descendants of {name}":"Collapse descendants of {name}",{name:nameById(t.pid)}))}"><circle r="${t.collapsed?15:10}"/><text>${t.collapsed?"+"+t.hidden:"−"}</text></g>`).join("");
  return edges + labels + cards + toggles;
}

let svgEl = null;
function renderTreeCanvas(fit){
  const wrap = $("#canvasWrap"); if(!wrap) return;
  const L = computeLayout(); T.layout = L;
  if(!L || L.empty){
    wrap.innerHTML = `<div class="empty-tree"><div><h2>${!L? "No one in the tree yet" : "Nothing to show"}</h2><p class="muted">${!L? "Add the first person — yourself, or the oldest ancestor you know." : esc(L.empty)}</p>${!L?`<button class="btn primary" data-act="add-person">Add first person</button>`:""}</div></div>`;
    return;
  }
  wrap.innerHTML = `<svg id="treeSvg" role="group" aria-label="Family tree. Drag to pan, scroll or use plus and minus to zoom." tabindex="0"><g id="treeG">${treeContentSVG(L,false)}</g></svg>
    <div class="zoomctl"><button data-z="in" aria-label="Zoom in">+</button><button data-z="out" aria-label="Zoom out">−</button><button data-z="fit" aria-label="Fit tree to screen">Fit</button></div>
    ${legendHTML()}`;
  svgEl = $("#treeSvg");
  bindTreeInteraction();
  if(fit || !T.hasView) fitTree(); else applyView();
  T.hasView = true;
}
function legendHTML(){
  const ln = (cls, label) => `<li><svg width="40" height="10"><path class="${cls}" d="M2,5 H38"/></svg>${label}</li>`;
  return `<div class="legend ${T.showLegend?"":"hidden"}" id="legend"><div class="row" style="justify-content:space-between"><b>Line styles</b><button class="link small" data-act="legend-off">Hide</button></div><ul>
   ${ln("t-edge","Biological, supported")}${ln("t-edge adopt","Adoptive")}${ln("t-edge step","Step, guardian or foster")}${ln("t-edge doubt","Unverified or family tradition")}${ln("t-couple","Marriage (label: m. year)")}${ln("t-couple partnership","Partnership")}
   <li><span class="warn" style="color:var(--brick);font-weight:700;font-size:12px;width:40px">⚠</span>Sources disagree about dates</li><li><span style="font-weight:700;width:40px;text-align:center">~</span>Year is approximate</li></ul></div>`;
}
function applyView(){ const g = $("#treeG"); if(!g) return; g.setAttribute("transform", `translate(${T.x},${T.y}) scale(${T.k})`); svgEl.classList.toggle("far", T.k < 0.5); }
function fitTree(){
  if(!svgEl || !T.layout || !T.layout.box) return; const b = T.layout.box; const W = svgEl.clientWidth || 800, H = svgEl.clientHeight || 600;
  const w = b.x1-b.x0+80, h = b.y1-b.y0+80; T.k = Math.min(W/w, H/h, 1.15); T.k = Math.max(T.k, 0.08);
  T.x = (W - (b.x1-b.x0)*T.k)/2 - b.x0*T.k; T.y = (H - (b.y1-b.y0)*T.k)/2 - b.y0*T.k; applyView();
}
function zoomAt(cx, cy, f){ const k2 = Math.min(3, Math.max(0.08, T.k*f)); f = k2/T.k; T.x = cx - (cx - T.x)*f; T.y = cy - (cy - T.y)*f; T.k = k2; applyView(); }
function centerOn(pid, highlight){
  const nd = T.layout && T.layout.nodes && T.layout.nodes.find(n=>n.pid===pid && !n.dup); if(!nd || !svgEl) return false;
  const W = svgEl.clientWidth, H = svgEl.clientHeight; if(T.k < 0.6) T.k = 0.85;
  T.x = W/2 - (nd.x + CW/2)*T.k; T.y = H/2 - (nd.y + CH/2)*T.k; applyView();
  if(highlight){ const el = svgEl.querySelector(`[data-pid="${pid}"]:not([data-dup])`); if(el){ el.classList.add("hl"); setTimeout(()=>el.classList.remove("hl"), 1600); el.focus({preventScroll:true}); } }
  return true;
}
function bindTreeInteraction(){
  const pts = new Map(); let moved = 0, start = null, pinch = null;
  svgEl.addEventListener("wheel", e=>{ e.preventDefault(); const r = svgEl.getBoundingClientRect(); zoomAt(e.clientX-r.left, e.clientY-r.top, Math.exp(-e.deltaY*0.0015)); }, {passive:false});
  svgEl.addEventListener("pointerdown", e=>{ pts.set(e.pointerId, {x:e.clientX, y:e.clientY}); moved = 0; start = {x:e.clientX, y:e.clientY, tx:T.x, ty:T.y};
    if(pts.size===2){ const [a,b] = [...pts.values()]; pinch = {d:Math.hypot(a.x-b.x,a.y-b.y), k:T.k}; } });
  svgEl.addEventListener("pointermove", e=>{ if(!pts.has(e.pointerId)) return; pts.set(e.pointerId, {x:e.clientX, y:e.clientY});
    if(pts.size===2 && pinch){ const [a,b] = [...pts.values()]; const d = Math.hypot(a.x-b.x,a.y-b.y); const r = svgEl.getBoundingClientRect(); zoomAt((a.x+b.x)/2-r.left, (a.y+b.y)/2-r.top, (pinch.k*d/pinch.d)/T.k); moved = 99; return; }
    const dx = e.clientX-start.x, dy = e.clientY-start.y; if(Math.abs(dx)+Math.abs(dy) > 4){ moved = 99; if(!svgEl.hasPointerCapture(e.pointerId)) svgEl.setPointerCapture(e.pointerId); svgEl.classList.add("dragging"); }
    if(moved){ T.x = start.tx + dx; T.y = start.ty + dy; applyView(); } });
  const up = e=>{ pts.delete(e.pointerId); if(pts.size<2) pinch=null; svgEl.classList.remove("dragging"); };
  svgEl.addEventListener("pointerup", up); svgEl.addEventListener("pointercancel", up);
  svgEl.addEventListener("click", e=>{ if(moved>4){ moved=0; return; } activateTreeTarget(e.target); });
  svgEl.addEventListener("keydown", e=>{
    if((e.key==="Enter"||e.key===" ") && e.target !== svgEl){ e.preventDefault(); activateTreeTarget(e.target); return; }
    const step = 60; const r = svgEl.getBoundingClientRect();
    const map = {ArrowLeft:[step,0], ArrowRight:[-step,0], ArrowUp:[0,step], ArrowDown:[0,-step]};
    if(map[e.key] && e.target===svgEl){ e.preventDefault(); T.x+=map[e.key][0]; T.y+=map[e.key][1]; applyView(); }
    if(e.key==="+"||e.key==="="){ zoomAt(r.width/2, r.height/2, 1.2); } if(e.key==="-"){ zoomAt(r.width/2, r.height/2, 1/1.2); } if(e.key==="0"){ fitTree(); }
  });
  $(".zoomctl").addEventListener("click", e=>{ const z = e.target.closest("[data-z]"); if(!z) return; const r = svgEl.getBoundingClientRect(); if(z.dataset.z==="in") zoomAt(r.width/2,r.height/2,1.25); else if(z.dataset.z==="out") zoomAt(r.width/2,r.height/2,0.8); else fitTree(); });
}
function activateTreeTarget(t){
  const tog = t.closest("[data-toggle]"); if(tog){ const id = tog.dataset.toggle; T.collapsed.has(id)? T.collapsed.delete(id) : T.collapsed.add(id); renderTreeCanvas(false); return; }
  const gh = t.closest("[data-ghost]"); if(gh){ openAddRelative(gh.dataset.ghost, gh.dataset.sex==="male"?"father":gh.dataset.sex==="female"?"mother":"parent"); return; }
  const c = t.closest("[data-pid]"); if(!c) return;
  if(c.dataset.dup){ centerOn(c.dataset.pid, true); return; }
  go("person", c.dataset.pid);
}

/* ---------- export (SVG / PNG) — light theme inlined for print ---------- */
const EXPORT_CSS = `
text{font-family:Georgia,'Times New Roman',serif}
.t-card rect.bg{fill:#fff;stroke:#B7BFBC;stroke-width:1}.t-card.focus rect.bg{stroke:#2C6A60;stroke-width:2.5}
.t-card .mono{fill:#F6F7F5;stroke:#B7BFBC}.t-card .mono-t{fill:#5A666A;font:600 15px Georgia,serif;text-anchor:middle;dominant-baseline:central}
.t-card .nm{fill:#1B2427;font:600 14.5px Georgia,serif}.t-card .yr{fill:#5A666A;font:12.5px Helvetica,Arial,sans-serif}.t-card .yr.yr-warn{fill:#9E3727;font-weight:600;font-size:11.5px}
.t-card .lb{fill:#2C6A60;font:500 11.5px Helvetica,Arial,sans-serif}.t-card .warn{fill:#9E3727;font:700 12px Helvetica,Arial,sans-serif}
.t-card.dup rect.bg,.t-card.ghost rect.bg{fill:none;stroke-dasharray:5 4}.t-card.ghost .nm{fill:#5A666A;font-style:italic;font-weight:400}
.t-card .stripe{fill:#B7BFBC}.t-card.living .stripe{fill:#2C6A60}
.t-edge{fill:none;stroke:#1B2427;stroke-opacity:.55;stroke-width:1.6}.t-edge.adopt{stroke-dasharray:8 5}
.t-edge.step,.t-edge.guardian,.t-edge.foster{stroke-dasharray:3 4}.t-edge.doubt{stroke-opacity:.35;stroke-dasharray:1.5 4;stroke-linecap:round}
.t-couple{fill:none;stroke:#1B2427;stroke-opacity:.6;stroke-width:1.6}.t-couple.partnership{stroke-dasharray:6 4}.t-couple.doubt{stroke-opacity:.35;stroke-dasharray:1.5 4}
.t-ulabel{fill:#5A666A;font:11px Helvetica,Arial,sans-serif;text-anchor:middle}.t-elabel{fill:#5A666A;font:italic 11px Helvetica,Arial,sans-serif}
.ttl{font:600 26px Georgia,serif;fill:#1B2427}.sub{font:13px Helvetica,Arial,sans-serif;fill:#5A666A}`;
function buildExportSVG(){
  const L = T.layout; if(!L || !L.box) return null; const b = L.box; const pad = 48, head = 70;
  const w = Math.ceil(b.x1-b.x0+pad*2), h = Math.ceil(b.y1-b.y0+pad*2+head);
  const nm = nameById(T.focusId); const title = ({family:t("Family of {name}",{name:nm}), ancestors:t("Ancestors of {name}",{name:nm}), descendants:t("Descendants of {name}",{name:nm}), full:t("{title} — full tree",{title:archiveTitle()})})[T.mode] || L.title || archiveTitle();
  const privacy = t("Living people are shown with names and birth years only. Exported {d}",{d:new Date().toISOString().slice(0,10)}) + (WS==="demo"?" · "+t("DEMO DATA — fictional family"):"");
  return locString(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><style>${EXPORT_CSS}</style><rect width="100%" height="100%" fill="#fff"/>
  <text class="ttl" x="${pad}" y="${pad}">${esc(title)}</text><text class="sub" x="${pad}" y="${pad+22}">${esc(privacy)}</text>
  <g transform="translate(${pad-b.x0},${pad+head-b.y0})">${treeContentSVG(L,true)}</g></svg>`);
}
async function exportTree(fmt){
  const svg = buildExportSVG(); if(!svg){ toast("Nothing to export — the tree view is empty."); return; }
  const base = (archiveTitle()+"-"+T.mode+"-tree").replace(/[^\w\-]+/g,"-").toLowerCase();
  if(fmt==="svg") return saveFile(base+".svg", new Blob([svg],{type:"image/svg+xml"}));
  const img = new Image(); const url = URL.createObjectURL(new Blob([svg],{type:"image/svg+xml"}));
  try{
    await new Promise((res,rej)=>{ img.onload=res; img.onerror=()=>rej(new Error("The tree image could not be drawn.")); img.src=url; });
    const w = img.naturalWidth || img.width, h = img.naturalHeight || img.height;
    const scale = Math.min(3, Math.sqrt(60e6/(w*h))); // stay under typical canvas limits
    const c = document.createElement("canvas"); c.width = Math.round(w*scale); c.height = Math.round(h*scale);
    const ctx = c.getContext("2d"); ctx.scale(scale,scale); ctx.drawImage(img,0,0);
    const blob = await new Promise(r=>c.toBlob(r,"image/png"));
    if(!blob) throw new Error("This tree is too large for a PNG in this browser. Export SVG instead — it stays sharp at any size.");
    await saveFile(base+".png", blob);
  }catch(e){ toast(e.message); } finally { URL.revokeObjectURL(url); }
}
