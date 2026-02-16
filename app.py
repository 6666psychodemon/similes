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
        padding: 2px 4px;
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
st.caption("Search for a word to see what it is compared to (Signifier) or what is compared to it (Signified).")

# 2. LOAD DATA
@st.cache_data
def load_data():
    # ENSURE THIS MATCHES YOUR NEW FILE NAME
    filename = "smart_similes_v3.csv" 
    try:
        df = pd.read_csv(filename)
        # Clean data
        df['signified'] = df['signified'].astype(str).str.lower().str.strip()
        df['signifier'] = df['signifier'].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is None:
    st.error(f"❌ Database not found! Please upload 'smart_similes_v3.csv' to GitHub.")
    st.stop()

# 3. HELPER: HIGHLIGHT TEXT
def highlight_sentence(text, target_words):
    # Case insensitive replacement
    for word in target_words:
        if len(word) > 2: # Avoid highlighting small words like 'a'
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub(f'<span class="highlight">{word}</span>', text)
    return text

# 4. SEARCH UI
query = st.text_input("Enter a word (e.g., 'nut', 'boss', 'ice')...", "")

if query:
    query = query.lower().strip()
    
    # FILTER: Look in specific columns only
    results = df[
        (df['signified'] == query) | 
        (df['signifier'].str.contains(query, regex=False))
    ]
    
    st.markdown(f"### Found {len(results)} matches for *'{query}'*")
    
    # 5. CUSTOM DISPLAY LOOP
    # We use a loop instead of a table to render the HTML highlighting
    for index, row in results.head(50).iterrows():
        
        # Highlight the Subject and the Object in the full line
        clean_line = highlight_sentence(row['line'], [row['signified'], row['signifier']])
        
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
    st.info("Try searching for words like 'wolf', 'ghost', 'money', or 'soft'.")
