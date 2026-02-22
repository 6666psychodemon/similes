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
st.caption("Powered by Datamuse AI & 5 Million Songs.")

# 2. LOAD ALL DATA
@st.cache_data
def load_all_chunks():
    all_files = glob.glob("similes_part_*.csv")
    if not all_files: return None
    
    df_list = [pd.read_csv(f) for f in sorted(all_files)]
    full_df = pd.concat(df_list, ignore_index=True)
    
    full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
    full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
    full_df = full_df.drop_duplicates(subset=['artist', 'line'])
    
    return full_df

df = load_all_chunks()

if df is None:
    st.error("❌ No data files found! Please upload your 'similes_part_X.csv' files to GitHub.")
    st.stop()
else:
    st.sidebar.success(f"🔥 Online: {len(df):,} unique similes loaded.")

# 3. DATAMUSE API INTEGRATION
@st.cache_data
def get_synonyms(word):
    """Fetches top 4 synonyms from Datamuse API to expand the search."""
    try:
        response = requests.get(f"https://api.datamuse.com/words?ml={word}&max=4", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return [item['word'] for item in data]
    except:
        pass
    return []

# 4. HIGHLIGHTING UTILITY
def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        pattern = re.compile(r'\b' + re.escape(str(term)) + r'\b', re.IGNORECASE)
        text = pattern.sub(f'<span class="highlight">{term}</span>', text)
    return text

# 5. SEARCH UI
query = st.text_input("Search for a concept (e.g., 'money', 'fast', 'ghost')...", "")

if query:
    q = query.lower().strip()
    
    # Get Synonyms!
    synonyms = get_synonyms(q)
    search_terms = [q] + synonyms
    
    if synonyms:
        st.info(f"🧠 **Smart Search Active:** Also looking for *{', '.join(synonyms)}*")
    
    # SEARCH LOGIC (Checks for exact word or synonyms)
    def is_match(row_val):
        row_val = re.sub(r'^(a|an|the|my|his|her|your|our|their|that|this)\s+', '', row_val)
        last_word = row_val.split()[-1] if row_val else ""
        
        # Check against the original query AND all synonyms
        for term in search_terms:
            if term == row_val or term == last_word:
                return True
        return False

    mask = df.apply(lambda row: is_match(row['signified']) or is_match(row['signifier']), axis=1)
    results = df[mask]
    
    st.markdown(f"### Found {len(results):,} results")
    
    for index, row in results.head(100).iterrows():
        # Highlight original query AND any synonyms found
        highlight_targets = [row['signified'], row['signifier']] + search_terms
        clean_line = highlight_sentence(row['line'], highlight_targets)
        
        st.markdown(f"""
        <div class="simile-box">
            <div class="meta-text">{row['artist']} — {row['song']}</div>
            <div style="font-size: 1.1em;">"{clean_line}"</div>
            <div style="margin-top: 8px; font-size: 0.9em; color: #aaa;">
                Comparing <b>{row['signified']}</b> → <b>{row['signifier']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif not df.empty:
    st.info("The engine is ready. Enter a word above to explore metaphors across the entire database.")
