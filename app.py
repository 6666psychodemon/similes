import streamlit as st
import pandas as pd
import glob
import re
import requests

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    .highlight { background-color: #ffd700; color: black; padding: 0 4px; border-radius: 4px; font-weight: bold; }
    .simile-box { background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #444; }
    .meta-text { color: #888; font-size: 0.85em; margin-bottom: 5px; }
    .stButton>button { width: 100%; border-radius: 20px; }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA
@st.cache_data
def load_all_chunks():
    all_files = glob.glob("similes_part_*.csv")
    if not all_files: return None
    with st.spinner("📥 Waking up the engine..."):
        df_list = [pd.read_csv(f) for f in sorted(all_files)]
        full_df = pd.concat(df_list, ignore_index=True)
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        return full_df.drop_duplicates(subset=['artist', 'line'])

df = load_all_chunks()

if df is None:
    st.error("❌ No data files found.")
    st.stop()

# 3. UTILITIES & API
@st.cache_data
def get_synonyms(word):
    try:
        response = requests.get(f"https://api.datamuse.com/words?ml={word}&max=5", timeout=2)
        return [item['word'] for item in response.json()] if response.status_code == 200 else []
    except: return []

def crop_long_text(text, target_word, radius=100):
    text_str = str(text)
    if len(text_str) < 250: return text_str
    match = re.search(r'\b' + re.escape(str(target_word)) + r'\b', text_str, re.IGNORECASE)
    if match:
        start = max(0, match.start() - radius)
        end = min(len(text_str), match.end() + radius)
        return ("..." if start > 0 else "") + text_str[start:end] + ("..." if end < len(text_str) else "")
    return text_str[:250] + "..."

def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        pattern = re.compile(r'\b' + re.escape(str(term)) + r'\b', re.IGNORECASE)
        text = pattern.sub(f'<span class="highlight">{term}</span>', text)
    return text

# 4. SEARCH UI
st.title("🎤 Rap Simile Engine")
query = st.text_input("What are you looking for?", placeholder="e.g. cat, bullet, winter")
use_synonyms = st.checkbox("🧠 Brainstorm: Search for related concepts too", value=False)

# Initialize Session State for pagination and shuffling
if 'display_limit' not in st.session_state: st.session_state.display_limit = 100
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42

if query:
    q = query.lower().strip()
    search_terms = [q]
    
    if use_synonyms:
        with st.spinner("Expanding vocabulary..."):
            search_terms.extend(get_synonyms(q))

    with st.spinner(f"Scanning {len(df):,} similes..."):
        # We use Word Boundaries (\b) for all searches now to solve the 'caterpillar' issue
        pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        results = df[df['signified'].str.contains(pattern, regex=True, na=False) | 
                     df['signifier'].str.contains(pattern, regex=True, na=False)]

    if not results.empty:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.success(f"Found {len(results):,} total matches for your concept.")
        with col2:
            if st.button("🎲 Re-Shuffle"):
                st.session_state.random_seed += 1
                st.session_state.display_limit = 100
        
        # Shuffle results based on seed
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        
        # Display Loop
        for _, row in display_df.head(st.session_state.display_limit).iterrows():
            short_line = crop_long_text(row['line'], q)
            clean_line = highlight_sentence(short_line, search_terms)
            st.markdown(f"""
            <div class="simile-box">
                <div class="meta-text">{row['artist']} — {row['song']}</div>
                <div style="font-size: 1.1em;">"{clean_line}"</div>
                <div style="margin-top: 8px; font-size: 0.9em; color: #aaa;">
                    Comparing <b>{row['signified']}</b> → <b>{row['signifier']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # "Load More" as an alternative to Auto-scroll (Streamlit limitation)
        if len(results) > st.session_state.display_limit:
            if st.button("⬇️ Load 100 More Results"):
                st.session_state.display_limit += 100
                st.rerun()
    else:
        st.warning(f"No results found for '{q}'.")

else:
    st.info(f"The engine is hot. {len(df):,} similes ready to be explored.")
