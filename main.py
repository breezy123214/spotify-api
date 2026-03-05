import streamlit as st
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
load_dotenv()


# ---- Page Config ----
st.set_page_config(page_title="Spotify Insights", page_icon="🎵", layout="wide")

# ---- Styling ----
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
        }
        .artist-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            margin: 5px 0;
        }
        [data-testid="stMetricValue"] { color: #1ED760 !important; }
        [data-testid="stMetricLabel"] { color: #aaaaaa !important; }
    </style>
""", unsafe_allow_html=True)

# ---- Credentials ----
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

# ---- Auth ----
auth_manager = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-top-read",
    open_browser=False,
    cache_path=".cache"
)

code = st.query_params.get("code")
if code:
    auth_manager.get_access_token(code, as_dict=False)
    st.query_params.clear()

token_info = auth_manager.get_cached_token()

if not token_info:
    auth_url = auth_manager.get_authorize_url()
    st.title("🎵 Spotify Listening Insights")
    st.markdown(f"### [👉 Login with Spotify]({auth_url})")
    st.stop()

if auth_manager.is_token_expired(token_info):
    token_info = auth_manager.refresh_access_token(token_info["refresh_token"])

sp = spotipy.Spotify(auth=token_info["access_token"])

# ---- Fetch Data ----
user = sp.current_user()
top_tracks = sp.current_user_top_tracks(limit=15)
top_artists_data = sp.current_user_top_artists(limit=5)

if not top_tracks["items"]:
    st.warning("No listening history found. Listen to more music on Spotify and come back!")
    st.stop()

st.title(f"🎵 {user.get('display_name', 'Your')} Spotify Insights")
st.markdown("---")

# ---- Build DataFrame ----
data = []
for i, track in enumerate(top_tracks["items"]):
    all_artists = ", ".join([a["name"] for a in track.get("artists", [])])
    release_date = track.get("album", {}).get("release_date", "0")
    release_year = release_date[:4]
    data.append({
        "Rank": i + 1,
        "Track": track.get("name", "Unknown"),
        "Artist": track.get("artists", [{}])[0].get("name", "Unknown"),
        "All Artists": all_artists,
        "Album": track.get("album", {}).get("name", "Unknown"),
        "Popularity": track.get("popularity", 0),
        "Duration (s)": round(track.get("duration_ms", 0) / 1000),
        "Explicit": "Yes" if track.get("explicit") else "No",
        "Release Year": int(release_year) if release_year.isdigit() else 0,
    })

df = pd.DataFrame(data)

def get_tier(p):
    if p >= 80: return "🔥 Mainstream"
    elif p >= 60: return "📈 Popular"
    elif p >= 40: return "🎯 Mid"
    else: return "💎 Underground"

df["Tier"] = df["Popularity"].apply(get_tier)

# ---- Quick Stats ----
st.subheader("📊 Quick Stats")
col1, col2, col3, col4 = st.columns(4)

most_popular_idx = df["Popularity"].idxmax()
top_artist_name = df["Artist"].value_counts().idxmax()

col1.metric("🏆 Most Popular Track", df.loc[most_popular_idx, "Track"], f"Score: {df.loc[most_popular_idx, 'Popularity']}")
col2.metric("⭐ Avg Popularity", round(df["Popularity"].mean(), 1), "out of 100")
col3.metric("⏱ Avg Duration", f"{round(df['Duration (s)'].mean())}s")
col4.metric("🎤 Top Artist", top_artist_name, f"{df['Artist'].value_counts().max()} tracks")

st.markdown("---")

# ---- Charts ----
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔥 Popularity Scores")
    st.bar_chart(df[["Track", "Popularity"]].set_index("Track"))

with col_right:
    st.subheader("⏱ Track Duration (seconds)")
    st.bar_chart(df[["Track", "Duration (s)"]].set_index("Track"))

st.markdown("---")

# ---- Top Artists Deep Dive ----
st.subheader("🎤 Top Artists")

col_a, col_b = st.columns([1, 2])

with col_a:
    st.markdown("**Appearances in Your Top 15**")
    st.bar_chart(df["Artist"].value_counts())

with col_b:
    st.markdown("**Your Top 5 Artists — Data Spotify Hides**")
    for artist in top_artists_data.get("items", []):
        name = artist.get("name", "Unknown")
        genres_list = artist.get("genres", [])
        genres = ", ".join(genres_list[:3]) if genres_list else "Genre not available"
        followers = f"{artist.get('followers', {}).get('total', 0):,}"
        pop = artist.get("popularity", 0)
        pop_bar = "🟢" * (pop // 20) + "⚪" * (5 - pop // 20)
        st.markdown(f"""
        <div class='artist-card'>
            <b style='color:#1ED760; font-size:16px'>{name}</b><br>
            🎸 {genres}<br>
            👥 {followers} followers &nbsp;&nbsp;
            🔥 Popularity: {pop_bar} ({pop}/100)
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ---- Hidden Insights ----
st.subheader("🔍 Insights Spotify Doesn't Show You")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**📅 Your Listening Era**")
    valid_years = df[df["Release Year"] > 0]
    if not valid_years.empty:
        oldest = valid_years.loc[valid_years["Release Year"].idxmin()]
        newest = valid_years.loc[valid_years["Release Year"].idxmax()]
        st.markdown(f"Oldest: **{oldest['Track']}** ({oldest['Release Year']})")
        st.markdown(f"Newest: **{newest['Track']}** ({newest['Release Year']})")
        st.bar_chart(valid_years["Release Year"].value_counts().sort_index())

with col2:
    st.markdown("**🔞 Content Breakdown**")
    explicit_count = (df["Explicit"] == "Yes").sum()
    explicit_pct = round(explicit_count / len(df) * 100)
    st.markdown(f"**{explicit_pct}%** of your top tracks are explicit ({explicit_count}/15)")
    st.progress(explicit_pct / 100)
    total_mins = round(df["Duration (s)"].sum() / 60, 1)
    st.markdown(f"**Total runtime** of top 15: `{total_mins} minutes`")

with col3:
    st.markdown("**🏅 Popularity Tiers**")
    st.dataframe(df["Tier"].value_counts().rename("Tracks"), use_container_width=True)

st.markdown("---")

# ---- Full Table ----
st.subheader("📋 Full Track List")
st.dataframe(df.drop(columns=["Tier"]).set_index("Rank"), use_container_width=True)