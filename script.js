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

// let currentlyPlayingAudio = null; // ÖNİZLEME KALDIRILDI - Bu satır silindi veya yorum satırı yapıldı
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
            handleLogoutUI(); // Login gerekli ise logout olmuş gibi göster
            showError("Oturum süresi doldu veya giriş yapmanız gerekiyor.");
            return null; // Hata durumunda null dön
        }

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
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

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return await response.json();
        } else {
            return { success: true };
        }

    } catch (error) {
        console.error(`API isteği hatası (${endpoint}):`, error);
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
        showProfileButton.style.display = 'inline-block';
        userInfoDiv.style.display = 'block';
        if (initialRecommendationsDiv) initialRecommendationsDiv.style.display = 'none';
        if (recommendationsDiv) recommendationsDiv.innerHTML = '';
        if (profileSection) profileSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block';

        if (recommendationsDiv) {
            recommendationsDiv.innerHTML = `<h2>Merhaba ${userData.display_name || userData.id}! Yeni öneriler almak için 'Şarkı Öner!' butonuna tıklayın veya profilinizi görüntüleyin.</h2>`;
        }
    }
}

function handleLogoutUI() {
    if (userInfoDiv && loginButton && logoutButton && getRecommendationsButton && showProfileButton) {
        userInfoDiv.textContent = '';
        loginButton.style.display = 'inline-block';
        logoutButton.style.display = 'none';
        getRecommendationsButton.style.display = 'none';
        showProfileButton.style.display = 'none';
        userInfoDiv.style.display = 'none';
        if (recommendationsDiv) recommendationsDiv.innerHTML = '';
        if (profileSection) profileSection.innerHTML = '';
        if (profileSection) profileSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block';

        if (initialRecommendationsDiv) initialRecommendationsDiv.style.display = 'none';
        if (recommendationsDiv) {
            recommendationsDiv.innerHTML = `<h2>Hoş Geldiniz! Müzik keşfetmeye başlamak için lütfen giriş yapın.</h2>`;
        }
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

        const albumArt = track.album_art_url || 'placeholder.png';
        const title = track.title || 'Bilinmeyen Şarkı';
        const artist = track.artist || 'Bilinmeyen Sanatçı';
        const spotifyUrl = track.spotify_url;
        // const previewUrl = track.preview_url; // ÖNİZLEME KALDIRILDI
        const trackId = track.id;

        trackElement.innerHTML = `
            <img src="${albumArt}" alt="Albüm Kapağı - ${title}" class="album-art">
            <div class="song-info">
                <p class="title">${title}</p>
                <p class="artist">${artist}</p>
            </div>
            <div class="song-actions">
                <!-- ÖNİZLEME BUTONU KALDIRILDI -->
                <button class="action-btn add-playlist-btn" data-track-id="${trackId}" title="Playlist'e Ekle">➕</button>
                ${spotifyUrl ? `<a href="${spotifyUrl}" target="_blank" class="action-btn spotify-link-btn" title="Spotify'da Aç">🎵</a>` : ''}
                <button class="action-btn share-btn" data-spotify-url="${spotifyUrl || ''}" title="Paylaş">🔗</button>
             </div>
             <!-- ÖNİZLEME AUDIO ELEMENTİ KALDIRILDI -->
        `;

        containerElement.appendChild(trackElement);
    });

    // Yeni eklenen butonlara event listener'ları ata
    attachActionListeners(containerElement);
}

function attachActionListeners(container) {
    // ÖNİZLEME BUTONU EVENT LISTENER'I KALDIRILDI
    // container.querySelectorAll('.preview-btn:not(.disabled)').forEach(button => {
    //     button.onclick = handlePreviewClick;
    // });

    container.querySelectorAll('.add-playlist-btn').forEach(button => {
        button.onclick = handleAddToPlaylistClick;
    });
    container.querySelectorAll('.share-btn').forEach(button => {
        button.onclick = handleShareClick;
    });

    // ÖNİZLEME AUDIO EVENT LISTENER'LARI KALDIRILDI
    // container.querySelectorAll('.preview-audio').forEach(audio => {
    //     audio.onended = (event) => { ... };
    //     audio.onerror = (event) => { ... };
    // });
}

// --- Event Handlers ---

// ÖNİZLEME FONKSİYONU KALDIRILDI
// function handlePreviewClick(event) { ... }

async function handleAddToPlaylistClick(event) {
    const trackId = event.target.dataset.trackId;
    if (!trackId) return;

    if (userPlaylists.length === 0) {
        const playlistsData = await fetchApi('/playlists');
        if (!playlistsData || !Array.isArray(playlistsData)) {
            showError("Playlistler alınamadı veya geçersiz formatta.");
            return;
        }
        userPlaylists = playlistsData;
    }

    if (userPlaylists.length === 0) {
        showError("Hiç playlist'iniz bulunamadı veya alınamadı.");
        return;
    }

    // TODO: Burayı daha kullanıcı dostu bir modal ile değiştir.
    let playlistOptions = userPlaylists.map((pl, index) => `${index + 1}: ${pl.name}`).join('\n');
    const choice = prompt(`Şarkıyı hangi playlist'e eklemek istersiniz?\n(Numara girin):\n${playlistOptions}`);

    if (choice === null || choice.trim() === '') return;

    const choiceIndex = parseInt(choice) - 1;
    if (isNaN(choiceIndex) || choiceIndex < 0 || choiceIndex >= userPlaylists.length) {
        showError("Geçersiz playlist numarası.");
        return;
    }

    const selectedPlaylistId = userPlaylists[choiceIndex].id;
    const selectedPlaylistName = userPlaylists[choiceIndex].name;

    const result = await fetchApi('/playlist/add', {
        method: 'POST',
        body: JSON.stringify({
            playlist_id: selectedPlaylistId,
            track_uri: trackId // Backend ID veya URI kabul ediyor (Backend'e göre ayarla)
        })
    });

    if (result && result.message) {
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

    if (navigator.share) {
        navigator.share({
            title: 'Spotify Şarkı Önerisi',
            text: 'Şu harika şarkıya bir bak!',
            url: spotifyUrl,
        })
            .then(() => console.log('Başarılı paylaşım'))
            .catch((error) => {
                console.error('Paylaşım hatası:', error)
                copyToClipboard(spotifyUrl);
            });
    } else {
        copyToClipboard(spotifyUrl);
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text)
        .then(() => alert('Spotify linki panoya kopyalandı!'))
        .catch(err => {
            console.error('Link kopyalanamadı:', err);
            showError('Link otomatik kopyalanamadı. Manuel olarak kopyalayabilirsiniz.');
        });
}


// --- Initialization and Main Logic ---

async function checkLoginStatus() {
    const userData = await fetchApi('/user_data');
    if (userData && !userData.error) {
        handleLoginUI(userData);
    } else {
        handleLogoutUI();
    }
}

async function fetchInitialRecommendations() {
    // Bu fonksiyon artık kullanılmıyor.
    console.log("fetchInitialRecommendations çağrıldı ama artık kullanılmıyor.");
}

async function fetchUserRecommendations() {
    if (!recommendationsDiv) return;
    recommendationsDiv.innerHTML = ''; // Mevcut içeriği temizle
    const response = await fetchApi('/recommendations', { method: 'POST' });
    if (response && response.recommendations) {
        displayTracks(response.recommendations, recommendationsDiv);
        if (response.message) {
            console.info("Öneri Bilgisi:", response.message);
            const infoMsg = document.createElement('p');
            infoMsg.textContent = response.message;
            infoMsg.style.textAlign = 'center';
            infoMsg.style.marginBottom = '10px';
            recommendationsDiv.prepend(infoMsg);
        }
    } else if (response && response.error) {
        recommendationsDiv.innerHTML = '<p>Öneriler alınamadı.</p>';
    } else {
        recommendationsDiv.innerHTML = '<p>Öneriler alınırken bir sorun oluştu.</p>';
    }
}

async function fetchAndDisplayProfile() {
    if (!profileSection || !mainContent) return;

    if (profileSection.style.display === 'block') {
        profileSection.style.display = 'none';
        mainContent.style.display = 'block';
        return;
    }

    const profileData = await fetchApi('/profile');

    if (profileData && !profileData.error) {
        profileSection.innerHTML = ''; // Önceki içeriği temizle

        // --- Profil içeriğini oluşturma fonksiyonları ---
        function createProfileHeader(user) {
            const header = document.createElement('div');
            header.classList.add('profile-header');
            const profilePic = user.images?.[0]?.url || 'placeholder.png';
            header.innerHTML = `
                <img src="${profilePic}" alt="Profil Resmi" class="profile-pic">
                <h2>${user.display_name || user.id}</h2>
                ${user.email ? `<p><a href="mailto:${user.email}">${user.email}</a></p>` : ''}
                <p><a href="${user.external_urls?.spotify || '#'}" target="_blank" rel="noopener noreferrer">Spotify Profili</a></p>
            `;
            return header;
        }

        function createProfileSection(title, items, renderItem) {
            if (!items || items.length === 0) return null;

            const section = document.createElement('div');
            section.classList.add('profile-list-section');
            section.innerHTML = `<h3>${title}</h3>`;
            const list = document.createElement('div');
            list.classList.add('profile-list');
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
                listItem.textContent = genrePair[0];
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

        mainContent.style.display = 'none';
        profileSection.style.display = 'block';

    } else {
        showError("Profil bilgileri alınamadı.");
        profileSection.style.display = 'none';
        mainContent.style.display = 'block';
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
        // ÖNİZLEME KALDIRILDI - Çalan sesi durdurma kodu silindi
        await fetchApi('/logout');
        userPlaylists = [];
        handleLogoutUI();
    };
}

if (getRecommendationsButton) {
    getRecommendationsButton.onclick = () => {
        if (profileSection) profileSection.style.display = 'none';
        if (mainContent) mainContent.style.display = 'block';
        fetchUserRecommendations();
    }
}

if (showProfileButton) {
    showProfileButton.onclick = fetchAndDisplayProfile;
}


// --- Initial Load ---
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error');
    const messageParam = urlParams.get('message');

    if (errorParam) {
        showError(messageParam || `Bir hata oluştu (${errorParam})`);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    checkLoginStatus();
});
