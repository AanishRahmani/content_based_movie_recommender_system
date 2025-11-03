# 🎬 Movie Recommender System

This project is a **Movie Recommendation App** built with **Streamlit**.  
It suggests movies similar to the one you select, using a precomputed similarity matrix and movie metadata.  
The app fetches movie posters from **The Movie Database (TMDB)** API to make the experience more visual and engaging.

---

## 🌟 Features

- **Smart Recommendations** – suggests movies based on similarity scores from a trained model.
- **Poster Fetching via TMDB API** – each recommended movie comes with its poster.
- **Local Poster Caching** – posters are saved in a local JSON cache to reduce API calls.
- **Retry and Connection Handling** – robust fetching system that gracefully handles network issues.
- **Progressive Loading** – shows 5 movies at a time with a “More” button to load additional recommendations.
- **Smooth UI** – clean Streamlit interface with responsive layout and styled components.

---

## 🧠 How It Works

1. The system loads preprocessed data from two files:

   - `movies.pkl` – contains movie titles and metadata.
   - `similarity.pkl` – stores a similarity matrix generated from features like genre, cast, or plot overview.

2. When you select a movie, the app:

   - Finds the corresponding index in the movie DataFrame.
   - Retrieves the top similar movies from the similarity matrix.
   - Calls the TMDB API to get poster images for those movies.
   - Displays them neatly in rows of 5.

3. Each new batch of recommendations is cached locally for faster loading next time.

---

## 🧰 Tech Stack

- **Python**
- **Streamlit** for the frontend and app logic
- **Pandas** and **Pickle** for data management
- **Requests** for API communication
- **TMDB API** for movie posters
- **dotenv** for environment variable management

---

## ⚙️ Project Structure
