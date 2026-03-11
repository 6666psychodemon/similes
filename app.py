import streamlit as st
import pandas as pd
import glob
import re
import requests
import os

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine V11", page_icon="🎤", layout="wide")

# Custom Dark Aesthetic
st.markdown("""
<style>
    .highlight { background-color: #ff4b4b; color: #ffffff; padding: 0 4px; border-radius: 4px; font-weight: bold; }
    .simile-box { 
        background-color: #1e1e24; padding: 20px; border-radius: 12px; margin-bottom: 16px; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); border: 1px solid #333;
    }
    .lyric-text { font-size: 1.2em; line-height: 1.6; color: #f0f0f0; margin-bottom: 10px; font-family: 'Courier New', Courier, monospace; }
    .meta-text { color: #999; font-size: 0.8em; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .year-tag { color: #ff4b4b; font-weight: bold; margin-left: 10px; }
</style>
""", unsafe_allow_html=True)

# 2. LOAD DATA & LIVE SANITIZE
@st.cache_data
def load_all_chunks():
    # Detect the script's actual location
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_pattern = os.path.join(base_dir, "similes_metadata_part_*.csv")
    all_files = glob.glob(file_pattern)
    
    if not all_files:
        # Fallback to current working directory if absolute path fails
        all_files = glob.glob("similes_metadata_part_*.csv")
        
    if not all_files:
        return None
    
    with st.spinner("📥 Extracting metaphors from the vault..."):
        # Sort files numerically to ensure consistent loading
        all_files.sort(key=lambda x: [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', x)])
        
        df_list = []
        for f in all_files:
            try:
                temp_df = pd.read_csv(f)
                df_list.append(temp_df)
            except Exception as e:
                st.warning(f"Skipping {f} due to error: {e}")
        
        full_df = pd.concat(df_list, ignore_index=True)
        
        # Clean data
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        
        # Filter sensory clichés
        bad_phrases = 'sounds like|sound like|feels like|feel like|looks like|look like|seems like'
        full_df = full_df[~full_df['line'].str.contains(bad_phrases, case=False, regex=True, na=False)]
        
        # Ensure 'year' is numeric and drop invalid entries
        full_df['year'] = pd.to_numeric(full_df['year'], errors='coerce')
        full_df = full_df.dropna(subset=['year'])
        
        return full_df.drop_duplicates(subset=['artist', 'line'])

df = load_all_chunks()

if df is None:
    # Debug helper for when it fails
    st.error("❌ No data files found.")
    st.write("Checking directory:", os.getcwd())
    st.write("Visible files:", os.listdir("."))
    st.stop()

# 3. UTILITIES
@st.cache_data
def get_synonyms(word, limit=10):
    try:
        res = requests.get(f"https://api.datamuse.com/words?ml={word}&max={limit}", timeout=2)
        return [item['word'] for item in res.json()] if res.status_code == 200 else []
    except: return []

def highlight_sentence(text, terms):
    # Sort terms by length (desc) to avoid partial highlighting of longer words
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        text = re.sub(rf'\b({re.escape(str(term))})\b', r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
    return text

# 4. SIDEBAR - METADATA FILTERS
st.sidebar.title("🎛️ Filter the Engine")

min_year_val = int(df['year'].min())
max_year_val = int(df['year'].max())
year_range = st.sidebar.slider("Era (Year)", min_year_val, max_year_val, (1990, max_year_val))

# Views filter
min_views = st.sidebar.select_slider("Popularity (Views)", options=[0, 1000, 10000, 100000, 1000000], value=0)

# Apply Sidebar Filters
df_filtered = df[
    (df['year'].between(year_range[0], year_range[1])) &
    (df['views'] >= min_views)
]

# 5. MAIN SEARCH UI
st.write("<br>", unsafe_allow_html=True)
query = st.text_input("Search", placeholder="Search for a concept (e.g. ghost, brick, concrete)...", label_visibility="collapsed")
use_synonyms = st.checkbox("🧠 Brainstorm: Include related concepts", value=False)

# 6. EXPERIMENTAL CONTROLS
with st.expander("🧪 Advanced Logic", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Structure**")
        pivot = st.radio("Target position:", ["Anywhere", "Subject (e.g., 'Target like X')", "Object (e.g., 'X like Target')"], label_visibility="collapsed")
    
    with col2:
        st.markdown("**2. Semantic Lens**")
        collider_lens = st.text_input("Aesthetic Filter (e.g. religion, anatomy, technology)", placeholder="Filter results by vibe...")

if 'display_limit' not in st.session_state: st.session_state.display_limit = 50
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42

# 7. SEARCH ENGINE LOGIC
if query:
    q = query.lower().strip()
    search_terms = [q]
    
    if use_synonyms:
        with st.spinner("Expanding vocabulary..."):
            search_terms.extend(get_synonyms(q, 8))

    with st.spinner("Scanning..."):
        pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        
        if pivot == "Subject (e.g., 'Target like X')":
            mask = df_filtered['signified'].str.contains(pattern, regex=True, na=False)
        elif pivot == "Object (e.g., 'X like Target')":
            mask = df_filtered['signifier'].str.contains(pattern, regex=True, na=False)
        else:
            mask = df_filtered['signified'].str.contains(pattern, regex=True, na=False) | df_filtered['signifier'].str.contains(pattern, regex=True, na=False)
            
        results = df_filtered[mask]

        if collider_lens and not results.empty:
            lens_terms = [collider_lens.lower().strip()] + get_synonyms(collider_lens.lower().strip(), 10)
            lens_pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in lens_terms])
            results = results[results['line'].str.contains(lens_pattern, regex=True, case=False, na=False)]

    # 8. DISPLAY RESULTS
    if not results.empty:
        st.success(f"Found {len(results):,} similes for '{query}' from {year_range[0]} to {year_range[1]}.")
        
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            clean_line = highlight_sentence(row['line'], search_terms)
            
            st.markdown(f"""
            <div class="simile-box">
                <div class="lyric-text">{clean_line}</div>
                <div class="meta-text">
                    {row['artist']} — {row['song']} 
                    <span class="year-tag">[{int(row['year'])}]</span>
                    <span style="color:#555"> • {int(row['views']):,} views</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        if len(results) > st.session_state.display_limit:
            if st.button("⬇️ Load More"):
                st.session_state.display_limit += 50
                st.rerun()
    else:
        st.warning("No matches in this era. Try widening the Year range or checking for synonyms.")
else:
    st.info(f"The Engine is loaded with {len(df_filtered):,} similes. Type a word to start.")
