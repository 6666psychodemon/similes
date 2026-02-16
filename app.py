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
    .meta-text {
        color: #888; 
        font-size: 0.8em; 
        margin-bottom: 5px;
    }
    .comparison-text {
        margin-top: 5px; 
        font-size: 0.9em; 
        color: #aaa;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎤 Rap Simile Engine")
st.caption("Strict Semantic Search: No pronouns, no verbs, just pure imagery.")

# 2. LOAD DATA
@st.cache_data
def load_data():
    # UPDATE FILENAME TO V7
    filename = "smart_similes_v7.csv" 
    try:
        df = pd.read_csv(filename)
        df['signified'] = df['signified'].astype(str).str.lower().str.strip()
        df['signifier'] = df['signifier'].astype(str).str.lower().str.strip()
        return df
    except FileNotFoundError:
        return None

df = load_data()

if df is None:
    st.error("❌ Database not found! Please upload 'smart_similes_v7.csv' to GitHub.")
    st.stop()

# 3. HELPER: Clean words for comparison
def clean_word(text):
    # Removes 'a', 'the' from start of phrases for better matching
    return re.sub(r'^(a|an|the|my|his|her|your|our|their|that|this)\s+', '', text)

# 4. HIGHLIGHTING ENGINE (Fault Tolerant)
def highlight_sentence(text, terms):
    # Deduplicate terms and sort by length (longest first)
    # This ensures "Ice Cream" is highlighted before "Ice"
    terms = list(set([t for t in terms if t and len(t) > 1]))
    terms.sort(key=len, reverse=True)
    
    for term in terms:
        # Escape special regex chars (like + or ?)
        safe_term = re.escape(term)
        
        # \b ensures word boundaries. Case insensitive.
        pattern = re.compile(r'\b' + safe_term + r'\b', re.IGNORECASE)
        text = pattern.sub(f'<span class="highlight">{term}</span>', text)
        
    return text

# 5. SEARCH UI
query = st.text_input("Search for a concept (e.g., 'ice', 'wolf', 'ghost')...", "")

if query:
    q = query.lower().strip()
    
    # --- SEARCH LOGIC ---
    def is_match(row_val):
        clean_val = clean_word(row_val)
        
        # 1. Exact Match
        if q == clean_val: return True
        
        # 2. Last Word Match (The "Head" Noun)
        # e.g. Query "Leaves" matches "Maple Leaves"
        if q == clean_val.split()[-1]: return True
        
        return False

    # Apply search mask
    mask = df.apply(lambda row: is_match(row['signified']) or is_match(row['signifier']), axis=1)
    results = df[mask]
    
    st.markdown(f"### Found {len(results)} matches for *'{q}'*")
    
    # 6. DISPLAY LOOP
    for index, row in results.head(50).iterrows():
        
        # We pass 3 things to the highlighter:
        # 1. The Subject (Signified)
        # 2. The Object (Signifier)
        # 3. The User's Query (As a backup, in case the phrases don't match exactly)
        highlight_targets = [row['signified'], row['signifier'], q]
        
        clean_line = highlight_sentence(row['line'], highlight_targets)
        
        st.markdown(f"""
        <div class="simile-box">
            <div class="meta-text">
                {row['artist']} — {row['song']}
            </div>
            <div style="font-size: 1.1em;">
                "{clean_line}"
            </div>
            <div class="comparison-text">
                Comparing <b>{row['signified']}</b> → <b>{row['signifier']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif not df.empty:
    st.info("Try searching for nouns or adjectives. The engine now filters out 'like me' and 'like that'.")
