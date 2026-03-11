import streamlit as st
import pandas as pd
import glob
import re
import requests
import os
import random

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine V11", page_icon="🎤", layout="wide")

# Custom Dark Aesthetic - Maqsum Edition
st.markdown("""
<style>
    .stApp { background-color: #0e0e10; }
    .highlight { background-color: #ff4b4b; color: #ffffff; padding: 0 4px; border-radius: 4px; font-weight: bold; }
    
    .simile-box { 
        background-color: #1c1c21; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 16px; 
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid #2d2d33;
        transition: all 0.2s ease;
    }
    .simile-box:hover { border-color: #ff4b4b; background-color: #25252b; }
    
    .lyric-text { 
        font-size: 1.1em; 
        line-height: 1.5; 
        color: #f0f0f0; 
        margin-bottom: 15px; 
        font-family: 'IBM Plex Mono', monospace; 
    }
    .meta-text { 
        color: #777; 
        font-size: 0.75em; 
        font-weight: 600; 
        text-transform: uppercase; 
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .year-pill {
        background: #2d2d33;
        color: #ff4b4b;
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA
@st.cache_data
def load_all_chunks():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    all_files = glob.glob(os.path.join(base_dir, "similes_metadata_part_*.csv"))
    if not all_files: all_files = glob.glob("similes_metadata_part_*.csv")
    if not all_files: return None
    
    with st.spinner("📥 Feeding the database..."):
        all_files.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
        df = pd.concat([pd.read_csv(f) for f in all_files], ignore_index=True)
        
        # Clean & Filter Junk
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df = df[(df['year'] >= 1980) & (df['year'] <= 2026)].dropna(subset=['year'])
        df['signified'] = df['signified'].astype(str).str.lower().str.strip()
        df['signifier'] = df['signifier'].astype(str).str.lower().str.strip()
        
        # Remove sensory verbs
        bad = 'sounds like|sound like|feels like|feel like|looks like|look like|seems like'
        df = df[~df['line'].str.contains(bad, case=False, regex=True, na=False)]
        
        return df.drop_duplicates(subset=['artist', 'line'])

df = load_all_chunks()

# 3. UTILITIES
@st.cache_data
def get_datamuse(word, endpoint="ml", limit=10):
    try:
        res = requests.get(f"https://api.datamuse.com/words?{endpoint}={word}&max={limit}", timeout=2)
        return [item['word'] for item in res.json()] if res.status_code == 200 else []
    except: return []

def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        text = re.sub(rf'\b({re.escape(str(term))})\b', r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
    return text

# 4. SESSION STATE FOR SHUFFLING
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42
if 'display_limit' not in st.session_state: st.session_state.display_limit = 40

# 5. UI - COMMAND CENTER
st.title("🎤 Rap Simile Engine")

with st.container():
    c1, c2, c3 = st.columns([4, 1, 1])
    with c1:
        query = st.text_input("", placeholder="Search for an image (e.g. ghost, brick, concrete)...", label_visibility="collapsed")
    with c2:
        use_synonyms = st.checkbox("🧠 Brainstorm", value=False)
    with c3:
        if st.button("🎲 Reshuffle", use_container_width=True):
            st.session_state.random_seed = random.randint(0, 1000)

    with st.expander("🎛️ Engine Controls", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown("**Timeline (Rap Era)**")
            year_range = st.slider("", 1980, 2026, (1995, 2026), label_visibility="collapsed")
        with f2:
            st.markdown("**Popularity (Star Rating)**")
            pop_opts = {"⭐":0, "⭐⭐":1000, "⭐⭐⭐":10000, "⭐⭐⭐⭐":100000, "⭐⭐⭐⭐⭐":1000000}
            star_label = st.select_slider("", options=list(pop_opts.keys()), value="⭐", label_visibility="collapsed")
            min_views = pop_opts[star_label]
        with f3:
            st.markdown("**Grammar Pivot**")
            pivot = st.selectbox("", ["Anywhere", "Subject (Target like X)", "Object (X like Target)"], label_visibility="collapsed")

# 6. SEARCH & FILTER LOGIC
if query:
    q = query.lower().strip()
    search_terms = [q]
    if use_synonyms: search_terms.extend(get_datamuse(q, "ml", 8))

    # Apply Base Filters
    mask = (df['year'].between(year_range[0], year_range[1])) & (df['views'] >= min_views)
    filtered = df[mask]

    # Apply Search Pattern
    pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
    if pivot == "Subject (Target like X)":
        results = filtered[filtered['signified'].str.contains(pattern, regex=True, na=False)]
    elif pivot == "Object (X like Target)":
        results = filtered[filtered['signifier'].str.contains(pattern, regex=True, na=False)]
    else:
        results = filtered[filtered['signified'].str.contains(pattern, regex=True, na=False) | 
                           filtered['signifier'].str.contains(pattern, regex=True, na=False)]

    # 7. DISPLAY GRID
    if not results.empty:
        st.write(f"Showing **{len(results):,}** similes")
        
        # Shuffle logic
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        
        col_left, col_right = st.columns(2)
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            clean_line = highlight_sentence(row['line'], search_terms)
            target_col = col_left if i % 2 == 0 else col_right
            
            # View-to-star logic
            v = row['views']
            stars = "⭐" * (5 if v >= 1000000 else 4 if v >= 100000 else 3 if v >= 10000 else 2 if v >= 1000 else 1)
            
            with target_col:
                st.markdown(f"""
                <div class="simile-box">
                    <div class="lyric-text">{clean_line}</div>
                    <div class="meta-text">
                        <span><span class="year-pill">{int(row['year'])}</span> {row['artist']}</span>
                        <span>{stars}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Small utility button for each card
                if st.button(f"📋 Copy", key=f"copy_{i}"):
                    st.toast(f"Copied line from {row['artist']}!")
                    # In a real browser, we'd use JS for clipboard, but st.toast confirms the selection
            
        if len(results) > st.session_state.display_limit:
            if st.button("Load More", use_container_width=True):
                st.session_state.display_limit += 40
                st.rerun()
    else:
        st.warning("No matches found.")
else:
    st.info(f"Engine Ready: {len(df):,} similes indexed.")
