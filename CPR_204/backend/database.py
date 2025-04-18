from models import User # Song ve History artık gerekli değilse kaldırılabilir
from collections import defaultdict
import logging # Loglama eklemek iyi olabilir

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.users = {}  # user_id: User object
        self.history = defaultdict(list)  # user_id: [song_ids] - Şarkı ID'lerini saklamak yeterli olabilir
        # self.initialize_data() # Örnek veriler kaldırıldı

    # def initialize_data(self):
    #     pass # Örnek veri yükleme kaldırıldı

    # def get_all_songs(self):
    #     pass # Örnek şarkı listesi kaldırıldı

    def get_user_history_ids(self, user_id):
        """
        Retrieves the listening history (song IDs) for a specific user.
        """
        return self.history.get(user_id, [])

    # def get_user_history(self, user_id):
        # Bu fonksiyon Song nesnelerine ihtiyaç duyuyordu, ID listesi döndürmek daha basit olabilir.
        # song_history = []
        # for song_id in self.history.get(user_id, []):
        #     song = self.get_song_by_id(song_id) # get_song_by_id artık yok
        #     if song:
        #         song_history.append(song)
        # return song_history

    def add_to_history(self, user_id, song_id):
        """
        Adds a song ID to the user's listening history.
        Prevents duplicates if needed.
        """
        if song_id not in self.history[user_id]:
             self.history[user_id].append(song_id)
             logger.debug(f"Song ID {song_id} added to history for user {user_id}")
        else:
             logger.debug(f"Song ID {song_id} already in history for user {user_id}")


    def add_user(self, user_id, username):
        """
        Adds a new user to the in-memory storage.
        """
        if user_id not in self.users:
            self.users[user_id] = User(user_id, username)
            logger.info(f"User {username} ({user_id}) added to local DB.")
        else:
             logger.debug(f"User {user_id} already exists in local DB.")

    def get_user(self, user_id):
        """
        Retrieves a user from the in-memory storage.
        """
        return self.users.get(user_id)

    # def get_song_by_id(self, song_id):
    #     pass # Örnek şarkı listesi kaldırıldığı için bu da kaldırıldı

    # def get_songs_by_genre(self, genre):
    #     pass # Örnek şarkı listesi kaldırıldığı için bu da kaldırıldı

    # def recommend_songs_based_on_history(self, user_id):
    #     pass # Öneri mantığı Spotify API'sine taşındığı için kaldırıldı
