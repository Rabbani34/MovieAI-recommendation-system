/* ═══════════════════════════════════════════════
   MovieAI — Full script.js
   ═══════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {

  // ─── NAVBAR ──────────────────────────────────
  const navbar = document.getElementById("navbar");
  const scrollTopBtn = document.getElementById("scroll-top");
  window.addEventListener("scroll", () => {
    navbar?.classList.toggle("scrolled", window.scrollY > 20);
    scrollTopBtn?.classList.toggle("visible", window.scrollY > 400);
  }, { passive: true });
  scrollTopBtn?.addEventListener("click", () => window.scrollTo({ top:0, behavior:"smooth" }));
  document.querySelectorAll("form").forEach(f =>
    f.addEventListener("submit", () => document.body.classList.add("loading"))
  );

  // ─── NAVBAR/CHIP ACTIVE STATE ─────────────────
  const params      = new URLSearchParams(window.location.search);
  const activeGenre = (params.get("genre_name") || params.get("genre") || "").toLowerCase();
  document.querySelectorAll(".genre-chip").forEach(c => {
    c.classList.toggle("active", c.textContent.trim().toLowerCase() === activeGenre);
  });
  document.querySelectorAll(".nav-link").forEach(l => {
    try {
      const u = new URL(l.href);
      const g = (u.searchParams.get("genre") || "").toLowerCase();
      const isDiscover = u.pathname === "/" && !g;
      l.classList.toggle("active",
        (g && g === activeGenre) || (isDiscover && !activeGenre && !window.location.search)
      );
    } catch {}
  });

  // ═══════════════════════════════════════════════
  //   TOAST
  // ═══════════════════════════════════════════════
  function toast(html, type="info", ms=3000) {
    const c = document.getElementById("toast-container"); if(!c) return;
    const icons={success:"fa-circle-check",info:"fa-circle-info",warning:"fa-triangle-exclamation"};
    const colors={success:"#22c55e",info:"#f5c518",warning:"#f97316"};
    const t = document.createElement("div");
    t.className=`toast toast-${type}`;
    t.innerHTML=`<i class="fa-solid ${icons[type]||icons.info}" style="color:${colors[type]||colors.info}"></i> ${html}`;
    c.appendChild(t);
    setTimeout(()=>{ t.classList.add("fade-out"); t.addEventListener("animationend",()=>t.remove()); },ms);
  }

  // ═══════════════════════════════════════════════
  //   LAZY POSTER LOADER
  // ═══════════════════════════════════════════════
  async function loadOnePoster(card) {
    const img   = card.querySelector(".card-poster"); if (!img) return;
    const src   = img.getAttribute("src") || "";
    const hasGoodPoster = src && src !== "" && src !== window.location.href &&
      !src.endsWith("/") && !src.includes("placehold.co");
    if (hasGoodPoster) {
      img.style.opacity = "1"; // already loaded server-side
      return;
    }
    const title = card.dataset.title; if (!title) return;
    const wrap  = img.closest(".card-poster-wrap");
    wrap?.classList.add("skeleton");
    img.style.opacity = "0";
    try {
      const res  = await fetch(`/api/poster?title=${encodeURIComponent(title)}`);
      const data = await res.json();
      if (data.url && !data.url.includes("placehold.co")) {
        img.src             = data.url;
        card.dataset.poster = data.url;
        img.style.transition = "opacity .5s ease";
        img.style.opacity    = "1";
      } else {
        // Show title text as fallback — no ugly grey box
        wrap.style.background = "linear-gradient(135deg,#1a1a2e,#16213e)";
        img.style.display = "none";
        if (!wrap.querySelector(".card-no-poster-title")) {
          const t = document.createElement("p");
          t.className   = "card-no-poster-title";
          t.textContent = title.replace(/\s*\(\d{4}\)\s*$/, "");
          wrap.appendChild(t);
        }
      }
    } catch { img.style.opacity = "1"; }
    finally { wrap?.classList.remove("skeleton"); }
  }

  async function loadSimilarPosters(card) {
    await Promise.all([...card.querySelectorAll(".sim-item img[data-title]")].map(async img => {
      if (img.src && !img.src.includes("placehold.co") && img.src!==window.location.href) return;
      const t = img.dataset.title; if(!t) return;
      try {
        const d = await (await fetch(`/api/poster?title=${encodeURIComponent(t)}`)).json();
        if (d.url && !d.url.includes("placehold.co")) { img.src=d.url; img.style.transition="opacity .3s"; }
      } catch {}
    }));
  }

  async function lazyLoadAll() {
    const cards = [...document.querySelectorAll(".movie-card")];
    await Promise.all(cards.map(loadOnePoster));
    cards.forEach(loadSimilarPosters);
  }
  lazyLoadAll();

  document.querySelectorAll("img").forEach(img =>
    img.addEventListener("error", function(){
      if (!this.dataset.err){ this.dataset.err="1"; this.src="https://placehold.co/300x450/111111/555?text=No+Poster"; }
    })
  );

  // ═══════════════════════════════════════════════
  //   STAR RATING
  // ═══════════════════════════════════════════════
  function initStarWidgets() {
    document.querySelectorAll(".star-rating").forEach(widget => {
      if (widget.dataset.init) return;
      widget.dataset.init = "1";
      const stars = [...widget.querySelectorAll(".star")];
      const title  = widget.dataset.title;
      const poster = widget.dataset.poster || "";
      const genres = widget.dataset.genres || "";

      stars.forEach((star, i) => {
        star.addEventListener("mouseenter", () =>
          stars.forEach((s,j) => s.classList.toggle("hover", j<=i))
        );
        star.addEventListener("mouseleave", () =>
          stars.forEach(s => s.classList.remove("hover"))
        );
        star.addEventListener("click", async (e) => {
          e.stopPropagation();
          if (!IS_LOGGED_IN) {
            toast('Please <a href="/login" style="color:var(--gold)">login</a> to rate movies.', "info");
            return;
          }
          const rating = i + 1;
          const res = await fetch("/api/rate", {
            method:"POST", headers:{"Content-Type":"application/json"},
            body: JSON.stringify({ title, poster, genres, rating })
          });
          const data = await res.json();
          if (data.ok) {
            stars.forEach((s,j) => s.classList.toggle("filled", j < rating));
            toast(`Rated <strong>${title}</strong> ${rating}/5 ⭐`, "success");
          }
        });
      });
    });
  }
  initStarWidgets();

  // ═══════════════════════════════════════════════
  //   WATCHLIST (server if logged in, localStorage fallback)
  // ═══════════════════════════════════════════════
  const WL_KEY = "movieai_watchlist";
  const getLocalWL  = () => { try{return JSON.parse(localStorage.getItem(WL_KEY))||[];}catch{return[];} };
  const saveLocalWL = l  => { localStorage.setItem(WL_KEY, JSON.stringify(l)); updateWLBadge(l.length); };
  const inLocalWL   = t  => getLocalWL().some(m=>m.title===t);

  async function toggleWL(data) {
    if (IS_LOGGED_IN) {
      const res  = await fetch("/api/watchlist/toggle", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({title:data.title, poster:data.poster, genres:data.genres})
      });
      const d = await res.json();
      if (d.ok) {
        toast(d.added ? `Added <strong>${data.title}</strong> to watchlist ❤️` : `Removed <strong>${data.title}</strong>`,
              d.added ? "success" : "info");
        await loadServerWL();
      }
    } else {
      let l = getLocalWL(), i = l.findIndex(m=>m.title===data.title);
      if (i>=0) { l.splice(i,1); toast(`Removed <strong>${data.title}</strong>`,"info"); }
      else       { l.unshift(data); toast(`Added <strong>${data.title}</strong> ❤️`,"success"); }
      saveLocalWL(l); renderWL(l);
    }
    refreshWLBtns();
  }

  async function loadServerWL() {
    if (!IS_LOGGED_IN) { renderWL(getLocalWL()); return; }
    try {
      const list = await (await fetch("/api/watchlist")).json();
      updateWLBadge(list.length);
      renderWL(list.map(m=>({title:m.movie_title, poster:m.poster, genres:m.genres})));
    } catch {}
  }

  function updateWLBadge(n) {
    const b=document.getElementById("wl-badge"); if(!b) return;
    b.textContent=n; b.classList.toggle("hidden",n===0);
  }

  function renderWL(list) {
    const c=document.getElementById("wl-items"); if(!c) return;
    if (!list?.length) {
      c.innerHTML=`<p class="wl-empty">Nothing saved yet.<br>Tap <i class="fa-solid fa-bookmark"></i> on any movie.</p>`;
      return;
    }
    c.innerHTML=list.map(m=>`
      <div class="wl-item">
        <img class="wl-item-poster" src="${m.poster||'https://placehold.co/42x60/111/555?text=?'}" alt="${m.title}"/>
        <div class="wl-item-info">
          <div class="wl-item-title">${m.title}</div>
          <div class="wl-item-genres">${(m.genres||"").replace(/\|/g," · ")}</div>
        </div>
        <button class="wl-item-remove" data-title="${m.title}" data-poster="${m.poster||""}" data-genres="${m.genres||""}">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>`).join("");
    c.querySelectorAll(".wl-item-remove").forEach(b=>
      b.addEventListener("click", ()=>toggleWL({title:b.dataset.title,poster:b.dataset.poster,genres:b.dataset.genres}))
    );
  }

  function refreshWLBtns() {
    const wl = IS_LOGGED_IN ? [] : getLocalWL(); // server state managed separately
    if (!IS_LOGGED_IN) {
      document.querySelectorAll(".add-wl-btn").forEach(b=>{
        const c=b.closest("[data-title]");
        if(c) b.classList.toggle("in-wl", inLocalWL(c.dataset.title));
      });
    }
  }

  // Drawer
  const wlDrawer=document.getElementById("watchlist-drawer");
  const wlOverlay=document.getElementById("watchlist-overlay");
  const openWL=()=>{ wlDrawer?.classList.add("open"); wlOverlay?.classList.add("open"); loadServerWL(); };
  const closeWL=()=>{ wlDrawer?.classList.remove("open"); wlOverlay?.classList.remove("open"); };
  document.getElementById("wl-open-btn")?.addEventListener("click", openWL);
  document.getElementById("wl-close")?.addEventListener("click", closeWL);
  wlOverlay?.addEventListener("click", closeWL);
  document.getElementById("wl-clear")?.addEventListener("click", async () => {
    if (IS_LOGGED_IN) {
      const list = await (await fetch("/api/watchlist")).json();
      for (const m of list)
        await fetch("/api/watchlist/toggle",{method:"POST",headers:{"Content-Type":"application/json"},
          body:JSON.stringify({title:m.movie_title,poster:m.poster,genres:m.genres})});
      loadServerWL();
    } else {
      saveLocalWL([]); renderWL([]);
    }
    toast("Watchlist cleared","info");
  });

  // Card data helper
  function cardData(card) {
    return {
      title:       card.dataset.title||"",
      genres:      card.dataset.genres||"",
      rating:      card.dataset.rating||"",
      poster:      card.querySelector(".card-poster")?.src || card.dataset.poster || "",
      imdb_link:   card.dataset.imdb||"#",
      year:        card.dataset.year||"",
      overview:    card.dataset.overview||"",
      backdrop:    card.dataset.backdrop||"",
      tmdb_rating: card.dataset.tmdbRating||"",
    };
  }

  // WL button click (delegated)
  document.addEventListener("click", e=>{
    const b=e.target.closest(".add-wl-btn");
    if(b){ e.stopPropagation(); const c=b.closest("[data-title]"); if(c) toggleWL(cardData(c)||{title:c.dataset.title,poster:c.dataset.poster,genres:c.dataset.genres}); }
  });

  // Load initial badge
  loadServerWL();

  // ═══════════════════════════════════════════════
  //   MODAL
  // ═══════════════════════════════════════════════
  const modalOverlay=document.getElementById("modal-overlay");
  const modalClose=document.getElementById("modal-close");
  const modalWlBtn=document.getElementById("modal-wl-btn");

  function openModal(data) {
    document.getElementById("modal-title").textContent      = data.title;
    document.getElementById("modal-year").textContent       = data.year||"–";
    document.getElementById("modal-rating-val").textContent = data.tmdb_rating||data.rating||"–";
    document.getElementById("modal-genres").textContent     = (data.genres||"").replace(/\|/g," · ");
    document.getElementById("modal-overview").textContent   = data.overview||"No synopsis available.";
    document.getElementById("modal-imdb").href              = data.imdb_link||"#";
    document.getElementById("modal-detail").href            = `/movie?title=${encodeURIComponent(data.title)}`;
    const p=document.getElementById("modal-poster"); p.src=data.poster; p.alt=data.title;
    const bg=document.getElementById("modal-backdrop"); bg.src=data.backdrop||data.poster;
    modalWlBtn.dataset.title=data.title; modalWlBtn._data=data;
    modalOverlay?.classList.add("open"); document.body.style.overflow="hidden";
  }
  const closeModal=()=>{ modalOverlay?.classList.remove("open"); document.body.style.overflow=""; };
  modalClose?.addEventListener("click", closeModal);
  modalOverlay?.addEventListener("click", e=>{ if(e.target===modalOverlay) closeModal(); });
  document.addEventListener("keydown", e=>{ if(e.key==="Escape") closeModal(); });
  modalWlBtn?.addEventListener("click",()=>{ if(modalWlBtn._data) toggleWL(modalWlBtn._data); });

  document.addEventListener("click", e=>{
    const ob=e.target.closest(".open-modal-btn");
    if(ob){ e.stopPropagation(); const c=ob.closest(".movie-card"); if(c) openModal(cardData(c)); return; }
    const c=e.target.closest(".movie-card");
    if(c && !e.target.closest("a") && !e.target.closest("button")) openModal(cardData(c));
  });
  document.querySelectorAll(".movie-card").forEach(c=>
    c.addEventListener("keydown",e=>{ if(e.key==="Enter") openModal(cardData(c)); })
  );

  // ═══════════════════════════════════════════════
  //   AUTOCOMPLETE
  // ═══════════════════════════════════════════════
  const movieInput=document.getElementById("movie-input");
  const dropdown=document.getElementById("autocomplete-dropdown");
  const RECENT_KEY="movieai_recent";
  let acTimer=null, focusIdx=-1;
  const getRecent=()=>{ try{return JSON.parse(localStorage.getItem(RECENT_KEY))||[];}catch{return[];} };
  const saveRecent=t=>{ let r=getRecent().filter(x=>x!==t); r.unshift(t); localStorage.setItem(RECENT_KEY,JSON.stringify(r.slice(0,5))); };

  function renderAC(items,isRecent=false){
    if(!items.length){ dropdown?.classList.add("hidden"); return; }
    dropdown.innerHTML=items.map(it=>`<div class="ac-item" data-value="${it}"><i class="fa-solid ${isRecent?"fa-clock-rotate-left":"fa-film"}"></i>${it}</div>`).join("");
    dropdown?.classList.remove("hidden"); focusIdx=-1;
    dropdown.querySelectorAll(".ac-item").forEach(it=>
      it.addEventListener("mousedown",e=>{ e.preventDefault(); movieInput.value=it.dataset.value; dropdown.classList.add("hidden"); movieInput.closest("form")?.submit(); })
    );
  }
  movieInput?.addEventListener("input",e=>{
    clearTimeout(acTimer);
    if(!e.target.value.trim()){ const r=getRecent(); r.length?renderAC(r,true):dropdown?.classList.add("hidden"); return; }
    acTimer=setTimeout(async()=>{
      try{ renderAC(await (await fetch(`/api/autocomplete?q=${encodeURIComponent(e.target.value)}`)).json()); }
      catch{ dropdown?.classList.add("hidden"); }
    },200);
  });
  movieInput?.addEventListener("focus",e=>{ if(!e.target.value){const r=getRecent();if(r.length)renderAC(r,true);} });
  movieInput?.addEventListener("blur",()=>setTimeout(()=>dropdown?.classList.add("hidden"),150));
  movieInput?.addEventListener("keydown",e=>{
    const items=[...(dropdown?.querySelectorAll(".ac-item")||[])]; if(!items.length) return;
    if(e.key==="ArrowDown"){e.preventDefault();focusIdx=Math.min(focusIdx+1,items.length-1);items.forEach((it,i)=>it.classList.toggle("focused",i===focusIdx));}
    else if(e.key==="ArrowUp"){e.preventDefault();focusIdx=Math.max(focusIdx-1,-1);items.forEach((it,i)=>it.classList.toggle("focused",i===focusIdx));}
    else if(e.key==="Enter"&&focusIdx>=0){e.preventDefault();movieInput.value=items[focusIdx].dataset.value;dropdown?.classList.add("hidden");movieInput.closest("form")?.submit();}
  });
  document.getElementById("movie-form")?.addEventListener("submit",()=>{ const v=movieInput?.value?.trim(); if(v) saveRecent(v); });

  // ═══════════════════════════════════════════════
  //   LIVE GENRE FILTER
  // ═══════════════════════════════════════════════
  document.getElementById("genre-live-filter")?.addEventListener("input",function(){
    const q=this.value.toLowerCase();
    document.querySelectorAll("#genre-grid .movie-card").forEach(c=>{
      c.style.display=(!q||(c.dataset.title||"").toLowerCase().includes(q)||(c.dataset.genres||"").toLowerCase().includes(q))?"":"none";
    });
  });

  // ═══════════════════════════════════════════════
  //   THEME TOGGLE
  // ═══════════════════════════════════════════════
  const THEME_KEY="movieai_theme";
  const themeBtn=document.getElementById("theme-toggle");
  function applyTheme(t){
    if(t==="light"){
      document.documentElement.style.setProperty("--bg","#f5f0e8");
      document.documentElement.style.setProperty("--bg-card","#ffffff");
      document.documentElement.style.setProperty("--bg-elevated","#ece8e0");
      document.documentElement.style.setProperty("--text-primary","#1a1a1a");
      document.documentElement.style.setProperty("--text-secondary","#555555");
      document.documentElement.style.setProperty("--text-muted","#999999");
      if(themeBtn) themeBtn.innerHTML='<i class="fa-solid fa-sun"></i>';
    } else {
      ["--bg","--bg-card","--bg-elevated","--text-primary","--text-secondary","--text-muted"]
        .forEach(v=>document.documentElement.style.removeProperty(v));
      if(themeBtn) themeBtn.innerHTML='<i class="fa-solid fa-moon"></i>';
    }
    localStorage.setItem(THEME_KEY,t);
  }
  applyTheme(localStorage.getItem(THEME_KEY)||"dark");
  themeBtn?.addEventListener("click",()=>applyTheme(localStorage.getItem(THEME_KEY)==="dark"?"light":"dark"));

  // Re-init stars after any dynamic content
  initStarWidgets();

}); // end DOMContentLoaded
