import streamlit as st
import pandas as pd
import glob
import re
import requests

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    /* 2. White background / black font highlight */
    .highlight { 
        background-color: #ffffff; 
        color: #000000; 
        padding: 0 4px; 
        border-radius: 4px; 
        font-weight: bold; 
    }
    /* 7. Tasteful shadow, no border */
    .simile-box { 
        background-color: #1e1e24; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 20px; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: none;
    }
    .lyric-text {
        font-size: 1.15em;
        line-height: 1.5;
        color: #e0e0e0;
        margin-bottom: 12px;
    }
    .meta-text { 
        color: #777; 
        font-size: 0.85em; 
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA & LIVE SANITIZE
@st.cache_data
def load_all_chunks():
    all_files = glob.glob("similes_part_*.csv")
    if not all_files: return None
    with st.spinner("📥 Waking up the engine..."):
        df_list = [pd.read_csv(f) for f in sorted(all_files)]
        full_df = pd.concat(df_list, ignore_index=True)
        
        # 8. Live Sanitizer: Drop lingering sensory verbs
        bad_phrases = 'sounds like|sound like|feels like|feel like|looks like|look like|seems like'
        full_df = full_df[~full_df['line'].str.contains(bad_phrases, case=False, regex=True, na=False)]
        
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

# 6. Intelligent Truncation
def crop_long_text(text, target_word, radius=50):
    text_str = str(text).strip()
    # If the text is short enough, leave it alone
    if len(text_str) <= radius * 2 + len(str(target_word)): return text_str
    
    match = re.search(r'\b' + re.escape(str(target_word)) + r'\b', text_str, re.IGNORECASE)
    if match:
        start = max(0, match.start() - radius)
        end = min(len(text_str), match.end() + radius)
        
        # Snap to the nearest space so we don't chop words in half
        if start > 0: start = text_str.find(' ', start) + 1
        if end < len(text_str): 
            last_space = text_str.rfind(' ', 0, end)
            if last_space > start: end = last_space
            
        prefix = "... " if start > 0 else ""
        suffix = " ..." if end < len(text_str) else ""
        return prefix + text_str[start:end].strip() + suffix
        
    return text_str[:radius*2] + "..."

def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        pattern = re.compile(r'\b' + re.escape(str(term)) + r'\b', re.IGNORECASE)
        text = pattern.sub(f'<span class="highlight">{term}</span>', text)
    return text

# 4. SEARCH UI
st.title("🎤 Rap Simile Engine")
query = st.text_input("What are you looking for?", placeholder="e.g. beast, money, ghost")
use_synonyms = st.checkbox("🧠 Brainstorm: Search for related concepts too", value=False)

if 'display_limit' not in st.session_state: st.session_state.display_limit = 100
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42

if query:
    q = query.lower().strip()
    search_terms = [q]
    
    if use_synonyms:
        with st.spinner("Expanding vocabulary..."):
            search_terms.extend(get_synonyms(q))

    with st.spinner(f"Scanning {len(df):,} similes..."):
        pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        results = df[df['signified'].str.contains(pattern, regex=True, na=False) | 
                     df['signifier'].str.contains(pattern, regex=True, na=False)]

    if not results.empty:
        col_header, col_btn = st.columns([4, 1])
        with col_header:
            # 4. Removed "for your concept"
            st.success(f"Found {len(results):,} total matches.")
        with col_btn:
            if st.button("🎲 Re-Shuffle"):
                st.session_state.random_seed += 1
                st.session_state.display_limit = 100
        
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        
        # 5. Two tiles in a row
        cols = st.columns(2)
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            # 6. Apply tighter intelligent cropping
            short_line = crop_long_text(row['line'], q)
            clean_line = highlight_sentence(short_line, search_terms)
            
            # Determine which column to place the tile in (0 or 1)
            col = cols[i % 2]
            
            with col:
                # 1. Removed quotes, 9. Removed 'Comparing', 10. Swapped metadata order
                st.markdown(f"""
                <div class="simile-box">
                    <div class="lyric-text">{clean_line}</div>
                    <div class="meta-text">{row['artist']} — {row['song']}</div>
                </div>
                """, unsafe_allow_html=True)

        if len(results) > st.session_state.display_limit:
            st.write("") # Spacer
            if st.button("⬇️ Load 100 More Results"):
                st.session_state.display_limit += 100
                st.rerun()
    else:
        st.warning(f"No results found for '{q}'.")

else:
    st.info(f"The engine is hot. {len(df):,} similes ready to be explored.")
