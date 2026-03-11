import streamlit as st
import pandas as pd
import glob
import re
import requests
import os

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine V11", page_icon="🎤", layout="wide")

# Custom Dark Aesthetic - Maqsum Edition
st.markdown("""
<style>
    .stApp { background-color: #0e0e10; }
    .highlight { background-color: #ff4b4b; color: #ffffff; padding: 0 4px; border-radius: 4px; font-weight: bold; }
    
    /* Control Panel Styling */
    .control-panel {
        background-color: #16161a;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #2d2d33;
        margin-bottom: 24px;
    }

    /* Simile Box Styling */
    .simile-box { 
        background-color: #1c1c21; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 16px; 
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        border: 1px solid #2d2d33;
        transition: transform 0.2s ease;
    }
    .simile-box:hover { border-color: #ff4b4b; transform: translateY(-2px); }
    
    .lyric-text { 
        font-size: 1.15em; 
        line-height: 1.5; 
        color: #e0e0e0; 
        margin-bottom: 12px; 
        font-family: 'IBM Plex Mono', monospace; 
    }
    .meta-text { 
        color: #666; 
        font-size: 0.8em; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 1px; 
    }
    .year-pill {
        background: #2d2d33;
        color: #ff4b4b;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.9em;
        margin-right: 8px;
    }
    .star-rating { color: #ffb400; font-size: 0.9em; margin-left: 5px; }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA & LIVE SANITIZE
@st.cache_data
def load_all_chunks():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_pattern = os.path.join(base_dir, "similes_metadata_part_*.csv")
    all_files = glob.glob(file_pattern)
    
    if not all_files:
        all_files = glob.glob("similes_metadata_part_*.csv")
        
    if not all_files:
        return None
    
    with st.spinner("📥 Feeding the database..."):
        all_files.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
        df_list = [pd.read_csv(f) for f in all_files]
        full_df = pd.concat(df_list, ignore_index=True)
        
        # Hygiene
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        full_df['year'] = pd.to_numeric(full_df['year'], errors='coerce')
        
        # FIX: The "Christ's Birth" Problem - Force a realistic Rap era
        full_df = full_df[(full_df['year'] >= 1980) & (full_df['year'] <= 2026)]
        
        # Remove sensory noise
        bad_phrases = 'sounds like|sound like|feels like|feel like|looks like|look like|seems like'
        full_df = full_df[~full_df['line'].str.contains(bad_phrases, case=False, regex=True, na=False)]
        
        return full_df.drop_duplicates(subset=['artist', 'line'])

df = load_all_chunks()

if df is None:
    st.error("❌ No data files found.")
    st.stop()

# 3. UTILITIES
@st.cache_data
def get_synonyms(word, limit=10):
    try:
        res = requests.get(f"https://api.datamuse.com/words?ml={word}&max={limit}", timeout=2)
        return [item['word'] for item in res.json()] if res.status_code == 200 else []
    except: return []

def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        text = re.sub(rf'\b({re.escape(str(term))})\b', r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
    return text

# 4. UNIFIED COMMAND CENTER
st.title("🎤 Rap Simile Engine")

with st.container():
    col_search, col_syn = st.columns([4, 1])
    with col_search:
        query = st.text_input("", placeholder="Search for an image (e.g. ghost, brick, winter)...", label_visibility="collapsed")
    with col_syn:
        use_synonyms = st.checkbox("🧠 Brainstorm", value=False)

    with st.expander("🎛️ Engine Controls", expanded=True):
        f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
        
        with f_col1:
            st.markdown("**Timeline (Rap Era)**")
            # Logic check: ensures slider stays within real hip-hop bounds
            year_range = st.slider("", 1980, 2026, (1995, 2026), label_visibility="collapsed")
            
        with f_col2:
            st.markdown("**Popularity (Underground vs. Stars)**")
            # Mapping 5 stars to view counts
            pop_map = {
                "⭐ (Deep Underground)": 0,
                "⭐⭐ (Niche)": 1000,
                "⭐⭐⭐ (Established)": 10000,
                "⭐⭐⭐⭐ (Mainstream)": 100000,
                "⭐⭐⭐⭐⭐ (Superstars)": 1000000
            }
            star_label = st.select_slider("", options=list(pop_map.keys()), value="⭐ (Deep Underground)", label_visibility="collapsed")
            min_views = pop_map[star_label]
            
        with f_col3:
            st.markdown("**Grammar Pivot**")
            pivot = st.selectbox("", ["Anywhere", "Subject (Target like X)", "Object (X like Target)"], label_visibility="collapsed")

# 5. FILTER APPLICATION
df_filtered = df[
    (df['year'].between(year_range[0], year_range[1])) &
    (df['views'] >= min_views)
]

if 'display_limit' not in st.session_state: st.session_state.display_limit = 40
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42

# 6. SEARCH LOGIC
if query:
    q = query.lower().strip()
    search_terms = [q]
    if use_synonyms:
        search_terms.extend(get_synonyms(q, 8))

    with st.spinner("Scanning..."):
        pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        
        if pivot == "Subject (Target like X)":
            mask = df_filtered['signified'].str.contains(pattern, regex=True, na=False)
        elif pivot == "Object (X like Target)":
            mask = df_filtered['signifier'].str.contains(pattern, regex=True, na=False)
        else:
            mask = df_filtered['signified'].str.contains(pattern, regex=True, na=False) | df_filtered['signifier'].str.contains(pattern, regex=True, na=False)
            
        results = df_filtered[mask]

    # 7. TWO-COLUMN DISPLAY
    if not results.empty:
        st.write(f"Showing **{len(results):,}** similes")
        
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        res_col1, res_col2 = st.columns(2)
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            clean_line = highlight_sentence(row['line'], search_terms)
            target_col = res_col1 if i % 2 == 0 else res_col2
            
            # Simple view-to-star display in the card
            v = row['views']
            stars = "⭐" * (5 if v >= 1000000 else 4 if v >= 100000 else 3 if v >= 10000 else 2 if v >= 1000 else 1)
            
            with target_col:
                st.markdown(f"""
                <div class="simile-box">
                    <div class="lyric-text">{clean_line}</div>
                    <div class="meta-text">
                        <span class="year-pill">{int(row['year'])}</span>
                        {row['artist']} <span class="star-rating">{stars}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
        if len(results) > st.session_state.display_limit:
            if st.button("Load More", use_container_width=True):
                st.session_state.display_limit += 40
                st.rerun()
    else:
        st.warning(f"No results for '{query}'. Try lowering the star rating.")
else:
    st.info(f"Database ready: {len(df_filtered):,} similes active.")
