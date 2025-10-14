// Premium Particle System
        const canvas = document.getElementById('particles-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const particles = [];
        const particleCount = window.innerWidth < 768 ? 50 : 100;

        class PremiumParticle {
            constructor() {
                this.x = Math.random() * canvas.width;
                this.y = Math.random() * canvas.height;
                this.size = Math.random() * 2 + 0.5;
                this.speedX = (Math.random() - 0.5) * 0.3;
                this.speedY = (Math.random() - 0.5) * 0.3;
                this.opacity = Math.random() * 0.3 + 0.1;
            }

            update() {
                this.x += this.speedX;
                this.y += this.speedY;

                if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
                if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
            }

            draw() {
                ctx.fillStyle = `rgba(255, 255, 255, ${this.opacity})`;
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
                ctx.fill();
            }
        }

        for (let i = 0; i < particleCount; i++) {
            particles.push(new PremiumParticle());
        }

        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw connection lines
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 120) {
                        ctx.strokeStyle = `rgba(255, 255, 255, ${0.05 * (1 - distance / 120)})`;
                        ctx.lineWidth = 0.5;
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.stroke();
                    }
                }
            }

            particles.forEach(particle => {
                particle.update();
                particle.draw();
            });

            requestAnimationFrame(animateParticles);
        }

        animateParticles();

        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });

        // Mobile Menu
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.getElementById('sidebar');
        const menuOverlay = document.getElementById('menuOverlay');

        function toggleMobileMenu() {
            mobileMenuBtn.classList.toggle('active');
            sidebar.classList.toggle('active');
            menuOverlay.classList.toggle('active');
            document.body.style.overflow = sidebar.classList.contains('active') ? 'hidden' : '';
        }

        mobileMenuBtn.addEventListener('click', toggleMobileMenu);
        menuOverlay.addEventListener('click', toggleMobileMenu);

        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    toggleMobileMenu();
                }
            });
        });

        // API Configuration
        const API_BASE = 'http://localhost:5000';

        // State
        let currentSong = null;
        let currentLyrics = [];
        let isPlaying = false;
        let sessionId = null;

        // DOM Elements
        const audioPlayer = document.getElementById('audioPlayer');
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const miniPlayer = document.getElementById('miniPlayer');
        const contentArea = document.getElementById('contentArea');
        const searchInput = document.getElementById('searchInput');

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            loadHomePage();
            setupEventListeners();
        });

        function setupEventListeners() {
            document.querySelectorAll('.nav-item').forEach(item => {
                item.addEventListener('click', () => {
                    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');
                    loadPage(item.dataset.page);
                });
            });

            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    if (e.target.value.trim()) {
                        searchContent(e.target.value);
                    }
                }, 500);
            });

            document.getElementById('playerClose').addEventListener('click', closeFullscreen);
            document.getElementById('miniExpandBtn').addEventListener('click', openFullscreen);
            document.getElementById('playPauseBtn').addEventListener('click', togglePlay);
            document.getElementById('miniPlayBtn').addEventListener('click', togglePlay);
            document.getElementById('nextBtn').addEventListener('click', playNext);
            document.getElementById('miniNextBtn').addEventListener('click', playNext);
            document.getElementById('prevBtn').addEventListener('click', playPrevious);
            document.getElementById('miniPrevBtn').addEventListener('click', playPrevious);

            audioPlayer.addEventListener('timeupdate', updateProgress);
            audioPlayer.addEventListener('ended', playNext);
            audioPlayer.addEventListener('loadedmetadata', () => {
                document.getElementById('totalTime').textContent = formatTime(audioPlayer.duration);
            });

            document.getElementById('progressTrack').addEventListener('click', (e) => {
                const rect = e.target.getBoundingClientRect();
                const percent = (e.clientX - rect.left) / rect.width;
                audioPlayer.currentTime = percent * audioPlayer.duration;
            });
        }

        async function loadPage(page) {
            switch(page) {
                case 'home': await loadHomePage(); break;
                case 'search': loadSearchPage(); break;
                case 'library': await loadLibrary(); break;
                case 'playlists': await loadPlaylists(); break;
                case 'trending': await loadTrending(); break;
                case 'podcasts': await loadPodcasts(); break;
                case 'mood': await loadMoods(); break;
                case 'genres': await loadGenres(); break;
            }
        }

        async function loadHomePage() {
            showLoading();

            try {
                const [chartsRes, moodRes] = await Promise.all([
                    fetch(`${API_BASE}/charts?limit=12`),
                    fetch(`${API_BASE}/mood?mood=happy&limit=12`)
                ]);

                const charts = await chartsRes.json();
                const mood = await moodRes.json();

                let html = '';

                if (charts.results && charts.results.length > 0) {
                    const featured = charts.results[0];
                    const thumbnail = featured.thumbnails?.[0] || '';
                    html += `
                        <div class="mega-featured">
                            <img class="featured-bg" src="${thumbnail}" alt="" onerror="this.style.display='none'">
                            <div class="featured-overlay">
                                <span class="featured-badge">Featured Track</span>
                                <h2 class="featured-title">${featured.title || 'Discover Music'}</h2>
                                <p class="featured-subtitle">Premium sound. Immersive experience.</p>
                                <div class="featured-actions">
                                    <button class="btn-primary" onclick="playSongFromCard('${encodeURIComponent(JSON.stringify(featured))}')">
                                        ▶️ Play Now
                                    </button>
                                    <button class="btn-secondary">Add to Library</button>
                                </div>
                            </div>
                        </div>
                    `;
                }

                if (charts.results && charts.results.length > 0) {
                    html += `
                        <div class="section">
                            <div class="section-header">
                                <div class="section-title-wrapper">
                                    <h2 class="section-title">Trending Now</h2>
                                    <p class="section-subtitle">The hottest tracks of the moment</p>
                                </div>
                                <button class="view-all">View All →</button>
                            </div>
                            <div class="cards-grid">
                                ${charts.results.slice(0, 6).map(song => createSongCard(song)).join('')}
                            </div>
                        </div>
                    `;
                }

                if (mood.playlists && mood.playlists.length > 0) {
                    html += `
                        <div class="section">
                            <div class="section-header">
                                <div class="section-title-wrapper">
                                    <h2 class="section-title">Curated Collections</h2>
                                    <p class="section-subtitle">Handpicked playlists for every mood</p>
                                </div>
                                <button class="view-all">Explore →</button>
                            </div>
                            <div class="cards-grid">
                                ${mood.playlists.slice(0, 6).map(playlist => createPlaylistCard(playlist)).join('')}
                            </div>
                        </div>
                    `;
                }

                contentArea.innerHTML = html;
            } catch (error) {
                showError('Unable to load content. Please ensure the API server is running.');
                console.error('Error:', error);
            }
        }

        function loadSearchPage() {
            contentArea.innerHTML = `
                <div class="section">
                    <h2 class="section-title">Search</h2>
                    <p style="color: var(--text-tertiary); margin-top: 24px; font-size: 16px;">Discover your favorite songs, artists, albums, and podcasts using the search bar above.</p>
                </div>
            `;
        }

        async function searchContent(query) {
            showLoading();

            try {
                const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}&page_size=24`);
                const data = await response.json();

                if (data.results && data.results.length > 0) {
                    const html = `
                        <div class="section">
                            <div class="section-header">
                                <div class="section-title-wrapper">
                                    <h2 class="section-title">Search Results</h2>
                                    <p class="section-subtitle">${data.results.length} results for "${query}"</p>
                                </div>
                            </div>
                            <div class="cards-grid">
                                ${data.results.map(song => createSongCard(song)).join('')}
                            </div>
                        </div>
                    `;
                    contentArea.innerHTML = html;
                } else {
                    showError('No results found. Try different keywords.');
                }
            } catch (error) {
                showError('Search failed. Please try again.');
                console.error('Search error:', error);
            }
        }

        async function loadTrending() {
            showLoading();

            try {
                const response = await fetch(`${API_BASE}/trending?type=all&limit=24`);
                const data = await response.json();

                let html = `
                    <div class="tabs">
                        <div class="tab active" data-tab="songs">Songs</div>
                        <div class="tab" data-tab="videos">Videos</div>
                        <div class="tab" data-tab="playlists">Playlists</div>
                    </div>
                `;

                if (data.data?.songs) {
                    html += `
                        <div class="tab-content active" data-content="songs">
                            <div class="section">
                                <h2 class="section-title">Trending Songs</h2>
                                <div class="cards-grid">
                                    ${data.data.songs.map(song => createSongCard(song)).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                }

                if (data.data?.videos) {
                    html += `
                        <div class="tab-content" data-content="videos">
                            <div class="section">
                                <h2 class="section-title">Trending Videos</h2>
                                <div class="cards-grid">
                                    ${data.data.videos.map(video => createVideoCard(video)).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                }

                if (data.data?.playlists) {
                    html += `
                        <div class="tab-content" data-content="playlists">
                            <div class="section">
                                <h2 class="section-title">Trending Playlists</h2>
                                <div class="cards-grid">
                                    ${data.data.playlists.map(playlist => createPlaylistCard(playlist)).join('')}
                                </div>
                            </div>
                        </div>
                    `;
                }

                contentArea.innerHTML = html;
                setupTabs();
            } catch (error) {
                showError('Failed to load trending content.');
                console.error('Trending error:', error);
            }
        }

        async function loadLibrary() {
            showLoading();

            try {
                const response = await fetch(`${API_BASE}/user/library?limit=50`);
                const data = await response.json();

                let html = '';

                if (data.songs && data.songs.length > 0) {
                    html += `
                        <div class="section">
                            <h2 class="section-title">Your Library</h2>
                            <div class="cards-grid">
                                ${data.songs.map(song => createSongCard(song)).join('')}
                            </div>
                        </div>
                    `;
                }

                contentArea.innerHTML = html || '<div class="loading"><p class="loading-text">Your library is empty.</p></div>';
            } catch (error) {
                showError('Failed to load library.');
                console.error('Library error:', error);
            }
        }

        async function loadPlaylists() {
            showLoading();

            try {
                const response = await fetch(`${API_BASE}/trending?type=playlists&limit=24`);
                const data = await response.json();

                if (data.data?.playlists && data.data.playlists.length > 0) {
                    const html = `
                        <div class="section">
                            <h2 class="section-title">Popular Playlists</h2>
                            <div class="cards-grid">
                                ${data.data.playlists.map(playlist => createPlaylistCard(playlist)).join('')}
                            </div>
                        </div>
                    `;
                    contentArea.innerHTML = html;
                } else {
                    showError('No playlists found.');
                }
            } catch (error) {
                showError('Failed to load playlists.');
                console.error('Playlists error:', error);
            }
        }

        async function loadPodcasts() {
            showLoading();

            try {
                const response = await fetch(`${API_BASE}/podcast/search?query=popular&limit=24`);
                const data = await response.json();

                if (data.podcasts && data.podcasts.length > 0) {
                    const html = `
                        <div class="section">
                            <h2 class="section-title">Popular Podcasts</h2>
                            <div class="cards-grid">
                                ${data.podcasts.map(podcast => createPodcastCard(podcast)).join('')}
                            </div>
                        </div>
                    `;
                    contentArea.innerHTML = html;
                } else {
                    showError('No podcasts found.');
                }
            } catch (error) {
                showError('Failed to load podcasts.');
                console.error('Podcasts error:', error);
            }
        }

        async function loadMoods() {
            const moods = ['happy', 'sad', 'party', 'chill', 'workout', 'romantic'];
            showLoading();

            try {
                const promises = moods.map(mood => fetch(`${API_BASE}/mood?mood=${mood}&limit=6`));
                const responses = await Promise.all(promises);
                const data = await Promise.all(responses.map(r => r.json()));

                let html = '';
                data.forEach((moodData, index) => {
                    if (moodData.playlists && moodData.playlists.length > 0) {
                        const title = moods[index].charAt(0).toUpperCase() + moods[index].slice(1);
                        html += `
                            <div class="section">
                                <div class="section-header">
                                    <div class="section-title-wrapper">
                                        <h2 class="section-title">${title} Vibes</h2>
                                        <p class="section-subtitle">Perfect for ${moods[index]} moments</p>
                                    </div>
                                </div>
                                <div class="cards-grid">
                                    ${moodData.playlists.map(playlist => createPlaylistCard(playlist)).join('')}
                                </div>
                            </div>
                        `;
                    }
                });

                contentArea.innerHTML = html || '<div class="loading"><p class="loading-text">No mood playlists found.</p></div>';
            } catch (error) {
                showError('Failed to load moods.');
                console.error('Moods error:', error);
            }
        }

        async function loadGenres() {
            showLoading();
            const genres = ['Pop', 'Rock', 'Hip-Hop', 'Electronic', 'Jazz', 'Classical', 'R&B', 'Country'];

            const html = `
                <div class="section">
                    <h2 class="section-title">Browse Genres</h2>
                    <div class="cards-grid">
                        ${genres.map(genre => `
                            <div class="music-card" onclick="searchContent('${genre}')">
                                <div class="card-image-wrapper">
                                    <div class="card-overlay"></div>
                                    <div class="play-btn">▶️</div>
                                </div>
                                <div class="card-info">
                                    <div class="card-title">${genre}</div>
                                    <div class="card-artist">Explore ${genre.toLowerCase()}</div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            contentArea.innerHTML = html;
        }

        function createSongCard(song) {
            const thumbnail = song.thumbnails?.[0] || '';
            const artists = song.artists?.join(', ') || 'Unknown Artist';

            return `
                <div class="music-card" onclick="playSongFromCard('${encodeURIComponent(JSON.stringify(song))}')">
                    <div class="card-image-wrapper">
                        ${thumbnail ? `<img class="card-image" src="${thumbnail}" alt="${song.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%231a1a1a%22 width=%22200%22 height=%22200%22/%3E%3C/svg%3E'">` : ''}
                        <div class="card-overlay"></div>
                        <div class="play-btn">▶️</div>
                    </div>
                    <div class="card-info">
                        <div class="card-title">${song.title || 'Untitled'}</div>
                        <div class="card-artist">${artists}</div>
                    </div>
                </div>
            `;
        }

        function createPlaylistCard(playlist) {
            const thumbnail = Array.isArray(playlist.thumbnails) ? playlist.thumbnails[0] : '';

            return `
                <div class="music-card" onclick="playPlaylist('${playlist.playlist_id || playlist.playlistId}')">
                    <div class="card-image-wrapper">
                        ${thumbnail ? `<img class="card-image" src="${thumbnail}" alt="${playlist.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%232a2a2a%22 width=%22200%22 height=%22200%22/%3E%3C/svg%3E'">` : ''}
                        <div class="card-overlay"></div>
                        <div class="play-btn">▶️</div>
                    </div>
                    <div class="card-info">
                        <div class="card-title">${playlist.title || 'Untitled'}</div>
                        <div class="card-artist">${playlist.track_count || 0} tracks</div>
                    </div>
                </div>
            `;
        }

        function createVideoCard(video) {
            const thumbnail = video.thumbnails?.[0] || '';
            return `
                <div class="music-card" onclick="playSongFromCard('${encodeURIComponent(JSON.stringify({videoId: video.videoId || video.video_id, title: video.title, artists: [video.channel || 'Unknown'], thumbnails: video.thumbnails}))}')">
                    <div class="card-image-wrapper">
                        ${thumbnail ? `<img class="card-image" src="${thumbnail}" alt="${video.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%232a2a2a%22 width=%22200%22 height=%22200%22/%3E%3C/svg%3E'">` : ''}
                        <div class="card-overlay"></div>
                        <div class="play-btn">▶️</div>
                    </div>
                    <div class="card-info">
                        <div class="card-title">${video.title || 'Untitled'}</div>
                        <div class="card-artist">${video.channel || 'Unknown'}</div>
                    </div>
                </div>
            `;
        }

        function createPodcastCard(podcast) {
            const thumbnail = Array.isArray(podcast.thumbnails) ? podcast.thumbnails[0] : '';

            return `
                <div class="music-card" onclick="playPodcast('${podcast.browseId}')">
                    <div class="card-image-wrapper">
                        ${thumbnail ? `<img class="card-image" src="${thumbnail}" alt="${podcast.title}" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22%3E%3Crect fill=%22%232a2a2a%22 width=%22200%22 height=%22200%22/%3E%3C/svg%3E'">` : ''}
                        <div class="card-overlay"></div>
                        <div class="play-btn">▶️</div>
                    </div>
                    <div class="card-info">
                        <div class="card-title">${podcast.title || 'Untitled'}</div>
                        <div class="card-artist">${podcast.author || 'Unknown'}</div>
                    </div>
                </div>
            `;
        }

        window.playSongFromCard = async function(encodedSong) {
            const song = JSON.parse(decodeURIComponent(encodedSong));
            await playSong(song);
        };

        async function playSong(song) {
            try {
                currentSong = song;

                const queueRes = await fetch(`${API_BASE}/song/${song.videoId}/upnext/start`, {method: 'POST'});
                const queueData = await queueRes.json();
                sessionId = queueData.session_id;

                const streamRes = await fetch(`${API_BASE}/stream/${song.videoId}?quality=high`);
                const streamData = await streamRes.json();

                audioPlayer.src = streamData.stream_url;
                audioPlayer.play();
                isPlaying = true;

                updatePlayerUI(song);
                miniPlayer.classList.add('active');

                await loadLyrics(song.videoId);

            } catch (error) {
                console.error('Play error:', error);
                alert('Failed to play song. Please try again.');
            }
        }

        function updatePlayerUI(song) {
            const thumbnail = song.thumbnails?.[0] || '';
            const artists = song.artists?.join(', ') || 'Unknown Artist';

            document.getElementById('playerTitle').textContent = song.title || 'Untitled';
            document.getElementById('playerArtist').textContent = artists;
            document.getElementById('playerArtwork').src = thumbnail;
            document.getElementById('playerBg').style.backgroundImage = `url('${thumbnail}')`;

            document.getElementById('miniTitle').textContent = song.title || 'Untitled';
            document.getElementById('miniArtist').textContent = artists;
            document.getElementById('miniArtwork').src = thumbnail;

            updatePlayButtons();
        }

        async function loadLyrics(videoId) {
            const lyricsPanel = document.getElementById('lyricsPanel');
            lyricsPanel.innerHTML = '<div class="lyric-line">Loading synced lyrics...</div>';

            try {
                const response = await fetch(`${API_BASE}/song/${videoId}/lyrics`);
                const data = await response.json();

                if (data.lyrics && data.lyrics.length > 0) {
                    currentLyrics = data.lyrics;
                    displayLyrics();
                } else {
                    lyricsPanel.innerHTML = '<div class="lyric-line">No lyrics available</div>';
                }
            } catch (error) {
                lyricsPanel.innerHTML = '<div class="lyric-line">Failed to load lyrics</div>';
                console.error('Lyrics error:', error);
            }
        }

        function displayLyrics() {
            const lyricsPanel = document.getElementById('lyricsPanel');
            lyricsPanel.innerHTML = currentLyrics.map((line, index) => 
                `<div class="lyric-line" data-index="${index}" data-start="${line.start || 0}" data-end="${line.end || 999999}">${line.text || line}</div>`
            ).join('');

            audioPlayer.addEventListener('timeupdate', syncLyrics);
        }

        function syncLyrics() {
            if (currentLyrics.length === 0) return;

            const currentTime = audioPlayer.currentTime;

            currentLyrics.forEach((line, index) => {
                const lineElement = document.querySelector(`.lyric-line[data-index="${index}"]`);
                if (!lineElement) return;

                const start = parseFloat(lineElement.dataset.start) || 0;
                const end = parseFloat(lineElement.dataset.end) || 999999;

                if (currentTime >= start && currentTime < end) {
                    lineElement.classList.add('active');
                    lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                } else {
                    lineElement.classList.remove('active');
                }
            });
        }

        function togglePlay() {
            if (isPlaying) {
                audioPlayer.pause();
                isPlaying = false;
            } else {
                audioPlayer.play();
                isPlaying = true;
            }
            updatePlayButtons();
        }

        function updatePlayButtons() {
            const icon = isPlaying ? '⏸️' : '▶️';
            document.getElementById('playPauseBtn').textContent = icon;
            document.getElementById('miniPlayBtn').textContent = icon;
        }

        async function playNext() {
            if (!sessionId) return;

            try {
                const response = await fetch(`${API_BASE}/song/upnext/next/${sessionId}`, {method: 'POST'});
                const data = await response.json();

                if (data.current) {
                    await playSong(data.current);
                }
            } catch (error) {
                console.error('Next error:', error);
            }
        }

        function playPrevious() {
            audioPlayer.currentTime = 0;
        }

        function updateProgress() {
            const progress = (audioPlayer.currentTime / audioPlayer.duration) * 100;
            document.getElementById('progressFill').style.width = progress + '%';
            document.getElementById('currentTime').textContent = formatTime(audioPlayer.currentTime);
        }

        async function playPlaylist(playlistId) {
            try {
                const response = await fetch(`${API_BASE}/playlist?id=${playlistId}&limit=100`);
                const data = await response.json();

                if (data.tracks && data.tracks.length > 0) {
                    await playSong(data.tracks[0]);
                }
            } catch (error) {
                console.error('Playlist error:', error);
            }
        }

        async function playPodcast(browseId) {
            try {
                const response = await fetch(`${API_BASE}/podcast/${browseId}/episodes`);
                const data = await response.json();

                if (data.episodes && data.episodes.length > 0) {
                    const episode = data.episodes[0];
                    await playSong({
                        videoId: episode.videoId,
                        title: episode.title,
                        artists: [data.author || 'Podcast'],
                        thumbnails: episode.thumbnails || []
                    });
                }
            } catch (error) {
                console.error('Podcast error:', error);
            }
        }

        function openFullscreen() {
            fullscreenPlayer.classList.add('active');
            miniPlayer.classList.remove('active');
            document.body.style.overflow = 'hidden';
        }

        function closeFullscreen() {
            fullscreenPlayer.classList.remove('active');
            miniPlayer.classList.add('active');
            document.body.style.overflow = '';
        }

        function setupTabs() {
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    const tabName = tab.dataset.tab;

                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');

                    document.querySelectorAll('.tab-content').forEach(content => {
                        content.classList.remove('active');
                    });

                    document.querySelector(`[data-content="${tabName}"]`)?.classList.add('active');
                });
            });
        }

        function formatTime(seconds) {
            if (isNaN(seconds)) return '0:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        }

        function showLoading() {
            contentArea.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p class="loading-text">Loading premium content...</p>
                </div>
            `;
        }

        function showError(message) {
            contentArea.innerHTML = `
                <div class="loading">
                    <p class="loading-text">${message}</p>
                </div>
            `;
        }