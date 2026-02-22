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
</style>
""", unsafe_allow_html=True)

st.title("🎤 Rap Simile Engine")

# 2. LOAD DATA
@st.cache_data
def load_all_chunks():
    all_files = glob.glob("similes_part_*.csv")
    if not all_files: return None
    
    with st.status("📥 Loading master database...", expanded=False) as status:
        df_list = [pd.read_csv(f) for f in sorted(all_files)]
        full_df = pd.concat(df_list, ignore_index=True)
        # Standardizing text for faster searching
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        full_df = full_df.drop_duplicates(subset=['artist', 'line'])
        status.update(label="✅ Database Online!", state="complete")
    return full_df

df = load_all_chunks()

# SIDEBAR CONTROLS
if df is not None:
    st.sidebar.header("Search Settings")
    exact_match = st.sidebar.checkbox("Exact match only (no 'caterpillar' for 'cat')", value=True)
    use_synonyms = st.sidebar.checkbox("Enable Synonym Expansion (Datamuse)", value=False)
    result_limit = st.sidebar.slider("Results to display", 10, 500, 50)
    st.sidebar.divider()
    st.sidebar.success(f"🔥 {len(df):,} unique similes loaded.")
else:
    st.error("❌ No data files found in root!")
    st.stop()

# 3. UTILITIES
@st.cache_data
def get_synonyms(word):
    try:
        response = requests.get(f"https://api.datamuse.com/words?ml={word}&max=5", timeout=2)
        if response.status_code == 200:
            return [item['word'] for item in response.json()]
    except: pass
    return []

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
query = st.text_input("Search for a concept...", placeholder="e.g. cat, bullet, winter")

if query:
    q = query.lower().strip()
    search_terms = [q]
    
    if use_synonyms:
        with st.spinner("🧠 Expanding vocabulary..."):
            syns = get_synonyms(q)
            search_terms.extend(syns)
            if syns: st.caption(f"Also searching for: {', '.join(syns)}")

    with st.spinner(f"🔍 Scanning {len(df):,} similes..."):
        # Create Regex Pattern
        if exact_match:
            # \b matches word boundaries only
            pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        else:
            pattern = '|'.join([re.escape(t) for t in search_terms])
            
        mask = (df['signified'].str.contains(pattern, regex=True, na=False)) | \
               (df['signifier'].str.contains(pattern, regex=True, na=False))
        results = df[mask]

    if results.empty:
        st.warning(f"No results found for '{q}'.")
    else:
        st.success(f"Found {len(results):,} matches.")
        for _, row in results.head(result_limit).iterrows():
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
