import uuid

# Song sınıfı artık database.py'de kullanılmıyor,
# eğer başka bir yerde de kullanılmıyorsa kaldırılabilir.
# class Song:
#     def __init__(self, title, artist, mood, genre, _id=None):
#         self.title = title
#         self.artist = artist
#         self.mood = mood
#         self.genre = genre
#         self._id = _id if _id else str(uuid.uuid4())

class User:
    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

# History sınıfı kullanılmıyordu, kaldırıldı.
# class History:
#     def __init__(self, user_id, song):
#         self.user_id = user_id
#         self.song = song
