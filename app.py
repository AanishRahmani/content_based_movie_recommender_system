import streamlit as st
import pickle
import pandas as pd
import requests
import os
import json
import time
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

# Proper API key handling
def get_api_key():
    """Safely retrieve API key from Streamlit secrets or environment variables."""
    try:
        if hasattr(st, 'secrets') and "API_KEY" in st.secrets:
            return st.secrets["API_KEY"]
    except Exception:
        pass
    
    api_key = os.getenv("API_KEY")
    
    if not api_key:
        st.error("❌ API Key not found! Please set up your TMDB API key.")
        st.info("""
        **For local development:** Add `API_KEY=your_key_here` to your `.env` file
        
        **For deployment:** Add your API key to Streamlit secrets:
        1. Go to App settings → Secrets
        2. Add: `API_KEY = "your_key_here"`
        """)
        st.stop()
    
    return api_key

API_KEY = get_api_key()

# Use session state for cache instead of file writing
if 'poster_cache' not in st.session_state:
    CACHE_FILE = "poster_cache.json"
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                st.session_state.poster_cache = json.load(f)
        except Exception:
            st.session_state.poster_cache = {}
    else:
        st.session_state.poster_cache = {}

def create_session():
    """Create a requests session with retry logic and connection pooling."""
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    return session

API_SESSION = create_session()

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_poster(movie_id):
    """Fetch poster URL from TMDB API with caching."""
    movie_id = str(movie_id)
    
    # Check session state cache
    if movie_id in st.session_state.poster_cache:
        return st.session_state.poster_cache[movie_id]

    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    
    try:
        response = API_SESSION.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "poster_path" not in data or not data["poster_path"]:
            return None

        poster_url = "https://image.tmdb.org/t/p/w500" + data["poster_path"]
        
        # Store in session state instead of file
        st.session_state.poster_cache[movie_id] = poster_url

        return poster_url

    except Exception:
        return None

@st.cache_data(show_spinner=False)
def load_data():
    """Load movie data and similarity matrix safely."""
    
    def safe_pickle_load(file_path, description):
        """Helper to safely unpickle files with multiple fallbacks."""
        if not os.path.exists(file_path):
            st.error(f"❌ File not found: {file_path}")
            st.stop()
            
        try:
            with open(file_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            try:
                with open(file_path, "rb") as f:
                    return pickle.load(f, encoding="latin1")
            except Exception as e:
                st.error(f"❌ Failed to load {description}: {str(e)}")
                st.stop()

    movies_df = safe_pickle_load("movies.pkl", "movie data")
    similarity = safe_pickle_load("similarity.pkl", "similarity matrix")

    if movies_df is not None:
        try:
            movies_df = movies_df.reset_index(drop=True)
        except Exception as e:
            st.error(f"❌ Error processing movie data: {str(e)}")
            st.stop()

    return movies_df, similarity

# Load data at startup
try:
    movies_df, similarity = load_data()
except Exception as e:
    st.error(f"❌ Failed to initialize app: {str(e)}")
    st.stop()

def get_recommended_movie_indices(movie):
    """Return sorted list of movie indices by similarity."""
    try:
        movie_index = movies_df[movies_df["title"] == movie].index[0]
    except IndexError:
        st.error("Selected movie not found in database.")
        return []

    if movie_index >= len(similarity):
        st.error("Data mismatch: similarity matrix and movie list are out of sync.")
        return []

    distances = similarity[movie_index]
    movie_list = sorted(list(enumerate(distances)), reverse=True, key=lambda x: x[1])[1:]
    
    return [i[0] for i in movie_list]

def fetch_recommendations_batch(movie_indices, start_idx, batch_size=5):
    """Fetch a batch of recommendations with posters."""
    end_idx = min(start_idx + batch_size, len(movie_indices))
    
    recommended_movies = []
    recommended_posters = []
    
    for i in range(start_idx, end_idx):
        idx = movie_indices[i]
        movie_id = movies_df.iloc[idx].movie_id
        title = movies_df.iloc[idx].title
        
        poster_url = fetch_poster(movie_id)
        
        recommended_movies.append(title)
        recommended_posters.append(poster_url)
        
        if (i - start_idx + 1) % 5 == 0 and i < end_idx - 1:
            time.sleep(0.2)
    
    return recommended_movies, recommended_posters

# Initialize session state
if 'movies_to_show' not in st.session_state:
    st.session_state.movies_to_show = 5

if 'current_movie' not in st.session_state:
    st.session_state.current_movie = None

if 'movie_indices' not in st.session_state:
    st.session_state.movie_indices = []

if 'cached_names' not in st.session_state:
    st.session_state.cached_names = []

if 'cached_posters' not in st.session_state:
    st.session_state.cached_posters = []

def increment_movies():
    """Callback to increment the number of movies to show."""
    st.session_state.movies_to_show += 5

def reset_movie_count():
    """Reset movie count when a new movie is selected."""
    st.session_state.movies_to_show = 5
    st.session_state.cached_names = []
    st.session_state.cached_posters = []

# Page configuration
st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Movie Recommender System")

# Movie selection dropdown
selected_movie = st.selectbox(
    "Select a movie:",
    movies_df["title"].values,
    index=None,
    placeholder="Search or select a movie...",
)

# Check if a different movie was selected
if selected_movie and selected_movie != st.session_state.current_movie:
    st.session_state.current_movie = selected_movie
    reset_movie_count()
    st.session_state.movie_indices = get_recommended_movie_indices(selected_movie)

if selected_movie:
    movie_indices = st.session_state.movie_indices
    
    if movie_indices:
        st.subheader("🎥 Recommended Movies:")
        
        num_to_display = min(st.session_state.movies_to_show, len(movie_indices))
        num_already_cached = len(st.session_state.cached_names)
        
        # Fetch additional movies if needed
        if num_to_display > num_already_cached:
            with st.spinner(f"Loading {num_to_display - num_already_cached} more movies..."):
                new_names, new_posters = fetch_recommendations_batch(
                    movie_indices, 
                    num_already_cached, 
                    num_to_display - num_already_cached
                )
                st.session_state.cached_names.extend(new_names)
                st.session_state.cached_posters.extend(new_posters)
        
        # Display all cached movies
        for row_start in range(0, num_to_display, 5):
            cols = st.columns(5)
            for idx, col in enumerate(cols):
                movie_idx = row_start + idx
                if movie_idx < num_to_display:
                    with col:
                        if st.session_state.cached_posters[movie_idx]:
                            st.image(st.session_state.cached_posters[movie_idx], use_container_width=True)
                        else:
                            st.markdown(
                                """
                                <div style="
                                    background-color: #2d2d2d;
                                    height: 300px;
                                    display: flex;
                                    align-items: center;
                                    justify-content: center;
                                    border-radius: 5px;
                                ">
                                    <span style="font-size: 48px;">🎬</span>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        st.caption(st.session_state.cached_names[movie_idx])
        
        # Show "More" button if there are more movies to display
        if num_to_display < len(movie_indices):
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                st.button(
                    "More",
                    on_click=increment_movies,
                    use_container_width=True,
                    type="primary"
                )
        else:
            st.success(f"✓ All {len(movie_indices)} recommendations displayed")
    else:
        st.info("No recommendations found.")
else:
    st.markdown(
        """
        <div style="
            background-color: #1e1e1e;
            padding: 2rem;
            border-radius: 10px;
            text-align: center;
            font-size: 1.1rem;
            border: 2px solid #333;
        ">
            👋 <b>Welcome to Movie Recommender!</b><br><br>
            Please select a movie from the dropdown above to discover similar movies you might enjoy.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.9rem;">
        Powered by TMDB API | Built with Streamlit
    </div>
    """,
    unsafe_allow_html=True
)
