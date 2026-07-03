import requests
import streamlit as st


# -----------------------------
# Page + Theme Configuration
# -----------------------------
st.set_page_config(
    page_title="Offline Emergency Information Repository",
    page_icon="🛟",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --bg: #000000;
        --text: #FFFFFF;
        --muted: #9CA3AF;
        --panel: #0A0A0A;
        --border: #1F2937;
        --accent: #3B82F6;
        --ok: #10B981;
        --warn: #F59E0B;
        --err: #EF4444;
    }

    .stApp {
        background-color: var(--bg);
        color: var(--text);
    }

    section[data-testid="stSidebar"] {
        background-color: var(--panel);
        border-right: 1px solid var(--border);
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    h1, h2, h3, h4, h5, h6, p, label, div, span {
        color: var(--text) !important;
    }

    .muted {
        color: var(--muted) !important;
        font-size: 0.9rem;
    }

    .card {
        background: var(--panel);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
    }

    .article-box {
        background: #050505;
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 14px;
        min-height: 280px;
        max-height: 60vh;
        overflow-y: auto;
    }

    div[data-testid="stChatMessage"] {
        background: #050505;
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 8px;
    }

    .status-pill {
        display: inline-block;
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.8rem;
        color: var(--muted);
        margin-right: 6px;
    }

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: #101010;
        color: var(--text);
    }

    .stButton > button:hover {
        border-color: var(--accent);
        color: var(--text);
    }

    .stTextInput > div > div > input {
        background-color: #080808;
        color: var(--text);
        border: 1px solid var(--border);
    }

    .stChatInputContainer {
        border-top: 1px solid var(--border);
    }

    @media (max-width: 900px) {
        .block-container {
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛟 Offline Emergency Information Repository")
st.markdown(
    '<div class="muted">Local-first intelligence over LAN-connected Kiwix + Ollama infrastructure.</div>',
    unsafe_allow_html=True,
)


# -----------------------------
# Session State Initialization
# -----------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_article_title" not in st.session_state:
    st.session_state.current_article_title = ""

if "current_article_text" not in st.session_state:
    st.session_state.current_article_text = ""

if "ai_context" not in st.session_state:
    st.session_state.ai_context = ""

if "last_search_term" not in st.session_state:
    st.session_state.last_search_term = ""


# -----------------------------
# Network Infrastructure Settings
# -----------------------------
with st.expander("Network Infrastructure Settings", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        ollama_server = st.text_input(
            "Ollama Server IP/Port",
            value=st.session_state.get("ollama_server", "http://127.0.0.1:11434"),
            help="Example: http://192.168.1.50:11434",
        )
        ollama_model = st.text_input(
            "Ollama Model Name",
            value=st.session_state.get("ollama_model", "llama3.2"),
            help="Example: llama3.2, mistral, qwen2.5",
        )
    with c2:
        kiwix_server = st.text_input(
            "Kiwix Server IP/Port",
            value=st.session_state.get("kiwix_server", "http://127.0.0.1:8000"),
            help="Example: http://192.168.1.60:8000",
        )

    st.session_state.ollama_server = ollama_server.strip().rstrip("/")
    st.session_state.ollama_model = ollama_model.strip()
    st.session_state.kiwix_server = kiwix_server.strip().rstrip("/")


# -----------------------------
# Backend Functions
# -----------------------------
def query_kiwix(search_term: str, server_url: str) -> dict:
    """
    Query local Kiwix-Serve endpoint and return article content.
    This prototype uses a common search endpoint style and gracefully handles failures.

    Returns:
        {
            "ok": bool,
            "title": str,
            "text": str,
            "raw": any,
            "error": str
        }
    """
    if not search_term.strip():
        return {"ok": False, "title": "", "text": "", "raw": None, "error": "Please enter a search term."}

    url = f"{server_url}/search"
    params = {"q": search_term, "format": "json"}

    try:
        r = requests.get(url, params=params, timeout=12)
        r.raise_for_status()

        # Attempt JSON response parsing
        data = r.json()

        # Flexible parsing for different possible Kiwix wrappers
        title = ""
        text = ""

        if isinstance(data, dict):
            if "title" in data and "content" in data:
                title = data.get("title", "")
                text = data.get("content", "")
            elif "results" in data and isinstance(data["results"], list) and data["results"]:
                first = data["results"][0]
                title = first.get("title", search_term)
                text = first.get("content") or first.get("snippet") or ""
            elif "text" in data:
                title = data.get("title", search_term)
                text = data.get("text", "")

        if not text:
            # Fallback pretty dump
            text = str(data)

        return {"ok": True, "title": title or search_term, "text": text, "raw": data, "error": ""}

    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "title": "",
            "text": "",
            "raw": None,
            "error": "Kiwix request timed out. The knowledge server may be unreachable.",
        }
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "title": "",
            "text": "",
            "raw": None,
            "error": "Could not connect to Kiwix server. Verify IP/port and LAN availability.",
        }
    except requests.exceptions.HTTPError as e:
        return {
            "ok": False,
            "title": "",
            "text": "",
            "raw": None,
            "error": f"Kiwix HTTP error: {e}",
        }
    except Exception as e:
        return {
            "ok": False,
            "title": "",
            "text": "",
            "raw": None,
            "error": f"Unexpected Kiwix error: {e}",
        }


def query_ollama(prompt: str, context: str, server_url: str, model: str) -> dict:
    """
    Query local Ollama server using /api/generate with stream=False.

    Returns:
        {"ok": bool, "response": str, "error": str}
    """
    url = f"{server_url}/api/generate"

    # Hidden RAG context is injected into the prompt body.
    if context.strip():
        full_prompt = (
            "You are an emergency information AI advisor. "
            "Use the provided context first when answering.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"USER QUESTION:\n{prompt}\n\n"
            "If context is insufficient, state what is missing."
        )
    else:
        full_prompt = prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
    }

    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        # /api/generate typically returns {"response": "..."}
        answer = data.get("response", "").strip()
        if not answer:
            answer = "No response content received from Ollama."

        return {"ok": True, "response": answer, "error": ""}

    except requests.exceptions.Timeout:
        return {"ok": False, "response": "", "error": "Ollama request timed out."}
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "response": "",
            "error": "Could not connect to Ollama server. Verify IP/port and LAN availability.",
        }
    except requests.exceptions.HTTPError as e:
        return {"ok": False, "response": "", "error": f"Ollama HTTP error: {e}"}
    except Exception as e:
        return {"ok": False, "response": "", "error": f"Unexpected Ollama error: {e}"}


# -----------------------------
# Responsive Dual-Pane Layout
# -----------------------------
left_col, right_col = st.columns([1, 1], gap="large")

# ---------- Left Pane: Kiwix Knowledge Base ----------
with left_col:
    st.subheader("📚 Knowledge Base (Kiwix)")

    search_term = st.text_input(
        "Search offline emergency repository",
        value=st.session_state.last_search_term,
        placeholder="e.g., CPR steps, water purification, wildfire evacuation",
        key="kiwix_search_input",
    )

    if st.button("Search Kiwix", key="search_kiwix_btn"):
        st.session_state.last_search_term = search_term
        result = query_kiwix(search_term, st.session_state.kiwix_server)
        if result["ok"]:
            st.session_state.current_article_title = result["title"]
            st.session_state.current_article_text = result["text"]
        else:
            st.error(result["error"])

    if st.session_state.current_article_text:
        st.markdown(
            f"""
            <div class="card">
                <span class="status-pill">Article Loaded</span>
                <strong>{st.session_state.current_article_title}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="article-box">', unsafe_allow_html=True)
        st.markdown(st.session_state.current_article_text, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Send Context to AI Advisor", key="send_context_btn"):
            st.session_state.ai_context = st.session_state.current_article_text
            st.success("Article context sent to AI Advisor.")
    else:
        st.markdown(
            '<div class="card muted">No article loaded yet. Search Kiwix to fetch emergency content.</div>',
            unsafe_allow_html=True,
        )

# ---------- Right Pane: AI Interaction ----------
with right_col:
    st.subheader("🤖 AI Interaction Engine (Ollama)")

    if st.session_state.ai_context.strip():
        st.markdown(
            '<div class="card"><span class="status-pill">RAG Context Active</span>AI responses will reference the last shared article.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="card muted">No context attached. You can still ask general questions.</div>',
            unsafe_allow_html=True,
        )

    # Render prior chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask emergency questions, triage steps, or document-specific follow-ups...")

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Consulting local AI advisor..."):
                ai = query_ollama(
                    prompt=user_prompt,
                    context=st.session_state.ai_context,
                    server_url=st.session_state.ollama_server,
                    model=st.session_state.ollama_model,
                )
                if ai["ok"]:
                    st.markdown(ai["response"])
                    st.session_state.chat_history.append({"role": "assistant", "content": ai["response"]})
                else:
                    st.error(ai["error"])
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": f"⚠️ Error: {ai['error']}"}
                    )
