// script.js

const backendUrl = 'http://127.0.0.1:5000'; // Backend adresiniz
const loginButton = document.getElementById('login-button');
const logoutButton = document.getElementById('logout-button');
const userInfoDiv = document.getElementById('user-info');
const recommendationsDiv = document.getElementById('recommendations');
const initialRecommendationsDiv = document.getElementById('initial-recommendations');
const getRecommendationsButton = document.getElementById('get-recommendations-button');
const profileSection = document.getElementById('profile-section'); // Profil bölümü için yeni div
const showProfileButton = document.getElementById('show-profile-button'); // Profil gösterme butonu
const mainContent = document.getElementById('main-content'); // Ana içerik bölümü
const loadingIndicator = document.getElementById('loading'); // Yükleme göstergesi
const errorMessageDiv = document.getElementById('error-message'); // Hata mesajı alanı

let currentlyPlayingAudio = null; // O an çalan sesi takip etmek için
let userPlaylists = []; // Kullanıcı playlistlerini saklamak için

// --- Helper Functions ---

function showLoading() {
    if (loadingIndicator) loadingIndicator.style.display = 'block';
}

function hideLoading() {
    if (loadingIndicator) loadingIndicator.style.display = 'none';
}

function showError(message) {
    console.error("Hata:", message); // Konsola da yazdır
    if (errorMessageDiv) {
        errorMessageDiv.textContent = `Hata: ${message}`;
        errorMessageDiv.style.display = 'block';
        // Belirli bir süre sonra hata mesajını gizle (isteğe bağlı)
        setTimeout(() => {
            errorMessageDiv.style.display = 'none';
        }, 5000);
    } else {
        alert(`Hata: ${message}`); // Fallback
    }
}

function clearError() {
    if (errorMessageDiv) {
        errorMessageDiv.textContent = '';
        errorMessageDiv.style.display = 'none';
    }
}

// --- API Call Functions ---

async function fetchApi(endpoint, options = {}) {
    showLoading();
    clearError(); // Yeni istek öncesi eski hatayı temizle
    try {
        const response = await fetch(`${backendUrl}${endpoint}`, {
            credentials: 'include', // Session cookie'lerini göndermek için önemli
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {}),
            },
        });

        if (response.status === 401) {
            // Yetkilendirme hatası (login gerekli)
            console.warn('Yetkilendirme gerekli, login sayfasına yönlendiriliyor olabilir.');
            // Otomatik login yönlendirmesi veya kullanıcıya bilgi verme
            handleLogoutUI(); // Login gerekli ise logout olmuş gibi göster
            showError("Oturum süresi doldu veya giriş yapmanız gerekiyor.");
            // İsteğe bağlı: window.location.href = `${backendUrl}/login`;
            return null; // Hata durumunda null dön
        }

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                // JSON parse edilemezse
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const errorMessage = errorData.error || `İstek başarısız oldu (HTTP ${response.status})`;
            if (errorData.login_required) {
                handleLogoutUI();
                showError("Oturum süresi doldu veya giriş yapmanız gerekiyor.");
            } else {
                showError(errorMessage);
            }
            throw new Error(errorMessage); // Hata fırlat
        }

        // Başarılı yanıtı işle (içerik varsa)
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return await response.json();
        } else {
            // JSON olmayan yanıtlar için (örn: logout)
            return { success: true }; // Veya boş bir nesne
        }

    } catch (error) {
        console.error(`API isteği hatası (${endpoint}):`, error);
        // showError fonksiyonu zaten çağrıldı, burada tekrar çağırmaya gerek yok
        return null; // Hata durumunda null dön
    } finally {
        hideLoading();
    }
}

// --- UI Update Functions ---

function handleLoginUI(userData) {
    if (userInfoDiv && loginButton && logoutButton && getRecommendationsButton && showProfileButton) {
        userInfoDiv.textContent = `Hoş geldin, ${userData.display_name || userData.id}!`;
        loginButton.style.display = 'none';
        logoutButton.style.display = 'inline-block';
        getRecommendationsButton.style.display = 'inline-block';
        showProfileButton.style.display = 'inline-block'; // Profil butonunu göster
        userInfoDiv.style.display = 'block';
        if (initialRecommendationsDiv) initialRecommendationsDiv.style.display = 'none'; // Başlangıç önerilerini gizle
        if (recommendationsDiv) recommendationsDiv.innerHTML = ''; // Eski önerileri temizle
        if (profileSection) profileSection.style.display = 'none'; // Profil bölümünü gizle
        if (mainContent) mainContent.style.display = 'block'; // Ana içeriği göster

        // Hoş geldiniz mesajını göster (Başlangıç önerileri yerine)
        if (recommendationsDiv) {
            recommendationsDiv.innerHTML = `<h2>Merhaba ${userData.display_name || userData.id}! Yeni öneriler almak için 'Önerileri Getir' butonuna tıklayın veya profilinizi görüntüleyin.</h2>`;
        }
    }
}

function handleLogoutUI() {
    if (userInfoDiv && loginButton && logoutButton && getRecommendationsButton && showProfileButton) {
        userInfoDiv.textContent = '';
        loginButton.style.display = 'inline-block';
        logoutButton.style.display = 'none';
        getRecommendationsButton.style.display = 'none';
        showProfileButton.style.display = 'none'; // Profil butonunu gizle
        userInfoDiv.style.display = 'none';
        if (recommendationsDiv) recommendationsDiv.innerHTML = ''; // Önerileri temizle
        if (profileSection) profileSection.innerHTML = ''; // Profil bölümünü temizle
        if (profileSection) profileSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block'; // Ana içeriği göster

        // Başlangıç önerileri yerine hoş geldiniz mesajı
        if (initialRecommendationsDiv) initialRecommendationsDiv.style.display = 'none'; // Bunu da gizleyelim
        if (recommendationsDiv) {
            recommendationsDiv.innerHTML = `<h2>Hoş Geldiniz! Müzik keşfetmeye başlamak için lütfen giriş yapın.</h2>`;
        }
        // fetchInitialRecommendations(); // Çıkış yapınca başlangıç önerilerini GETİRME
    }
}

function displayTracks(tracks, containerElement) {
    if (!containerElement) return;
    containerElement.innerHTML = ''; // Önceki içeriği temizle

    if (!tracks || tracks.length === 0) {
        containerElement.innerHTML = '<p>Gösterilecek şarkı bulunamadı.</p>';
        return;
    }

    tracks.forEach(track => {
        const trackElement = document.createElement('div');
        trackElement.classList.add('song-card'); // Stil için sınıf

        const albumArt = track.album_art_url || 'placeholder.png'; // Varsayılan resim
        const title = track.title || 'Bilinmeyen Şarkı';
        const artist = track.artist || 'Bilinmeyen Sanatçı';
        const spotifyUrl = track.spotify_url;
        const previewUrl = track.preview_url;
        const trackId = track.id; // Playlist'e eklemek için ID

        trackElement.innerHTML = `
            <img src="${albumArt}" alt="Albüm Kapağı - ${title}" class="album-art">
            <div class="song-info">
                <p class="title">${title}</p>
                <p class="artist">${artist}</p>
            </div>
            <div class="song-actions">
                ${previewUrl ? `<button class="action-btn preview-btn" data-preview-url="${previewUrl}">▶️</button>` : '<button class="action-btn preview-btn disabled" title="Önizleme yok" disabled>🚫</button>'}
                <button class="action-btn add-playlist-btn" data-track-id="${trackId}" title="Playlist'e Ekle">➕</button>
                ${spotifyUrl ? `<a href="${spotifyUrl}" target="_blank" class="action-btn spotify-link-btn" title="Spotify'da Aç">🎵</a>` : ''}
                <button class="action-btn share-btn" data-spotify-url="${spotifyUrl || ''}" title="Paylaş">🔗</button>
             </div>
             <audio class="preview-audio" src="${previewUrl || ''}"></audio>
        `;

        containerElement.appendChild(trackElement);
    });

    // Yeni eklenen butonlara event listener'ları ata
    attachActionListeners(containerElement);
}

function attachActionListeners(container) {
    container.querySelectorAll('.preview-btn:not(.disabled)').forEach(button => {
        button.onclick = handlePreviewClick;
    });
    container.querySelectorAll('.add-playlist-btn').forEach(button => {
        button.onclick = handleAddToPlaylistClick;
    });
    container.querySelectorAll('.share-btn').forEach(button => {
        button.onclick = handleShareClick;
    });

    // Ses bitince butonu sıfırla
    container.querySelectorAll('.preview-audio').forEach(audio => {
        audio.onended = (event) => {
            const button = event.target.closest('.song-card')?.querySelector('.preview-btn'); // Daha güvenli seçici
            if (button) {
                button.textContent = '▶️';
            }
            if (currentlyPlayingAudio === audio) {
                currentlyPlayingAudio = null;
            }
        };
        // Hata durumunda da sıfırla
        audio.onerror = (event) => {
            console.error("Audio error:", event.target.error);
            const button = event.target.closest('.song-card')?.querySelector('.preview-btn');
            if (button) {
                button.textContent = '▶️'; // Hata olsa da butonu sıfırla
                button.disabled = true; // Butonu devre dışı bırak
                button.title = "Önizleme yüklenemedi";
            }
            if (currentlyPlayingAudio === audio) {
                currentlyPlayingAudio = null;
            }
            showError("Bir şarkı önizlemesi yüklenirken hata oluştu.");
        }
    });
}

// --- Event Handlers ---

function handlePreviewClick(event) {
    const button = event.target;
    const audio = button.closest('.song-card')?.querySelector('.preview-audio'); // Güvenli seçici
    const previewUrl = button.dataset.previewUrl;

    if (!audio || !previewUrl) return;

    if (currentlyPlayingAudio && currentlyPlayingAudio !== audio) {
        // Başka bir ses çalıyorsa onu durdur
        currentlyPlayingAudio.pause();
        // Doğrudan src ile aramak yerine daha sağlam bir yöntem (örn. ID ile) daha iyi olabilir
        // ama şimdilik bu şekilde bırakabiliriz.
        const playingButton = document.querySelector(`button[data-preview-url="${currentlyPlayingAudio.src}"]`);
        if (playingButton) playingButton.textContent = '▶️';
    }

    if (audio.paused) {
        // Oynatmadan önce yüklenmesini bekleme (tarayıcı genellikle halleder)
        audio.play()
            .then(() => {
                button.textContent = '⏸️';
                currentlyPlayingAudio = audio;
            })
            .catch(error => {
                console.error("Önizleme çalınırken hata:", error);
                showError("Önizleme çalınamadı.");
                button.textContent = '▶️'; // Hata durumunda butonu sıfırla
                currentlyPlayingAudio = null; // Hata durumunda sıfırla
            });
    } else {
        audio.pause();
        button.textContent = '▶️';
        currentlyPlayingAudio = null;
    }
}

async function handleAddToPlaylistClick(event) {
    const trackId = event.target.dataset.trackId;
    if (!trackId) return;

    // 1. Kullanıcı playlistlerini al (cache'lenmişse kullan, yoksa fetch et)
    if (userPlaylists.length === 0) {
        const playlistsData = await fetchApi('/playlists');
        if (!playlistsData || !Array.isArray(playlistsData)) { // Daha sağlam kontrol
            showError("Playlistler alınamadı veya geçersiz formatta.");
            return;
        }
        userPlaylists = playlistsData;
    }

    if (userPlaylists.length === 0) {
        showError("Hiç playlist'iniz bulunamadı veya alınamadı.");
        return;
    }

    // 2. Playlist seçimi için daha iyi bir UI (Modal) önerilir, şimdilik prompt ile devam
    // TODO: Burayı daha kullanıcı dostu bir modal ile değiştir.
    let playlistOptions = userPlaylists.map((pl, index) => `${index + 1}: ${pl.name}`).join('\n');
    const choice = prompt(`Şarkıyı hangi playlist'e eklemek istersiniz?\n(Numara girin):\n${playlistOptions}`);

    if (choice === null || choice.trim() === '') return; // Kullanıcı iptal etti

    const choiceIndex = parseInt(choice) - 1;
    if (isNaN(choiceIndex) || choiceIndex < 0 || choiceIndex >= userPlaylists.length) {
        showError("Geçersiz playlist numarası.");
        return;
    }

    const selectedPlaylistId = userPlaylists[choiceIndex].id;
    const selectedPlaylistName = userPlaylists[choiceIndex].name; // Mesaj için ismi al

    // 3. Backend'e ekleme isteği gönder
    const result = await fetchApi('/playlist/add', {
        method: 'POST',
        body: JSON.stringify({
            playlist_id: selectedPlaylistId,
            track_uri: trackId // Backend ID veya URI kabul ediyor
        })
    });

    if (result && result.message) {
        // Daha bilgilendirici mesaj
        alert(`Şarkı "${selectedPlaylistName}" playlistine başarıyla eklendi!`);
    }
    // Hata mesajı fetchApi içinde gösteriliyor
}

function handleShareClick(event) {
    const spotifyUrl = event.target.dataset.spotifyUrl;
    if (!spotifyUrl) {
        showError("Paylaşılacak Spotify linki bulunamadı.");
        return;
    }

    // Modern Paylaşım API'sini kullanmayı dene (varsa)
    if (navigator.share) {
        navigator.share({
            title: 'Spotify Şarkı Önerisi',
            text: 'Şu harika şarkıya bir bak!',
            url: spotifyUrl,
        })
            .then(() => console.log('Başarılı paylaşım'))
            .catch((error) => {
                console.error('Paylaşım hatası:', error)
                // Paylaşım API hatası veya iptali durumunda kopyalamaya fallback yap
                copyToClipboard(spotifyUrl);
            });
    } else {
        // Paylaşım API'si yoksa panoya kopyala
        copyToClipboard(spotifyUrl);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => alert('Spotify linki panoya kopyalandı!'))
        .catch(err => {
            console.error('Link kopyalanamadı:', err);
            showError('Link otomatik kopyalanamadı. Manuel olarak kopyalayabilirsiniz.');
            // Eski yöntem fallback (güvenli olmayan context'lerde çalışmayabilir)
            // try {
            //     const textArea = document.createElement("textarea");
            //     textArea.value = text;
            //     document.body.appendChild(textArea);
            //     textArea.focus();
            //     textArea.select();
            //     document.execCommand('copy');
            //     document.body.removeChild(textArea);
            //     alert('Spotify linki panoya kopyalandı!');
            // } catch (execErr) {
            //     console.error('Fallback kopyalama da başarısız:', execErr);
            //     showError('Link otomatik kopyalanamadı.');
            // }
        });
}


// --- Initialization and Main Logic ---

async function checkLoginStatus() {
    const userData = await fetchApi('/user_data');
    if (userData && !userData.error) {
        handleLoginUI(userData);
        // Giriş yapılmışsa kişisel önerileri otomatik GETİRME
        // fetchUserRecommendations();
    } else {
        // Giriş yapılmamışsa veya token geçersizse
        handleLogoutUI();
    }
}

// Başlangıç önerileri fonksiyonu artık çağrılmıyor ama kod olarak kalabilir (ileride gerekirse diye)
// Veya tamamen silinebilir.
async function fetchInitialRecommendations() {
    console.log("fetchInitialRecommendations çağrıldı ama artık kullanılmıyor.");
    // if (!initialRecommendationsDiv) return;
    // const recommendations = await fetchApi('/initial_recommendations');
    // if (recommendations) {
    //     displayTracks(recommendations, initialRecommendationsDiv);
    //     initialRecommendationsDiv.style.display = 'block'; // Göster
    // } else {
    //     initialRecommendationsDiv.innerHTML = '<p>Başlangıç önerileri alınamadı.</p>';
    //     initialRecommendationsDiv.style.display = 'block';
    // }
}

async function fetchUserRecommendations() {
    if (!recommendationsDiv) return;
    // Mevcut hoş geldiniz mesajını temizle
    recommendationsDiv.innerHTML = '';
    // POST isteği olduğu için options ekliyoruz
    const response = await fetchApi('/recommendations', { method: 'POST' });
    if (response && response.recommendations) {
        displayTracks(response.recommendations, recommendationsDiv);
        if (response.message) {
            // Bilgi mesajını göstermek için bir alan eklenebilir veya konsola yazdırılabilir
            console.info("Öneri Bilgisi:", response.message);
            // Örnek: Mesajı şarkıların üstüne ekle
            const infoMsg = document.createElement('p');
            infoMsg.textContent = response.message;
            infoMsg.style.textAlign = 'center';
            infoMsg.style.marginBottom = '10px';
            recommendationsDiv.prepend(infoMsg);
        }
    } else if (response && response.error) {
        // Hata fetchApi içinde gösterildi, burada sadece div'i temizleyebiliriz
        recommendationsDiv.innerHTML = '<p>Öneriler alınamadı.</p>';
    } else {
        // Beklenmedik durum, fetchApi null döndü ama hata göstermedi?
        recommendationsDiv.innerHTML = '<p>Öneriler alınırken bir sorun oluştu.</p>';
    }
}

async function fetchAndDisplayProfile() {
    if (!profileSection || !mainContent) return;

    // Profil zaten açıksa kapat
    if (profileSection.style.display === 'block') {
        profileSection.style.display = 'none';
        mainContent.style.display = 'block';
        return; // Fonksiyondan çık
    }

    // Profili getir
    const profileData = await fetchApi('/profile');

    if (profileData && !profileData.error) {
        profileSection.innerHTML = ''; // Önceki içeriği temizle

        // --- Profil içeriğini oluşturma fonksiyonları ---
        function createProfileHeader(user) {
            const header = document.createElement('div');
            header.classList.add('profile-header');
            const profilePic = user.images?.[0]?.url || 'placeholder.png'; // Optional chaining
            header.innerHTML = `
                <img src="${profilePic}" alt="Profil Resmi" class="profile-pic">
                <h2>${user.display_name || user.id}</h2>
                ${user.email ? `<p><a href="mailto:${user.email}">${user.email}</a></p>` : ''}
                <p><a href="${user.external_urls?.spotify || '#'}" target="_blank" rel="noopener noreferrer">Spotify Profili</a></p>
            `;
            return header;
        }

        function createProfileSection(title, items, renderItem) {
            if (!items || items.length === 0) return null; // Veri yoksa bölüm oluşturma

            const section = document.createElement('div');
            section.classList.add('profile-list-section');
            section.innerHTML = `<h3>${title}</h3>`;
            const list = document.createElement('div');
            list.classList.add('profile-list'); // Genel sınıf
            // İçeriğe göre ek sınıf ekle (örn: artist-list, track-list)
            if (title.toLowerCase().includes('sanatçı')) list.classList.add('artist-list');
            if (title.toLowerCase().includes('şarkı')) list.classList.add('track-list');

            items.forEach(item => {
                const itemElement = renderItem(item);
                if (itemElement) list.appendChild(itemElement);
            });
            section.appendChild(list);
            return section;
        }

        function renderArtistItem(artist) {
            const itemDiv = document.createElement('div');
            itemDiv.classList.add('profile-item');
            const artistPic = artist.images?.[2]?.url || artist.images?.[0]?.url || 'placeholder.png';
            itemDiv.innerHTML = `
                <a href="${artist.external_urls?.spotify || '#'}" target="_blank" rel="noopener noreferrer">
                    <img src="${artistPic}" alt="${artist.name}" loading="lazy">
                    <span>${artist.name}</span>
                </a>
            `;
            return itemDiv;
        }

        function renderTrackItem(track) {
            const itemDiv = document.createElement('div');
            itemDiv.classList.add('profile-item');
            const trackPic = track.album?.images?.[2]?.url || track.album?.images?.[0]?.url || 'placeholder.png';
            itemDiv.innerHTML = `
                 <a href="${track.external_urls?.spotify || '#'}" target="_blank" rel="noopener noreferrer">
                    <img src="${trackPic}" alt="${track.album?.name || ''}" loading="lazy">
                    <span>${track.name}</span>
                    <small>${track.artists?.map(a => a.name).join(', ') || ''}</small>
                </a>
            `;
            return itemDiv;
        }

        function createGenreSection(title, genres) {
            if (!genres || genres.length === 0) return null;
            const section = document.createElement('div');
            section.classList.add('profile-list-section');
            section.innerHTML = `<h3>${title}</h3>`;
            const list = document.createElement('ul');
            list.classList.add('genre-list');
            genres.forEach(genrePair => {
                const listItem = document.createElement('li');
                listItem.textContent = genrePair[0]; // Sadece tür adı
                list.appendChild(listItem);
            });
            section.appendChild(list);
            return section;
        }
        // --- Profil içeriğini oluşturma ---

        profileSection.appendChild(createProfileHeader(profileData.user));

        const artistsSection = createProfileSection('En Çok Dinlenen Sanatçılar', profileData.top_artists, renderArtistItem);
        if (artistsSection) profileSection.appendChild(artistsSection);

        const tracksSection = createProfileSection('En Çok Dinlenen Şarkılar', profileData.top_tracks, renderTrackItem);
        if (tracksSection) profileSection.appendChild(tracksSection);

        const genresSection = createGenreSection('En Çok Dinlenen Türler', profileData.top_genres);
        if (genresSection) profileSection.appendChild(genresSection);

        // Ana içeriği gizle, profili göster
        mainContent.style.display = 'none';
        profileSection.style.display = 'block';

    } else {
        // Hata fetchApi içinde gösterildi
        showError("Profil bilgileri alınamadı.");
        // Profili gösterme işlemini geri al (eğer açıksa)
        profileSection.style.display = 'none';
        mainContent.style.display = 'block';
    }
}

// --- Event Listeners Setup ---

if (loginButton) {
    loginButton.onclick = () => {
        // Mevcut konumu veya spesifik bir yönlendirme URL'sini state'e ekleyebiliriz
        // ama şimdilik basit tutalım.
        window.location.href = `${backendUrl}/login`;
    };
}

if (logoutButton) {
    logoutButton.onclick = async () => {
        // Önce çalan sesi durdur
        if (currentlyPlayingAudio) {
            currentlyPlayingAudio.pause();
            currentlyPlayingAudio = null;
            // Butonları da sıfırla (opsiyonel)
            document.querySelectorAll('.preview-btn').forEach(btn => btn.textContent = '▶️');
        }
        await fetchApi('/logout'); // Backend'de session'ı temizle
        userPlaylists = []; // Playlist cache'ini temizle
        handleLogoutUI(); // UI'ı güncelle
    };
}

if (getRecommendationsButton) {
    // Öneri almadan önce profilin kapalı olduğundan emin ol
    getRecommendationsButton.onclick = () => {
        if (profileSection) profileSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block';
        fetchUserRecommendations();
    }
}

if (showProfileButton) {
    // Buton tıklaması doğrudan fetchAndDisplayProfile'ı çağırabilir,
    // çünkü fonksiyon kendi içinde açık/kapalı durumunu kontrol ediyor.
    showProfileButton.onclick = fetchAndDisplayProfile;
}


// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    // Sayfa yüklendiğinde URL'de hata parametresi var mı kontrol et (callback'ten dönmüş olabilir)
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error');
    const messageParam = urlParams.get('message');

    if (errorParam) {
        showError(messageParam || `Bir hata oluştu (${errorParam})`);
        // Hata parametrelerini URL'den temizle (isteğe bağlı)
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    checkLoginStatus(); // Sayfa yüklendiğinde giriş durumunu kontrol et
});
