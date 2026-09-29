import re

import streamlit as st

from agents import build_search_agent, build_reader_agent, writer_chain, critic_chain
from pipeline import get_text, get_tool_outputs, extract_urls

st.set_page_config(page_title="ResearchMind", page_icon="🔎", layout="wide")

NUM_URLS = 2  # how many URLs the reader agent scrapes
EXAMPLES = ["LLM agents 2026", "CRISPR gene editing", "Fusion energy progress"]
STEPS = [
    ("01", "Search Agent", "Gathers recent web information"),
    ("02", "Reader Agent", "Scrapes & extracts deep content"),
    ("03", "Writer Chain", "Drafts the full research report"),
    ("04", "Critic Chain", "Reviews & scores the report"),
]

# ---------------- Styling ----------------
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&family=Space+Mono:wght@700&display=swap');
:root{--bg:#0e0e10;--card:#1c1c21;--line:#2a2a31;--orange:#ff8a1f;--text:#ecebe6;--muted:#8b8b94;}
.stApp{background:radial-gradient(ellipse at 20% 0%,#1f1b17 0%,var(--bg) 55%);font-family:'DM Sans',sans-serif;}
#MainMenu,footer,header[data-testid="stHeader"]{visibility:hidden;}
.block-container{max-width:1150px;padding-top:2.5rem;}
.stMarkdown p,.stMarkdown li,.stMarkdown h1,.stMarkdown h2,.stMarkdown h3,.stMarkdown h4,.stMarkdown td,.stMarkdown th{color:var(--text);}

.eyebrow{font-family:'Space Mono',monospace;font-size:.72rem;letter-spacing:.25em;color:var(--orange);text-transform:uppercase;}
.title{font-family:'Syne',sans-serif;font-weight:800;font-size:clamp(2.6rem,7vw,5rem);line-height:1.05;margin:.3rem 0 1rem;color:var(--text);}
.title span{color:var(--orange);}
.sub{color:#c9c8c2;max-width:540px;font-size:1rem;line-height:1.5;}
.rule{border:none;border-top:1px solid var(--line);margin:1.8rem 0;}
.label{font-family:'Space Mono',monospace;font-size:.7rem;letter-spacing:.18em;color:var(--orange);text-transform:uppercase;margin-bottom:.4rem;}
.ph{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:700;color:var(--text);margin-bottom:.8rem;}

.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:.9rem 1.1rem;margin-bottom:.75rem;transition:all .25s;}
.card .row{display:flex;justify-content:space-between;align-items:center;}
.card .num{font-family:'Space Mono',monospace;color:var(--orange);font-size:.75rem;margin-right:.6rem;}
.card .name{font-weight:600;color:var(--text);}
.card .desc{color:var(--muted);font-size:.8rem;margin-top:.25rem;}
.card .badge{font-family:'Space Mono',monospace;font-size:.62rem;letter-spacing:.15em;color:var(--muted);}
.card.running{border-color:var(--orange);box-shadow:0 0 22px rgba(255,138,31,.18);}
.card.running .badge{color:var(--orange);animation:pulse 1.1s infinite;}
.card.done{border-color:#2f6b45;} .card.done .badge{color:#4ade80;}
.card.error{border-color:#7a2c2c;} .card.error .badge{color:#f87171;}
@keyframes pulse{50%{opacity:.3}}

div[data-testid="stTextInput"] input{background:#2a2a30;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:.75rem .9rem;}
div[data-testid="stTextInput"] input:focus{border-color:var(--orange);box-shadow:none;}

button[kind="primary"],button[data-testid="stBaseButton-primary"]{background:linear-gradient(90deg,#ff8a1f,#ff9d3d);color:#1a1108;border:none;border-radius:10px;font-weight:700;padding:.65rem 1rem;width:100%;}
button[kind="primary"]:hover,button[data-testid="stBaseButton-primary"]:hover{filter:brightness(1.1);color:#1a1108;}
button[kind="secondary"],button[data-testid="stBaseButton-secondary"]{background:#26262c;color:#c9c8c2;border:1px solid var(--line);border-radius:6px;font-size:.78rem;padding:.15rem .6rem;min-height:0;}
button[kind="secondary"]:hover,button[data-testid="stBaseButton-secondary"]:hover{border-color:var(--orange);color:var(--orange);}

button[data-baseweb="tab"]{color:var(--muted);}
button[data-baseweb="tab"][aria-selected="true"]{color:var(--orange);}
div[data-baseweb="tab-highlight"]{background:var(--orange);}
.score{display:inline-block;background:var(--card);border:1px solid var(--orange);border-radius:12px;padding:.6rem 1.2rem;font-family:'Syne',sans-serif;color:var(--muted);}
.score b{font-size:2rem;color:var(--orange);}
.verdict{color:#c9c8c2;margin-left:1rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ---------------- Helpers ----------------
def pipeline_html(statuses):
    labels = {"waiting": "WAITING", "running": "RUNNING", "done": "DONE", "error": "FAILED"}
    cards = ""
    for (num, name, desc), s in zip(STEPS, statuses):
        cards += (
            f'<div class="card {s}"><div class="row"><div><span class="num">{num}</span>'
            f'<span class="name">{name}</span></div><div class="badge">{labels[s]}</div></div>'
            f'<div class="desc">{desc}</div></div>'
        )
    return f'<div class="ph">Pipeline</div>{cards}'


def set_topic(t):
    st.session_state.topic = t


def run_pipeline(topic, box):
    """Same 4 steps as pipeline.py, but updates the status cards live."""
    statuses = ["waiting"] * 4
    st.session_state.statuses = statuses

    def mark(i, s):
        statuses[i] = s
        box.markdown(pipeline_html(statuses), unsafe_allow_html=True)

    state = {"topic": topic}
    step = 0
    try:
        # Step 1 - Search agent
        mark(0, "running")
        search_result = build_search_agent().invoke({
            "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
        })
        state["search_results"] = get_text(search_result["messages"][-1].content)
        state["urls"] = extract_urls(get_tool_outputs(search_result))
        mark(0, "done")

        # Step 2 - Reader agent
        step = 1
        mark(1, "running")
        if state["urls"]:
            reader_result = build_reader_agent().invoke({
                "messages": [("user",
                    f"Scrape these URLs for detailed content about '{topic}':\n"
                    + "\n".join(state["urls"][:NUM_URLS]))]
            })
            state["scraped_content"] = get_text(reader_result["messages"][-1].content)
        else:
            state["scraped_content"] = "No URLs were available to scrape."
        mark(1, "done")

        # Step 3 - Writer chain
        step = 2
        mark(2, "running")
        research = (
            f"Search Results:\n{state['search_results']}\n\n"
            f"Detailed Scraped Content:\n{state['scraped_content']}"
        )
        state["report"] = get_text(writer_chain.invoke({"topic": topic, "research": research}))
        mark(2, "done")

        # Step 4 - Critic chain
        step = 3
        mark(3, "running")
        state["feedback"] = get_text(critic_chain.invoke({"report": state["report"]}))
        mark(3, "done")
    except Exception:
        mark(step, "error")
        raise

    return state


# ---------------- Header ----------------
st.markdown(
    '<div class="eyebrow">Multi-Agent AI System</div>'
    '<div class="title">Research<span>Mind</span></div>'
    '<div class="sub">Four specialized AI agents collaborate — searching, scraping, writing, '
    "and critiquing — to deliver a polished research report on any topic.</div>"
    '<hr class="rule">',
    unsafe_allow_html=True,
)

if "statuses" not in st.session_state:
    st.session_state.statuses = ["waiting"] * 4

# ---------------- Two-column layout ----------------
left, right = st.columns([1.15, 1], gap="large")

with left:
    st.markdown('<div class="label">Research Topic</div>', unsafe_allow_html=True)
    topic = st.text_input(
        "Research topic",
        key="topic",
        placeholder="e.g. Quantum computing breakthroughs in 2026",
        label_visibility="collapsed",
    )
    run_clicked = st.button("⚡ Run Research Pipeline", type="primary")

    st.markdown('<div class="label" style="margin-top:1.2rem">Try →</div>', unsafe_allow_html=True)
    for ex in EXAMPLES:
        st.button(ex, key=f"ex_{ex}", on_click=set_topic, args=(ex,))

with right:
    pipeline_box = st.empty()
    pipeline_box.markdown(pipeline_html(st.session_state.statuses), unsafe_allow_html=True)

# ---------------- Run ----------------
if run_clicked:
    if not topic.strip():
        st.warning("Please enter a research topic first.")
    else:
        try:
            st.session_state["state"] = run_pipeline(topic.strip(), pipeline_box)
        except Exception as e:
            st.session_state.pop("state", None)
            st.error(f"Pipeline failed: {e}")
            st.caption(
                "Common causes: API rate limit, a wrong model name in agents.py, "
                "or a missing API key in .env."
            )

# ---------------- Results ----------------
state = st.session_state.get("state")
if state:
    st.markdown('<hr class="rule">', unsafe_allow_html=True)

    score = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", state["feedback"])
    verdict = re.search(r"One line Verdict:\s*(.+)", state["feedback"])
    st.markdown(
        f'<div class="score"><b>{score.group(1) if score else "N/A"}</b>/10</div>'
        f'<span class="verdict">{verdict.group(1).strip() if verdict else ""}</span>',
        unsafe_allow_html=True,
    )
    st.write("")

    tab_report, tab_feedback, tab_search, tab_scraped, tab_sources = st.tabs(
        ["Report", "Critic feedback", "Search results", "Scraped content", "Sources"]
    )

    with tab_report:
        if state["report"].strip():
            st.markdown(state["report"])
            st.download_button(
                "Download report (.md)",
                data=state["report"],
                file_name="research_report.md",
                mime="text/markdown",
            )
        else:
            st.warning(
                "The writer returned an empty report. This is usually a model or token-limit "
                "issue. Try lowering SCRAPE_CHARS in tools.py or switching the model in agents.py."
            )
    with tab_feedback:
        st.markdown(state["feedback"] or "_No feedback returned._")
    with tab_search:
        st.markdown(state["search_results"] or "_No search summary returned._")
    with tab_scraped:
        st.markdown(state["scraped_content"] or "_No scraped content returned._")
    with tab_sources:
        if state["urls"]:
            for u in state["urls"]:
                st.markdown(f"- {u}")
        else:
            st.write("No URLs were found.")
            