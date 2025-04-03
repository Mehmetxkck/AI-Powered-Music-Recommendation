from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from recommendations import RecommendationEngine
from database import Database
from models import User, Song
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "asdfasdfasdf")  # Use environment variable for security

# Spotify API Credentials (replace with your actual credentials)
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID", "8e881dd7d57947f79003b34d33557d07")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET", "6c5262493daf4ac38195c787e3808030")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5500")

# Spotify API scopes (permissions)
SPOTIPY_SCOPES = "user-read-recently-played user-top-read user-read-private user-read-email"

# Initialize database and recommendation engine
db = Database()
music_data = db.get_all_songs()
engine = RecommendationEngine(music_data)

# Spotify OAuth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SPOTIPY_SCOPES,
    show_dialog=True
)

@app.route('/login')
def login():
    """
    Redirects the user to the Spotify authorization URL.
    """
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """
    Handles the callback from Spotify after user authorization.
    """
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('get_user_data'))

@app.route('/get_user_data')
def get_user_data():
    """
    Fetches user data from Spotify and stores it in the session.
    """
    token_info = get_token()
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_data = sp.me()
    session['user_data'] = user_data
    
    # Add user to the database
    db.add_user(user_data['id'], user_data['display_name'])
    
    # After successful login and user data retrieval, redirect to frontend to show recommendations
    return redirect(FRONTEND_URL)

@app.route('/user_data')
def user_data():
    """
    Returns the user data.
    """
    user_data = session.get('user_data')
    if user_data:
        return jsonify(user_data)
    else:
        return jsonify({"error": "User data not found"}), 404

@app.route('/recommendations', methods=['POST'])
def get_recommendations():
    """
    Endpoint to get music recommendations based on user history and mood.
    """
    token_info = get_token()
    if not token_info:
        return redirect(url_for('login'))

    sp = spotipy.Spotify(auth=token_info['access_token'])
    user_data = session.get('user_data')
    user_id = user_data['id']
    
    data = request.get_json()
    mood = data.get('mood')

    if not user_id or not mood:
        return jsonify({'error': 'Missing user_id or mood'}), 400

    user_history = db.get_user_history(user_id)
    
    # Get user's recently played tracks from Spotify
    recently_played = sp.current_user_recently_played(limit=5)
    
    # Get user's top tracks from Spotify
    top_tracks = sp.current_user_top_tracks(limit=5)
    
    # Combine user history and spotify data
    for item in recently_played['items']:
        track = item['track']
        song = db.get_song_by_id(track['id'])
        if song:
            user_history.append(song)
            db.add_to_history(user_id, song._id)
    for item in top_tracks['items']:
        song = db.get_song_by_id(item['id'])
        if song:
            user_history.append(song)
            db.add_to_history(user_id, song._id)
    
    # Get content-based recommendations
    content_based_recommendations = engine.get_content_based_recommendations(user_history, mood, db)
    
    # Get collaborative recommendations
    collaborative_recommendations = engine.get_collaborative_recommendations(user_id, mood)
    
    # Combine recommendations
    recommendations = content_based_recommendations + collaborative_recommendations
    
    # If there are no recommendations, get basic recommendations
    if not recommendations:
        recommendations = engine.get_recommendations(user_history, mood)
    
    return jsonify(recommendations)

def get_token():
    """
    Gets the token from the session and refreshes it if necessary.
    """
    token_info = session.get('token_info')
    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return token_info

if __name__ == '__main__':
    app.run(debug=True)
