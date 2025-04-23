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
        if (mainContent) mainContent.style.display = 'block'; // Ana içeriği göster (başlangıç önerileri için)
        fetchInitialRecommendations(); // Çıkış yapınca başlangıç önerilerini getir
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
            const button = event.target.previousElementSibling.querySelector('.preview-btn');
            if (button) {
                button.textContent = '▶️';
            }
            if (currentlyPlayingAudio === audio) {
                currentlyPlayingAudio = null;
            }
        };
    });
}

// --- Event Handlers ---

function handlePreviewClick(event) {
    const button = event.target;
    const audio = button.closest('.song-card').querySelector('.preview-audio');
    const previewUrl = button.dataset.previewUrl;

    if (!audio || !previewUrl) return;

    if (currentlyPlayingAudio && currentlyPlayingAudio !== audio) {
        // Başka bir ses çalıyorsa onu durdur
        currentlyPlayingAudio.pause();
        const playingButton = document.querySelector(`button[data-preview-url="${currentlyPlayingAudio.src}"]`);
        if (playingButton) playingButton.textContent = '▶️';
    }

    if (audio.paused) {
        audio.play()
            .then(() => {
                button.textContent = '⏸️';
                currentlyPlayingAudio = audio;
            })
            .catch(error => {
                console.error("Önizleme çalınırken hata:", error);
                showError("Önizleme çalınamadı.");
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
        if (!playlistsData) return; // Hata fetchApi içinde gösterildi
        userPlaylists = playlistsData;
    }

    if (userPlaylists.length === 0) {
        showError("Hiç playlist'iniz bulunamadı veya alınamadı.");
        return;
    }

    // 2. Playlist seçimi için basit bir prompt (daha iyisi modal olurdu)
    let playlistOptions = userPlaylists.map((pl, index) => `${index + 1}: ${pl.name}`).join('\n');
    const choice = prompt(`Şarkıyı hangi playlist'e eklemek istersiniz?\n(Numara girin):\n${playlistOptions}`);

    if (choice === null || choice.trim() === '') return; // Kullanıcı iptal etti

    const choiceIndex = parseInt(choice) - 1;
    if (isNaN(choiceIndex) || choiceIndex < 0 || choiceIndex >= userPlaylists.length) {
        showError("Geçersiz playlist numarası.");
        return;
    }

    const selectedPlaylistId = userPlaylists[choiceIndex].id;

    // 3. Backend'e ekleme isteği gönder
    const result = await fetchApi('/playlist/add', {
        method: 'POST',
        body: JSON.stringify({
            playlist_id: selectedPlaylistId,
            track_uri: trackId // Backend ID veya URI kabul ediyor
        })
    });

    if (result && result.message) {
        alert(result.message); // Başarı mesajı
    }
    // Hata mesajı fetchApi içinde gösteriliyor
}

function handleShareClick(event) {
    const spotifyUrl = event.target.dataset.spotifyUrl;
    if (!spotifyUrl) {
        showError("Paylaşılacak Spotify linki bulunamadı.");
        return;
    }

    // Basit paylaşım seçenekleri (daha iyisi ikonlarla modal olabilir)
    const choice = prompt(`Paylaşma Seçenekleri:\n1: Linki Kopyala\n2: Twitter'da Paylaş`);

    switch (choice) {
        case '1':
            navigator.clipboard.writeText(spotifyUrl)
                .then(() => alert('Spotify linki panoya kopyalandı!'))
                .catch(err => {
                    console.error('Link kopyalanamadı:', err);
                    showError('Link otomatik kopyalanamadı. Manuel olarak kopyalayabilirsiniz.');
                });
            break;
        case '2':
            const tweetText = encodeURIComponent("Şu harika şarkıya bir bak: ");
            window.open(`https://twitter.com/intent/tweet?url=${encodeURIComponent(spotifyUrl)}&text=${tweetText}`, '_blank');
            break;
        default:
            // Geçersiz seçim veya iptal
            break;
    }
}

// --- Initialization and Main Logic ---

async function checkLoginStatus() {
    const userData = await fetchApi('/user_data');
    if (userData && !userData.error) {
        handleLoginUI(userData);
        // Giriş yapılmışsa kişisel önerileri otomatik getir (isteğe bağlı)
        // fetchUserRecommendations();
    } else {
        // Giriş yapılmamışsa veya token geçersizse
        handleLogoutUI();
    }
}

async function fetchInitialRecommendations() {
    if (!initialRecommendationsDiv) return;
    const recommendations = await fetchApi('/initial_recommendations');
    if (recommendations) {
        displayTracks(recommendations, initialRecommendationsDiv);
        initialRecommendationsDiv.style.display = 'block'; // Göster
    } else {
        initialRecommendationsDiv.innerHTML = '<p>Başlangıç önerileri alınamadı.</p>';
        initialRecommendationsDiv.style.display = 'block';
    }
}

async function fetchUserRecommendations() {
    if (!recommendationsDiv) return;
    // POST isteği olduğu için options ekliyoruz
    const response = await fetchApi('/recommendations', { method: 'POST' });
    if (response && response.recommendations) {
        displayTracks(response.recommendations, recommendationsDiv);
        if (response.message) {
            // Bilgi mesajını göstermek için bir alan eklenebilir
            console.info("Öneri Bilgisi:", response.message);
        }
    } else if (response && response.error) {
        // Hata fetchApi içinde gösterildi, burada sadece div'i temizleyebiliriz
        recommendationsDiv.innerHTML = '<p>Öneriler alınamadı.</p>';
    } else {
        recommendationsDiv.innerHTML = '<p>Öneriler alınamadı.</p>';
    }
}

async function fetchAndDisplayProfile() {
    if (!profileSection || !mainContent) return;

    const profileData = await fetchApi('/profile');

    if (profileData && !profileData.error) {
        profileSection.innerHTML = ''; // Önceki içeriği temizle

        // Kullanıcı Bilgisi
        const user = profileData.user;
        const profileHeader = document.createElement('div');
        profileHeader.classList.add('profile-header');
        const profilePic = user.images && user.images.length > 0 ? user.images[0].url : 'placeholder.png';
        profileHeader.innerHTML = `
            <img src="${profilePic}" alt="Profil Resmi" class="profile-pic">
            <h2>${user.display_name || user.id}</h2>
            ${user.email ? `<p>${user.email}</p>` : ''}
            <p><a href="${user.external_urls?.spotify || '#'}" target="_blank">Spotify Profili</a></p>
        `;
        profileSection.appendChild(profileHeader);

        // En Çok Dinlenen Sanatçılar
        if (profileData.top_artists && profileData.top_artists.length > 0) {
            const artistsSection = document.createElement('div');
            artistsSection.classList.add('profile-list-section');
            artistsSection.innerHTML = '<h3>En Çok Dinlenen Sanatçılar</h3>';
            const artistsList = document.createElement('div');
            artistsList.classList.add('profile-list', 'artist-list');
            profileData.top_artists.forEach(artist => {
                const artistPic = artist.images && artist.images.length > 0 ? artist.images[2]?.url || artist.images[0].url : 'placeholder.png';
                artistsList.innerHTML += `
                    <div class="profile-item">
                        <a href="${artist.external_urls?.spotify || '#'}" target="_blank">
                            <img src="${artistPic}" alt="${artist.name}" loading="lazy">
                            <span>${artist.name}</span>
                        </a>
                    </div>
                `;
            });
            artistsSection.appendChild(artistsList);
            profileSection.appendChild(artistsSection);
        }

        // En Çok Dinlenen Şarkılar
        if (profileData.top_tracks && profileData.top_tracks.length > 0) {
            const tracksSection = document.createElement('div');
            tracksSection.classList.add('profile-list-section');
            tracksSection.innerHTML = '<h3>En Çok Dinlenen Şarkılar</h3>';
            const tracksList = document.createElement('div');
            tracksList.classList.add('profile-list', 'track-list');
            profileData.top_tracks.forEach(track => {
                const trackPic = track.album?.images && track.album.images.length > 0 ? track.album.images[2]?.url || track.album.images[0].url : 'placeholder.png';
                tracksList.innerHTML += `
                    <div class="profile-item">
                         <a href="${track.external_urls?.spotify || '#'}" target="_blank">
                            <img src="${trackPic}" alt="${track.album?.name || ''}" loading="lazy">
                            <span>${track.name}</span>
                            <small>${track.artists.map(a => a.name).join(', ')}</small>
                        </a>
                    </div>
                `;
            });
            tracksSection.appendChild(tracksList);
            profileSection.appendChild(tracksSection);
        }

        // En Çok Dinlenen Türler
        if (profileData.top_genres && profileData.top_genres.length > 0) {
            const genresSection = document.createElement('div');
            genresSection.classList.add('profile-list-section');
            genresSection.innerHTML = '<h3>En Çok Dinlenen Türler</h3>';
            const genresList = document.createElement('ul'); // Liste olarak gösterelim
            genresList.classList.add('genre-list');
            profileData.top_genres.forEach(genrePair => {
                genresList.innerHTML += `<li>${genrePair[0]}</li>`; // Sadece tür adını göster
            });
            genresSection.appendChild(genresList);
            profileSection.appendChild(genresSection);
        }


        // Ana içeriği gizle, profili göster
        mainContent.style.display = 'none';
        profileSection.style.display = 'block';

    } else {
        // Hata fetchApi içinde gösterildi
        showError("Profil bilgileri alınamadı.");
    }
}

// --- Event Listeners Setup ---

if (loginButton) {
    loginButton.onclick = () => {
        window.location.href = `${backendUrl}/login`;
    };
}

if (logoutButton) {
    logoutButton.onclick = async () => {
        // Önce çalan sesi durdur
        if (currentlyPlayingAudio) {
            currentlyPlayingAudio.pause();
            currentlyPlayingAudio = null;
        }
        await fetchApi('/logout'); // Backend'de session'ı temizle
        userPlaylists = []; // Playlist cache'ini temizle
        handleLogoutUI();
    };
}

if (getRecommendationsButton) {
    getRecommendationsButton.onclick = fetchUserRecommendations;
}

if (showProfileButton) {
    showProfileButton.onclick = () => {
        if (profileSection && profileSection.style.display === 'block') {
            // Profil zaten açıksa ana içeriğe dön
            profileSection.style.display = 'none';
            mainContent.style.display = 'block';
        } else {
            // Profili getir ve göster
            fetchAndDisplayProfile();
        }
    };
}


// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    checkLoginStatus(); // Sayfa yüklendiğinde giriş durumunu kontrol et
});
