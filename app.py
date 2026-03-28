"""
Streamlit frontend for the AI E-commerce Product Scout.

Provides a chat interface that communicates with the FastAPI backend
to query the ADK Shopping Assistant.
"""

import os
import uuid

import streamlit as st
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AI Product Scout",
    page_icon="🛒",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom Styling
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global reset */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 4rem;
        max-width: 800px;
    }

    /* Header styling */
    .scout-header {
        text-align: center;
        padding: 2rem 1rem 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }

    .scout-header h1 {
        color: white !important;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }

    .scout-header p {
        color: rgba(255, 255, 255, 0.85);
        font-size: 1rem;
        margin: 0;
    }

    /* Chat messages */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        margin-bottom: 0.5rem;
        animation: fadeIn 0.3s ease-in-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Suggestion chips */
    .suggestion-chip {
        display: inline-block;
        padding: 0.5rem 1rem;
        margin: 0.25rem;
        background: linear-gradient(135deg, #f0f0ff 0%, #e8e0ff 100%);
        border: 1px solid #d4c5f9;
        border-radius: 20px;
        font-size: 0.85rem;
        color: #4a3b8f;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .suggestion-chip:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: transparent;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }

    /* Status badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .status-online {
        background: #e6f9f0;
        color: #1a7a4c;
    }

    .status-offline {
        background: #fde8e8;
        color: #9b1c1c;
    }

    /* Input styling */
    [data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
        font-family: 'Inter', sans-serif !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "backend_healthy" not in st.session_state:
    st.session_state.backend_healthy = None

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def check_backend_health() -> bool:
    """Check if the FastAPI backend is reachable."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
        return resp.status_code == 200
    except requests.ConnectionError:
        return False
    except Exception:
        return False


def send_message(message: str) -> str:
    """Send a message to the backend and return the response."""
    try:
        payload = {
            "message": message,
            "session_id": st.session_state.session_id,
            "model": st.session_state.get("selected_model", "gemini-2.5-flash"),
        }
        if st.session_state.get("custom_api_key"):
            payload["api_key"] = st.session_state.custom_api_key

        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except requests.ConnectionError:
        return "❌ **Cannot reach the backend server.** Please make sure the FastAPI server is running on port 8000."
    except requests.Timeout:
        return "⏰ **Request timed out.** The server took too long to respond. Please try again."
    except requests.HTTPError as e:
        return f"⚠️ **Server error** ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"❌ **Unexpected error:** {str(e)}"


# ---------------------------------------------------------------------------
# UI Layout
# ---------------------------------------------------------------------------

# -- Header --
st.markdown(
    """
    <div class="scout-header">
        <h1>🛒 AI Product Scout</h1>
        <p>Your intelligent shopping assistant — ask about products, prices & recommendations</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -- System Status (auto-check on load) --
if "diag_checked" not in st.session_state:
    st.session_state.diag_checked = False
    st.session_state.diag_result = None

with st.expander("🔧 System Status — click to check", expanded=not st.session_state.diag_checked):
    if st.button("Run Diagnostics", key="diag_btn"):
        try:
            resp = requests.get(f"{BACKEND_URL}/diag", timeout=15)
            if resp.status_code == 200:
                diag = resp.json()
                st.session_state.diag_result = diag
                st.session_state.diag_checked = True

                # Show results
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Backend", "✅ Online")
                    st.caption(f"DB Host: `{diag.get('db_host', '?')}`")
                with col2:
                    db_status = diag.get("db_connection", "?")
                    if db_status == "SUCCESS":
                        count = diag.get("product_count", "?")
                        st.metric("Database", f"✅ {count} products")
                    else:
                        st.metric("Database", "❌ Failed")
                        st.error(f"Connection error: {db_status}")

                if "db_traceback" in diag:
                    st.code(diag["db_traceback"], language="text")

                # Show env vars status
                st.caption(
                    f"DB User: `{diag.get('db_user')}` | "
                    f"DB Name: `{diag.get('db_name')}` | "
                    f"Password set: {diag.get('db_pass_set')} | "
                    f"API Key set: {diag.get('google_api_key_set')}"
                )
            else:
                st.error(f"Backend returned: {resp.status_code}")
        except requests.ConnectionError:
            st.error("❌ Backend not reachable (FastAPI on port 8000)")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# -- Sidebar with info --
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.caption(f"**Session ID:** `{st.session_state.session_id[:8]}...`")

    st.markdown("### 🔑 Gemini API Key")
    st.caption("Please securely enter your Gemini API Key to chat with the assistant.")
    st.text_input(
        "API Key", 
        type="password", 
        key="custom_api_key",
        placeholder="AIzaSy..."
    )

    st.markdown("### 🧠 AI Engine")
    st.selectbox(
        "Model Version",
        options=[
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash-exp",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ],
        index=0,
        key="selected_model",
        help="Higher-tier models answer slower but provide deeper reasoning."
    )

    st.divider()

    # Diagnostic check
    if st.button("🔍 Run Diagnostics", use_container_width=True):
        with st.spinner("Checking..."):
            # Check 1: FastAPI reachable?
            try:
                resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
                if resp.status_code == 200:
                    health_data = resp.json()
                    st.success(f"✅ Backend: Online")
                    db_status = health_data.get("database", "unknown")
                    if db_status == "connected":
                        st.success(f"✅ Database: Connected")
                    else:
                        st.error(f"❌ Database: {db_status}")
                        st.info("💡 Check: VPC connector, DB_HOST, DB_USER, DB_PASS env vars")
                else:
                    st.error(f"❌ Backend returned: {resp.status_code}")
                    st.code(resp.text[:500])
            except requests.ConnectionError:
                st.error("❌ Backend: Unreachable (FastAPI not running on port 8000)")
            except Exception as e:
                st.error(f"❌ Backend error: {str(e)}")

        # Show env info
        st.caption(f"Backend URL: `{BACKEND_URL}`")

    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.divider()
    st.markdown("### 💡 Example Queries")
    st.markdown(
        """
- *Show me electronics under ₹2000*
- *What's the cheapest yoga mat?*
- *Compare smartwatches and fitness bands*
- *Recommend a Diwali gift under ₹1000*
- *What categories do you have?*
        """
    )

# -- Welcome message (only if no chat history) --
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(
            """
**Welcome!** 👋 I'm your AI Shopping Assistant.

I can help you:
- 🔍 **Search** for products by name, category, or features
- 💰 **Compare** prices and find the best deals
- 🎁 **Recommend** products based on your preferences

**Try one of these to get started:**
            """
        )

    # Suggestion chips
    suggestions = [
        "Show me wireless headphones",
        "Electronics deals",
        "Recommend a gift",
    ]

    cols = st.columns(len(suggestions))
    for i, suggestion in enumerate(suggestions):
        with cols[i]:
            if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                if not st.session_state.get("custom_api_key"):
                    st.error("⚠️ Please enter your Gemini API Key in the sidebar first!")
                    st.stop()
                st.session_state.messages.append(
                    {"role": "user", "content": suggestion}
                )
                with st.spinner("Thinking..."):
                    response = send_message(suggestion)
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()

# -- Chat History --
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# -- Chat Input --
if user_input := st.chat_input("Ask about products, prices, or recommendations..."):
    if not st.session_state.get("custom_api_key"):
        st.error("⚠️ Please enter your Gemini API Key in the sidebar first!")
        st.stop()

    # Display user message immediately
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Get and display assistant response
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Searching products..."):
            response = send_message(user_input)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
