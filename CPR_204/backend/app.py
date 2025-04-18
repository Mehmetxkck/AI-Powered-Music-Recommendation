import os
import random # Rastgele tür seçimi için eklendi
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials # Client Credentials eklendi
from spotipy import SpotifyException
# RecommendationEngine ve Database artık doğrudan öneri için kullanılmıyor.
# from recommendations import RecommendationEngine
# from database import Database
# from models import User # User modeli isteğe bağlı DB kullanımı için kalabilir
import logging

app = Flask(__name__)

# CORS ayarları
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}}, supports_credentials=True) # Frontend origin'inizi doğrulayın

# Logging ayarı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ortam değişkenleri ve varsayılan değerler
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "cok_gizli_bir_anahtar_olmalı")
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID", "8e881dd7d57947f79003b34d33557d07") # Kendi Client ID'nizi girin
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET", "6c5262493daf4ac38195c787e3808030") # Kendi Client Secret'ınızı girin
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5500") # Frontend'inizin çalıştığı ana URL (örn: index.html'in olduğu yer)
SPOTIPY_SCOPES = "user-read-recently-played user-top-read user-read-private user-read-email"

# Eksik ortam değişkenlerini kontrol et
if not all([SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI, FRONTEND_URL, app.secret_key]):
    logger.error("Eksik ortam değişkenleri veya Flask secret key!")
    if app.secret_key == "cok_gizli_bir_anahtar_olmalı":
        logger.warning("Varsayılan FLASK_SECRET_KEY kullanılıyor. Lütfen üretim ortamı için güvenli bir anahtar ayarlayın.")
    # exit(1) # Üretimde çıkış yap

# İsteğe bağlı: Veritabanı nesnesi
# from database import Database
# db = Database()

# Spotify OAuth (Kullanıcı Girişi İçin)
try:
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIPY_SCOPES,
        show_dialog=True
    )
except Exception as e:
    logger.error(f"SpotifyOAuth başlatılırken hata oluştu: {e}")
    exit(1)

# --- Client Credentials Manager (Genel API Erişimi İçin) ---
try:
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp_cc = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
    # Uygulama kimlik bilgileriyle mevcut türleri çekelim
    AVAILABLE_GENRE_SEEDS = sp_cc.recommendation_genre_seeds()['genres']
    logger.info(f"{len(AVAILABLE_GENRE_SEEDS)} adet kullanılabilir tür bulundu.")
except Exception as e:
    logger.error(f"Spotify Client Credentials başlatılırken veya türler çekilirken hata: {e}")
    AVAILABLE_GENRE_SEEDS = ['pop', 'rock', 'electronic', 'hip-hop', 'latin', 'jazz', 'classical', 'turkish pop'] # Fallback listesi

# --- Token Yardımcı Fonksiyonu ---
def get_token():
    token_info = session.get('token_info')
    if not token_info:
        logger.warning("Session'da token bilgisi bulunamadı.")
        return None

    # Token süresinin dolup dolmadığını kontrol et
    # Spotipy'nin is_token_expired metodu token_info sözlüğünü bekler
    if isinstance(token_info, dict) and sp_oauth.is_token_expired(token_info):
        logger.info("Spotify token süresi dolmuş, yenileniyor...")
        try:
            refresh_token = token_info.get('refresh_token')
            if not refresh_token:
                 raise ValueError("Refresh token bulunamadı.")
            # refresh_access_token metodu refresh_token string'ini bekler
            new_token_info = sp_oauth.refresh_access_token(refresh_token)
            session['token_info'] = new_token_info # Yenilenen token'ı session'a kaydet
            logger.info("Token başarıyla yenilendi.")
            return new_token_info # Yenilenmiş token bilgisini döndür
        except Exception as e:
            logger.error(f"Token yenilenirken hata oluştu: {e}. Kullanıcının tekrar giriş yapması gerekebilir.")
            session.pop('token_info', None)
            session.pop('user_data', None)
            return None # Yenileme başarısız oldu
    elif not isinstance(token_info, dict):
         logger.error(f"Session'daki token_info beklenen formatta değil: {type(token_info)}")
         session.pop('token_info', None)
         session.pop('user_data', None)
         return None

    return token_info # Token geçerliyse mevcut olanı döndür

# --- Rotalar ---
@app.route('/login')
def login():
    logger.info("Kullanıcı Spotify yetkilendirmesi için yönlendiriliyor.")
    try:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Spotify yetkilendirme URL'si alınırken hata: {e}")
        return jsonify({"error": "Spotify ile bağlantı kurulamadı."}), 500

@app.route('/callback')
def callback():
    logger.info("Spotify callback işleniyor.")
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        logger.error(f"Spotify yetkilendirme hatası: {error}")
        return redirect(f"{FRONTEND_URL}?error=spotify_auth_error")

    if not code:
        logger.error("Callback isteğinde 'code' parametresi eksik.")
        return redirect(f"{FRONTEND_URL}?error=missing_code")

    try:
        # Token'ı sözlük olarak al
        token_info = sp_oauth.get_access_token(code, as_dict=True, check_cache=False)
        if not token_info:
             raise Exception("Token alınamadı.")
        session['token_info'] = token_info
        logger.info("Spotify access token başarıyla alındı.")
        return redirect(url_for('get_user_data'))
    except Exception as e:
        logger.error(f"Token değişimi sırasında hata: {e}")
        return redirect(f"{FRONTEND_URL}?error=token_exchange_error")


@app.route('/get_user_data')
def get_user_data():
    logger.info("Spotify'dan kullanıcı verileri çekiliyor.")
    token_info = get_token()
    if not token_info:
        logger.warning("Kullanıcı verisi çekmek için geçerli token yok. Login sayfasına yönlendiriliyor.")
        # Token yoksa veya yenilenemediyse login'e yönlendir
        return redirect(url_for('login'))

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             raise ValueError("Access token bulunamadı.")

        sp = spotipy.Spotify(auth=access_token)
        user_data = sp.me()
        user_id = user_data['id']
        username = user_data.get('display_name', user_id)

        session['user_data'] = user_data
        logger.info(f"Kullanıcı bilgileri session'a kaydedildi: {username} ({user_id})")

        # İsteğe bağlı: Kullanıcıyı kendi veritabanına ekleme/güncelleme
        # ... (DB kodu) ...

        logger.info(f"Kullanıcı verileri başarıyla çekildi ve kaydedildi: {username}. Frontend'e yönlendiriliyor.")
        # Başarılı olursa frontend'e yönlendir
        return redirect(FRONTEND_URL)

    except SpotifyException as e:
        logger.error(f"Spotify API hatası (kullanıcı verisi çekme): {e}")
        # Token geçersiz veya yetki sorunu olabilir, session'ı temizleyip login'e yönlendir
        session.pop('token_info', None)
        session.pop('user_data', None)
        return redirect(f"{FRONTEND_URL}?error=spotify_api_error")
    except Exception as e:
        logger.error(f"Kullanıcı verisi çekme sırasında beklenmedik hata: {e}")
        return redirect(f"{FRONTEND_URL}?error=internal_error")

@app.route('/user_data')
def user_data():
    logger.debug("Session'daki kullanıcı verisi kontrol ediliyor.")
    token_info = get_token() # Token kontrolü (ve yenileme) burada da önemli
    user_data = session.get('user_data')

    if user_data and token_info:
        # Hem kullanıcı verisi hem de geçerli token varsa bilgiyi döndür
        logger.info(f"Mevcut kullanıcı verisi döndürülüyor: {user_data.get('display_name')}")
        return jsonify(user_data)
    else:
        # Kullanıcı verisi veya geçerli token yoksa giriş yapılması gerektiğini belirt
        logger.warning("Session'da geçerli kullanıcı verisi veya token bulunamadı.")
        return jsonify({"error": "Kullanıcı girişi gerekli.", "login_required": True}), 401


# --- YENİ ROTA: Başlangıç Önerileri ---
@app.route('/initial_recommendations')
def get_initial_recommendations():
    logger.info("Başlangıç için rastgele öneri isteği alındı.")
    recommendations_json = []
    try:
        # Rastgele 1-5 tür seç (Daha fazla çeşitlilik için)
        if not AVAILABLE_GENRE_SEEDS:
             logger.warning("Kullanılabilir tür listesi boş veya alınamadı. Fallback türler kullanılıyor.")
             # Daha geniş bir fallback listesi
             fallback_genres = ['pop', 'rock', 'electronic', 'hip-hop', 'latin', 'jazz', 'classical', 'turkish pop', 'r-n-b', 'indie', 'dance']
             num_seeds = random.randint(1, min(5, len(fallback_genres))) # En fazla 5 tür
             seed_genres = random.sample(fallback_genres, num_seeds)
        else:
            # 1 ile 5 arasında veya mevcut tür sayısı kadar seç
            num_seeds = random.randint(1, min(5, len(AVAILABLE_GENRE_SEEDS)))
            seed_genres = random.sample(AVAILABLE_GENRE_SEEDS, num_seeds)

        logger.info(f"Başlangıç önerileri için rastgele türler seçildi: {seed_genres}")

        # Client credentials ile önerileri al
        # Market parametresini test için yorum satırı yapabilirsin: market='TR'
        recommendations_data = sp_cc.recommendations(
            seed_genres=seed_genres,
            limit=10,
            market='TR'
        )

        # Sonucu JSON formatına çevir
        if recommendations_data and recommendations_data.get('tracks'):
            logger.info(f"Spotify'dan {len(recommendations_data['tracks'])} adet başlangıç önerisi bulundu.")
            for track in recommendations_data['tracks']:
                if track and track.get('id'):
                    album_art = None
                    if track.get('album') and isinstance(track['album'].get('images'), list) and track['album']['images']:
                        album_art = track['album']['images'][0]['url']

                    recommendations_json.append({
                        "_id": track['id'],
                        "title": track.get('name', 'N/A'),
                        "artist": ", ".join([artist.get('name', 'N/A') for artist in track.get('artists', [])]),
                        "album_art_url": album_art,
                        "spotify_url": track.get('external_urls', {}).get('spotify'),
                        "preview_url": track.get('preview_url'),
                    })
            logger.info(f"Başarıyla {len(recommendations_json)} adet başlangıç önerisi formatlandı.")
        else:
            logger.warning("Başlangıç önerileri için Spotify API'den geçerli öneri alınamadı.")
            # API'den geçerli veri gelmezse boş liste döndürülür.

        return jsonify(recommendations_json)

    except SpotifyException as e:
        # --- DÜZELTME BURADA ---
        # Hata durumunda status kodunu logla, e.url kaldırıldı.
        logger.error(f"Başlangıç önerileri alınırken Spotify API hatası: Status={e.http_status}, Code={e.code}, Msg={e.msg}")
        # Frontend'e daha genel bir hata mesajı gönder
        # 4xx hataları için ilgili status kodunu, diğerleri için 500 döndür
        error_status_code = e.http_status if e.http_status in [400, 401, 403, 404, 429] else 500
        return jsonify({"error": f"Başlangıç önerileri alınamadı (Spotify API Hatası)."}), error_status_code
    except Exception as e:
        # Beklenmedik hatalar için traceback'i logla
        logger.error(f"Başlangıç önerileri alınırken beklenmedik hata: {e}", exc_info=True)
        return jsonify({"error": "Başlangıç önerileri alınırken sunucu hatası oluştu."}), 500



# --- Mevcut /recommendations Rotası (Kullanıcı Geçmişine Göre) ---
@app.route('/recommendations', methods=['POST'])
def get_recommendations_api():
    logger.info("Geçmişe dayalı müzik önerisi isteği alındı.")
    token_info = get_token()
    if not token_info:
        logger.warning("Öneri isteği için geçerli token bulunamadı.")
        return jsonify({"error": "Yetkilendirme gerekli. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_data = session.get('user_data')
    if not user_data or not user_data.get('id'):
        logger.error("Öneri isteği sırasında session'da geçerli kullanıcı verisi bulunamadı!")
        return jsonify({"error": "Oturum hatası veya geçersiz kullanıcı verisi. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_id = user_data['id']

    logger.info(f"Kullanıcı ID: {user_id} için Spotify'dan öneriler hazırlanıyor.")

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             raise ValueError("Access token bulunamadı.")
        sp = spotipy.Spotify(auth=access_token)

        # 1. Spotify'dan "seed" (tohum) verileri çek
        seed_tracks = []
        seed_artists = []
        seed_genres = []
        using_default_seeds = False # Varsayılan seed kullanılıp kullanılmadığını takip etmek için flag

        try:
            # En çok dinlenen şarkıları al
            top_tracks = sp.current_user_top_tracks(limit=5, time_range='short_term')
            if top_tracks and top_tracks.get('items'):
                seed_tracks = [track['id'] for track in top_tracks['items']]
                logger.info(f"Seed için {len(seed_tracks)} adet top track ID'si bulundu.")
                # Türleri de ekleyelim (limit dahilinde)
                for track in top_tracks['items']:
                    if len(seed_tracks) + len(seed_artists) + len(seed_genres) < 5:
                        try:
                            artist_id = track['artists'][0]['id']
                            artist_info = sp.artist(artist_id)
                            if artist_info and artist_info.get('genres'):
                                potential_genres = list(set(seed_genres + artist_info['genres']))
                                seed_genres = potential_genres[:5 - len(seed_tracks) - len(seed_artists)]
                        except IndexError:
                             logger.warning(f"Şarkı {track.get('id')} için sanatçı bilgisi bulunamadı.")
                        except SpotifyException as artist_e:
                             logger.warning(f"Sanatçı {artist_id} için tür bilgisi alınamadı: {artist_e}")

            # Yeterli şarkı yoksa sanatçıları al
            if len(seed_tracks) + len(seed_artists) + len(seed_genres) < 5:
                artist_limit = 5 - len(seed_tracks) - len(seed_genres)
                if artist_limit > 0:
                    top_artists = sp.current_user_top_artists(limit=artist_limit, time_range='short_term')
                    if top_artists and top_artists.get('items'):
                        new_artist_ids = [artist['id'] for artist in top_artists['items']]
                        seed_artists.extend(new_artist_ids)
                        logger.info(f"Seed için {len(new_artist_ids)} adet top artist ID'si eklendi.")
                        for artist in top_artists['items']:
                             if artist.get('genres') and len(seed_tracks) + len(seed_artists) + len(seed_genres) < 5:
                                 potential_genres = list(set(seed_genres + artist['genres']))
                                 seed_genres = potential_genres[:5 - len(seed_tracks) - len(seed_artists)]

            # Hiç kişisel seed bulunamadıysa, varsayılan türleri kullan
            if not seed_tracks and not seed_artists and not seed_genres:
                 logger.warning(f"Kullanıcı {user_id} için kişisel seed bulunamadı. Varsayılan popüler türler kullanılacak.")
                 if not AVAILABLE_GENRE_SEEDS:
                      logger.warning("Kullanılabilir tür listesi boş. Fallback türler kullanılıyor.")
                      seed_genres = ['pop', 'rock', 'electronic'] # Fallback
                 else:
                      num_seeds = min(5, len(AVAILABLE_GENRE_SEEDS)) # En fazla 5 tür
                      seed_genres = random.sample(AVAILABLE_GENRE_SEEDS, num_seeds)
                 using_default_seeds = True

            # Seed sayısını tekrar kontrol et
            seed_tracks = seed_tracks[:5]
            seed_artists = seed_artists[:5-len(seed_tracks)]
            seed_genres = seed_genres[:5-len(seed_tracks)-len(seed_artists)]

            logger.info(f"Kullanılacak Seed'ler - Tracks: {seed_tracks}, Artists: {seed_artists}, Genres: {seed_genres}")

        except SpotifyException as e:
            logger.error(f"Spotify'dan seed verisi çekilemedi (Kullanıcı: {user_id}): {e}")
            return jsonify({"error": f"Spotify dinleme geçmişinize erişirken bir sorun oluştu: {e.msg}", "login_required": e.http_status == 401}), e.http_status if e.http_status in [401, 429] else 500
        except Exception as e:
            logger.error(f"Seed verilerini işlerken beklenmedik hata (Kullanıcı: {user_id}): {e}")
            return jsonify({"error": "Dinleme geçmişiniz işlenirken beklenmedik bir hata oluştu."}), 500

        # 3. Spotify'dan önerileri al
        recommendations_data = None
        try:
            logger.info("Spotify recommendations API çağrılıyor...")
            recommendations_data = sp.recommendations(
                seed_tracks=seed_tracks if seed_tracks else None,
                seed_artists=seed_artists if seed_artists else None,
                seed_genres=seed_genres if seed_genres else None,
                limit=20,
                country='TR'
            )
            logger.info("Spotify recommendations API'den cevap alındı.")

        except SpotifyException as e:
             logger.error(f"Spotify recommendations API hatası (Kullanıcı: {user_id}): {e}")
             if e.http_status == 401:
                 return jsonify({"error": "Spotify yetkilendirme hatası. Lütfen tekrar giriş yapın.", "login_required": True}), 401
             elif e.http_status == 429:
                 return jsonify({"error": "Çok fazla istek yapıldı. Lütfen biraz bekleyip tekrar deneyin."}), 429
             elif e.http_status == 400 or e.http_status == 404:
                 logger.warning(f"Spotify API {e.http_status} hatası (muhtemelen geçersiz seed): {e.msg}")
                 error_message = "Öneriler alınırken bir sorun oluştu."
                 if using_default_seeds:
                     error_message += " Varsayılan türlerle bile öneri alınamadı."
                 else:
                     error_message = "Öneri oluşturmak için yeterli veya geçerli dinleme verisi bulunamadı. Spotify'da daha fazla müzik dinleyin."
                 return jsonify({"error": error_message}), 400
             else:
                 return jsonify({"error": f"Spotify'dan öneri alınamadı: {e.msg}"}), 500
        except Exception as e:
             logger.error(f"Spotify önerileri alınırken beklenmedik hata: {e}")
             return jsonify({"error": "Öneriler alınırken beklenmedik bir sunucu hatası oluştu."}), 500


        # 4. Sonucu JSON formatına çevir
        recommendations_json = []
        if recommendations_data and recommendations_data.get('tracks'):
            logger.info(f"Spotify'dan {len(recommendations_data['tracks'])} adet öneri bulundu.")
            for track in recommendations_data['tracks']:
                if track and track.get('id'):
                    album_art = None
                    if track.get('album') and isinstance(track['album'].get('images'), list) and track['album']['images']:
                        album_art = track['album']['images'][0]['url']

                    recommendations_json.append({
                        "_id": track['id'],
                        "title": track.get('name', 'N/A'),
                        "artist": ", ".join([artist.get('name', 'N/A') for artist in track.get('artists', [])]),
                        "album_art_url": album_art,
                        "spotify_url": track.get('external_urls', {}).get('spotify'),
                        "preview_url": track.get('preview_url'),
                    })
            logger.info(f"Başarıyla {len(recommendations_json)} adet gerçek şarkı önerisi formatlandı.")
        else:
            logger.warning("Spotify API'den geçerli öneri alınamadı veya 'tracks' anahtarı bulunamadı.")

        # Yanıtı oluştur
        response_payload = {"recommendations": recommendations_json}
        if using_default_seeds:
            response_payload["message"] = "Dinleme geçmişiniz yetersiz olduğu için genel popüler türlere göre öneriler gösterilmektedir."

        return jsonify(response_payload)


    except Exception as e:
        # Genel hata yakalama
        logger.exception(f"Öneri oluşturma sırasında kritik hata oluştu (Kullanıcı: {user_id}): {e}")
        return jsonify({"error": "Öneriler oluşturulurken sunucu hatası oluştu.", "details": str(e)}), 500


if __name__ == '__main__':
    # Debug modunu ortam değişkeninden almak daha iyi olabilir
    # DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=True, port=5000)
