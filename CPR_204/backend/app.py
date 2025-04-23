import os
import random # Rastgele tür seçimi için eklendi
import traceback # Hata ayıklama için eklendi
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
# Geliştirme ortamı için frontend'in çalıştığı adresi belirtin.
# Üretimde daha kısıtlı bir origin listesi kullanın.
CORS(app, resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}}, supports_credentials=True)

# Logging ayarı
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# --- Ortam Değişkenleri ve Yapılandırma ---
# Güvenli bir secret key kullanın ve ortam değişkeninden alınması önerilir.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "123!@#")
# --- GÜVENLİK UYARISI: Gizli bilgileri kod içinde hardcode ETME! Sadece ortam değişkenlerinden al. ---
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID","8e881dd7d57947f79003b34d33557d07")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET","6c5262493daf4ac38195c787e3808030")
# -------------------------------------------------------------------------------------------------
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5500") # Frontend'in çalıştığı adres
SPOTIPY_SCOPES = "user-read-recently-played user-top-read user-read-private user-read-email"

# Eksik ortam değişkenlerini kontrol et
missing_vars = []
if not SPOTIPY_CLIENT_ID: missing_vars.append("SPOTIPY_CLIENT_ID")
if not SPOTIPY_CLIENT_SECRET: missing_vars.append("SPOTIPY_CLIENT_SECRET")
# SPOTIPY_REDIRECT_URI ve FRONTEND_URL için varsayılan değerler kabul edilebilir, ancak üretimde ayarlanmaları önerilir.
# if not SPOTIPY_REDIRECT_URI: missing_vars.append("SPOTIPY_REDIRECT_URI")
# if not FRONTEND_URL: missing_vars.append("FRONTEND_URL")

if app.secret_key == "123!@#":
    logger.warning("Varsayılan FLASK_SECRET_KEY kullanılıyor. Lütfen üretim ortamı için güvenli bir anahtar ayarlayın (FLASK_SECRET_KEY ortam değişkeni).")

if missing_vars:
    # Eksik değişkenler varsa uygulamayı başlatma
    logger.critical(f"Kritik ortam değişkenleri eksik: {', '.join(missing_vars)}. Uygulama başlatılamıyor.")
    logger.critical("Lütfen SPOTIPY_CLIENT_ID ve SPOTIPY_CLIENT_SECRET ortam değişkenlerini ayarlayın.")
    exit(1) # Eksik değişkenlerle başlatmayı durdur

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
        # cache_path=".spotify_cache" # Token'ları diskte saklamak için (isteğe bağlı)
    )

    # Spotify Client Credentials (Genel API Erişimi İçin)
    client_credentials_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET
    )
    sp_cc = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    # Tür listesini API'den çekme denemesi (Artık 404 veriyor gibi görünüyor, bu yüzden devre dışı)
    # try:
    #     genre_data = sp_cc.recommendation_genre_seeds()
    #     # ... (önceki kod)
    # except SpotifyException as e:
    #     # ... (önceki kod)
    # except Exception as e:
    #     # ... (önceki kod)

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

    # Token'ın geçerli bir sözlük olup olmadığını kontrol et
    if not isinstance(token_info, dict) or 'access_token' not in token_info:
        # Refresh token kontrolü burada kritik değil, yenileme sırasında kontrol edilecek.
        logger.error(f"Session'daki token_info beklenen formatta değil veya access_token eksik: {token_info}")
        session.pop('token_info', None)
        session.pop('user_data', None) # İlişkili kullanıcı verisini de temizle
        return None

    # Token süresinin dolup dolmadığını kontrol et
    try:
        # Token süresinin dolup dolmadığını kontrol et
        if sp_oauth.is_token_expired(token_info):
            logger.info("Spotify token süresi dolmuş, yenileniyor...")
            refresh_token = token_info.get('refresh_token')
            # Yenileme token'ı olmadan yenileme yapılamaz
            if not refresh_token:
                 logger.error("Token yenilemek için refresh_token bulunamadı. Kullanıcının tekrar giriş yapması gerekiyor.")
                 session.pop('token_info', None)
                 session.pop('user_data', None)
                 return None

            # --- YENİ TOKEN BURADA ALINIYOR ---
            new_token_info = sp_oauth.refresh_access_token(refresh_token)
            # ------------------------------------

            session['token_info'] = new_token_info # Yenilenen token'ı session'a kaydet
            logger.info("Token başarıyla yenilendi.")
            return new_token_info # Yenilenmiş token bilgisini döndür
        else:
            # Token hala geçerli
            logger.debug("Mevcut token hala geçerli.")
            return token_info

    except SpotifyException as e:
        logger.error(f"Token yenilenirken Spotify API hatası: {e}. Kullanıcının tekrar giriş yapması gerekebilir.")
        # Hata durumunda session'ı temizle
        session.pop('token_info', None)
        session.pop('user_data', None)
        return None # Yenileme başarısız oldu
    except Exception as e:
        logger.error(f"Token yenilenirken beklenmedik hata: {e}", exc_info=True)
        session.pop('token_info', None)
        session.pop('user_data', None)
        return None # Yenileme başarısız oldu

# --- Rotalar ---
@app.route('/')
def index():
    # Basit bir hoşgeldin mesajı veya API durum sayfası
    return jsonify({"message": "Spotify Recommendation API Backend", "status": "running"})

@app.route('/login')
def login():
    """Kullanıcıyı Spotify yetkilendirme sayfasına yönlendirir."""
    logger.info("Kullanıcı Spotify yetkilendirmesi için yönlendiriliyor.")
    if not sp_oauth:
        logger.error("Spotify OAuth nesnesi başlatılamadı.")
        return jsonify({"error": "Sunucu yapılandırma hatası."}), 500
    try:
        # State parametresi eklemek CSRF saldırılarına karşı koruma sağlar.
        # state = os.urandom(16).hex()
        # session['oauth_state'] = state
        # auth_url = sp_oauth.get_authorize_url(state=state)
        auth_url = sp_oauth.get_authorize_url() # Şimdilik state olmadan devam ediliyor
        return redirect(auth_url)
    except Exception as e:
        logger.error(f"Spotify yetkilendirme URL'si alınırken hata: {e}", exc_info=True)
        return jsonify({"error": "Spotify ile bağlantı kurulamadı."}), 500


@app.route('/callback')
def callback():
    """Spotify tarafından geri çağrılan endpoint. Yetkilendirme kodunu alır ve token ile değiştirir."""
    logger.info("Spotify callback işleniyor.")
    code = request.args.get('code')
    error = request.args.get('error')
    # state = request.args.get('state') # State kontrolü eklenecekse

    # State kontrolü (CSRF koruması için önerilir)
    # stored_state = session.pop('oauth_state', None)
    # if not state or state != stored_state:
    #     logger.error("OAuth state uyuşmazlığı veya eksik state.")
    #     return redirect(f"{FRONTEND_URL}?error=state_mismatch")

    if error:
        logger.error(f"Spotify yetkilendirme hatası: {error}")
        # Hata mesajını frontend'e ilet
        return redirect(f"{FRONTEND_URL}?error=spotify_auth_error&message={error}")

    if not code:
        logger.error("Callback isteğinde 'code' parametresi eksik.")
        return redirect(f"{FRONTEND_URL}?error=missing_code")

    if not sp_oauth:
        logger.error("Spotify OAuth nesnesi başlatılamadı.")
        return redirect(f"{FRONTEND_URL}?error=server_config_error")

    try:
        # Token'ı al.
        # Not: `spotipy`'nin bazı sürümlerinde bu satır hala DeprecationWarning verebilir,
        # ancak `as_dict=True` olmadan kullanım güncel sürümler için doğrudur.
        token_info = sp_oauth.get_access_token(code, check_cache=False)

        if not token_info or not isinstance(token_info, dict) or 'access_token' not in token_info:
             logger.error(f"Token alınamadı veya geçersiz format: {token_info}")
             # Frontend'e daha açıklayıcı bir hata yönlendirmesi yapılabilir
             return redirect(f"{FRONTEND_URL}?error=token_exchange_failed")

        session['token_info'] = token_info
        logger.info("Spotify access token başarıyla alındı ve session'a kaydedildi.")
        # Token alındıktan sonra kullanıcı verilerini çekmek için başka bir route'a yönlendir
        return redirect(url_for('fetch_and_store_user_data'))
    except SpotifyException as e:
        logger.error(f"Token değişimi sırasında Spotify API hatası: {e}")
        return redirect(f"{FRONTEND_URL}?error=token_exchange_error&message={e.msg}")
    except Exception as e:
        logger.error(f"Token değişimi sırasında beklenmedik hata: {e}", exc_info=True)
        return redirect(f"{FRONTEND_URL}?error=token_exchange_error")


@app.route('/fetch_and_store_user_data')
def fetch_and_store_user_data():
    """Access token kullanarak Spotify'dan kullanıcı verilerini çeker ve session'a kaydeder."""
    logger.info("Spotify'dan kullanıcı verileri çekiliyor ve session'a kaydediliyor.")
    token_info = get_token() # Token'ı al (veya yenile)
    if not token_info:
        logger.warning("Kullanıcı verisi çekmek için geçerli token yok. Login gerekli.")
        # Token yoksa veya yenilenemediyse frontend'e hata ilet
        return redirect(f"{FRONTEND_URL}?error=authentication_required")

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             logger.error("Token bilgisinde access_token bulunamadı.")
             # Bu durum get_token içinde yakalanmalıydı ama ek kontrol
             session.pop('token_info', None)
             session.pop('user_data', None)
             return redirect(f"{FRONTEND_URL}?error=internal_error_token")

        sp = spotipy.Spotify(auth=access_token)
        user_data = sp.me() # Kullanıcı bilgilerini al
        if not user_data or 'id' not in user_data:
             logger.error(f"Spotify API'den geçerli kullanıcı verisi alınamadı: {user_data}")
             # Token geçerli ama veri alınamıyorsa API sorunu olabilir
             return redirect(f"{FRONTEND_URL}?error=spotify_user_data_error")

        user_id = user_data['id']
        username = user_data.get('display_name', user_id) # Görünen ad yoksa ID kullan

        session['user_data'] = user_data # Kullanıcı verisini session'a kaydet
        logger.info(f"Kullanıcı bilgileri session'a kaydedildi: {username} ({user_id})")

        # Başarılı olursa frontend'in ana sayfasına veya dashboard'una yönlendir
        logger.info(f"Kullanıcı verileri başarıyla çekildi. Frontend'e yönlendiriliyor: {FRONTEND_URL}")
        return redirect(FRONTEND_URL)

    except SpotifyException as e:
        logger.error(f"Spotify API hatası (kullanıcı verisi çekme): {e}")
        # Token geçersiz veya yetki sorunu olabilir, session'ı temizle
        session.pop('token_info', None)
        session.pop('user_data', None)
        error_code = "spotify_api_error"
        if e.http_status == 401 or e.http_status == 403:
            error_code = "authentication_required" # Yetki hatası ise tekrar login gerektiğini belirt
        return redirect(f"{FRONTEND_URL}?error={error_code}&message={e.msg}")
    except Exception as e:
        logger.error(f"Kullanıcı verisi çekme sırasında beklenmedik hata: {e}", exc_info=True)
        session.pop('token_info', None) # Güvenlik için session'ı temizle
        session.pop('user_data', None)
        return redirect(f"{FRONTEND_URL}?error=internal_server_error")


@app.route('/user_data')
def get_user_data_from_session():
    """Session'daki mevcut kullanıcı verisini döndürür veya giriş gerektiğini belirtir."""
    logger.debug("Session'daki kullanıcı verisi kontrol ediliyor.")
    token_info = get_token() # Token'ın hala geçerli olup olmadığını kontrol et (ve yenile)
    user_data = session.get('user_data')

    if user_data and token_info:
        # Hem kullanıcı verisi hem de geçerli token varsa bilgiyi döndür
        username = user_data.get('display_name', user_data.get('id', 'N/A'))
        logger.info(f"Mevcut kullanıcı verisi döndürülüyor: {username}")
        return jsonify(user_data)
    elif user_data and not token_info:
        # Kullanıcı verisi var ama token süresi dolmuş ve yenilenememiş
        logger.warning("Kullanıcı verisi var ama token geçersiz/yenilenemedi. Tekrar giriş gerekli.")
        session.pop('user_data', None) # Eski kullanıcı verisini temizle
        return jsonify({"error": "Oturum süresi doldu. Lütfen tekrar giriş yapın.", "login_required": True}), 401
    else:
        # Kullanıcı verisi veya token yoksa giriş yapılması gerektiğini belirt
        logger.info("Session'da geçerli kullanıcı verisi veya token bulunamadı. Giriş gerekli.")
        return jsonify({"error": "Kullanıcı girişi gerekli.", "login_required": True}), 401


@app.route('/logout')
def logout():
    """Kullanıcı oturumunu sonlandırır."""
    user_id = session.get('user_data', {}).get('id', 'Bilinmeyen Kullanıcı')
    logger.info(f"Kullanıcı {user_id} oturumu sonlandırılıyor.")
    session.pop('token_info', None)
    session.pop('user_data', None)
    # session.clear() # Tüm session verilerini temizlemek için alternatif
    # İsteğe bağlı: Spotify tarafında da yetkiyi kaldırma (genellikle gerekli değil)
    # Cache kullanılıyorsa cache dosyasını silmek de düşünülebilir.
    return jsonify({"message": "Başarıyla çıkış yapıldı."})


# --- Öneri Rotaları (Search Endpoint'i Kullanarak Güncellendi) ---

@app.route('/initial_recommendations')
def get_initial_recommendations():
    """
    Giriş yapmamış kullanıcılar için rastgele türlere dayalı arama sonuçları sunar
    (Önceki recommendations endpoint'i yerine search kullanılıyor).
    """
    logger.info("Başlangıç için rastgele türlere göre arama isteği alındı.")

    if not sp_cc:
        logger.error("Client Credentials istemcisi başlatılamadı.")
        return jsonify({"error": "Sunucu yapılandırma hatası."}), 500

    recommendations_json = []
    try:
        # Rastgele 1-5 tür seç
        if not AVAILABLE_GENRE_SEEDS:
             logger.error("Kullanılabilir tür listesi boş! Başlangıç araması yapılamıyor.")
             return jsonify({"error": "Arama için tür listesi bulunamadı."}), 500

        num_seeds = random.randint(1, min(5, len(AVAILABLE_GENRE_SEEDS)))
        seed_genres = random.sample(AVAILABLE_GENRE_SEEDS, num_seeds)
        logger.info(f"Başlangıç araması için rastgele türler seçildi: {seed_genres}")

        # --- Spotify API Çağrısı (Search Endpoint'i Kullanarak) ---
        # Seçilen türleri içeren bir arama sorgusu oluştur
        # Not: Spotify'ın 'genre:' filtresi bazen kısıtlı olabilir, genel arama daha fazla sonuç verebilir.
        # search_query = f"genre:{' '.join(seed_genres)}"
        search_query = f"{random.choice(seed_genres)} music" # Daha genel bir arama
        logger.debug(f"sp_cc.search çağrılıyor, query: '{search_query}'")

        search_results = sp_cc.search(
            q=search_query,
            type='track', # Sadece şarkı ara
            limit=10,     # Sonuç sayısı
            market='TR'   # Pazar kodu (isteğe bağlı)
        )
        logger.debug("sp_cc.search çağrısı tamamlandı.")
        # -------------------------------------------------------

        # Sonucu JSON formatına çevir (Search API'sinin yapısı farklı)
        if search_results and search_results.get('tracks') and search_results['tracks'].get('items'):
            tracks = search_results['tracks']['items'] # 'items' listesine eriş
            logger.info(f"Spotify aramasından {len(tracks)} adet başlangıç sonucu bulundu.")
            for track in tracks:
                if track and track.get('id'):
                    album_art = None
                    if track.get('album') and isinstance(track['album'].get('images'), list) and track['album']['images']:
                        album_art = track['album']['images'][0]['url']

                    recommendations_json.append({
                        "id": track['id'],
                        "title": track.get('name', 'N/A'),
                        "artist": ", ".join([artist.get('name', 'N/A') for artist in track.get('artists', []) if artist]),
                        "album_art_url": album_art,
                        "spotify_url": track.get('external_urls', {}).get('spotify'),
                        "preview_url": track.get('preview_url'),
                    })
            logger.info(f"Başarıyla {len(recommendations_json)} adet başlangıç sonucu formatlandı.")
        else:
            logger.warning(f"Başlangıç araması için Spotify API'den geçerli 'tracks' veya 'items' verisi alınamadı. Yanıt: {search_results}")

        return jsonify(recommendations_json)

    except SpotifyException as e:
        # Search endpoint'i için 404 genellikle beklenmez, ancak diğer hatalar olabilir.
        logger.error(f"Başlangıç araması sırasında Spotify API hatası: Status={e.http_status}, Code={e.code}, Msg={e.msg}")
        error_status_code = e.http_status if e.http_status in [400, 401, 403, 429] else 500
        error_message = "Başlangıç sonuçları alınamadı."
        if e.http_status == 429:
             error_message += " (API limit aşıldı)"
        elif e.http_status == 401 or e.http_status == 403:
             error_message += " (Yetkilendirme sorunu)"
        # 404 durumunu yine de loglayalım
        elif e.http_status == 404:
             logger.error(f"Spotify Search API 404 (Not Found) hatası alındı! URL: {e.msg}. Bu beklenmedik bir durum.")
             error_message += " (Kaynak bulunamadı - Spotify API sorunu olabilir)"

        return jsonify({"error": error_message}), error_status_code
    except Exception as e:
        logger.error(f"Başlangıç araması sırasında beklenmedik hata: {e}", exc_info=True)
        return jsonify({"error": "Başlangıç sonuçları alınırken sunucu hatası oluştu."}), 500


@app.route('/recommendations', methods=['POST'])
def get_recommendations_for_user():
    """
    Giriş yapmış kullanıcının dinleme geçmişine göre arama sonuçları sunar
    (Önceki recommendations endpoint'i yerine search kullanılıyor).
    """
    logger.info("Geçmişe dayalı müzik arama isteği alındı.")
    token_info = get_token()
    if not token_info:
        logger.warning("Arama isteği için geçerli token bulunamadı. Giriş gerekli.")
        return jsonify({"error": "Yetkilendirme gerekli. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_data = session.get('user_data')
    if not user_data or not user_data.get('id'):
        logger.error("Arama isteği sırasında session'da geçerli kullanıcı verisi bulunamadı!")
        session.pop('token_info', None)
        session.pop('user_data', None)
        return jsonify({"error": "Oturum hatası veya geçersiz kullanıcı verisi. Lütfen tekrar giriş yapın.", "login_required": True}), 401

    user_id = user_data['id']
    logger.info(f"Kullanıcı ID: {user_id} için Spotify'dan arama sonuçları hazırlanıyor.")

    try:
        access_token = token_info.get('access_token')
        if not access_token:
             logger.error(f"Kullanıcı {user_id} için access_token alınamadı.")
             session.pop('token_info', None)
             session.pop('user_data', None)
             return jsonify({"error": "Oturum hatası (token alınamadı). Lütfen tekrar giriş yapın.", "login_required": True}), 401
        sp = spotipy.Spotify(auth=access_token)

        # 1. Spotify'dan arama için "ipucu" verileri çek (Top Artists/Tracks)
        search_query = None
        query_basis = "rastgele popüler türler" # Sorgunun neye dayandığını belirtmek için

        try:
            # En çok dinlenen sanatçıları al (kısa vadeli)
            logger.debug(f"Kullanıcı {user_id} için top artists çekiliyor...")
            top_artists_data = sp.current_user_top_artists(limit=5, time_range='short_term') # 5 sanatçı alalım

            if top_artists_data and top_artists_data.get('items'):
                top_artists = [artist for artist in top_artists_data['items'] if artist and artist.get('name')]
                if top_artists:
                    # En popüler sanatçının adını arama sorgusu yap
                    selected_artist = top_artists[0]['name']
                    search_query = f"{selected_artist}" # Sadece sanatçı adı ile arama
                    query_basis = f"en çok dinlenen sanatçı ({selected_artist})"
                    logger.info(f"Arama için en çok dinlenen sanatçı bulundu: {selected_artist}")

            # Eğer sanatçı bulunamazsa, en çok dinlenen şarkıların türlerini kullanmayı dene
            if not search_query:
                logger.debug(f"Kullanıcı {user_id} için top tracks çekiliyor...")
                top_tracks_data = sp.current_user_top_tracks(limit=5, time_range='short_term')
                if top_tracks_data and top_tracks_data.get('items'):
                    track_ids = [track['id'] for track in top_tracks_data['items'] if track and track.get('id')]
                    if track_ids:
                        # Şarkıların sanatçılarının türlerini al (biraz daha karmaşık)
                        # Basitlik için ilk şarkının sanatçısını alalım
                        first_track_details = sp.track(track_ids[0])
                        if first_track_details and first_track_details.get('artists'):
                            first_artist_id = first_track_details['artists'][0]['id']
                            if first_artist_id:
                                artist_details = sp.artist(first_artist_id)
                                if artist_details and artist_details.get('genres'):
                                    selected_genre = random.choice(artist_details['genres'])
                                    search_query = f"{selected_genre} music" # Tür ile arama
                                    query_basis = f"en çok dinlenen şarkının türü ({selected_genre})"
                                    logger.info(f"Arama için en çok dinlenen şarkının türü bulundu: {selected_genre}")
                                elif artist_details and artist_details.get('name'):
                                     # Tür yoksa sanatçı adını kullan
                                     selected_artist = artist_details['name']
                                     search_query = f"{selected_artist}"
                                     query_basis = f"en çok dinlenen şarkının sanatçısı ({selected_artist})"
                                     logger.info(f"Arama için en çok dinlenen şarkının sanatçısı bulundu: {selected_artist}")


            # Hala arama sorgusu yoksa, varsayılan türleri kullan
            if not search_query:
                 logger.warning(f"Kullanıcı {user_id} için kişisel arama ipucu (sanatçı/tür) bulunamadı. Rastgele popüler türler kullanılacak.")
                 if not AVAILABLE_GENRE_SEEDS:
                      logger.error("Kullanılabilir tür listesi boş! Varsayılan arama yapılamıyor.")
                      return jsonify({"error": "Arama yapmak için yeterli veri veya yapılandırma bulunamadı."}), 500
                 else:
                      selected_genre = random.choice(AVAILABLE_GENRE_SEEDS)
                      search_query = f"{selected_genre} music" # Rastgele tür ile arama
                      query_basis = f"rastgele popüler tür ({selected_genre})"
                      logger.info(f"Varsayılan arama türü seçildi: {selected_genre}")

            logger.info(f"Kullanılacak Arama Sorgusu: '{search_query}' (Kaynak: {query_basis})")

        except SpotifyException as e:
            logger.error(f"Spotify'dan arama ipucu verisi çekilemedi (Kullanıcı: {user_id}): {e}")
            error_status = e.http_status if e.http_status in [401, 403, 429] else 500
            login_req = error_status in [401, 403]
            return jsonify({"error": f"Spotify dinleme geçmişinize erişirken bir sorun oluştu.", "details": e.msg, "login_required": login_req}), error_status
        except Exception as e:
            logger.error(f"Arama ipucu verilerini işlerken beklenmedik hata (Kullanıcı: {user_id}): {e}", exc_info=True)
            return jsonify({"error": "Dinleme geçmişiniz işlenirken beklenmedik bir hata oluştu."}), 500

        # 2. Spotify'dan arama sonuçlarını al
        search_results = None
        try:
            # --- Spotify API Çağrısı (Search Endpoint'i Kullanarak) ---
            logger.info("Spotify search API çağrılıyor...")
            logger.debug(f"Params - q: '{search_query}', type: 'track', limit: 20, market: 'TR'")
            search_results = sp.search(
                q=search_query,
                type='track',
                limit=20,
                market='TR'
            )
            logger.info("Spotify search API'den cevap alındı.")
            # -------------------------------------------------------

        except SpotifyException as e:
             logger.error(f"Spotify search API hatası (Kullanıcı: {user_id}): Status={e.http_status}, Code={e.code}, Msg={e.msg}")
             if e.http_status == 401 or e.http_status == 403:
                 session.pop('token_info', None)
                 session.pop('user_data', None)
                 return jsonify({"error": "Spotify yetkilendirme hatası. Lütfen tekrar giriş yapın.", "login_required": True}), e.http_status
             elif e.http_status == 429:
                 return jsonify({"error": "Çok fazla istek yapıldı. Lütfen biraz bekleyip tekrar deneyin."}), 429
             elif e.http_status == 400:
                 logger.warning(f"Spotify API 400 (Bad Request) hatası (muhtemelen geçersiz arama sorgusu): {e.msg}")
                 return jsonify({"error": "Arama sorgusu oluşturulurken bir sorun oluştu."}), 400
             # Search için 404 beklenmez ama yine de kontrol edelim
             elif e.http_status == 404:
                 logger.error(f"Spotify Search API 404 (Not Found) hatası alındı! URL: {e.msg}. Bu beklenmedik bir durum.")
                 return jsonify({"error": "Arama yapılırken bir sorun oluştu (Kaynak bulunamadı - Spotify API sorunu olabilir)."}), 404
             else:
                 return jsonify({"error": f"Spotify'dan arama sonucu alınamadı.", "details": e.msg}), e.http_status if e.http_status else 500
        except Exception as e:
             logger.error(f"Spotify arama sonuçları alınırken beklenmedik hata (Kullanıcı: {user_id}): {e}", exc_info=True)
             return jsonify({"error": "Arama sonuçları alınırken beklenmedik bir sunucu hatası oluştu."}), 500


        # 3. Sonucu JSON formatına çevir
        recommendations_json = []
        if search_results and search_results.get('tracks') and search_results['tracks'].get('items'):
            tracks = search_results['tracks']['items']
            logger.info(f"Spotify aramasından {len(tracks)} adet kişisel sonuç bulundu.")
            for track in tracks:
                 if track and track.get('id'):
                    album_art = None
                    # En uygun boyuttaki resmi seçmek için iyileştirme yapılabilir (örn. 300px civarı)
                    if track.get('album') and isinstance(track['album'].get('images'), list) and track['album']['images']:
                        # Ortanca boyuttaki resmi veya ilk resmi al
                        images = track['album']['images']
                        if len(images) > 1:
                             album_art = images[1]['url'] # Genellikle 300px
                        else:
                             album_art = images[0]['url'] # Tek resim varsa onu al

                    recommendations_json.append({
                        "id": track['id'],
                        "title": track.get('name', 'N/A'),
                        "artist": ", ".join([artist.get('name', 'N/A') for artist in track.get('artists', []) if artist]),
                        "album_art_url": album_art,
                        "spotify_url": track.get('external_urls', {}).get('spotify'),
                        "preview_url": track.get('preview_url'),
                    })
            logger.info(f"Başarıyla {len(recommendations_json)} adet kişisel sonuç formatlandı.")
        else:
            logger.warning(f"Kullanıcı {user_id} için Spotify API aramasından geçerli sonuç ('tracks'/'items') alınamadı veya boş döndü.")

        # Yanıtı oluştur
        response_payload = {"recommendations": recommendations_json} # Frontend'in hala 'recommendations' beklemesi muhtemel
        response_payload["message"] = f"Sonuçlar '{query_basis}' baz alınarak yapılan aramaya göre gösterilmektedir."
        if not recommendations_json:
             response_payload["message"] += " Bu aramaya uygun sonuç bulunamadı."


        return jsonify(response_payload)

    except Exception as e:
        # Genel Hata Yakalama (Yukarıdaki bloklardan kaçan beklenmedik durumlar için)
        logger.exception(f"Kişisel arama sırasında kritik hata oluştu (Kullanıcı: {user_id}): {e}")
        return jsonify({"error": "Sonuçlar oluşturulurken beklenmedik bir sunucu hatası oluştu."}), 500


# --- Uygulama Başlatma ---
if __name__ == '__main__':
    # Debug modunu ortam değişkeninden almak daha güvenli olabilir
    # Örn: export FLASK_DEBUG=1 veya set FLASK_DEBUG=1
    # DEBUG_MODE = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    # app.run(debug=DEBUG_MODE, host='0.0.0.0', port=5000) # host='0.0.0.0' ağdaki diğer cihazlardan erişim için
    logger.info("Flask uygulaması başlatılıyor...")
    # Geliştirme sırasında debug=True kullanışlıdır, ancak üretimde False olmalıdır.
    # host='0.0.0.0' yerine '127.0.0.1' kullanmak, sadece yerel makineden erişime izin verir.
    app.run(debug=True, host='127.0.0.1', port=5000)
logger.info("Flask uygulaması başarıyla başlatıldı.") # Bu satır app.run() sonrasına gelmez, loglama için farklı bir yöntem gerekir.
