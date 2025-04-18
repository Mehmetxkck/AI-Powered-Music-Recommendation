import random
from models import Song
from collections import defaultdict

class RecommendationEngine:
    def __init__(self, music_data):
        self.music_data = music_data
        self.user_song_interactions = defaultdict(list)  # user_id: [song_ids]

    def add_user_song_interaction(self, user_id, song_id):
        """
        Adds a user-song interaction to the database.
        """
        self.user_song_interactions[user_id].append(song_id)

    def get_recommendations(self, user_listening_history, mood):
        """
        Generates music recommendations based on listening history and mood.
        (This is a simplified example)
        """
        mood_filtered_music = [
            song for song in self.music_data if song.mood == mood
        ]

        if not mood_filtered_music:
            return random.sample(self.music_data, 5)

        recommendations = []
        for song in mood_filtered_music:
            if song.artist not in [
                history.artist for history in user_listening_history
            ]:
                recommendations.append(song)

        if not recommendations:
            return random.sample(mood_filtered_music, 5)

        return random.sample(recommendations, min(5, len(recommendations)))

    def get_collaborative_recommendations(self, user_id, mood):
        """
        Generates collaborative recommendations for a user.
        (This is a very basic example)
        """
        similar_users = self.find_similar_users(user_id)
        recommended_songs = set()
        for similar_user_id in similar_users:
            for song_id in self.user_song_interactions[similar_user_id]:
                recommended_songs.add(song_id)

        # Filter out songs the user has already interacted with
        user_interacted_songs = set(self.user_song_interactions[user_id])
        filtered_recommendations = []
        for song in self.music_data:
            if song._id in recommended_songs and song._id not in user_interacted_songs and song.mood == mood:
                filtered_recommendations.append(song)

        return random.sample(filtered_recommendations, min(5, len(filtered_recommendations)))

    def find_similar_users(self, user_id):
        """
        Finds users similar to the given user based on their song interactions.
        (This is a very basic example)
        """
        similarities = {}
        for other_user_id, other_user_songs in self.user_song_interactions.items():
            if other_user_id != user_id:
                common_songs = set(self.user_song_interactions[user_id]) & set(other_user_songs)
                similarities[other_user_id] = len(common_songs)

        # Sort users by similarity
        sorted_similar_users = sorted(similarities.items(), key=lambda item: item[1], reverse=True)
        return [user_id for user_id, similarity in sorted_similar_users[:3]]  # Return top 3 similar users
    
    def get_content_based_recommendations(self, user_listening_history, mood, db):
        """
        Generates content-based recommendations for a user.
        (This is a very basic example)
        """
        if not user_listening_history:
            return []

        # Get the genres of the songs the user has listened to
        user_genres = set(song.genre for song in user_listening_history)

        # Get songs from the database that match the user's genres
        genre_filtered_songs = []
        for genre in user_genres:
            genre_filtered_songs.extend(db.get_songs_by_genre(genre))

        # Filter by mood
        mood_filtered_songs = [song for song in genre_filtered_songs if song.mood == mood]

        # Remove songs the user has already listened to
        user_song_ids = {song._id for song in user_listening_history}
        new_songs = [song for song in mood_filtered_songs if song._id not in user_song_ids]

        return random.sample(new_songs, min(5, len(new_songs)))
