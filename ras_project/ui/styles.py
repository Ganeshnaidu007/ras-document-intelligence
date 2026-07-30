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

/* ─── Tokens ─────────────────────────────────────────────────── */
:root{
  --bg:       #0a0b0d;
  --bg1:      #101215;
  --bg2:      #16181c;
  --bg3:      #1d2024;
  --border:   #262a2f;
  --border2:  #33383f;
  --accent:   #2dd4bf;
  --accent2:  #14b8a6;
  --accent3:  rgba(45,212,191,.12);
  --green:    #22c55e;
  --amber:    #f59e0b;
  --red:      #ef4444;
  --blue:     #3b82f6;
  --tx:       #e7e8ec;
  --tx2:      #9298a1;
  --tx3:      #565b63;
  --r:        6px;
  --r2:       10px;
  --shadow:   0 1px 2px rgba(0,0,0,.4),0 8px 24px rgba(0,0,0,.28);
}

/* ─── App shell ──────────────────────────────────────────────── */
.stApp{background:var(--bg)!important;color:var(--tx)!important}
[data-testid="stSidebar"]{background:var(--bg1)!important;border-right:1px solid var(--border)!important}

/* ─── Typography helpers ─────────────────────────────────────── */
.label{font-size:.68rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--tx3);display:block;margin-bottom:.5rem}
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
  background:transparent!important;border:1px solid var(--border2)!important;
  color:var(--tx2)!important;border-radius:var(--r)!important;
  font-size:.8rem!important;font-weight:500!important;
  padding:.38rem .9rem!important;transition:border-color .15s,color .15s!important;
  box-shadow:none!important;
}
.stButton>button:hover{border-color:var(--accent)!important;color:var(--accent)!important;background:transparent!important}
.stButton>button:active{background:var(--accent3)!important}
div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--accent)!important;border-color:var(--accent)!important;
  color:#04120f!important;font-weight:600!important;font-size:.875rem!important;
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

/* ─── Auth page ──────────────────────────────────────────────── */
.auth-shell{max-width:420px;margin:3.5rem auto 0 auto}
.auth-brand{text-align:center;margin-bottom:2rem}
.auth-mark{display:block;font-size:1.9rem;font-weight:700;color:var(--tx);letter-spacing:-.02em}
.auth-tagline{display:block;font-size:.85rem;color:var(--tx3);margin-top:.15rem}

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

/* Chat-list / doc-list rows: flat, left-aligned, subtle hover — not
   bordered boxes. The "New chat" button (kind=primary) keeps its filled
   accent treatment; everything else in the sidebar is a quiet list row. */
[data-testid="stSidebar"] .stButton>button{
  border:none!important;background:transparent!important;color:var(--tx2)!important;
  text-align:left!important;justify-content:flex-start!important;
  font-size:.83rem!important;font-weight:400!important;padding:.45rem .6rem!important;
}
[data-testid="stSidebar"] .stButton>button:hover{background:var(--bg3)!important;color:var(--tx)!important}
[data-testid="stSidebar"] div[data-testid="stButton"]>button[kind="primary"]{
  background:var(--accent3)!important;border:1px solid transparent!important;
  color:var(--accent)!important;font-weight:600!important;text-align:center!important;
  justify-content:center!important;height:2.4rem!important;
}
[data-testid="stSidebar"] div[data-testid="stButton"]>button[kind="primary"]:hover{
  background:var(--accent)!important;color:#04120f!important;
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

</style>
"""