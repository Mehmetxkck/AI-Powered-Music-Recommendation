from models import Song, User, History
from collections import defaultdict

class Database:
    def __init__(self):
        self.songs = []
        self.users = {}  # user_id: User object
        self.history = defaultdict(list)  # user_id: [song_ids]
        self.initialize_data()

    def initialize_data(self):
        """
        Initializes the in-memory data with some sample data.
        """
        sample_songs = [
            Song("Song A", "Artist X", "happy", "pop"),
            Song("Song B", "Artist Y", "sad", "rock"),
            Song("Song C", "Artist Z", "happy", "pop"),
            Song("Song D", "Artist W", "energetic", "electronic"),
            Song("Song E", "Artist V", "calm", "classical"),
            Song("Song F", "Artist U", "happy", "pop"),
            Song("Song G", "Artist T", "sad", "rock"),
            Song("Song H", "Artist A", "happy", "pop"),
            Song("Song I", "Artist B", "sad", "rock"),
            Song("Song J", "Artist C", "happy", "pop"),
            Song("Song K", "Artist D", "energetic", "electronic"),
            Song("Song L", "Artist E", "calm", "classical"),
            Song("Song M", "Artist F", "happy", "pop"),
            Song("Song N", "Artist G", "sad", "rock"),
        ]
        self.songs.extend(sample_songs)

    def get_all_songs(self):
        """
        Retrieves all songs from the in-memory storage.
        """
        return self.songs

    def get_user_history(self, user_id):
        """
        Retrieves the listening history for a specific user.
        """
        song_history = []
        for song_id in self.history[user_id]:
            song = self.get_song_by_id(song_id)
            if song:
                song_history.append(song)
        return song_history

    def add_to_history(self, user_id, song_id):
        """
        Adds a song to the user's listening history.
        """
        self.history[user_id].append(song_id)

    def add_user(self, user_id, username):
        """
        Adds a new user to the in-memory storage.
        """
        if user_id not in self.users:
            self.users[user_id] = User(user_id, username)

    def get_user(self, user_id):
        """
        Retrieves a user from the in-memory storage.
        """
        return self.users.get(user_id)

    def get_song_by_id(self, song_id):
        """
        Retrieves a song by its ID.
        """
        for song in self.songs:
            if song._id == song_id:
                return song
        return None
    
    def get_songs_by_genre(self, genre):
        """
        Retrieves songs by genre.
        """
        return [song for song in self.songs if song.genre == genre]
