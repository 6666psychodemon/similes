import streamlit as st
import pandas as pd
import glob
import re
import requests

# 1. PAGE CONFIG
st.set_page_config(page_title="Rap Simile Engine", page_icon="🎤", layout="wide")

st.markdown("""
<style>
    .highlight { background-color: #ffffff; color: #000000; padding: 0 4px; border-radius: 4px; font-weight: bold; }
    .simile-box { 
        background-color: #1e1e24; padding: 16px; border-radius: 12px; margin-bottom: 12px; 
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); border: none;
    }
    .lyric-text { font-size: 1.15em; line-height: 1.5; color: #e0e0e0; margin-bottom: 8px; }
    .meta-text { color: #777; font-size: 0.85em; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
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
        
        full_df['signified'] = full_df['signified'].astype(str).str.lower().str.strip()
        full_df['signifier'] = full_df['signifier'].astype(str).str.lower().str.strip()
        
        # 1. Catch bad phrases in the raw line (sensory verbs)
        bad_phrases = 'sounds like|sound like|feels like|feel like|looks like|look like|seems like'
        full_df = full_df[~full_df['line'].str.contains(bad_phrases, case=False, regex=True, na=False)]
        
        # 2. THE WEAK VERB & PREFERENCE PURGE
        # Kills lazy writing AND "preference vs comparison" false positives
        blocked_signifiers = {
            # Weak verbs
            'feel', 'feels', 'feeling', 'felt', 'look', 'looks', 'looking', 'looked',
            'smile', 'smiles', 'smiling', 'smiled', 'act', 'acts', 'acting', 'acted',
            'sound', 'sounds', 'sounding', 'sounded', 'seem', 'seems', 'seeming', 'seemed',
            'smell', 'smells', 'smelling', 'smelled', 'taste', 'tastes', 'tasting', 'tasted',
            'stare', 'stares', 'staring', 'stared', 'laugh', 'laughs', 'laughing', 'laughed',
            'cry', 'cries', 'crying', 'cried', 'walk', 'walks', 'walking', 'walked',
            'talk', 'talks', 'talking', 'talked', 'run', 'runs', 'running', 'ran',
            'dress', 'dresses', 'dressing', 'dressed', 'stand', 'stands', 'standing', 'stood',
            'work', 'works', 'working', 'worked', 'play', 'plays', 'playing', 'played',
            'treat', 'treats', 'treating', 'treated',
            # Preference & Conversational filler
            'just', 'really', 'simply', 'actually', 'already', 'only', 'some',
            'men', 'women', 'people', 'niggas', 'bitches', 'hoes', 'girls', 'boys',
            'they', 'we', 'i', 'you', 'he', 'she', 'everybody', 'nobody', 'someone', 'anyone'
        }
        full_df = full_df[~full_df['signified'].isin(blocked_signifiers)]
        
        return full_df.drop_duplicates(subset=['artist', 'line'])

df = load_all_chunks()

if df is None:
    st.error("❌ No data files found.")
    st.stop()

# 3. UTILITIES & DATAMUSE API
@st.cache_data
def get_synonyms(word, limit=10):
    try:
        res = requests.get(f"https://api.datamuse.com/words?ml={word}&max={limit}", timeout=2)
        return [item['word'] for item in res.json()] if res.status_code == 200 else []
    except: return []

@st.cache_data
def get_cliches(word, limit):
    if limit == 0: return []
    try:
        res = requests.get(f"https://api.datamuse.com/words?rel_trg={word}&max={limit}", timeout=2)
        return [item['word'] for item in res.json()] if res.status_code == 200 else []
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
        return ("... " if start > 0 else "") + text_str[start:end].strip() + (" ..." if end < len(text_str) else "")
    return text_str[:radius*2] + "..."

def highlight_sentence(text, terms):
    terms = sorted(list(set([t for t in terms if len(str(t)) > 1])), key=len, reverse=True)
    for term in terms:
        text = re.sub(rf'\b({re.escape(str(term))})\b', r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)
    return text

# 4. SEARCH UI
st.write("<br>", unsafe_allow_html=True)
query = st.text_input("Search", placeholder="Search for a concept (e.g. beast, money, ghost)...", label_visibility="collapsed")
use_synonyms = st.checkbox("🧠 Brainstorm: Include related concepts", value=False)

# 5. EXPERIMENTAL CONTROLS
with st.expander("🧪 Experimental Controls", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Structure**")
        pivot = st.radio("Target position:", ["Anywhere", "Subject (e.g., 'Target like X')", "Object (e.g., 'X like Target')"], label_visibility="collapsed")
        end_of_bar = st.checkbox("Word must be at the very end of the bar")
    
    with col2:
        st.markdown("**2. Semantics**")
        cliche_strictness = st.slider("Anti-Cliché Dial (Blocks X most obvious associations)", 0, 100, 0, step=10)
        collider_lens = st.text_input("Concept Collider (Aesthetic Lens)", placeholder="e.g. metal, religion, war")

if 'display_limit' not in st.session_state: st.session_state.display_limit = 100
if 'random_seed' not in st.session_state: st.session_state.random_seed = 42

# 6. SEARCH ENGINE LOGIC
if query:
    q = query.lower().strip()
    search_terms = [q]
    lens_terms = []
    
    if use_synonyms:
        with st.spinner("Expanding base vocabulary..."):
            search_terms.extend(get_synonyms(q, 5))
            
    if collider_lens:
        with st.spinner(f"Loading '{collider_lens}' aesthetic..."):
            lens_terms = [collider_lens.lower().strip()] + get_synonyms(collider_lens.lower().strip(), 40)

    with st.spinner("Scanning database..."):
        pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in search_terms])
        
        if pivot == "Subject (e.g., 'Target like X')":
            mask = df['signified'].str.contains(pattern, regex=True, na=False)
        elif pivot == "Object (e.g., 'X like Target')":
            mask = df['signifier'].str.contains(pattern, regex=True, na=False)
        else:
            mask = df['signified'].str.contains(pattern, regex=True, na=False) | df['signifier'].str.contains(pattern, regex=True, na=False)
            
        results = df[mask]

        if collider_lens and not results.empty:
            lens_pattern = '|'.join([rf'\b{re.escape(t)}\b' for t in lens_terms])
            results = results[
                results['signified'].str.contains(lens_pattern, regex=True, na=False) | 
                results['signifier'].str.contains(lens_pattern, regex=True, na=False)
            ]
            search_terms.extend(lens_terms)

        if cliche_strictness > 0 and not results.empty:
            cliches = get_cliches(q, cliche_strictness)
            if cliches:
                cliche_pattern = '|'.join([rf'\b{re.escape(c)}\b' for c in cliches])
                results = results[~results['signified'].str.contains(cliche_pattern, regex=True, na=False) & 
                                  ~results['signifier'].str.contains(cliche_pattern, regex=True, na=False)]

        if end_of_bar and not results.empty:
            end_pattern = rf"({pattern})[^\w]*$"
            results = results[results['line'].str.contains(end_pattern, regex=True, case=False, na=False)]

    # 7. DISPLAY LOGIC
    if not results.empty:
        col_header, col_btn = st.columns([4, 1])
        with col_header:
            st.success(f"Found {len(results):,} total matches.")
        with col_btn:
            if st.button("🎲 Re-Shuffle", use_container_width=True):
                st.session_state.random_seed += 1
                st.session_state.display_limit = 100
        
        display_df = results.sample(frac=1, random_state=st.session_state.random_seed)
        cols = st.columns(2, gap="small")
        
        for i, (_, row) in enumerate(display_df.head(st.session_state.display_limit).iterrows()):
            short_line = crop_long_text(row['line'], q)
            clean_line = highlight_sentence(short_line, search_terms)
            
            with cols[i % 2]:
                st.markdown(f"""
                <div class="simile-box">
                    <div class="lyric-text">{clean_line}</div>
                    <div class="meta-text">{row['artist']} — {row['song']}</div>
                </div>
                """, unsafe_allow_html=True)

        if len(results) > st.session_state.display_limit:
            st.write("") 
            if st.button("⬇️ Load 100 More Results", use_container_width=True):
                st.session_state.display_limit += 100
                st.rerun()
    else:
        st.warning("No results found. Try lowering the Anti-Cliché dial or removing the Collider lens.")
else:
    st.info(f"{len(df):,} similes ready. Open the Experimental Controls to narrow your search.")
