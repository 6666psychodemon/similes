import streamlit as st
import pandas as pd
import re

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    .highlight {
        background-color: #ffd700;
        color: black;
        padding: 0 4px;
        border-radius: 4px;
        font-weight: bold;
    }
    .simile-box {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎤 Rap Simile Engine")
st.caption("Strict search: Finds exact words only (e.g., 'ice' will not match 'police').")

# 2. LOAD DATA
@st.cache_data
def load_data():
    # Make sure this matches your uploaded CSV name (v3 or v4)
    filename = "smart_similes_v6_diversd.csv" 
    try:
        df = pd.read_csv(filename)
        # Ensure strings are clean
        df['signified'] = df['signified'].astype(str).str.lower().str.strip()
        df['signifier'] = df['signifier'].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is None:
    st.error("❌ Database not found! Please upload 'smart_similes_v6_diverse.csv' to GitHub.")
    st.stop()

# 3. STRICT HIGHLIGHTING FUNCTION
def highlight_sentence_strict(text, terms):
    # Sort by length to handle phrases first
    terms = sorted(terms, key=len, reverse=True)
    
    for term in terms:
        if len(term) >= 1:
            # \b = Word Boundary (The magic fix)
            # It ensures 'ice' matches 'ice' but NOT 'police'
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            text = pattern.sub(f'<span class="highlight">{term}</span>', text)
    return text

# 4. SEARCH UI
query = st.text_input("Search for a word (e.g., 'ice', 'leaves', 'nut')...", "")

if query:
    q = query.lower().strip()
    
    # 5. STRICT SEARCH LOGIC
    # We use regex=True with \b boundaries
    mask = (
        df['signified'].str.contains(r'\b' + re.escape(q) + r'\b', case=False, regex=True) | 
        df['signifier'].str.contains(r'\b' + re.escape(q) + r'\b', case=False, regex=True)
    )
    
    results = df[mask]
    
    st.markdown(f"### Found {len(results)} exact matches for *'{q}'*")
    
    # LIMIT RESULTS to 50 to prevent crashing on common words
    for index, row in results.head(50).iterrows():
        
        # Highlight strict matches only
        clean_line = highlight_sentence_strict(row['line'], [row['signified'], row['signifier']])
        
        st.markdown(f"""
        <div class="simile-box">
            <div style="color: #888; font-size: 0.8em; margin-bottom: 5px;">
                {row['artist']} — {row['song']}
            </div>
            <div style="font-size: 1.1em;">
                "{clean_line}"
            </div>
            <div style="margin-top: 5px; font-size: 0.9em; color: #aaa;">
                Comparing <b>{row['signified']}</b> → <b>{row['signifier']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif not df.empty:
    st.info("Try searching for 'ice' — it will no longer find 'police'.")
