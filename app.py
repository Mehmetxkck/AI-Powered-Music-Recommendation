import os
import random # Rastgele tür seçimi için eklendi
import traceback # Hata ayıklama için eklendi
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials # Client Credentials eklendi
from spotipy import SpotifyException
import logging
from urllib.parse import quote_plus # URL encoding için eklendi


app = Flask(__name__)

# CORS ayarları
# Geliştirme ortamı için frontend'in çalıştığı adresi belirtin.
# Üretimde daha kısıtlı bir origin listesi kullanın.
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}}, supports_credentials=True)

# Logging ayarı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# --- Ortam Değişkenleri ve Yapılandırma ---
# Güvenli bir secret key kullanın ve ortam değişkeninden alınması önerilir.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "123!@#") # Geliştirme için geçici, üretimde değiştirin!
# --- GÜVENLİK UYARISI: Gizli bilgileri kod içinde hardcode ETME! Sadece ortam değişkenlerinden al. ---
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID","8e881dd7d57947f79003b34d33557d07") # Kendi ID'nizi girin veya ortam değişkeni kullanın
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET","6c5262493daf4ac38195c787e3808030") # Kendi Secret'ınızı girin veya ortam değişkeni kullanın
# -------------------------------------------------------------------------------------------------
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5500/frontend/") # Frontend'in çalıştığı adres

# --- YENİ SCOPE'LAR EKLENDİ ---
SPOTIPY_SCOPES = "user-read-recently-played user-top-read user-read-private user-read-email playlist-modify-public playlist-modify-private"

# Eksik ortam değişkenlerini kontrol et
missing_vars = []
if not SPOTIPY_CLIENT_ID: missing_vars.append("SPOTIPY_CLIENT_ID")
if not SPOTIPY_CLIENT_SECRET: missing_vars.append("SPOTIPY_CLIENT_SECRET")

if app.secret_key == "123!@#":
    logger.warning("Varsayılan FLASK_SECRET_KEY kullanılıyor. Lütfen üretim ortamı için güvenli bir anahtar ayarlayın (FLASK_SECRET_KEY ortam değişkeni).")

if missing_vars:
    logger.critical(f"Kritik ortam değişkenleri eksik: {', '.join(missing_vars)}. Uygulama başlatılamıyor.")
    logger.critical("Lütfen SPOTIPY_CLIENT_ID ve SPOTIPY_CLIENT_SECRET ortam değişkenlerini ayarlayın.")
    exit(1)

# --- Spotify İstemcileri ---
sp_oauth = None
sp_cc = None
AVAILABLE_GENRE_SEEDS = ['pop', 'rock', 'electronic', 'hip-hop', 'latin', 'jazz', 'classical', 'turkish pop', 'r-n-b', 'indie', 'dance', 'metal', 'alternative', 'acoustic', 'chill', 'country', 'funk', 'reggae', 'soul'] # Başlangıç için varsayılan liste

try:
    # Spotify OAuth (Kullanıcı Girişi İçin)
    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIPY_SCOPES,
        show_dialog=True # Her seferinde yetki ekranını gösterir (geliştirme için kullanışlı)
    )

    # Spotify Client Credentials (Genel API Erişimi İçin)
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp_cc = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    logger.info(f"Statik tür listesi kullanılıyor ({len(AVAILABLE_GENRE_SEEDS)} adet).")

except SpotifyException as e:
    logger.error(f"Spotify istemcisi başlatılırken Spotify API hatası: {e}")
    logger.error("Lütfen SPOTIPY_CLIENT_ID ve SPOTIPY_CLIENT_SECRET değerlerinin doğru olduğundan emin olun.")
    exit(1)
except Exception as e:
    logger.error(f"Spotify istemcisi başlatılırken beklenmedik hata: {e}", exc_info=True)
    exit(1)


# --- Token Yardımcı Fonksiyonu ---
def get_token():
    """
    Session'dan token bilgisini alır. Süresi dolmuşsa yenilemeye çalışır.
    Başarısız olursa veya token yoksa None döner.
    """
    token_info = session.get('token_info')
    if not token_info:
        logger.debug("Session'da token bilgisi bulunamadı.")
        return None

    if not isinstance(token_info, dict) or 'access_token' not in token_info:
        logger.error(f"Session'daki token_info beklenen formatta değil veya access_token eksik: {token_info}")
        session.pop('token_info', None)
        session.pop('user_data', None)
        return None

    try:
        if sp_oauth.is_token_expired(token_info):
            logger.info("Spotify token süresi dolmuş, yenileniyor...")
            refresh_token = token_info.get('refresh_token')
            if not refresh_token:
                 logger.error("Token yenilemek için refresh_token bulunamadı. Kullanıcının tekrar giriş yapması gerekiyor.")
                 session.pop('token_info', None)
                 session.pop('user_data', None)
                 return None

            new_token_info = sp_oauth.refresh_access_token(refresh_token)
            session['token_info'] = new_token_info
            logger.info("Token başarıyla yenilendi.")
            return new_token_info
        else:
            logger.debug("Mevcut token hala geçerli.")
            return token_info

    except SpotifyException as e:
        logger.error(f"Token yenilenirken Spotify API hatası: {e}. Kullanıcının tekrar giriş yapması gerekebilir.")
        session.pop('token_info', None)
        session.pop('user_data', None)
        return None
    except Exception as e:
        logger.error(f"Token yenilenirken beklenmedik hata: {e}", exc_info=True)
        session.pop('token_info', None)
        session.pop('user_data', None)
        return None

# --- Rotalar ---
@app.route('/')
def index():
    return jsonify({"message": "Spotify Recommendation API Backend", "status": "running"})

@app.route('/login')
def login():
    logger.info("Kullanıcı Spotify yetkilendirmesi için yönlendiriliyor.")
    if not sp_oauth:
        logger.error("Spotify OAuth nesnesi başlatılamadı.")
        return jsonify({"error": "Sunucu yapılandırma hatası."}), 500
    try:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Spotify yetkilendirme URL'si alınırken hata: {e}", exc_info=True)
        return jsonify({"error": "Spotify ile bağlantı kurulamadı."}), 500


@app.route('/callback')
def callback():
    logger.info("Spotify callback işleniyor.")
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        logger.error(f"Spotify yetkilendirme hatası: {error}")
        # Hata mesajını URL encode et
        safe_message = quote_plus(str(error))
        return redirect(f"{FRONTEND_URL}?error=spotify_auth_error&message={safe_message}")

    if not code:
        logger.error("Callback isteğinde 'code' parametresi eksik.")
        return redirect(f"{FRONTEND_URL}?error=missing_code")

    if not sp_oauth:
        logger.error("Spotify OAuth nesnesi başlatılamadı.")
        return redirect(f"{FRONTEND_URL}?error=server_config_error")

    try:
        token_info = sp_oauth.get_access_token(code, check_cache=False)

        if not token_info or not isinstance(token_info, dict) or 'access_token' not in token_info:
             logger.error(f"Token alınamadı veya geçersiz format: {token_info}")
             return redirect(f"{FRONTEND_URL}?error=token_exchange_failed")

        session['token_info'] = token_info
        logger.info("Spotify access token başarıyla alındı ve session'a kaydedildi.")
        return redirect(url_for('fetch_and_store_user_data'))
    except SpotifyException as e:
        logger.error(f"Token değişimi sırasında Spotify API hatası: {e}")
        # Hata mesajını URL encode et
        safe_message = quote_plus(str(e.msg))
        return redirect(f"{FRONTEND_URL}?error=token_exchange_error&message={safe_message}")
    except Exception as e:
        logger.error(f"Token değişimi sırasında beklenmedik hata: {e}", exc_info=True)
        # Genel hata mesajını URL encode et (içeriği bilinmediği için)
        safe_message = quote_plus("Bilinmeyen bir hata oluştu.")
        return redirect(f"{FRONTEND_URL}?error=token_exchange_error&message={safe_message}")


@app.route('/fetch_and_store_user_data')
def fetch_and_store_user_data():
    logger.info("Spotify'dan kullanıcı verileri çekiliyor ve session'a kaydediliyor.")
    token_info = get_token()
    if not token_info:
        logger.warning("Kullanıcı verisi çekmek için geçerli token yok. Login gerekli.")
        return redirect(f"{FRONTEND_URL}?error=authentication_required")

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             logger.error("Token bilgisinde access_token bulunamadı.")
             session.pop('token_info', None)
             session.pop('user_data', None)
             return redirect(f"{FRONTEND_URL}?error=internal_error_token")

        sp = spotipy.Spotify(auth=access_token)
        user_data = sp.me()
        if not user_data or 'id' not in user_data:
             logger.error(f"Spotify API'den geçerli kullanıcı verisi alınamadı: {user_data}")
             return redirect(f"{FRONTEND_URL}?error=spotify_user_data_error")

        user_id = user_data['id']
        username = user_data.get('display_name', user_id)

        session['user_data'] = user_data
        logger.info(f"Kullanıcı bilgileri session'a kaydedildi: {username} ({user_id})")

        logger.info(f"Kullanıcı verileri başarıyla çekildi. Frontend'e yönlendiriliyor: {FRONTEND_URL}")
        return redirect(FRONTEND_URL)

    except SpotifyException as e:
        logger.error(f"Spotify API hatası (kullanıcı verisi çekme): {e}")
        session.pop('token_info', None)
        session.pop('user_data', None)
        error_code = "spotify_api_error"
        if e.http_status == 401 or e.http_status == 403:
            error_code = "authentication_required"
        # Hata mesajını URL encode et
        safe_message = quote_plus(str(e.msg))
        return redirect(f"{FRONTEND_URL}?error={error_code}&message={safe_message}")
    except Exception as e:
        logger.error(f"Kullanıcı verisi çekme sırasında beklenmedik hata: {e}", exc_info=True)
        session.pop('token_info', None)
        session.pop('user_data', None)
        # Genel hata mesajını URL encode et
        safe_message = quote_plus("Sunucuda beklenmedik bir hata oluştu.")
        return redirect(f"{FRONTEND_URL}?error=internal_server_error&message={safe_message}")


@app.route('/user_data')
def get_user_data_from_session():
    logger.debug("Session'daki kullanıcı verisi kontrol ediliyor.")
    token_info = get_token()
    user_data = session.get('user_data')

    if user_data and token_info:
        username = user_data.get('display_name', user_data.get('id', 'N/A'))
        logger.info(f"Mevcut kullanıcı verisi döndürülüyor: {username}")
        return jsonify(user_data)
    elif user_data and not token_info:
        logger.warning("Kullanıcı verisi var ama token geçersiz/yenilenemedi. Tekrar giriş gerekli.")
        session.pop('user_data', None)
        return jsonify({"error": "Oturum süresi doldu. Lütfen tekrar giriş yapın.", "login_required": True}), 401
    else:
        logger.info("Session'da geçerli kullanıcı verisi veya token bulunamadı. Giriş gerekli.")
        return jsonify({"error": "Kullanıcı girişi gerekli.", "login_required": True}), 401


@app.route('/logout')
def logout():
    user_id = session.get('user_data', {}).get('id', 'Bilinmeyen Kullanıcı')
    logger.info(f"Kullanıcı {user_id} oturumu sonlandırılıyor.")
    session.pop('token_info', None)
    session.pop('user_data', None)
    return jsonify({"message": "Başarıyla çıkış yapıldı."})


# --- Öneri Rotaları (Search Endpoint'i Kullanarak Güncellendi) ---


@app.route('/recommendations', methods=['POST'])
def get_recommendations_for_user():
    logger.info("Geçmişe dayalı müzik arama isteği alındı.")
    token_info = get_token()
    if not token_info:
        logger.warning("Arama isteği için geçerli token bulunamadı. Giriş gerekli.")
        return jsonify({"error": "Yetkilendirme gerekli. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_data = session.get('user_data')
    if not user_data or not user_data.get('id'):
        logger.error("Arama isteği sırasında session'da geçerli kullanıcı verisi bulunamadı!")
        session.pop('token_info', None); session.pop('user_data', None)
        return jsonify({"error": "Oturum hatası veya geçersiz kullanıcı verisi. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_id = user_data['id']
    logger.info(f"Kullanıcı ID: {user_id} için Spotify'dan arama sonuçları hazırlanıyor.")

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             logger.error(f"Kullanıcı {user_id} için access_token alınamadı.")
             session.pop('token_info', None); session.pop('user_data', None)
             return jsonify({"error": "Oturum hatası (token alınamadı). Lütfen tekrar giriş yapın.", "login_required": True}), 401
        sp = spotipy.Spotify(auth=access_token)

        # 1. Arama için ipucu verileri çek
        search_query = None
        query_basis = "rastgele popüler türler"

        try:
            logger.debug(f"Kullanıcı {user_id} için top artists çekiliyor...")
            top_artists_data = sp.current_user_top_artists(limit=5, time_range='short_term')
            if top_artists_data and top_artists_data.get('items'):
                top_artists = [artist for artist in top_artists_data['items'] if artist and artist.get('name')]
                if top_artists:
                    selected_artist = top_artists[0]['name']
                    search_query = f"{selected_artist}"
                    query_basis = f"en çok dinlenen sanatçı ({selected_artist})"
                    logger.info(f"Arama için en çok dinlenen sanatçı bulundu: {selected_artist}")

            if not search_query:
                logger.debug(f"Kullanıcı {user_id} için top tracks çekiliyor...")
                top_tracks_data = sp.current_user_top_tracks(limit=5, time_range='short_term')
                if top_tracks_data and top_tracks_data.get('items'):
                    track_ids = [track['id'] for track in top_tracks_data['items'] if track and track.get('id')]
                    if track_ids:
                        first_track_details = sp.track(track_ids[0])
                        if first_track_details and first_track_details.get('artists'):
                            first_artist_id = first_track_details['artists'][0]['id']
                            if first_artist_id:
                                artist_details = sp.artist(first_artist_id)
                                if artist_details and artist_details.get('genres'):
                                    selected_genre = random.choice(artist_details['genres'])
                                    search_query = f"{selected_genre} music"
                                    query_basis = f"en çok dinlenen şarkının türü ({selected_genre})"
                                    logger.info(f"Arama için en çok dinlenen şarkının türü bulundu: {selected_genre}")
                                elif artist_details and artist_details.get('name'):
                                     selected_artist = artist_details['name']
                                     search_query = f"{selected_artist}"
                                     query_basis = f"en çok dinlenen şarkının sanatçısı ({selected_artist})"
                                     logger.info(f"Arama için en çok dinlenen şarkının sanatçısı bulundu: {selected_artist}")

            if not search_query:
                 logger.warning(f"Kullanıcı {user_id} için kişisel arama ipucu bulunamadı. Rastgele popüler türler kullanılacak.")
                 if not AVAILABLE_GENRE_SEEDS:
                      logger.error("Kullanılabilir tür listesi boş! Varsayılan arama yapılamıyor.")
                      return jsonify({"error": "Arama yapmak için yeterli veri veya yapılandırma bulunamadı."}), 500
                 else:
                      selected_genre = random.choice(AVAILABLE_GENRE_SEEDS)
                      search_query = f"{selected_genre} music"
                      query_basis = f"rastgele popüler tür ({selected_genre})"
                      logger.info(f"Varsayılan arama türü seçildi: {selected_genre}")

            logger.info(f"Kullanılacak Arama Sorgusu: '{search_query}' (Kaynak: {query_basis})")

        except SpotifyException as e:
            logger.error(f"Spotify'dan arama ipucu verisi çekilemedi (Kullanıcı: {user_id}): {e}")
            error_status = e.http_status if e.http_status in [401, 403, 429] else 500
            login_req = error_status in [401, 403]
            if login_req: session.pop('token_info', None); session.pop('user_data', None)
            # Hata mesajını JSON içinde güvenli hale getir
            safe_details = quote_plus(str(e.msg))
            return jsonify({"error": f"Spotify dinleme geçmişinize erişirken bir sorun oluştu.", "details": safe_details, "login_required": login_req}), error_status
        except Exception as e:
            logger.error(f"Arama ipucu verilerini işlerken beklenmedik hata (Kullanıcı: {user_id}): {e}", exc_info=True)
            return jsonify({"error": "Dinleme geçmişiniz işlenirken beklenmedik bir hata oluştu."}), 500

        # 2. Spotify'dan arama sonuçlarını al
        search_results = None
        try:
            logger.info("Spotify search API çağrılıyor...")
            # Daha fazla çeşitlilik için daha fazla sonuç isteyelim (örn: 50)
            search_limit = 50
            logger.debug(f"Params - q: '{search_query}', type: 'track', limit: {search_limit}")
            search_results = sp.search(
                q=search_query,
                type='track',
                limit=search_limit,
                #market='TR' # Pazar belirtmek sonuçları iyileştirebilir
            )
            logger.info("Spotify search API'den cevap alındı.")

        except SpotifyException as e:
             logger.error(f"Spotify search API hatası (Kullanıcı: {user_id}): Status={e.http_status}, Code={e.code}, Msg={e.msg}")
             status_code = e.http_status if e.http_status in [400, 401, 403, 404, 429] else 500
             login_req = status_code in [401, 403]
             if login_req: session.pop('token_info', None); session.pop('user_data', None)
             error_msg = "Spotify'dan arama sonucu alınamadı."
             if status_code == 400: error_msg = "Arama sorgusu oluşturulurken bir sorun oluştu."
             elif status_code == 401 or status_code == 403: error_msg = "Spotify yetkilendirme hatası. Lütfen tekrar giriş yapın."
             elif status_code == 404: error_msg = "Arama yapılırken bir sorun oluştu (Kaynak bulunamadı - Spotify API sorunu olabilir)."
             elif status_code == 429: error_msg = "Çok fazla istek yapıldı. Lütfen biraz bekleyip tekrar deneyin."
             # Hata mesajını JSON içinde güvenli hale getir
             safe_details = quote_plus(str(e.msg))
             return jsonify({"error": error_msg, "details": safe_details, "login_required": login_req}), status_code
        except Exception as e:
             logger.error(f"Spotify arama sonuçları alınırken beklenmedik hata (Kullanıcı: {user_id}): {e}", exc_info=True)
             return jsonify({"error": "Arama sonuçları alınırken beklenmedik bir sunucu hatası oluştu."}), 500

        # 3. Sonucu JSON formatına çevir
        recommendations_json = []
        if search_results and search_results.get('tracks') and search_results['tracks'].get('items'):
            all_tracks = search_results['tracks']['items']
            logger.info(f"Spotify aramasından {len(all_tracks)} adet potansiyel sonuç bulundu.")
            # Alınan sonuçlardan rastgele bir alt küme seçelim (örn: 10 tane)
            sample_size = min(12, len(all_tracks)) # En fazla 10 veya bulunan şarkı sayısı kadar
            selected_tracks = random.sample(all_tracks, sample_size) if all_tracks else []
            logger.info(f"Rastgele {len(selected_tracks)} adet sonuç seçildi.")

            for track in selected_tracks:
                 if track and track.get('id'):
                    album_art = None
                    if track.get('album') and isinstance(track['album'].get('images'), list) and track['album']['images']:
                        images = track['album']['images']
                        # Orta boy resmi tercih et (genellikle index 1), yoksa ilkini al
                        album_art = images[1]['url'] if len(images) > 1 else images[0]['url']

                    recommendations_json.append({
                        "id": track['id'],
                        "title": track.get('name', 'N/A'),
                        "artist": ", ".join([artist.get('name', 'N/A') for artist in track.get('artists', []) if artist]),
                        "album_art_url": album_art,
                        "spotify_url": track.get('external_urls', {}).get('spotify'),
                        #"preview_url": track.get('preview_url'), # Önizleme URL'si eklendi
                    })
            logger.info(f"Başarıyla {len(recommendations_json)} adet rastgele seçilmiş sonuç formatlandı.")
        else:
            logger.warning(f"Kullanıcı {user_id} için Spotify API aramasından geçerli sonuç ('tracks'/'items') alınamadı veya boş döndü.")

        response_payload = {"recommendations": recommendations_json}
        response_payload["message"] = f"Sonuçlar '{query_basis}' baz alınarak yapılan aramaya göre gösterilmektedir."
        if not recommendations_json:
             response_payload["message"] += " Bu aramaya uygun sonuç bulunamadı."

        return jsonify(response_payload)

    except Exception as e:
        logger.exception(f"Kişisel arama sırasında kritik hata oluştu (Kullanıcı: {user_id}): {e}")
        return jsonify({"error": "Sonuçlar oluşturulurken beklenmedik bir sunucu hatası oluştu."}), 500

# --- YENİ ROTALAR ---

@app.route('/playlists')
def get_user_playlists():
    """Kullanıcının Spotify playlist'lerini listeler."""
    logger.info("Kullanıcı playlist'leri isteği alındı.")
    token_info = get_token()
    if not token_info:
        return jsonify({"error": "Yetkilendirme gerekli.", "login_required": True}), 401
    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlists = sp.current_user_playlists(limit=50) # Daha fazla playlist için limit artırılabilir
        user_playlists = [{"id": pl['id'], "name": pl['name']} for pl in playlists.get('items', []) if pl] # Şimdilik tümünü al
        logger.info(f"{len(user_playlists)} adet playlist bulundu.")
        return jsonify(user_playlists)
    except SpotifyException as e:
        logger.error(f"Kullanıcı playlist'leri alınırken hata: {e}")
        status_code = e.http_status if e.http_status in [401, 403] else 500
        login_req = status_code in [401, 403]
        if login_req: session.pop('token_info', None); session.pop('user_data', None)
        # Hata mesajını JSON içinde güvenli hale getir
        safe_details = quote_plus(str(e.msg))
        return jsonify({"error": "Playlistler alınamadı.", "details": safe_details, "login_required": login_req}), status_code
    except Exception as e:
        logger.error(f"Playlist alırken beklenmedik hata: {e}", exc_info=True)
        return jsonify({"error": "Sunucu hatası."}), 500

@app.route('/playlist/add', methods=['POST'])
def add_track_to_playlist():
    """Belirtilen şarkıyı belirtilen playlist'e ekler."""
    logger.info("Playlist'e şarkı ekleme isteği alındı.")
    token_info = get_token()
    if not token_info:
        return jsonify({"error": "Yetkilendirme gerekli.", "login_required": True}), 401

    data = request.get_json()
    playlist_id = data.get('playlist_id')
    track_uri_or_id = data.get('track_uri') # Frontend track ID veya URI gönderebilir

    if not playlist_id or not track_uri_or_id:
        logger.warning("Eksik bilgi: playlist_id ve track_uri gerekli.")
        return jsonify({"error": "Eksik bilgi: playlist_id ve track_uri gerekli."}), 400

    # Track ID'yi URI formatına çevir (eğer ID geldiyse)
    if not track_uri_or_id.startswith('spotify:track:'):
         track_uri = f'spotify:track:{track_uri_or_id}'
    else:
         track_uri = track_uri_or_id

    logger.debug(f"Şarkı {track_uri} playlist {playlist_id}'ye ekleniyor...")
    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        sp.playlist_add_items(playlist_id, [track_uri])
        logger.info(f"Şarkı {track_uri}, playlist {playlist_id}'ye başarıyla eklendi.")
        return jsonify({"message": "Şarkı başarıyla playlist'e eklendi!"})
    except SpotifyException as e:
        logger.error(f"Playlist'e şarkı eklenirken hata: {e}")
        status_code = e.http_status if e.http_status in [400, 401, 403, 404] else 500
        login_req = status_code in [401, 403]
        if login_req: session.pop('token_info', None); session.pop('user_data', None)
        error_msg = "Şarkı eklenemedi."
        if status_code == 403: error_msg = "Bu playlist'e şarkı ekleme izniniz yok veya scope eksik."
        if status_code == 404: error_msg = "Playlist veya şarkı bulunamadı."
        if status_code == 400: error_msg = "Geçersiz istek (örn: şarkı zaten playlist'te olabilir)."
        # Hata mesajını JSON içinde güvenli hale getir
        safe_details = quote_plus(str(e.msg))
        return jsonify({"error": error_msg, "details": safe_details, "login_required": login_req}), status_code
    except Exception as e:
        logger.error(f"Playlist'e eklerken beklenmedik hata: {e}", exc_info=True)
        return jsonify({"error": "Sunucu hatası."}), 500

@app.route('/profile')
def get_user_profile():
    """Kullanıcının profil bilgilerini (top artist/track/genre) döndürür."""
    logger.info("Kullanıcı profili isteği alındı.")
    token_info = get_token()
    if not token_info:
        return jsonify({"error": "Yetkilendirme gerekli.", "login_required": True}), 401

    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        time_range = 'medium_term' # Orta vade (son ~6 ay) - 'short_term' veya 'long_term' de olabilir

        logger.debug(f"Profil için {time_range} verileri çekiliyor...")
        top_artists = sp.current_user_top_artists(limit=10, time_range=time_range)
        top_tracks = sp.current_user_top_tracks(limit=10, time_range=time_range)

        # Türleri sanatçılardan türet
        top_genres = {}
        if top_artists and top_artists.get('items'):
            for artist in top_artists['items']:
                if artist and artist.get('genres'):
                    for genre in artist['genres']:
                        top_genres[genre] = top_genres.get(genre, 0) + 1
        # Türe göre sıklığa göre sırala
        sorted_genres = sorted(top_genres.items(), key=lambda item: item[1], reverse=True)[:10] # İlk 10 tür

        profile_data = {
            "user": session.get('user_data', {}), # Temel kullanıcı bilgisi
            "top_artists": top_artists.get('items', []),
            "top_tracks": top_tracks.get('items', []),
            "top_genres": sorted_genres
        }
        logger.info("Profil verileri başarıyla çekildi.")
        return jsonify(profile_data)

    except SpotifyException as e:
         logger.error(f"Profil verisi alınırken hata: {e}")
         status_code = e.http_status if e.http_status in [401, 403] else 500
         login_req = status_code in [401, 403]
         if login_req: session.pop('token_info', None); session.pop('user_data', None)
         # Hata mesajını JSON içinde güvenli hale getir
         safe_details = quote_plus(str(e.msg))
         return jsonify({"error": "Profil verileri alınamadı.", "details": safe_details, "login_required": login_req}), status_code
    except Exception as e:
         logger.error(f"Profil alırken beklenmedik hata: {e}", exc_info=True)
         return jsonify({"error": "Sunucu hatası."}), 500

# --- Uygulama Başlatma ---
if __name__ == '__main__':
    logger.info("Flask uygulaması başlatılıyor...")
    # Geliştirme sırasında debug=True kullanışlıdır, ancak üretimde False olmalıdır.
    # host='0.0.0.0' ağdaki diğer cihazlardan erişim için kullanılabilir.
    app.run(debug=True, host='127.0.0.1', port=5000)
# logger.info("Flask uygulaması başarıyla başlatıldı.") # Bu satır app.run() sonrasına gelmez
