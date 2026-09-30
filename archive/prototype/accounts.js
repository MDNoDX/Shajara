/* =====================================================================
   ACCOUNTS — many people can each keep their own archive.
   Registry + archives live in the viewer's private claude.ai space when
   available, otherwise in this browser. Passwords are stored only as a
   salted PBKDF2 hash. This is a simple gate for a shared device, not
   internet-grade authentication (that needs a server — later phase).
   ===================================================================== */
const ACC = { ready:false, mode:null, db:null, me:null, ref:null, list:[], cur:null, err:null };
const ACC_KEY = "family-archive:accounts", SESSION_KEY = "family-archive:session", LEGACY_LOCAL = "family-archive:mine:v1";
let memSession = null;

const hex = (u8) => [...u8].map(b=>b.toString(16).padStart(2,"0")).join("");
const unhex = (h) => new Uint8Array((h.match(/../g)||[]).map(x=>parseInt(x,16)));
async function hashPw(pw, salt, algo){
  const want = algo || (window.crypto && crypto.subtle ? "pbkdf2" : "fnv");
  if(want==="pbkdf2"){
    if(!(window.crypto && crypto.subtle)) throw new Error(t("This browser can't check this password here. Open the archive in the same browser where the account was created."));
    const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveBits"]);
    const bits = await crypto.subtle.deriveBits({name:"PBKDF2", hash:"SHA-256", salt:unhex(salt), iterations:120000}, key, 256);
    return {algo:"pbkdf2", hash:hex(new Uint8Array(bits))};
  }
  let h1 = 2166136261>>>0, h2 = 5381; const s = salt+":"+pw;
  for(let r=0;r<4000;r++) for(let i=0;i<s.length;i++){ const c = s.charCodeAt(i); h1 = Math.imul(h1 ^ c, 16777619)>>>0; h2 = (Math.imul(h2, 33) ^ c ^ r)>>>0; }
  return {algo:"fnv", hash:h1.toString(16)+h2.toString(16)};
}
function newSalt(){ const u = new Uint8Array(16); (window.crypto && crypto.getRandomValues) ? crypto.getRandomValues(u) : u.forEach((_,i)=>u[i]=Math.random()*256|0); return hex(u); }
const userKey = (u) => fold(String(u||"").trim());

async function openAccountStore(){
  try{
    if(window.claude && window.claude.use){
      const db = await window.claude.use("db");
      const user = db ? await window.claude.use("user") : null;
      const me = user ? await user.id() : null;
      if(db && me){
        const ref = db.doc(`data/users/${me}/accounts`);
        const snap = await ref.get();
        let data = snap.exists ? snap.data() : null;
        if(!data){ await ref.set({list:[]}); data = {list:[]}; }   // also proves we may write here
        Object.assign(ACC, {mode:"db", db, me, ref, list: (data.list||[]).map(x=>({...x}))});
      }
    }
  }catch(e){ console.warn("claude.ai storage unavailable, using this browser", e); ACC.mode = null; }
  if(!ACC.mode){
    try{ localStorage.setItem("family-archive:probe","1"); localStorage.removeItem("family-archive:probe");
      ACC.mode = "local"; const v = localStorage.getItem(ACC_KEY); ACC.list = v ? (JSON.parse(v).list||[]) : []; }
    catch(e){ ACC.mode = "memory"; ACC.list = []; }
  }
  let sid = null; try{ sid = JSON.parse(localStorage.getItem(SESSION_KEY)||"null"); }catch(e){ sid = memSession; }
  ACC.cur = (sid && ACC.list.find(a=>a.id===sid.id)) || null;
  ACC.ready = true;
}
async function saveRegistry(){
  const list = ACC.list.map(a=>({...a}));
  if(ACC.mode==="db") await ACC.ref.set({list});
  else if(ACC.mode==="local") localStorage.setItem(ACC_KEY, JSON.stringify({list}));
}
function setSession(a){ memSession = a ? {id:a.id} : null; try{ if(a) localStorage.setItem(SESSION_KEY, JSON.stringify({id:a.id})); else localStorage.removeItem(SESSION_KEY); }catch(e){} }
function accountBackend(a){
  if(ACC.mode==="db") return DbBackend(ACC.db, ACC.me, a.store);
  if(ACC.mode==="local") return LocalBackend(a.store);
  return MemoryBackend("Not saved — this browser blocks storage. Download a backup before you close the page.");
}
async function legacyHasData(){
  try{
    if(ACC.mode==="db") return await DbBackend(ACC.db, ACC.me, "archive").hasData();
    if(ACC.mode==="local"){ const v = JSON.parse(localStorage.getItem(LEGACY_LOCAL)||"null"); return !!(v && v.people && Object.keys(v.people).length); }
  }catch(e){}
  return false;
}
function validUsername(u){
  u = String(u||"").trim();
  if(u.length < 3) return t("The username must be at least 3 characters.");
  if(u.length > 30) return t("The username can be at most 30 characters.");
  if(!/^[\p{L}\p{N}._-]+$/u.test(u)) return t("Use only letters, numbers, dot, dash or underscore in the username — no spaces.");
  return null;
}
async function registerAccount(username, pw){
  username = String(username||"").trim();
  const e = validUsername(username); if(e) return {err:e};
  if(!pw) return {err:t("Enter a password.")};
  if(ACC.list.some(a=>a.key===userKey(username))) return {err:t("This username is already taken on this device. Sign in, or choose another name.")};
  const salt = newSalt(); const h = await hashPw(pw, salt);
  const id = uid("acct");
  let store = ACC.mode==="db" ? "a_"+id : "family-archive:acct:"+id, adopted = false;
  if(!ACC.list.length && await legacyHasData()){ store = ACC.mode==="db" ? "archive" : LEGACY_LOCAL; adopted = true; }
  const a = {id, username, key:userKey(username), salt, algo:h.algo, hash:h.hash, store, created:nowISO()};
  ACC.list.push(a);
  try{ await saveRegistry(); }catch(x){ ACC.list.pop(); return {err:t("The account could not be saved ({code}).",{code:x.code||x.message})}; }
  return {account:a, adopted};
}
async function checkLogin(username, pw){
  const a = ACC.list.find(x=>x.key===userKey(username));
  if(!a) return {err:"no_user"};
  let h; try{ h = await hashPw(pw, a.salt, a.algo); }catch(x){ return {err:x.message}; }
  if(h.hash!==a.hash) return {err:"bad_pw"};
  return {account:a};
}
async function changePassword(a, oldPw, newPw){
  const c = await checkLogin(a.username, oldPw); if(c.err) return t("The current password is not correct.");
  if(!newPw) return t("Enter a new password.");
  const salt = newSalt(); const h = await hashPw(newPw, salt);
  Object.assign(a, {salt, algo:h.algo, hash:h.hash}); await saveRegistry(); return null;
}

/* ---------- session start / end ---------- */
async function startSession(a, note){
  ACC.cur = a; setSession(a);
  MINE = null; WS = "mine"; S = empty(); backend = MemoryBackend("…");
  T.focusId = null; T.collapsed = new Set(); T.hasView = false;
  R.screen = "app"; go("dashboard");
  await openMine();
  if(note) toast(note);
}
async function logout(){
  await writeChain;
  ACC.cur = null; setSession(null); MINE = null;
  WS = "demo"; S = DEMO_S; backend = MemoryBackend("Demo"); T.focusId = DEMO_ROOT; T.hasView = false;
  R.screen = "login"; LOGIN.tab = "in"; LOGIN.err = ""; go("login");
}
async function deleteAccount(a){
  await writeChain;
  if(MINE && MINE.backend){ try{ await MINE.backend.wipe(MINE.data); }catch(e){ console.warn(e); } }
  ACC.list = ACC.list.filter(x=>x.id!==a.id); await saveRegistry();
  await logout(); toast(t("The account and its archive were deleted."));
}

/* ---------- login screen ---------- */
const LOGIN = { tab:"in", err:"", busy:false, user:"" };
function storageNote(){
  return ACC.mode==="db" ? t("Accounts are kept in your private space on claude.ai.")
       : ACC.mode==="local" ? t("Accounts are kept in this browser on this device.")
       : t("This browser blocks storage, so accounts last only until the page is closed.");
}
function loginHTML(){
  const L = LOGIN; const inTab = L.tab==="in";
  return `<div class="login-wrap"><div class="login-top">${langSwitchHTML()}</div>
  <div class="login">
    <div class="login-brand">${BRAND_SVG}<div><h1>${t("Family Archive")}</h1><p>${t("Keep your family’s history, study it, and pass it on.")}</p></div></div>
    <div class="tabs" role="tablist">
      <button role="tab" data-ltab="in" aria-selected="${inTab}">${t("Sign in")}</button>
      <button role="tab" data-ltab="new" aria-selected="${!inTab}">${t("New account")}</button>
    </div>
    <form id="loginForm" novalidate>
      <label class="fld"><span>${t("Username")}</span><input name="user" autocomplete="username" autocapitalize="off" spellcheck="false" value="${esc(L.user)}" required></label>
      <label class="fld"><span>${t("Password")}</span><div class="pw"><input name="pw" type="password" autocomplete="${inTab?"current-password":"new-password"}" required><button type="button" class="btn sm ghost" data-showpw aria-label="${t("Show password")}">${t("Show")}</button></div></label>
      ${inTab?"":`<label class="fld"><span>${t("Repeat password")}</span><input name="pw2" type="password" autocomplete="new-password" required></label>`}
      <p class="err" id="loginErr" role="alert" ${L.err?"":"hidden"}>${L.err}</p>
      <button class="btn primary big" type="submit" ${L.busy?"disabled":""}>${inTab? t("Sign in") : t("Create account")}</button>
      <p class="hint center">${inTab? t("No account yet? Choose “New account” — any username and password will do for now.") : t("Pick any username and password. Remember the password: it can’t be recovered yet.")}</p>
    </form>
    <div class="or"><span>${t("or")}</span></div>
    <button class="btn wide" data-demo-guest>${t("Look at the demo family without an account")}</button>
    <p class="small muted center" style="margin:14px 0 0">${storageNote()}</p>
  </div></div>`;
}
const BRAND_SVG = `<svg width="40" height="40" viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="17" r="16" fill="none" stroke="currentColor" stroke-opacity=".35"/><circle cx="17" cy="9" r="3" fill="var(--accent)"/><circle cx="10" cy="24" r="3" fill="none" stroke="var(--ink)" stroke-width="1.5"/><circle cx="24" cy="24" r="3" fill="none" stroke="var(--ink)" stroke-width="1.5"/><path d="M17 12v5M10 21v-4h14v4" fill="none" stroke="var(--ink)" stroke-width="1.5"/></svg>`;
function renderLogin(){
  $("#app").innerHTML = loginHTML();
  const f = $("#loginForm"); const u = $('[name="user"]', f);
  setTimeout(()=>{ (u.value ? $('[name="pw"]', f) : u).focus(); }, 20);
}
async function submitLogin(f){
  const L = LOGIN; if(L.busy) return;
  const user = $('[name="user"]', f).value.trim(), pw = $('[name="pw"]', f).value; L.user = user;
  const show = (m) => { L.err = m; const e = $("#loginErr"); if(e){ e.textContent = m; e.hidden = false; } };
  if(!user) return show(t("Enter your username."));
  if(!pw) return show(t("Enter your password."));
  L.busy = true; $('button[type="submit"]', f).disabled = true;
  try{
    if(L.tab==="in"){
      const r = await checkLogin(user, pw);
      if(r.err==="no_user") return show(t("There is no account “{u}” on this device. Check the spelling, or create a new account.",{u:user}));
      if(r.err==="bad_pw") return show(t("The password is not correct."));
      if(r.err) return show(r.err);
      L.err = ""; await startSession(r.account, t("Welcome back, {u}!",{u:r.account.username}));
    } else {
      if(pw !== $('[name="pw2"]', f).value) return show(t("The two passwords are different."));
      const r = await registerAccount(user, pw); if(r.err) return show(r.err);
      L.err = ""; await startSession(r.account, r.adopted ? t("Account created. The archive you already had in this browser is now in this account.") : t("Account created. Welcome, {u}!",{u:r.account.username}));
    }
  } finally { L.busy = false; const b = $('#loginForm button[type="submit"]'); if(b) b.disabled = false; }
}
document.addEventListener("submit", e=>{ if(e.target.id==="loginForm"){ e.preventDefault(); submitLogin(e.target); } });
document.addEventListener("click", e=>{
  const lt = e.target.closest("[data-ltab]"); if(lt){ const u = $('#loginForm [name="user"]'); if(u) LOGIN.user = u.value; LOGIN.tab = lt.dataset.ltab; LOGIN.err = ""; renderLogin(); return; }
  const sp = e.target.closest("[data-showpw]"); if(sp){ const f = sp.closest("form") || sp.closest(".modal"); $$('input[name^="pw"], input[type="password"], input[data-pw]', f).forEach(i=>{ i.type = i.type==="password" ? "text" : "password"; i.dataset.pw = "1"; }); sp.textContent = sp.textContent===t("Show") ? t("Hide") : t("Show"); return; }
  if(e.target.closest("[data-demo-guest]")){ try{ sessionStorage.setItem("fa:guest","1"); }catch(x){} R.screen = "app"; if(WS!=="demo"){ WS = "demo"; S = DEMO_S; backend = MemoryBackend("Demo"); T.focusId = DEMO_ROOT; } go("dashboard"); return; }
  if(e.target.closest("[data-logout]")){ logout(); return; }
  if(e.target.closest("[data-login]")){ R.screen = "login"; LOGIN.tab = e.target.closest("[data-login]").dataset.login || "in"; go("login"); return; }
});

/* ---------- account settings modals ---------- */
function openChangePassword(){
  const a = ACC.cur; if(!a) return;
  openModal({title:t("Change password"), size:"sm", primary:t("Save"),
    body:`${fld(t("Current password"), '<input name="old" type="password" autocomplete="current-password">')}<div style="margin-top:12px">${fld(t("New password"), '<input name="n1" type="password" autocomplete="new-password">')}</div><div style="margin-top:12px">${fld(t("Repeat new password"), '<input name="n2" type="password" autocomplete="new-password">')}</div>`,
    onPrimary: async (root)=>{ const n1 = $('[name="n1"]',root).value; if(n1 !== $('[name="n2"]',root).value) return t("The two passwords are different."); const err = await changePassword(a, $('[name="old"]',root).value, n1); if(err) return err; toast(t("Password changed.")); }});
}
function openDeleteAccount(){
  const a = ACC.cur; if(!a) return;
  const n = MINE && MINE.data ? Object.keys(MINE.data.people||{}).length : 0;
  openModal({title:t("Delete account “{u}”?",{u:a.username}), size:"sm", primary:t("Delete account"),
    body:`<p>${t("This deletes the account and its whole archive ({n} people, with every event, relationship and source). It cannot be undone.",{n})}</p><p class="small muted">${t("Download a backup first if you may want this later.")}</p>${fld(t("Password"), '<input name="pw" type="password" autocomplete="current-password">')}`,
    onPrimary: async (root)=>{ const c = await checkLogin(a.username, $('[name="pw"]',root).value); if(c.err) return t("The password is not correct."); await deleteAccount(a); }});
}
