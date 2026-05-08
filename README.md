# LocalBeat: Interactive Music Quiz Game

A sophisticated web-based music quiz game with singleplayer and multiplayer modes, featuring AI-based music analysis, real-time audio visualization, and YouTube playlist support.

## Features

### Core Gameplay
- **Singleplayer Mode**: Play against yourself with customizable difficulty
- **Multiplayer Mode**: Play with 2-6 friends in real-time
- **Two Game Modes**:
  - Classic: Multiple choice (4 options)
  - Typing: Type artist name and song title
- **Intelligent Question Generation** (20-20-60 Rule):
  - 20% Intro guesses (from start of song)
  - 20% Outro guesses (from end of song)
  - 60% Climax guesses (AI-detected drop points)

### Audio & Visualization
- **Real-time Audio Spectrum**: Beat-synced visualization in background
- **Music Analysis**: Librosa AI for detecting musical peaks
- **Audio Sources**:
  - Local music library (MP3, FLAC, WAV, OGG, M4A)
  - YouTube playlists (for multiplayer)
- **Smart Caching**: Audio analysis cached for performance

### Multiplayer Features
- **Room System**: 6-character RNG codes for joining
- **Host Controls**: Create room, configure settings, manage players
- **Ready System**: All players must confirm before game starts
- **Local & Internet Modes**: Same-network or online play
- **Real-time Sync**: Polling-based player synchronization

### User Features
- **Authentication**: Register, login, or guest mode
- **Multi-language**: English and Bahasa Indonesia
- **User Profiles**: Track play history
- **Responsive Design**: Works on desktop and mobile

## Installation

### Prerequisites
- Python 3.8+
- Pip
- (Optional) PostgreSQL for production

### Local Setup

1. **Clone the repository**
```bash
git clone <repo-url>
cd LocalBeat-alpha
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env and set:
# - MUSIC_FOLDER: path to your music library
# - SECRET_KEY: random secret for Flask
# - DATABASE_URL: (optional, default uses SQLite)
```

5. **Initialize database**
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

6. **Run application**
```bash
python app.py
```

The app will automatically open at http://localhost:5000

## Usage

### Singleplayer
1. Log in or enter as guest
2. Click "Singleplayer"
3. Configure game mode and question count
4. Listen to song clips and answer questions

### Multiplayer
1. **Host**: Create room, configure settings, share code
2. **Join**: Enter room code from host
3. Click "Ready" when prepared
4. Host clicks "Start Game"
5. All players play simultaneously with independent scoring

## Project Structure

```
LocalBeat-alpha/
├── app.py                      # Main Flask application
├── models.py                   # SQLAlchemy models
├── requirements.txt            # Python dependencies
├── .env.example               # Environment template
├── static/
│   ├── css/style.css          # Styling
│   └── js/
│       ├── landing.js         # Landing visualization
│       └── quiz.js            # Game logic
├── templates/
│   ├── auth.html              # Authentication
│   ├── mode_selector.html     # Game mode selection
│   ├── singleplayer.html      # Singleplayer setup
│   ├── multiplayer.html       # Multiplayer menu
│   ├── host_setup.html        # Host configuration
│   ├── join_setup.html        # Join room
│   └── quiz.html              # Game interface
├── GAMEPLAY_TUTORIAL.txt      # User guide
└── DEVELOPER_DOCUMENTATION.txt # Technical docs
```

## Deployment to Vercel

### Prerequisites
- Vercel account
- PostgreSQL database (Supabase, Heroku Postgres, or similar)
- GitHub repository

### Steps

1. **Setup PostgreSQL**
   - Create PostgreSQL database (e.g., Supabase free tier)
   - Get connection string

2. **Deploy to Vercel**
```bash
npm i -g vercel
vercel
```

3. **Configure Environment Variables**
In Vercel dashboard:
```
DATABASE_URL=postgresql://user:pass@host:port/dbname
SECRET_KEY=<random-secret>
MUSIC_FOLDER=/tmp/music  # or cloud storage path
FLASK_ENV=production
```

4. **Important Notes**
   - Local music library scanning won't work on Vercel (serverless limitation)
   - Use YouTube playlist mode for multiplayer on production
   - Database must be external (PostgreSQL, not SQLite)
   - Max function runtime: 60 seconds

### Alternative: Render.com or Railway

These services have better Python support:
- Better WebSocket support
- Longer execution times
- File system persistence (limited)

## Technologies Used

**Backend**
- Flask: Web framework
- SQLAlchemy: ORM
- Librosa: Audio analysis
- yt-dlp: YouTube integration
- Bcrypt: Password hashing

**Frontend**
- Vanilla JavaScript
- Web Audio API
- Canvas
- CSS3 animations

**Database**
- SQLite: Development
- PostgreSQL: Production

## API Endpoints

### Authentication
- `POST /api/register` - Create account
- `POST /api/login` - Login
- `POST /api/guest` - Guest mode
- `GET /logout` - Logout

### Gameplay
- `GET /api/question` - Get next question
- `POST /submit_answer` - Submit answer
- `GET /stream_audio` - Stream audio file
- `GET /api/bgm` - Get background music

### Multiplayer
- `POST /api/room/create` - Create room
- `POST /api/room/join` - Join room
- `GET /api/room/<id>` - Get room info
- `POST /api/room/<id>/ready` - Toggle ready status
- `POST /api/room/<id>/start` - Start game (host only)

## Configuration

### Environment Variables
- `FLASK_ENV`: development or production
- `SECRET_KEY`: Flask secret key
- `DATABASE_URL`: Database connection string
- `MUSIC_FOLDER`: Path to music library

### Game Settings
Modify in `app.py`:
- `TOTAL_QUESTIONS`: Default 10 (configurable per session)
- `REPLAY_LIMIT`: 3 plays per question
- `CLIP_DURATION`: 15 seconds per clip
- `YOUTUBE_PLAYLIST_LIMIT`: 50 songs max

## Troubleshooting

### Audio Not Playing
- Check browser audio permissions
- Verify music files are in supported format
- Check browser console for CORS errors

### Database Errors
- Ensure database URL is correct
- Run migrations if using PostgreSQL
- Check file permissions for SQLite

### Multiplayer Sync Issues
- Verify network connectivity
- Check room code validity
- Ensure all players use same game version

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## Performance Considerations

- Audio analysis cached after first play
- Spectrum visualization optimized with requestAnimationFrame
- Database queries indexed for common filters
- Lazy loading for playlist entries

## Known Limitations

- Local music scanning not available on Vercel (serverless)
- YouTube audio streaming limited (privacy/CORS)
- WebSocket not available on Vercel (using polling instead)
- Multiplayer limited to 6 players per room

## License

MIT

## Support

For issues, questions, or feature requests:
- See `GAMEPLAY_TUTORIAL.txt` for user guide
- See `DEVELOPER_DOCUMENTATION.txt` for technical details
- Check browser console (F12) for error messages

## Changelog

### Version 2.0 (Current)
- Multiplayer support (2-6 players)
- User authentication system
- YouTube playlist support
- Multi-language support
- Real-time spectrum visualization
- Ready/start game mechanics
- Room code system

### Version 1.0
- Singleplayer only
- Local music library
- Classic and typing modes
- Audio visualization

---

**Made with love for music lovers everywhere**


### 🛠️ Tech Stack
* **Backend:** Python 3.x (Flask)
* **Audio Processing:** Librosa, NumPy, Mutagen
* **Frontend:** HTML5, CSS3 (Keyframes Animation), Vanilla JS
* **Audio Engine:** Web Audio API (Client-side Visualizer)

### 🚀 Installation & Usage

1.  **Clone & Setup**
    ```bash
    git clone [https://github.com/username/LocalBeat.git](https://github.com/briliant-tm/LocalBeat.git)
    cd LocalBeat
    pip install -r requirements.txt
    ```

2.  **Configure Music Path (IMPORTANT!)**
    Open `app.py` and find this line at the top:
    ```python
    # REPLACE WITH YOUR MUSIC FOLDER PATH
    MUSIC_FOLDER = r"D:\MyMusicCollection"
    ```

3.  **Run the Game**
    For the best experience (silent console), double-click:
    👉 **`Launcher.vbs`**
    
    *(Or run `python app.py` manually).*

---

<div id="-versi-bahasa-indonesia"></div>

## 🇮🇩 Versi Bahasa Indonesia

> **"Ubah folder musik 3GB-mu jadi game ritme arcade tanpa ribet."**

**LocalBeat** adalah aplikasi web berbasis Python (Flask) yang mengubah koleksi musik lokal (MP3/FLAC/WAV) menjadi game kuis tebak lagu yang interaktif, cerdas, dan visualnya memukau. Tidak perlu database SQL, tidak perlu edit metadata manual. **Tinggal run dan main.**

### ✨ Fitur Utama

#### 🧠 Otak (Kecerdasan Backend)
* **Auto-Scan Database:** Membaca ribuan lagu dari folder lokal secara rekursif.
* **Deteksi "Drop" Pintar:** Menggunakan **Librosa AI** untuk menganalisis waveform dan mencari bagian lagu yang paling "ramai" (Reff/Drop) secara otomatis.
* **Aturan 20-20-60:** Variasi soal dinamis:
    * 20% Tebak Intro (00:00).
    * 20% Tebak Outro (Ending).
    * 60% Tebak Climax (Hasil Analisis AI).
* **Smart Caching:** Analisis audio berat hanya dilakukan sekali, lalu disimpan ke JSON agar gameplay berikutnya instan.
* **Protokol Nama Bersih:** Otomatis membuang ekstensi (`.mp3`) dan mendeteksi pemisah (` - `) untuk memisahkan Artis dan Judul.

#### 👁️ Mata (Pengalaman Visual)
* **Visualizer Cermin:** Spektrum audio *real-time* yang memantul simetris di tengah layar (Web Audio API).
* **Background Dinamis:** Latar belakang bereaksi terhadap intensitas *Bass* lagu.
* **Transisi Glitch & CRT:** Transisi antar-soal menggunakan efek *Cyberpunk Glitch* dan *TV Switch-off* yang agresif ("Watahel" moment).
* **Lobby Jukebox:** Landing page berfungsi sebagai music player dengan partikel debu dan notifikasi "Now Playing" ala Osu!.

### 🎮 Mode Permainan

1.  **MODE KLASIK (Pilihan Ganda)**
    * Gameplay santai. 1 Jawaban Benar vs 3 Pengecoh.
    * Progress bar *real-time* (bukan animasi CSS palsu).
    * Batas 3x Replay per soal.

2.  **MODE HARDCORE (Ujian Mengetik)**
    * **Smart Parsing:** Menebak Artis dan Judul secara terpisah.
    * **Split Scoring:** Poin Artis (50) dibagi rata jika ada kolaborasi (feat/&), Poin Judul (50).
    * **Deteksi Asing:** File dengan karakter Jepang/Korea/Asing otomatis beralih ke mode **"Tebak Nama Folder"**.

### 🛠️ Teknologi
* **Backend:** Python 3.x (Flask)
* **Audio Processing:** Librosa, NumPy, Mutagen
* **Frontend:** HTML5, CSS3 (Keyframes Animation), Vanilla JS
* **Audio Engine:** Web Audio API (Client-side Visualizer)

### 🚀 Cara Install & Main

1.  **Clone & Setup**
    ```bash
    git clone [https://github.com/username/LocalBeat.git](https://github.com/briliant-tm/LocalBeat.git)
    cd LocalBeat
    pip install -r requirements.txt
    ```

2.  **Konfigurasi Folder Musik (PENTING!)**
    Buka file `app.py` dan cari baris ini di bagian atas:
    ```python
    # GANTI DENGAN PATH FOLDER MUSIK KAMU
    MUSIC_FOLDER = r"D:\KoleksiLagu\GedeBanget"
    ```

3.  **Jalankan Game**
    Untuk pengalaman terbaik tanpa jendela CMD yang mengganggu, klik dua kali file:
    👉 **`Launcher.vbs`**
    
    *(Atau jalankan `python app.py` secara manual di terminal).*

---

## 🕹️ Gameplay Mechanics (Mekanisme Skor)

Sistem penilaian **Hardcore Mode** LocalBeat sangat adil dan mendetail:

| Case / Kasus | Input User | Score | Logic / Logika |
| :--- | :--- | :--- | :--- |
| **Title / Judul** | "Numb" (Target: Numb) | **+50** | Fuzzy Match |
| **Solo Artist** | "Tulus" (Target: Tulus) | **+50** | Exact Match |
| **Duo Artist** | "Skrillex" (Target: Skrillex, Diplo) | **+25** | 50 Poin / 2 Artists |
| **Foreign/Folder** | "Anime" (Target: Folder Anime) | **+100** | Fallback Mode |

## 📂 Project Structure

```text
LocalBeat/
├── app.py              # Main Brain (Flask Server & Audio Logic)
├── audio_cache.json    # Librosa analysis cache (Auto-gen)
├── game_history.json   # Song history to avoid repetition (Auto-gen)
├── Launcher.vbs        # Silent Mode Launcher
├── Play.bat            # Batch file executor
├── static/
│   ├── css/style.css   # Styling (Glitch, Animations, Layout)
│   └── js/             # Frontend Logic (Visualizer, Game Loop)
└── templates/          # HTML Pages (Lobby & Arena)

```

---

## 📜 License

Project ini dibuat untuk tujuan edukasi dan hiburan pribadi ("Project Iseng").
**V-R1L Production © 2026**

Enjoy the beat! 🎧🔥

```

```
