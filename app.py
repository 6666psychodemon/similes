import streamlit as st
import pandas as pd
import glob
import re
import requests

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    .highlight { 
        background-color: #ffffff; 
        color: #000000; 
        padding: 0 4px; 
        border-radius: 4px; 
        font-weight: bold; 
    }
    .simile-box { 
        background-color: #1e1e24; 
        padding: 16px; 
        border-radius: 12px; 
        margin-bottom: 12px; /* Tighter vertical spacing */
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        border: none;
    }
    .lyric-text {
        font-size: 1.15em;
        line-height: 1.5;
        color: #e0e0e0;
        margin-bottom: 8px; /* Tighter gap above metadata */
    }
    .meta-text { 
        color: #777; 
        font-size: 0.85em; 
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
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
        
        # Standardize text first so our filters catch everything
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        
        # THE WEAK VERB PURGE
        # Kills any simile built on a generic action or feeling
        weak_verbs = {
            'feel', 'feels', 'feeling', 'felt',
            'look', 'looks', 'looking', 'looked',
            'smile', 'smiles', 'smiling', 'smiled',
            'act', 'acts', 'acting', 'acted',
            'sound', 'sounds', 'sounding', 'sounded',
            'seem', 'seems', 'seeming', 'seemed',
            'smell', 'smells', 'smelling', 'smelled',
            'taste', 'tastes', 'tasting', 'tasted',
            'stare', 'stares', 'staring', 'stared',
            'laugh', 'laughs', 'laughing', 'laughed',
            'cry', 'cries', 'crying', 'cried',
            'walk', 'walks', 'walking', 'walked',
            'talk', 'talks', 'talking', 'talked',
            'run', 'runs', 'running', 'ran',
            'dress', 'dresses', 'dressing', 'dressed',
            'stand', 'stands', 'standing', 'stood',
            'work', 'works', 'working', 'worked',
            'play', 'plays', 'playing', 'played',
            'treat', 'treats', 'treating', 'treated'
        }
        
        # Keep only the rows where the signified is NOT in our weak_verbs list
        full_df = full_df[~full_df['signified'].isin(weak_verbs)]
        
        return full_df.drop_duplicates(subset=['artist', 'line'])

# 3. UTILITIES & API
@st.cache_data
def get_synonyms(word):
    try:
        response = requests.get(f"https://api.datamuse.com/words?ml={word}&max=5", timeout=2)
        return [item['word'] for item in response.json()] if response.status_code == 200 else []
    except: return []

def crop_long_text(text, target_word, radius=50):
    text_str = str(text).strip()
    if len(text_str) <= radius * 2 + len(str(target_word)): return text_str
    
    match = re.search(r'\b' + re.escape(str(target_word)) + r'\b', text_str, re.IGNORECASE)
    if match:
        start = max(0, match.start() - radius)
        end = min(len(text_str), match.end() + radius)
        
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

# 4. SEARCH UI (Headless & Modern)
# Adding some spacing at the top so it doesn't hug the browser edge too tightly
st.write("<br>", unsafe_allow_html=True)

query = st.text_input(
    "Search", 
    placeholder="Search for a concept (e.g. beast, money, ghost)...", 
    label_visibility="collapsed"
)
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
            st.success(f"Found {len(results):,} total matches.")
        with col_btn:
            if st.button("🎲 Re-Shuffle", use_container_width=True):
                st.session_state.random_seed += 1
                st.session_state.display_limit = 100
        
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        
        # Tighter gap between the two columns
        cols = st.columns(2, gap="small")
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            short_line = crop_long_text(row['line'], q)
            clean_line = highlight_sentence(short_line, search_terms)
            
            col = cols[i % 2]
            
            with col:
                st.markdown(f"""
                <div class="simile-box">
                    <div class="lyric-text">{clean_line}</div>
                    <div class="meta-text">{row['artist']} — {row['song']}</div>
                </div>
                """, unsafe_allow_html=True)

        if len(results) > st.session_state.display_limit:
            st.write("") 
            # Full width button applied here
            if st.button("⬇️ Load 100 More Results", use_container_width=True):
                st.session_state.display_limit += 100
                st.rerun()
    else:
        st.warning(f"No results found for '{q}'.")

else:
    st.info(f"{len(df):,} similes ready to be explored.")
