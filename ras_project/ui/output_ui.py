"""ui/output_ui.py — Answer output panel."""
import streamlit as st


def _badge(label, score):
    cls = {"High":"badge-high","Medium":"badge-med","Low":"badge-low"}.get(label,"badge-na")
    s   = f"{score}/10" if score >= 0 else "—"
    return f'<span class="badge {cls}">{label} &nbsp;{s}</span>'


def _src_html(chunks):
    """Fallback plain-text renderer, kept for non-interactive contexts
    (e.g. exported output). The live UI uses _render_sources() below,
    which adds a 'View' button and confidence badge per source."""
    html = '<div class="src-list">'
    for i, c in enumerate(chunks[:5], 1):
        src  = c.get("source","?")
        pg   = c.get("page_number","?")
        sc   = c.get("hybrid_score", c.get("cosine_score", c.get("rerank_score",0.0)))
        text = c.get("text","")[:260].strip()
        dots = "..." if len(c.get("text","")) > 260 else ""
        html += (f'<div class="src-item">'
                 f'<div class="src-meta">[{i}] &nbsp;{src} &nbsp;·&nbsp; p.{pg} &nbsp;·&nbsp; {sc:.3f}</div>'
                 f'<div class="src-text">{text}{dots}</div>'
                 f'</div>')
    return html + '</div>'


def _render_sources(chunks, key_prefix, user_id):
    """Interactive source passages: filename, page, a confidence badge
    showing how strongly that passage backs the answer, and a 'View'
    button that opens the original PDF page highlighted — the same
    citation widget chat mode uses, so batch Q&A gets the same
    'view the source' option chat already had. Sorted strongest match
    first so the best evidence for the answer is always at the top."""
    from ui.chat_ui import _render_source_citation
    from utils.helpers import sort_by_confidence
    for i, c in enumerate(sort_by_confidence(chunks)[:5], 1):
        _render_source_citation(c, key_prefix=f"{key_prefix}_{i}", user_id=user_id)


def render_output_section():
    data     = st.session_state.output_data
    answered = data.get("answered_questions", [])

    # ── Stats bar ────────────────────────────────────────────────────────────
    scores  = [a["confidence"]["score"] for a in answered
               if a.get("confidence") and a["confidence"]["score"] >= 0]
    avg     = f"{sum(scores)/len(scores):.1f}" if scores else "—"
    cached  = sum(1 for a in answered if a.get("_cache_hit"))
    high    = sum(1 for a in answered if a.get("confidence",{}).get("label") == "High")

    st.markdown(
        f'<div class="stats-bar">'
        f'<div class="sb-item"><div class="sb-val">{len(answered)}</div><div class="sb-key">Answers</div></div>'
        f'<div class="sb-item"><div class="sb-val">{avg}</div><div class="sb-key">Avg confidence</div></div>'
        f'<div class="sb-item"><div class="sb-val">{high}</div><div class="sb-key">High confidence</div></div>'
        f'<div class="sb-item"><div class="sb-val">{cached}</div><div class="sb-key">From cache</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Document summaries ───────────────────────────────────────────────────
    summaries = st.session_state.get("doc_summaries", [])
    if summaries:
        with st.expander(f"Document summaries ({len(summaries)})", expanded=False):
            for s in summaries:
                src = s.get("source","?")
                st.markdown(
                    f'<div style="background:var(--bg2);border:1px solid var(--border);'
                    f'border-left:3px solid var(--accent);border-radius:8px;padding:1rem 1.25rem;margin-bottom:.75rem">'
                    f'<div style="font-size:.78rem;font-weight:600;color:var(--tx);font-family:monospace;margin-bottom:.4rem">{src}</div>'
                    f'<div style="font-size:.82rem;color:var(--tx2);line-height:1.65">{s.get("summary","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True)

    st.markdown("---")

    provider   = st.session_state.get("llm_provider","groq")
    fc_enabled = st.session_state.get("fact_check_enabled", False)

    for idx, item in enumerate(answered):
        q      = item.get("question","")
        prefix = item.get("prefix","")
        answer = item.get("answer","")
        conf   = item.get("confidence")
        chunks = item.get("chunks",[])
        num    = item.get("number","")

        # ── Answer card ──────────────────────────────────────────────────────
        meta_parts = []
        if num: meta_parts.append(f'<span class="ans-num">Q{num}</span>')
        if item.get("_cache_hit"):
            meta_parts.append('<span class="badge badge-cache">Cached</span>')
        if conf:
            meta_parts.append(_badge(conf.get("label","N/A"), conf.get("score",-1)))
        if item.get("_provider"):
            meta_parts.append(f'<span class="badge badge-na">{item["_provider"]}</span>')

        q_display = f"{prefix} {q}".strip()
        reason    = conf.get("reason","") if conf else ""

        st.markdown(
            f'<div class="ans-card">'
            f'  <div class="ans-meta">{"".join(meta_parts)}</div>'
            f'  <div class="ans-q">{q_display}</div>'
            + (f'  <div style="font-size:.7rem;color:var(--tx3);margin:.3rem 0 .75rem;font-style:italic">{reason}</div>' if reason else '')
            + (f'  <div style="font-size:.7rem;color:var(--tx3);margin-bottom:.5rem">Matched: {item.get("_cache_original","")[:70]}</div>' if item.get("_cache_hit") else '')
            + f'</div>',
            unsafe_allow_html=True,
        )

        # Answer text
        st.markdown(
            f'<div class="ans-body" style="margin:.25rem 0 1rem;padding:0 .25rem">{answer}</div>',
            unsafe_allow_html=True)

        # ── Source passages — full width, not squeezed into a narrow
        # column. That's what was making the filename, match %, and quote
        # text all wrap down to a barely-readable sliver. ─────────────────
        if chunks:
            with st.expander(f"Source passages ({min(5,len(chunks))})", expanded=False):
                _render_sources(chunks, key_prefix=f"src_{idx}", user_id=st.session_state.get("user_id"))

        # ── Supporting panels ────────────────────────────────────────────────
        cols = st.columns([3, 1])

        with cols[0]:
            if fc_enabled and chunks and answer:
                claims = item.get("fact_check_claims")
                if claims is None:
                    if st.button("Verify claims", key=f"fc_{idx}"):
                        with st.spinner("Checking..."):
                            from llm.fact_checker import fact_check_answer
                            claims = fact_check_answer(answer, chunks, provider)
                            answered[idx]["fact_check_claims"] = claims
                            st.rerun()
                if claims:
                    sup = sum(1 for c in claims if c.get("supported"))
                    pct = int(sup/len(claims)*100) if claims else 0
                    with st.expander(f"Verification — {sup}/{len(claims)} supported ({pct}%)", expanded=False):
                        for c in claims:
                            ok = c.get("supported")
                            st.markdown(
                                f'<div class="fc-row">'
                                f'<span class="{"fc-ok" if ok else "fc-no"}">'
                                f'{"supported" if ok else "not found"}</span> '
                                f'<span style="color:var(--tx);font-size:.82rem">{c.get("claim","")}</span>'
                                + (f'<div class="fc-quote">{c.get("source","")} — {c.get("quote","")}</div>' if ok and c.get("quote") else "")
                                + f'</div>', unsafe_allow_html=True)

        with cols[1]:
            if chunks:
                tried_key = f"_regen_tried_{idx}"
                tried = st.session_state.get(tried_key, [item.get("_provider", provider)])
                if st.button("", key=f"regen_{idx}", icon="🔄", use_container_width=True,
                             help="Regenerate this answer with a different model"):
                    from llm.regenerate import regenerate
                    from utils.feedback_store import store_feedback
                    with st.spinner("Trying a different model..."):
                        # Clicking regenerate is itself the "this wasn't good
                        # enough" signal — no separate Poor button needed —
                        # so the old answer + provider is logged automatically,
                        # same as before, just without an extra click.
                        store_feedback(q, answer, chunks, rating=-1,
                                       provider=item.get("_provider", provider))
                        res = regenerate(q, chunks, tried, item.get("_provider", provider),
                                         response_style=st.session_state.get("response_style", "concise"))
                    answered[idx]["answer"]     = res["answer"]
                    answered[idx]["confidence"] = res["confidence"]
                    answered[idx]["_provider"]  = res["provider"]
                    tried = tried + [res["provider"]]
                    st.session_state[tried_key] = tried
                    st.rerun()
                if len(tried) > 1:
                    st.caption(f"Tried: {', '.join(tried)}")

        st.markdown('<hr style="margin:.75rem 0">', unsafe_allow_html=True)

    # ── Session history ──────────────────────────────────────────────────────
    if st.session_state.get("job_history"):
        with st.expander("Session history", expanded=False):
            for i, j in enumerate(st.session_state.job_history, 1):
                st.markdown(
                    f'<span style="font-size:.78rem;color:var(--tx3)">'
                    f'Run {i} &nbsp;·&nbsp; {j["num_sources"]} doc(s) &nbsp;·&nbsp; '
                    f'{j["num_questions"]} Q &nbsp;·&nbsp; {j["format"]} &nbsp;·&nbsp; {j.get("mode","")}'
                    f'</span><br>', unsafe_allow_html=True)