document.addEventListener('DOMContentLoaded', () => {
    const loginButton = document.getElementById('login-button');
    const userProfileDiv = document.getElementById('user-profile');
    const userNameH2 = document.getElementById('user-name');
    const userImage = document.getElementById('user-image');
    const recommendationsContainer = document.getElementById('recommendations-container');
    const getRecommendationsBtn = document.getElementById('getRecommendationsBtn');

    // --- Başlangıç Önerilerini Al ---
    async function fetchInitialRecommendations() {
        recommendationsContainer.innerHTML = '<p class="loading">Rastgele öneriler yükleniyor...</p>';
        try {
            // Yeni endpoint'e GET isteği
            const response = await fetch('http://127.0.0.1:5000/initial_recommendations');

            if (!response.ok) {
                let errorMsg = `Başlangıç önerileri alınamadı: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.error || errorMsg;
                } catch (e) { /* JSON parse edilemezse orijinal hatayı kullan */ }
                throw new Error(errorMsg);
            }

            const recommendations = await response.json();
            // Başlığı değiştirerek gösterelim
            displayRecommendations(recommendations, "Güne Başlarken Dinleyebileceklerin");

        } catch (error) {
            console.error('Error fetching initial recommendations:', error);
            recommendationsContainer.innerHTML = `<p class="error">${error.message}</p>`;
        }
    }


    // --- Kullanıcı Giriş Durumunu Kontrol Et ---
    async function checkLoginStatus() {
        try {
            const response = await fetch('http://127.0.0.1:5000/user_data', {
                method: 'GET',
                credentials: 'include' // Session cookie'lerini göndermek için önemli
            });

            if (response.ok) {
                const userData = await response.json();
                if (userData && !userData.login_required) {
                    // Kullanıcı giriş yapmış
                    displayUserProfile(userData);
                    loginButton.style.display = 'none'; // Login butonunu gizle
                    if (getRecommendationsBtn) {
                        getRecommendationsBtn.style.display = 'inline-flex'; // Öneri butonunu göster
                    }
                } else {
                    // Kullanıcı giriş yapmamış veya session süresi dolmuş
                    showLoginButton();
                }
            } else {
                // /user_data endpoint'i 401 döndürürse (login_required: true)
                showLoginButton();
            }
        } catch (error) {
            console.error('Error checking login status:', error);
            showLoginButton(); // Hata durumunda login butonunu göster
            // Başlangıç önerileri zaten yüklenmeye çalışıldığı için buraya hata mesajı eklemeyebiliriz.
            // recommendationsContainer.innerHTML = '<p class="error">Kullanıcı durumu kontrol edilirken bir hata oluştu.</p>';
        }
    }

    // --- Kullanıcı Profilini Göster ---
    function displayUserProfile(userData) {
        userNameH2.textContent = `Hoş Geldin, ${userData.display_name || userData.id}`;
        if (userData.images && userData.images.length > 0) {
            // En küçük profil resmini bulmaya çalış (genellikle sonuncusu)
            const profileImageUrl = userData.images[userData.images.length - 1]?.url || userData.images[0]?.url;
            if (profileImageUrl) {
                userImage.src = profileImageUrl;
                userImage.style.display = 'block'; // Profil resmini göster
            } else {
                userImage.style.display = 'none';
            }
        } else {
            userImage.style.display = 'none'; // Resim yoksa gizle
        }
        userProfileDiv.style.display = 'flex'; // Profil bölümünü göster
    }

    // --- Login Butonunu Göster ---
    function showLoginButton() {
        userProfileDiv.style.display = 'none'; // Profil bölümünü gizle
        loginButton.style.display = 'inline-flex'; // Login butonunu göster
        if (getRecommendationsBtn) {
            getRecommendationsBtn.style.display = 'none'; // Öneri butonunu gizle
        }
        // Başlangıç önerileri zaten gösterildiği için buradaki mesajı kaldırabiliriz.
        // recommendationsContainer.innerHTML = '<p>Şarkı önerilerini görmek için lütfen Spotify ile giriş yapın.</p>';
    }


    // --- Kullanıcı Geçmişine Göre Önerileri Almak İçin Buton Event Listener ---
    if (getRecommendationsBtn) {
        getRecommendationsBtn.addEventListener('click', async () => {
            recommendationsContainer.innerHTML = '<p class="loading">Sana özel öneriler yükleniyor...</p>';
            try {
                const response = await fetch('http://127.0.0.1:5000/recommendations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include'
                });

                if (!response.ok) {
                    let errorMsg = `HTTP error! status: ${response.status}`;
                    try {
                        const errorData = await response.json();
                        errorMsg = errorData.error || errorMsg;
                        if (errorData.login_required) {
                            errorMsg += " Lütfen tekrar giriş yapmayı deneyin.";
                            // Opsiyonel: Otomatik yönlendirme
                            // setTimeout(() => { window.location.href = 'http://127.0.0.1:5000/login'; }, 3000);
                        }
                    } catch (e) { console.error("Could not parse error response:", e); }
                    throw new Error(errorMsg);
                }

                const responseData = await response.json(); // Yanıt artık {recommendations: [], message?: ""} şeklinde
                const recommendations = responseData.recommendations;
                const message = responseData.message; // Varsayılan seed kullanıldıysa gelen mesaj

                // Başlığı ve mesajı (varsa) göstererek önerileri işle
                displayRecommendations(recommendations, "Sana Özel Öneriler", message);

            } catch (error) {
                console.error('Error fetching user recommendations:', error);
                recommendationsContainer.innerHTML = `<p class="error">Hata: ${error.message}</p>`;
            }
        });
    } else {
        console.error("Recommendation button (#getRecommendationsBtn) not found!");
    }

    // --- Önerileri Ekranda Göster (Başlık ve Mesaj parametreleri eklendi) ---
    function displayRecommendations(recommendations, title = "Öneriler", message = null) {
        recommendationsContainer.innerHTML = ''; // Önceki içeriği temizle

        // Başlığı ekle
        const titleElement = document.createElement('h3');
        titleElement.textContent = title;
        titleElement.style.textAlign = 'center';
        titleElement.style.marginBottom = '15px';
        recommendationsContainer.appendChild(titleElement);

        // Mesajı ekle (varsa)
        if (message) {
            const messageElement = document.createElement('p');
            messageElement.textContent = message;
            messageElement.style.textAlign = 'center';
            messageElement.style.fontStyle = 'italic';
            messageElement.style.color = '#666';
            messageElement.style.marginBottom = '15px';
            recommendationsContainer.appendChild(messageElement);
        }

        // Öneri yoksa mesaj göster
        if (!recommendations || recommendations.length === 0) {
            const noDataDiv = document.createElement('div'); // Yeni div oluştur
            noDataDiv.innerHTML = '<p>Uygun şarkı önerisi bulunamadı.</p>';
            recommendationsContainer.appendChild(noDataDiv); // Başlık/mesaj sonrası ekle
            return;
        }

        // Öneri listesini oluştur
        const list = document.createElement('ul');
        recommendations.forEach(song => {
            const listItem = document.createElement('li');

            // Albüm Kapağı
            const img = document.createElement('img');
            img.src = song.album_art_url || 'placeholder.png'; // Varsayılan resim yolu ekleyebilirsin
            img.alt = `${song.title || 'N/A'} Album Art`;
            img.onerror = () => { img.src = 'placeholder.png'; }; // Resim yüklenemezse varsayılanı göster
            listItem.appendChild(img);

            // Şarkı Bilgileri Konteyneri
            const infoDiv = document.createElement('div');

            // Başlık
            const titleStrong = document.createElement('strong');
            titleStrong.textContent = song.title || 'Başlık Yok';
            infoDiv.appendChild(titleStrong);

            // Sanatçı
            const artistSpan = document.createElement('span');
            artistSpan.textContent = song.artist || 'Sanatçı Yok';
            infoDiv.appendChild(artistSpan);

            // Spotify Linki (varsa)
            if (song.spotify_url) {
                const spotifyLink = document.createElement('a');
                spotifyLink.href = song.spotify_url;
                spotifyLink.target = '_blank';
                spotifyLink.innerHTML = '<i class="fab fa-spotify"></i> Spotify\'da Aç';
                infoDiv.appendChild(spotifyLink);
            }

            listItem.appendChild(infoDiv); // Şarkı bilgilerini li'ye ekle

            // Önizleme (varsa)
            if (song.preview_url) {
                const audio = document.createElement('audio');
                audio.controls = true;
                audio.src = song.preview_url;
                // Tarayıcı desteğini kontrol etmek iyi bir pratik olabilir
                // if (audio.canPlayType('audio/mpeg')) {
                listItem.appendChild(audio);
                // }
            }

            list.appendChild(listItem);
        });
        recommendationsContainer.appendChild(list);
    }

    // --- Sayfa Yüklendiğinde Başlangıç İşlemleri ---
    checkLoginStatus(); // Önce login durumunu kontrol et (asenkron)
    fetchInitialRecommendations(); // Sonra başlangıç önerilerini çek (asenkron)

    // --- URL'deki Hataları Kontrol Et (Spotify callback sonrası) ---
    const urlParams = new URLSearchParams(window.location.search);
    const errorParam = urlParams.get('error');
    if (errorParam) {
        let userMessage = "Bilinmeyen bir hata oluştu.";
        // Hata kodlarına göre mesajları ayarla
        switch (errorParam) {
            case 'spotify_auth_error':
                userMessage = "Spotify yetkilendirmesi sırasında bir hata oluştu.";
                break;
            case 'missing_code':
                userMessage = "Spotify'dan geçerli kod alınamadı.";
                break;
            case 'token_exchange_error':
                userMessage = "Spotify token alınırken bir sorun oluştu.";
                break;
            case 'spotify_api_error':
                userMessage = "Spotify verileri alınırken bir sorun oluştu. Lütfen tekrar giriş yapmayı deneyin.";
                break;
            case 'internal_error':
                userMessage = "Sunucu tarafında beklenmedik bir hata oluştu.";
                break;
        }

        // Hata mesajını kullanıcıya göster
        const errorDisplayDiv = document.createElement('div');
        errorDisplayDiv.className = 'error'; // CSS'te tanımlı hata stili
        errorDisplayDiv.textContent = `Hata: ${userMessage}`;
        // Main elementinin başına ekle
        const mainElement = document.querySelector('main');
        if (mainElement) {
            mainElement.prepend(errorDisplayDiv);
            // Bir süre sonra hata mesajını kaldır (opsiyonel)
            setTimeout(() => { errorDisplayDiv.remove(); }, 7000); // 7 saniye sonra kaldır
        } else {
            alert(`Hata: ${userMessage}`); // Main bulunamazsa alert göster
        }

        // URL'den hata parametresini temizle
        window.history.replaceState({}, document.title, window.location.pathname + window.location.hash); // Hash'i koru
    }

});
