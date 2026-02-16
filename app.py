import streamlit as st
import pandas as pd

# 1. SETUP PAGE
st.set_page_config(page_title="Rap Simile Search", layout="wide")
st.title("🎤 Rap Simile Engine")
st.markdown("Type a word to find how rappers use it in similes.")

# 2. LOAD DATA (We use @st.cache so it only loads once, not every search)
@st.cache_data
def load_data():
    # If your file is huge, we'll just read the columns we need to save RAM
    df = pd.read_csv("simile_database.csv") # Make sure this file is in the same folder!
    # Ensure all text is lowercase for easier searching
    df['line_lower'] = df['line'].str.lower()
    return df

try:
    df = load_data()
    st.success(f"Loaded {len(df):,} similes from the database.")
except FileNotFoundError:
    st.error("❌ CSV file not found! Please put 'simile_database.csv' in this folder.")
    st.stop()

# 3. SEARCH INTERFACE
query = st.text_input("Search for a noun (e.g., 'kite'), adjective (e.g., 'high'), or verb...", "")

if query:
    # 4. THE SEARCH LOGIC
    # This finds the query anywhere in the line
    results = df[df['line_lower'].str.contains(query.lower())]
    
    # 5. DISPLAY RESULTS
    st.write(f"Found **{len(results)}** matches for '{query}':")
    
    if not results.empty:
        # Show a nice table
        st.dataframe(
            results[['artist', 'song', 'line']], 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No similes found. Try a different word!")

# Optional: Show random examples if no search
else:
    st.subheader("Random Examples:")
    st.table(df[['artist', 'song', 'line']].sample(5))