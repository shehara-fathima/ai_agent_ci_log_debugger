import streamlit as st
import os
from dotenv import load_dotenv
from analyzer import run_analysis

# Load from .env file
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
st.set_page_config(page_title="CI Failure Analyzer", layout="centered")
st.markdown("""
    <style>
    /* Body background */
    .stApp {
        background-color: #90ee90;
        color: #32174d;
    }

    h1, h2, h3 {
        color: #39ff14;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    .stButton>button {
        background-color: #00b4d8;
        color: white;
        font-weight: bold;
        border-radius: 10px;
        border: none;
        padding: 0.5em 1.2em;
        margin-top: 10px;
    }

    .stTextInput>div>div>input {
        background-color: #1e1e2f;
        color: #FFFFFF;
        border-radius: 8px;
    }

    .stCheckbox>div {
        background-color: transparent;
    }

    .stMarkdown, .stTextInput label, .stCheckbox label {
        color: #000000;
    }

    .stExpander>summary {
        color: #000000;
    }
    </style>
""", unsafe_allow_html=True)


st.title("🔍 GitHub CI Failure Analyzer with Gemini AI")

# Refresh button
if st.button("🔄 Refresh"):
    st.rerun()

# Instructions
with st.expander("📘 How to create a GitHub fine-grained token"):
    st.markdown("""
To generate a GitHub fine-grained token:
1. Go to [GitHub Developer Settings](https://github.com/settings/tokens).
2. Click **"Generate new token"** → **"Fine-grained token"**.
3. Select the **repository** you want access to.
4. Under **Permissions**, grant:
   - `Actions: Read-only`
   - `Metadata: Read-only`
   - `Contents: Read-only`
   - `Pull requests: Read & write` (if commenting is enabled)
5. Set an expiration if desired.
6. Click **Generate Token** and **copy** the token (you won’t see it again!).
""")

# Input fields
owner = st.text_input("GitHub Owner", placeholder="e.g. openai")
repo = st.text_input("Repository Name", placeholder="e.g. whisper")
github_token = st.text_input("GitHub Token", type="password")
should_comment = st.checkbox("💬 Post comments to PRs?", value=False)

if st.button("Analyze Failures"):
    if not all([owner, repo, github_token, gemini_api_key]):
        st.error("❌ Missing input or Gemini API Key not set in .env.")
    else:
        with st.spinner("Analyzing failed workflows..."):
            result = run_analysis(owner, repo, github_token, gemini_api_key, should_comment)
            st.success("✅ Analysis complete!")
            st.markdown(result)
