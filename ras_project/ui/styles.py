"""ui/styles.py — RAS Design System v2."""

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

/* ─── Reset ──────────────────────────────────────────────────── */
html,body,[class*="css"]{font-family:'Inter',-apple-system,sans-serif!important}
.block-container{max-width:100%!important;padding:4.25rem 2.5rem 5rem!important}
#MainMenu,footer,.stDeployButton{visibility:hidden;display:none}
/* Deliberately not touching <header> at all anymore. We previously tried
   hiding it (which took the sidebar's collapse arrow down with it) and then
   tried re-styling it in place (which risked the fixed-position header
   overlapping and swallowing clicks on the topbar buttons right below it —
   the likely cause of "logout / Batch Q&A button not working"). The deploy
   button / hamburger menu are hidden the safe way now, via
   .streamlit/config.toml's `toolbarMode = "minimal"`, which can't cause
   layout overlap because it never touches CSS positioning at all.

   What WAS still broken: Streamlit's native header is fixed-position and
   sits on top of the page at all times, but .block-container had NO top
   padding — so our own topbar (logo, Batch Q&A / Chat Mode / Log out)
   rendered starting at y=0 and the first ~4rem of it was physically
   underneath that fixed header, clipped/covered rather than pushed down.
   Giving the block-container real top padding (matching the native
   header's height, ~3.75rem, plus a little breathing room) is the fix —
   it moves our content below the header instead of behind it, without
   touching the header itself. */
[data-testid="stHeader"]{background:var(--bg)!important;z-index:999991!important}
[data-testid="stAppViewContainer"]{background:var(--bg)!important}

/* ─── Tokens — RAS Design System v3 (premium indigo/cyan palette) ──────── */
:root{
  /* Backgrounds — layered slate, never flat black */
  --bg:       #0B1120;
  --bg1:      #0F172A;
  --bg2:      #111827;
  --bg3:      #1E293B;
  --card:     #1F2937;
  --card2:    #273549;
  --border:   #2A3446;
  --border2:  #3B4A63;

  /* Brand + semantic colors */
  --accent:   #6366F1;   /* primary — indigo */
  --accent2:  #818CF8;
  --accent3:  rgba(99,102,241,.14);
  --secondary:#06B6D4;   /* cyan */
  --purple:   #8B5CF6;
  --green:    #10B981;
  --amber:    #F59E0B;
  --red:      #EF4444;
  --teal:     #14B8A6;
  --cyan:     #06B6D4;
  --blue:     #3B82F6;
  --gray:     #64748B;

  /* Gradients — every action button gets its own */
  --grad-blue:   linear-gradient(135deg,#3B82F6,#2563EB);
  --grad-purple: linear-gradient(135deg,#8B5CF6,#6366F1);
  --grad-green:  linear-gradient(135deg,#10B981,#059669);
  --grad-orange: linear-gradient(135deg,#F59E0B,#D97706);
  --grad-red:    linear-gradient(135deg,#EF4444,#DC2626);
  --grad-teal:   linear-gradient(135deg,#14B8A6,#0D9488);
  --grad-cyan:   linear-gradient(135deg,#22D3EE,#06B6D4);
  --grad-gray:   linear-gradient(135deg,#64748B,#475569);
  --grad-hero:   linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#06B6D4 100%);

  --tx:       #F1F5F9;
  --tx2:      #94A3B8;
  --tx3:      #64748B;
  --r:        10px;
  --r2:       16px;
  --shadow:   0 1px 2px rgba(0,0,0,.35),0 12px 32px rgba(0,0,0,.35);
  --shadow-glow: 0 0 0 1px rgba(99,102,241,.15),0 8px 28px rgba(99,102,241,.18);
  --glass-bg: rgba(31,41,55,.55);
  --glass-border: rgba(148,163,184,.14);
}

/* keep old variable names some pages still reference, mapped onto the new palette */
:root{ --accent-teal: var(--accent); }

/* ─── App shell ──────────────────────────────────────────────── */
.stApp{
  background:
    radial-gradient(1200px 600px at 12% -10%, rgba(99,102,241,.10), transparent 60%),
    radial-gradient(1000px 500px at 110% 10%, rgba(6,182,212,.08), transparent 55%),
    var(--bg)!important;
  color:var(--tx)!important;
}
[data-testid="stSidebar"]{
  background:linear-gradient(180deg,var(--bg1),var(--bg2))!important;
  border-right:1px solid var(--border)!important;
}

/* ─── Typography helpers ─────────────────────────────────────── */
.label,.ras-label{font-size:.68rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);display:block;margin-bottom:.5rem}
.caption{font-size:.75rem;color:var(--tx2);line-height:1.5}
h1,h2,h3{color:var(--tx)!important}

/* ─── Topbar ─────────────────────────────────────────────────── */
.topbar{
  display:flex;align-items:center;justify-content:space-between;
  padding:1.4rem 0 1.2rem;
  border-bottom:1px solid var(--border);
  margin-bottom:2rem;
}
.topbar-left{display:flex;align-items:center;gap:1rem}
.logo{
  width:34px;height:34px;border-radius:8px;
  background:var(--accent);
  display:flex;align-items:center;justify-content:center;
  font-size:.85rem;font-weight:800;color:white;letter-spacing:-.02em;
}
.product-name{font-size:1.4rem;font-weight:700;color:var(--accent);letter-spacing:-.02em}
.product-sub{font-size:.75rem;color:var(--tx3);margin-top:.05rem}
.product-sub-title{font-size:.85rem;color:var(--tx2);margin-top:.1rem;font-weight:500;letter-spacing:.01em}
.topbar-right{display:flex;align-items:center;gap:.5rem}
.mode-pill{
  font-size:.72rem;font-weight:500;padding:.3rem .8rem;border-radius:20px;
  border:1px solid var(--border2);color:var(--tx2);background:transparent;cursor:pointer;
  transition:all .15s;
}
.mode-pill.active{background:var(--accent3);border-color:var(--accent);color:var(--accent)}

/* ─── Config table ───────────────────────────────────────────── */
.cfg-table{width:100%;border-collapse:collapse;font-size:.82rem}
.cfg-table thead tr{border-bottom:1px solid var(--border2)}
.cfg-table thead th{padding:.45rem .75rem;text-align:left;font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--tx3)}
.cfg-table tbody tr{border-bottom:1px solid var(--border)}
.cfg-table tbody tr:last-child{border-bottom:none}
.cfg-table tbody td{padding:.55rem .75rem;color:var(--tx2)}
.cfg-table tbody td:first-child{font-weight:600;color:var(--tx);white-space:nowrap}
.cfg-table tbody td:nth-child(3){font-weight:600;color:var(--tx);white-space:nowrap}
.cfg-table tbody td:last-child{text-align:center}

/* ─── Wizard — hide step numbers, show clean dots ────────────── */
.wizard{display:none}

/* ─── Step wizard ─────────────────────────────────────────────── */
.wizard{display:flex;align-items:center;gap:0;margin-bottom:2.5rem}
.wstep{
  display:flex;align-items:center;gap:.6rem;
  padding:.55rem 1rem .55rem .75rem;
  font-size:.78rem;font-weight:500;color:var(--tx3);
  position:relative;
}
.wstep.active{color:var(--tx)}
.wstep.done{color:var(--green)}
.wnum{
  width:22px;height:22px;border-radius:50%;
  border:1.5px solid var(--border2);
  display:flex;align-items:center;justify-content:center;
  font-size:.65rem;font-weight:700;color:var(--tx3);flex-shrink:0;
}
.wstep.active .wnum{border-color:var(--accent);color:var(--accent);background:var(--accent3)}
.wstep.done  .wnum{border-color:var(--green); color:var(--green); background:rgba(34,197,94,.1)}
.wdiv{width:40px;height:1px;background:var(--border2);flex-shrink:0}
.wdiv.done{background:var(--green)}

/* ─── Upload zone ─────────────────────────────────────────────── */
.upload-grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem}
.upload-card{
  background:var(--bg2);border:1.5px dashed var(--border2);
  border-radius:var(--r2);padding:1.5rem 1.25rem;
  transition:border-color .2s,background .2s;cursor:pointer;
}
.upload-card:hover,.upload-card.has-file{
  border-color:var(--accent);background:var(--accent3);border-style:solid;
}
.upload-card .uc-icon{
  width:36px;height:36px;border-radius:8px;background:var(--bg3);
  display:flex;align-items:center;justify-content:center;margin-bottom:.75rem;
}
.upload-card h4{font-size:.85rem;font-weight:600;color:var(--tx);margin:0 0 .2rem}
.upload-card p{font-size:.75rem;color:var(--tx2);margin:0;line-height:1.4}

/* ─── File chips ─────────────────────────────────────────────── */
.file-chip{
  display:inline-flex;align-items:center;gap:.5rem;
  background:var(--bg3);border:1px solid var(--border);
  border-radius:6px;padding:.3rem .7rem;margin:.2rem .2rem 0 0;
  font-size:.75rem;color:var(--tx);font-family:'SF Mono',monospace;
}
.file-chip .ftype{
  background:var(--accent);color:white;border-radius:4px;
  padding:0 .35rem;font-size:.6rem;font-weight:700;
}
.file-chip .fsz{color:var(--tx3);font-size:.68rem}

/* ─── Config preview panel ──────────────────────────────────── */
.config-panel{
  background:var(--bg1);border:1px solid var(--border);
  border-radius:var(--r2);padding:1.5rem;margin-bottom:1rem;
  box-shadow:var(--shadow);
}
.config-panel h3{
  font-size:.75rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--tx3);margin:0 0 1.25rem;
}
.config-row{
  display:flex;align-items:flex-start;justify-content:space-between;
  padding:.55rem 0;border-bottom:1px solid var(--border);
  gap:1rem;
}
.config-row:last-child{border-bottom:none;padding-bottom:0}
.config-row .cr-label{font-size:.8rem;font-weight:500;color:var(--tx2)}
.config-row .cr-label small{display:block;font-size:.68rem;color:var(--tx3);font-weight:400;margin-top:.15rem}
.config-row .cr-val{
  font-size:.78rem;font-weight:600;color:var(--tx);
  background:var(--bg3);border:1px solid var(--border);
  border-radius:5px;padding:.2rem .6rem;white-space:nowrap;
}
.cr-badge-auto{
  font-size:.6rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  background:rgba(34,197,94,.1);color:var(--green);
  border:1px solid rgba(34,197,94,.25);border-radius:3px;padding:.1rem .4rem;
  margin-left:.4rem;
}
.cr-badge-manual{
  font-size:.6rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  background:var(--accent3);color:var(--accent);
  border:1px solid rgba(99,102,241,.3);border-radius:3px;padding:.1rem .4rem;
  margin-left:.4rem;
}

/* ─── Doc stats ──────────────────────────────────────────────── */
.doc-stats{display:flex;gap:.75rem;flex-wrap:wrap;margin:.75rem 0 0}
.ds-item{
  background:var(--bg3);border:1px solid var(--border);
  border-radius:6px;padding:.4rem .8rem;
  font-size:.72rem;color:var(--tx2);
}
.ds-item strong{color:var(--tx);font-weight:600}

/* ─── Feature toggles ────────────────────────────────────────── */
.feat-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:.75rem;margin:.75rem 0 1rem}
.feat-card{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:var(--r);padding:.9rem 1rem;
  transition:border-color .15s;
}
.feat-card:hover{border-color:var(--border2)}
.feat-card.feat-on{border-color:var(--accent);background:var(--accent3)}
.feat-name{font-size:.8rem;font-weight:600;color:var(--tx);margin-bottom:.15rem}
.feat-desc{font-size:.68rem;color:var(--tx3);line-height:1.4}
.feat-cost{
  font-size:.62rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--amber);margin-top:.35rem;
}

/* ─── Confirm bar ────────────────────────────────────────────── */
.confirm-bar{
  background:var(--bg1);border:1px solid var(--border);
  border-radius:var(--r2);padding:1.25rem 1.5rem;
  display:flex;align-items:center;justify-content:space-between;
  gap:1rem;margin:1.5rem 0;box-shadow:var(--shadow);
}
.cb-left .cb-title{font-size:.9rem;font-weight:600;color:var(--tx);margin-bottom:.2rem}
.cb-left .cb-sub{font-size:.75rem;color:var(--tx2)}
.cb-pills{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.5rem}
.cb-pill{
  font-size:.65rem;font-weight:600;padding:.2rem .55rem;border-radius:4px;
  border:1px solid var(--border);color:var(--tx2);background:var(--bg3);
}

/* ─── Progress timeline ──────────────────────────────────────── */
.timeline{padding:.5rem 0}
.tl-step{
  display:flex;align-items:flex-start;gap:.85rem;
  padding:.45rem 0;
  font-size:.8rem;color:var(--tx3);
}
.tl-step.tl-done{color:var(--tx2)}
.tl-step.tl-active{color:var(--tx)}
.tl-icon{
  width:20px;height:20px;border-radius:50%;flex-shrink:0;
  border:1.5px solid var(--border2);
  display:flex;align-items:center;justify-content:center;
  font-size:.6rem;margin-top:.05rem;
}
.tl-step.tl-done   .tl-icon{border-color:var(--green); background:rgba(34,197,94,.1); color:var(--green)}
.tl-step.tl-active .tl-icon{border-color:var(--accent); background:var(--accent3); color:var(--accent)}
.tl-step .tl-label{font-weight:500;line-height:1}
.tl-step .tl-detail{font-size:.7rem;color:var(--tx3);margin-top:.15rem}
.tl-connector{width:1.5px;height:12px;background:var(--border);margin-left:9px}

/* ─── Answer cards ───────────────────────────────────────────── */
.ans-card{
  background:var(--bg1);border:1px solid var(--border);
  border-left:3px solid var(--accent);
  border-radius:var(--r2);padding:1.5rem;margin-bottom:1.25rem;
  box-shadow:var(--shadow);
}
.ans-meta{
  display:flex;align-items:center;gap:.5rem;
  margin-bottom:.75rem;flex-wrap:wrap;
}
.ans-num{
  font-size:.65rem;font-weight:700;letter-spacing:.08em;
  text-transform:uppercase;color:var(--tx3);
}
.ans-q{font-size:.8rem;font-weight:500;color:var(--tx2);flex:1;line-height:1.4}
.ans-body{font-size:.9rem;line-height:1.8;color:var(--tx)}
.ans-body p{margin:.5rem 0}

/* ─── Badges ─────────────────────────────────────────────────── */
.badge{
  display:inline-flex;align-items:center;gap:.3rem;
  padding:.18rem .55rem;border-radius:4px;
  font-size:.65rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
}
.badge-high  {background:rgba(34,197,94,.1); color:var(--green);border:1px solid rgba(34,197,94,.25)}
.badge-med   {background:rgba(245,158,11,.1);color:var(--amber); border:1px solid rgba(245,158,11,.25)}
.badge-low   {background:rgba(239,68,68,.1); color:var(--red);   border:1px solid rgba(239,68,68,.25)}
.badge-cache {background:var(--accent3);     color:var(--accent); border:1px solid rgba(99,102,241,.3)}
.badge-na    {background:var(--bg3);         color:var(--tx3);    border:1px solid var(--border)}

/* ─── Source passages ────────────────────────────────────────── */
.src-list{margin-top:.75rem}
.src-item{
  border-left:2px solid var(--border);padding:.5rem 0 .5rem .9rem;
  margin-bottom:.75rem;transition:border-color .15s;
}
.src-item:hover{border-left-color:var(--accent)}
.src-meta{font-size:.68rem;color:var(--tx3);font-family:'SF Mono',monospace;margin-bottom:.2rem}
.src-text{font-size:.8rem;color:var(--tx2);line-height:1.6;font-style:italic}

/* ─── Fact-check ─────────────────────────────────────────────── */
.fc-row{padding:.5rem 0;border-bottom:1px solid var(--border);font-size:.82rem}
.fc-row:last-child{border-bottom:none}
.fc-ok {font-size:.65rem;font-weight:700;color:var(--green);letter-spacing:.05em;text-transform:uppercase}
.fc-no {font-size:.65rem;font-weight:700;color:var(--red);  letter-spacing:.05em;text-transform:uppercase}
.fc-quote{font-size:.72rem;color:var(--tx3);font-style:italic;margin-top:.2rem}

/* ─── Stats bar ──────────────────────────────────────────────── */
.stats-bar{
  display:flex;gap:1.5rem;padding:1.25rem 0;
  border-bottom:1px solid var(--border);margin-bottom:1.5rem;
}
.sb-item .sb-val{font-size:1.6rem;font-weight:300;color:var(--tx);letter-spacing:-.02em;line-height:1}
.sb-item .sb-key{font-size:.62rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);margin-top:.2rem}

/* ─── Feedback row ───────────────────────────────────────────── */
.fb-row{display:flex;align-items:center;gap:.5rem;margin-top:.75rem;padding-top:.75rem;border-top:1px solid var(--border)}
.fb-label{font-size:.7rem;color:var(--tx3)}

/* ─── Widget overrides ───────────────────────────────────────── */
.stProgress>div>div{height:2px!important;border-radius:0!important;background:var(--accent)!important}
.stProgress>div{background:var(--border)!important;border-radius:0!important;height:2px!important}

.stTextInput>div>div>input,.stTextArea>div>div>textarea,
.stSelectbox>div>div>div,.stMultiSelect>div>div>div{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;color:var(--tx)!important;font-size:.85rem!important;
}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{
  border-color:var(--accent)!important;
  box-shadow:0 0 0 2px rgba(99,102,241,.15)!important;
}

.stButton>button{
  background:var(--accent)!important;border:1px solid var(--accent)!important;
  color:#fff!important;border-radius:var(--r)!important;
  font-size:.8rem!important;font-weight:600!important;
  padding:.42rem 1rem!important;transition:filter .12s,transform .12s,box-shadow .12s!important;
  box-shadow:0 3px 10px rgba(99,102,241,.3)!important;
}
.stButton>button:hover{filter:brightness(1.1)!important;transform:translateY(-1px)!important;color:#fff!important}
.stButton>button:active{transform:translateY(0)!important;filter:brightness(.95)!important}
.stButton>button:disabled{
  background:var(--bg3)!important;border-color:var(--border2)!important;
  color:var(--tx3)!important;box-shadow:none!important;transform:none!important;
}
div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--accent)!important;border-color:var(--accent)!important;
  color:#fff!important;font-weight:600!important;font-size:.875rem!important;
  height:2.6rem!important;
}
div[data-testid="stButton"]>button[kind="primary"]:hover{background:var(--accent2)!important;border-color:var(--accent2)!important}

/* Icon-only / compact action buttons (rename, delete, view-in-pdf) are not
   forced to fill their column — that's what made a single emoji render as
   a large square block. Content-width + tighter padding = a real compact
   icon button instead. */
div[data-testid="stButton"]>button:has(> div > [data-testid="stIconMaterial"]),
div[data-testid="stButton"]>button:has(span[data-testid]){
  padding:.32rem .7rem!important;
}

.stToggle>label{font-size:.82rem!important;font-weight:500!important;color:var(--tx)!important}

.streamlit-expanderHeader{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;font-size:.8rem!important;font-weight:500!important;color:var(--tx)!important;
}
.streamlit-expanderContent{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-top:none!important;border-radius:0 0 var(--r) var(--r)!important;
}

.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid var(--border)!important;gap:0!important}
.stTabs [data-baseweb="tab"]{background:transparent!important;color:var(--tx2)!important;font-size:.8rem!important;font-weight:500!important;border-bottom:2px solid transparent!important;padding:.5rem 1.1rem!important}
.stTabs [aria-selected="true"]{color:var(--tx)!important;border-bottom-color:var(--accent)!important}

.stAlert{border-radius:var(--r)!important;font-size:.82rem!important}
.stInfo{background:rgba(59,130,246,.07)!important;border-color:rgba(59,130,246,.25)!important;color:var(--tx)!important}
.stSuccess{background:rgba(34,197,94,.07)!important;border-color:rgba(34,197,94,.25)!important;color:var(--tx)!important}
.stWarning{background:rgba(245,158,11,.07)!important;border-color:rgba(245,158,11,.25)!important;color:var(--tx)!important}
.stError{background:rgba(239,68,68,.07)!important;border-color:rgba(239,68,68,.25)!important;color:var(--tx)!important}

hr{border-color:var(--border)!important;margin:1.5rem 0!important}

/* ─── Auth page — premium SaaS login/signup ─────────────────────────────
   The whole viewport gets a vivid gradient backdrop with soft floating
   blobs; the form itself sits in a frosted glass card on top. Built with
   plain CSS (no JS) so it survives Streamlit reruns without extra state. */
.stApp:has(.auth-page){
  background:
    radial-gradient(900px 500px at 8% 0%, rgba(139,92,246,.35), transparent 55%),
    radial-gradient(900px 550px at 95% 15%, rgba(6,182,212,.30), transparent 55%),
    radial-gradient(1100px 700px at 50% 120%, rgba(99,102,241,.30), transparent 60%),
    linear-gradient(160deg,#0B1120 0%,#0F172A 45%,#111827 100%)!important;
}
.auth-page{max-width:460px;margin:2.25rem auto 0 auto;position:relative}
.auth-orb{
  position:absolute;border-radius:50%;filter:blur(60px);opacity:.55;z-index:0;
  animation:authFloat 9s ease-in-out infinite;
}
.auth-orb.o1{width:220px;height:220px;background:var(--accent);top:-90px;left:-70px}
.auth-orb.o2{width:180px;height:180px;background:var(--secondary);bottom:-70px;right:-60px;animation-delay:2.5s}
@keyframes authFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-14px)}}

.auth-card, .st-key-auth_card{
  position:relative;z-index:1;
  background:var(--glass-bg);
  backdrop-filter:blur(18px) saturate(140%);
  -webkit-backdrop-filter:blur(18px) saturate(140%);
  border:1px solid var(--glass-border);
  border-radius:22px;
  padding:2.5rem 2.25rem 1.75rem;
  box-shadow:var(--shadow-glow),0 20px 60px rgba(0,0,0,.45);
  animation:fadeInUp .4s ease-out;
}
.auth-brand{text-align:center;margin-bottom:1.6rem}
.auth-logo-badge{
  width:56px;height:56px;border-radius:16px;margin:0 auto .9rem;
  background:var(--grad-hero);
  display:flex;align-items:center;justify-content:center;
  font-size:1.5rem;font-weight:800;color:#fff;letter-spacing:-.02em;
  box-shadow:0 8px 24px rgba(99,102,241,.45);
}
.auth-mark{
  display:block;font-size:1.65rem;font-weight:800;letter-spacing:-.02em;
  background:var(--grad-hero);-webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;
}
.auth-tagline{display:block;font-size:.85rem;color:var(--tx2);margin-top:.3rem;font-weight:400}
.auth-welcome{
  text-align:center;font-size:1.05rem;font-weight:600;color:var(--tx);
  margin:1.3rem 0 .15rem;
}
.auth-sub{text-align:center;font-size:.8rem;color:var(--tx3);margin-bottom:.5rem}

.auth-note{
  display:flex;align-items:center;gap:.5rem;margin-top:1rem;
  font-size:.72rem;color:var(--tx3);justify-content:center;
}
.auth-note svg{flex-shrink:0}

/* Auth form fields — roomier, glowing focus ring in brand indigo */
.auth-card, .st-key-auth_card .stTextInput>div>div>input{
  background:rgba(15,23,42,.55)!important;border:1px solid var(--border2)!important;
  border-radius:12px!important;height:2.85rem!important;font-size:.88rem!important;
}
.auth-card, .st-key-auth_card .stTextInput>div>div>input:focus{
  border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(99,102,241,.22)!important;
}
.auth-card, .st-key-auth_card .stSelectbox>div>div>div{border-radius:12px!important;background:rgba(15,23,42,.55)!important}

/* Animated gradient primary button for auth actions */
.auth-card, .st-key-auth_card div[data-testid="stFormSubmitButton"]>button,
.auth-card, .st-key-auth_card div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--grad-hero)!important;background-size:180% 180%!important;
  border:none!important;color:#fff!important;font-weight:700!important;
  height:2.9rem!important;border-radius:12px!important;font-size:.9rem!important;
  letter-spacing:.01em;
  box-shadow:0 10px 26px rgba(99,102,241,.35)!important;
  transition:background-position .5s ease,transform .15s ease,box-shadow .15s ease!important;
}
.auth-card, .st-key-auth_card div[data-testid="stFormSubmitButton"]>button:hover,
.auth-card, .st-key-auth_card div[data-testid="stButton"]>button[kind="primary"]:hover{
  background-position:100% 0!important;transform:translateY(-1px)!important;
  box-shadow:0 14px 32px rgba(99,102,241,.5)!important;
}
.auth-card, .st-key-auth_card div[data-testid="stFormSubmitButton"]>button:active{transform:translateY(0)!important}

.auth-card, .st-key-auth_card .stTabs [data-baseweb="tab-list"]{
  justify-content:center!important;gap:.4rem!important;border-bottom:1px solid var(--border)!important;
}
.auth-card, .st-key-auth_card .stTabs [data-baseweb="tab"]{
  border-radius:8px 8px 0 0!important;padding:.5rem 1.2rem!important;
}
.auth-card, .st-key-auth_card .stTabs [aria-selected="true"]{
  background:var(--accent3)!important;border-bottom-color:var(--accent)!important;color:var(--accent2)!important;
}

/* pw-toggle checkbox styled as a small "show password" link, not a box */
.pw-toggle-row{margin-top:-.6rem;margin-bottom:.4rem}
.pw-toggle-row .stCheckbox{transform:scale(.85);transform-origin:left center}
.pw-toggle-row label p{font-size:.72rem!important;color:var(--tx3)!important}

[data-testid="metric-container"]{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:var(--r)!important;padding:1rem!important;
}
[data-testid="metric-container"] label{font-size:.65rem!important;letter-spacing:.08em!important;text-transform:uppercase!important;color:var(--tx3)!important}

[data-testid="stFileUploader"]{background:var(--bg2)!important;border:1.5px dashed var(--border2)!important;border-radius:var(--r2)!important}
[data-testid="stFileUploader"]:hover{border-color:var(--accent)!important}

/* ─── Sidebar: flat list items, ChatGPT/Claude-style ────────────────── */
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--border)!important}
[data-testid="stSidebar"] .block-container{padding-top:1.25rem!important}

.sidebar-section-label{
  font-size:.68rem!important;font-weight:600!important;letter-spacing:.08em!important;
  text-transform:uppercase!important;color:var(--tx3)!important;
  margin:1.1rem 0 .35rem 0!important;
}
.sidebar-divider{height:1px;background:var(--border);margin:1rem 0}

/* Chat-list rows only: flat, left-aligned, subtle hover — not bordered
   boxes. Scoped tightly to the session-switch buttons (key "sess_{id}")
   so it doesn't flatten every other sidebar button (Process & add, Build
   Knowledge, rename/delete/download, etc.) — those keep their real
   button look so they're recognizable as buttons. */
[data-testid="stSidebar"] [class*="st-key-sess_"]:not([class*="st-key-sess_del"]) button{
  border:none!important;background:transparent!important;color:var(--tx2)!important;
  text-align:left!important;justify-content:flex-start!important;
  font-size:.83rem!important;font-weight:400!important;padding:.45rem .6rem!important;
  box-shadow:none!important;
}
[data-testid="stSidebar"] [class*="st-key-sess_"]:not([class*="st-key-sess_del"]) button:hover{
  background:var(--bg3)!important;color:var(--tx)!important;
}
[data-testid="stSidebar"] div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--accent)!important;border:1px solid var(--accent)!important;
  color:#fff!important;font-weight:600!important;text-align:center!important;
  justify-content:center!important;height:2.4rem!important;
}
[data-testid="stSidebar"] div[data-testid="stButton"]>button[kind="primary"]:hover{
  background:var(--accent2)!important;
}

/* ─── Chat messages: plain assistant text, right-aligned user bubble ─── */
[data-testid="stChatMessage"]{
  background:transparent!important;border:none!important;
  padding:.7rem 0!important;margin-bottom:0!important;
  max-width:52rem;margin-left:auto!important;margin-right:auto!important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){
  max-width:70%!important;margin-right:0!important;margin-left:auto!important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:var(--r2)!important;padding:.7rem 1rem!important;
}

[data-testid="stChatInput"]{
  border-radius:1.4rem!important;border:1px solid var(--border2)!important;
  background:var(--bg2)!important;max-width:52rem;margin:0 auto!important;
}
[data-testid="stChatInput"]:focus-within{border-color:var(--accent)!important}
[data-testid="stBottomBlockContainer"]{background:linear-gradient(var(--bg) 60%,var(--bg) 100%)!important}

.empty-state{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:5rem 1rem;color:var(--tx3);
}
.empty-state-title{font-size:1.05rem;font-weight:600;color:var(--tx2);margin-bottom:.3rem}
.empty-state-sub{font-size:.85rem;color:var(--tx3);max-width:26rem}

/* ─── Source citation rows (chat + batch) — bigger and roomier than the
   old inline-column layout, which is what made everything read tiny and
   cramped. Each source is now a full-width card with real padding. ──── */
.src-row{
  background:var(--bg2);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:var(--r);padding:.85rem 1rem;margin:.6rem 0 .5rem;
}
.src-row-head{font-size:.88rem;color:var(--tx);margin-bottom:.35rem}
.cite-snippet{color:var(--tx2);font-size:.84rem;line-height:1.55}

::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}

/* ─── Motion ──────────────────────────────────────────────────── */
@keyframes fadeInUp{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}
[data-testid="stChatMessage"],.ans-card{animation:fadeInUp .25s ease-out}

/* ─── st.status — theme it to match everything else instead of the
   default Streamlit look, which otherwise stands out as unstyled ───── */
[data-testid="stStatusWidget"]{
  background:var(--bg2)!important;border:1px solid var(--border)!important;
  border-radius:var(--r2)!important;
}
[data-testid="stStatusWidget"] p{font-size:.82rem!important;color:var(--tx2)!important}
[data-testid="stStatusWidget"] svg{color:var(--accent)!important}

/* ─── Icon-only ghost buttons (👍 👎 🔄 ✏️ 🗑️) — round, quiet,
   ChatGPT/Claude-style hover circle instead of a bordered rectangle.
   Scoped to buttons with an icon AND an empty text label (p:empty) —
   buttons that pair an icon with real text (like the "View" source
   button) are deliberately excluded so their label doesn't get clipped
   into a 2.1rem circle. ───────────────────────────────────────────── */
div[data-testid="stButton"]>button:has(> div > [data-testid="stIconMaterial"]):has(p:empty):not([kind="primary"]),
div[data-testid="stButton"]>button:has(span[data-testid]):has(p:empty):not([kind="primary"]){
  border:1px solid transparent!important;background:transparent!important;
  border-radius:50%!important;width:2.1rem!important;height:2.1rem!important;
  padding:0!important;display:flex!important;align-items:center!important;justify-content:center!important;
}
div[data-testid="stButton"]>button:has(> div > [data-testid="stIconMaterial"]):has(p:empty):not([kind="primary"]):hover,
div[data-testid="stButton"]>button:has(span[data-testid]):has(p:empty):not([kind="primary"]):hover{
  background:var(--bg3)!important;border-color:var(--border2)!important;
}

/* ══════════════════════════════════════════════════════════════════════
   BUTTON SYSTEM — one constrained palette, no per-action rainbow.
     Primary   → purple/indigo accent  (main CTA: New chat, nav pills)
     Secondary → dark, bordered        (neutral actions: log out, add text)
     Info      → solid blue            (Process & add, Build Knowledge
                                         Base from Selection — the two
                                         document-ingestion actions)
     Danger    → outline red → fills   (destructive: delete confirm)
   Every solid variant shares the same radius/shadow/hover-lift mixin so
   the only thing that changes button-to-button is which one is used.
   ════════════════════════════════════════════════════════════════════ */
.st-key-new_chat_btn button,
.st-key-lib_process_btn button,
.st-key-btn_mode_batch button[kind="primary"],
.st-key-btn_mode_chat button[kind="primary"],
.st-key-apply_docs_btn button,
.st-key-phase1_next button,
.st-key-add_src_txt button,
.st-key-use_q_text button,
.st-key-export_qa_btn button,
[class*="st-key-doc_del_yes_"] button,
[class*="st-key-sess_del_yes_"] button,
.st-key-nav_logout_btn button{
  border:none!important;color:#fff!important;font-weight:600!important;
  border-radius:10px!important;box-shadow:0 4px 14px rgba(0,0,0,.22)!important;
  transition:transform .12s ease,box-shadow .12s ease,filter .12s ease!important;
}
.st-key-new_chat_btn button:hover,
.st-key-lib_process_btn button:hover,
.st-key-btn_mode_batch button[kind="primary"]:hover,
.st-key-btn_mode_chat button[kind="primary"]:hover,
.st-key-apply_docs_btn button:hover,
.st-key-phase1_next button:hover,
.st-key-add_src_txt button:hover,
.st-key-use_q_text button:hover,
.st-key-export_qa_btn button:hover,
[class*="st-key-doc_del_yes_"] button:hover,
[class*="st-key-sess_del_yes_"] button:hover,
.st-key-nav_logout_btn button:hover{
  transform:translateY(-1px)!important;filter:brightness(1.08)!important;
}
.st-key-new_chat_btn button:active,
.st-key-lib_process_btn button:active{transform:translateY(0)!important}

/* Primary — purple: the main call-to-action in whatever panel it's in */
.st-key-new_chat_btn button,
.st-key-btn_mode_batch button[kind="primary"],
.st-key-btn_mode_chat button[kind="primary"],
.st-key-phase1_next button{background:var(--accent)!important}

/* Info — blue, highlighted: the two document-ingestion actions —
   "Process & add" and "Build Knowledge Base from Selection" — share the
   same strong blue so they read as the primary path through the sidebar. */
.st-key-lib_process_btn button,
.st-key-apply_docs_btn button{
  background:var(--blue)!important;
  box-shadow:0 4px 16px rgba(59,130,246,.4)!important;
}

/* Segmented nav — inactive state stays dark/bordered so the active pill
   (solid accent, from the Primary group above) is the only one that
   reads as "selected". Without this, both would render identically once
   every plain button became solid-filled by default. */
.st-key-btn_mode_batch button:not([kind="primary"]),
.st-key-btn_mode_chat button:not([kind="primary"]){
  background:var(--bg3)!important;border:1px solid var(--border2)!important;
  color:var(--tx2)!important;box-shadow:none!important;
}
.st-key-btn_mode_batch button:not([kind="primary"]):hover,
.st-key-btn_mode_chat button:not([kind="primary"]):hover{
  border-color:var(--accent)!important;color:var(--tx)!important;
}

/* Secondary — dark, bordered: neutral utility actions */
.st-key-add_src_txt button,.st-key-use_q_text button,
.st-key-export_qa_btn button,.st-key-nav_logout_btn button{
  background:var(--bg3)!important;border:1px solid var(--border2)!important;
  box-shadow:none!important;
}

/* Danger — red: only ever the actual destructive confirmation */
[class*="st-key-doc_del_yes_"] button,
[class*="st-key-sess_del_yes_"] button{background:var(--red)!important}

/* ── Outline icon-only actions (rename / delete-trigger / download /
   regenerate / view-source) — transparent by default, color only shows on
   hover. This matches "FILE ACTION BUTTONS" in the design brief exactly:
   no filled circles at rest, small rounded corners, colored hover state. */
[class*="st-key-doc_rename_btn_"] button,
[class*="st-key-doc_del_btn_"] button,
[class*="st-key-sess_del_"]:not([class*="_yes_"]):not([class*="_no_"]) button,
[class*="st-key-doc_dl_"] button,
[class*="st-key-regen_"] button,
[class*="st-key-pdfbtn_"] button{
  background:transparent!important;color:var(--tx2)!important;
  border:1px solid var(--border2)!important;border-radius:8px!important;
  box-shadow:none!important;transition:all .12s ease!important;
}
[class*="st-key-doc_rename_btn_"] button:hover{
  border-color:var(--accent)!important;color:var(--accent2)!important;background:var(--accent3)!important;
}
[class*="st-key-doc_del_btn_"] button,
[class*="st-key-sess_del_"]:not([class*="_yes_"]):not([class*="_no_"]) button{
  border-color:rgba(239,68,68,.4)!important;color:var(--red)!important;
}
[class*="st-key-doc_del_btn_"] button:hover,
[class*="st-key-sess_del_"]:not([class*="_yes_"]):not([class*="_no_"]) button:hover{
  background:var(--red)!important;color:#fff!important;border-color:var(--red)!important;
}
[class*="st-key-doc_dl_"] button:hover{
  border-color:var(--blue)!important;color:var(--blue)!important;background:rgba(59,130,246,.1)!important;
}
[class*="st-key-regen_"] button:hover,
[class*="st-key-pdfbtn_"] button:hover{
  border-color:var(--accent)!important;color:var(--accent2)!important;background:var(--accent3)!important;
}

/* ══════════════════════════════════════════════════════════════════════
   CHAT MESSAGES v2 — avatars, timestamps, streaming cursor, bubbles
   ════════════════════════════════════════════════════════════════════ */
/* No avatar glyphs — Claude/ChatGPT-style plain bubbles, no mascot/robot/
   sparkle icon. The avatar element is kept in the DOM (collapsed to zero
   size) rather than display:none so the :has() selectors below — which are
   how this stylesheet tells a user bubble from an assistant bubble at all —
   keep matching. */
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"]{
  width:0!important;height:0!important;min-width:0!important;
  padding:0!important;margin:0!important;overflow:hidden!important;
  border:none!important;box-shadow:none!important;background:transparent!important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"]{
  background:linear-gradient(135deg,var(--card),var(--card2))!important;
  border:1px solid var(--border2)!important;border-radius:16px 16px 4px 16px!important;
  box-shadow:0 4px 16px rgba(0,0,0,.25)!important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"]{
  background:var(--bg1)!important;border:1px solid var(--border)!important;
  border-left:3px solid var(--accent)!important;border-radius:4px 16px 16px 16px!important;
  padding:1rem 1.2rem!important;box-shadow:var(--shadow)!important;
}
.chat-timestamp{font-size:.65rem;color:var(--tx3);margin-top:.3rem;letter-spacing:.02em}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .chat-timestamp{text-align:right}

.stream-cursor{display:inline-block;width:2px;height:1em;background:var(--accent);
  margin-left:2px;vertical-align:text-bottom;animation:blink 1s step-start infinite}
@keyframes blink{50%{opacity:0}}

[data-testid="stChatInput"]{
  border-radius:1.6rem!important;border:1px solid var(--border2)!important;
  background:linear-gradient(135deg,var(--card),var(--bg2))!important;
  max-width:52rem;margin:0 auto!important;
  box-shadow:0 6px 20px rgba(0,0,0,.3)!important;
}
[data-testid="stChatInput"]:focus-within{
  border-color:var(--accent)!important;box-shadow:0 0 0 3px rgba(99,102,241,.18)!important;
}

/* ── Helper notes — small, subtle, dismissible-looking hint lines ──────── */
.helper-note{
  display:flex;align-items:center;gap:.45rem;
  font-size:.72rem;color:var(--tx3);
  background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.14);
  border-radius:8px;padding:.45rem .7rem;margin:.4rem 0 .7rem;
}
.helper-note b{color:var(--accent2);font-weight:600}

/* ── Empty state with CTA ───────────────────────────────────────────── */
.empty-state-cta-wrap{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  text-align:center;padding:4rem 1rem 2rem;
}
.empty-illustration{
  width:84px;height:84px;border-radius:24px;margin-bottom:1.2rem;
  background:var(--grad-hero);opacity:.16;
  display:flex;align-items:center;justify-content:center;
}
.empty-illustration svg{opacity:1}

/* ── Success toast ready-banner ─────────────────────────────────────── */
.ready-banner{
  display:flex;align-items:center;gap:.6rem;
  background:linear-gradient(135deg,rgba(16,185,129,.14),rgba(6,182,212,.10));
  border:1px solid rgba(16,185,129,.35);border-radius:12px;
  padding:.75rem 1rem;margin:.6rem 0 1rem;
  animation:fadeInUp .3s ease-out;
}
.ready-banner b{color:var(--green)}

/* ── Skeleton loading blocks ────────────────────────────────────────── */
.skeleton{
  background:linear-gradient(90deg,var(--card) 25%,var(--card2) 37%,var(--card) 63%);
  background-size:400% 100%;animation:skeletonShine 1.4s ease infinite;
  border-radius:8px;
}
@keyframes skeletonShine{0%{background-position:100% 50%}100%{background-position:0 50%}}

/* ── Document cards (uploaded documents panel) ─────────────────────── */
.doc-card{
  display:flex;align-items:center;gap:.7rem;
  background:var(--card);border:1px solid var(--border);border-radius:12px;
  padding:.7rem .9rem;margin-bottom:.5rem;transition:border-color .15s,box-shadow .15s;
}
.doc-card.selected{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent),0 4px 14px rgba(99,102,241,.18)}
.doc-card .doc-icon{
  width:34px;height:34px;border-radius:8px;flex-shrink:0;
  background:var(--grad-red);display:flex;align-items:center;justify-content:center;
  font-size:.62rem;font-weight:800;color:#fff;
}
.doc-card .doc-meta{flex:1;min-width:0}
.doc-card .doc-name{font-size:.82rem;font-weight:600;color:var(--tx);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.doc-card .doc-sub{font-size:.68rem;color:var(--tx3);margin-top:.1rem}

/* ══════════════════════════════════════════════════════════════════════
   ADMIN DASHBOARD
   ════════════════════════════════════════════════════════════════════ */
[class*="st-key-resetpw_"] button{background:var(--grad-cyan)!important;border:none!important;color:#fff!important;font-weight:600!important}
[class*="st-key-del_confirm_"] button{background:var(--grad-red)!important;border:none!important;color:#fff!important;font-weight:700!important}
[class*="st-key-del_"]:not([class*="_confirm_"]):not([class*="_cancel_"]) button{background:var(--grad-orange)!important;border:none!important;color:#fff!important;font-weight:600!important}
[class*="st-key-del_cancel_"] button{background:var(--grad-gray)!important;border:none!important;color:#fff!important}
[class*="st-key-resetpw_"] button,[class*="st-key-del_"] button{
  border-radius:8px!important;box-shadow:0 3px 10px rgba(0,0,0,.25)!important;
  transition:transform .12s ease,filter .12s ease!important;
}
[class*="st-key-resetpw_"] button:hover,[class*="st-key-del_"] button:hover{transform:translateY(-1px)!important;filter:brightness(1.08)!important}

[data-testid="metric-container"]{
  background:linear-gradient(160deg,var(--card),var(--bg2))!important;
  border:1px solid var(--border)!important;border-radius:14px!important;
  padding:1.1rem 1.2rem!important;box-shadow:var(--shadow)!important;
  border-top:2px solid var(--accent)!important;
}
[data-testid="stMetricValue"]{
  background:var(--grad-hero)!important;-webkit-background-clip:text!important;
  background-clip:text!important;-webkit-text-fill-color:transparent!important;
}

.admin-section-title{
  display:flex;align-items:center;gap:.5rem;font-size:1rem;font-weight:700;
  color:var(--tx);margin:1.5rem 0 .75rem;
}
.status-pill{
  display:inline-flex;align-items:center;gap:.3rem;font-size:.65rem;font-weight:700;
  letter-spacing:.04em;text-transform:uppercase;padding:.18rem .6rem;border-radius:20px;
}
.status-pill.ok{background:rgba(16,185,129,.12);color:var(--green);border:1px solid rgba(16,185,129,.3)}
.status-pill.warn{background:rgba(245,158,11,.12);color:var(--amber);border:1px solid rgba(245,158,11,.3)}

/* Admin user rows — bordered containers get a subtle card treatment */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--card)!important;border:1px solid var(--border)!important;
  border-radius:12px!important;
}

.stTextInput[class*="admin-search"]{max-width:340px}

/* ══════════════════════════════════════════════════════════════════════
   AG GRID (streamlit-aggrid) — Batch Q&A overview table
   AG Grid's Alpine theme is built on CSS custom properties, so it can be
   restyled to match the rest of the app without fighting internal markup.
   ════════════════════════════════════════════════════════════════════ */
.ag-theme-alpine{
  --ag-background-color: var(--bg1);
  --ag-foreground-color: var(--tx);
  --ag-header-background-color: var(--card2);
  --ag-header-foreground-color: var(--tx);
  --ag-odd-row-background-color: var(--card);
  --ag-row-hover-color: rgba(99,102,241,.10);
  --ag-border-color: var(--border);
  --ag-secondary-border-color: var(--border);
  --ag-row-border-color: var(--border);
  --ag-font-family: inherit;
  --ag-font-size: 12.5px;
  --ag-cell-horizontal-padding: 12px;
  --ag-header-height: 38px;
  --ag-row-height: 36px;
  --ag-selected-row-background-color: rgba(99,102,241,.16);
  border-radius:12px!important;overflow:hidden;
  border:1px solid var(--border)!important;
  box-shadow:var(--shadow);
}
.ag-theme-alpine .ag-header{border-bottom:1px solid var(--border)!important;font-weight:700}
.ag-theme-alpine .ag-cell{display:flex;align-items:center}

/* ══════════════════════════════════════════════════════════════════════
   RESPONSIVENESS — desktop is the default above; these narrow the
   layout down for laptop and tablet widths without changing any
   structure, only spacing/columns. ════════════════════════════════════ */
@media (max-width: 1200px){
  .block-container{padding-left:1.5rem!important;padding-right:1.5rem!important}
  .upload-grid{grid-template-columns:1fr}
}
@media (max-width: 900px){
  .block-container{padding:3.5rem 1rem 3rem!important}
  .product-name{font-size:1.15rem!important}
  .product-sub-title{font-size:.75rem!important}
  [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){max-width:88%!important}
  [data-testid="stChatMessage"]{max-width:100%!important}
  .stats-bar{flex-wrap:wrap!important}
}

/* ══════════════════════════════════════════════════════════════════════
   ACCESSIBILITY — visible keyboard focus rings and a minimum comfortable
   tap-target size on every interactive control (buttons, tabs, checkbox
   labels), on top of the color-contrast already built into the palette
   above (light text on dark backgrounds throughout, semantic colors kept
   away from pure red/green pairings for status). ════════════════════
   ════════════════════════════════════════════════════════════════════ */
.stButton>button:focus-visible,
.stTextInput input:focus-visible,
[data-testid="stChatInput"] textarea:focus-visible,
.stTabs [data-baseweb="tab"]:focus-visible{
  outline:2px solid var(--accent2)!important;outline-offset:2px!important;
}
.stButton>button{min-height:2.4rem!important}
.stCheckbox,.stRadio{min-height:1.6rem}

</style>
"""