import os
import random
import json
import time
import hashlib
import threading
import webbrowser
import re
import string
import uuid
import subprocess
import urllib.parse
import numpy as np
import librosa
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, jsonify, send_file, request, session, redirect, url_for
from flask_cors import CORS
from models import (
    db, bcrypt, User, GameRoom, RoomPlayer, GameSession, 
    PlayerScore, QuestionCache, PlayHistory
)
from urllib.parse import urljoin

# ========================================
# APPLICATION SETUP
# ========================================
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'localbeat_vr1l_secu@re_key_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///localbeat.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)
bcrypt.init_app(app)
CORS(app)
with app.app_context():
    db.create_all()

MUSIC_FOLDER = os.environ.get('MUSIC_FOLDER', r"E:\Kakak\Music\Music")  # Ganti dengan path folder musik Anda
CACHE_FILE = 'audio_cache.json'
HISTORY_FILE = 'game_history.json'

# ========================================
# UTILITY FUNCTIONS
# ========================================

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f)
    except:
        pass

def get_clean_name(path):
    filename = os.path.basename(path)
    return os.path.splitext(filename)[0]

def is_foreign(text):
    return bool(re.search(r'[^\x00-\x7F]', text))

def parse_artist_title(clean_name):
    if ' - ' in clean_name:
        parts = clean_name.split(' - ', 1)
        return parts[0].strip(), parts[1].strip()
    return None, clean_name

def split_artists(artist_string):
    if not artist_string:
        return []
    delimiters = r',|&|\sfeat\.?|\sft\.?|\svs\.?'
    raw_list = re.split(delimiters, artist_string, flags=re.IGNORECASE)
    return [x.strip() for x in raw_list if x.strip()]

def get_all_songs():
    songs = []
    if not os.path.exists(MUSIC_FOLDER): 
        return []
    try:
        for root, dirs, files in os.walk(MUSIC_FOLDER):
            for file in files:
                if file.lower().endswith(('.mp3', '.flac', '.wav', '.ogg', '.m4a')):
                    songs.append(os.path.join(root, file))
    except:
        pass
    return songs

def get_smart_random_song():
    songs = get_all_songs()
    if not songs: 
        return None
    
    try:
        recent = db.session.query(PlayHistory.file_path).order_by(
            PlayHistory.played_at.desc()
        ).limit(30).all()
        recent_paths = [r[0] for r in recent]
    except:
        recent_paths = []

    for _ in range(10):
        selected = random.choice(songs)
        if selected in recent_paths:
            if random.random() < 0.15: 
                return selected
        else:
            return selected
    return selected

def update_history(song_path, user_id=None):
    try:
        history = PlayHistory(file_path=song_path, user_id=user_id)
        db.session.add(history)
        db.session.commit()
    except:
        db.session.rollback()

def analyze_drop(file_path, duration):
    try:
        cached = db.session.query(QuestionCache).filter_by(file_path=file_path).first()
        if cached:
            return cached.drop_time
    except:
        pass

    try:
        scan_dur = min(45, duration)
        offset = (duration - scan_dur) / 2
        y, sr = librosa.load(file_path, sr=22050, offset=offset, duration=scan_dur, mono=True)
        rms = librosa.feature.rms(y=y)[0]
        max_frame = np.argmax(rms)
        drop_time = offset + librosa.frames_to_time(max_frame, sr=sr)
        
        try:
            cache = QuestionCache(file_path=file_path, drop_time=drop_time, duration=duration)
            db.session.add(cache)
            db.session.commit()
        except:
            db.session.rollback()
        
        return drop_time
    except:
        return duration / 2

def get_duration(path):
    try:
        return librosa.get_duration(path=path)
    except:
        return 0

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('auth_page'))
        try:
            user = User.query.get(user_id)
            if not user:
                session.clear()
                return redirect(url_for('auth_page'))
        except:
            return redirect(url_for('auth_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        try:
            return User.query.get(user_id)
        except:
            pass
    return None

def get_youtube_playlist_songs(url, limit=50):
    """Extract songs from YouTube playlist using yt-dlp"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            songs = []
            entries = info.get('entries', [])
            
            for i, entry in enumerate(entries[:limit]):
                if i >= limit:
                    break
                songs.append({
                    'title': entry.get('title', f'Song {i+1}'),
                    'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                    'duration': entry.get('duration', 180)
                })
            
            return songs
    except Exception as e:
        print(f"Error fetching YouTube playlist: {str(e)}")
        return []

def get_youtube_video_info(url):
    """Get video info and duration"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 180),
                'url': url
            }
    except:
        return None

# ========================================
# ROUTES: AUTHENTICATION
# ========================================

@app.route('/auth')
def auth_page():
    if session.get('user_id'):
        return redirect(url_for('mode_selector'))
    return render_template('auth.html')

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        
        if not username or len(username) < 3:
            return jsonify({'success': False, 'error': 'Username minimal 3 karakter'}), 400
        
        if password and len(password) < 6:
            return jsonify({'success': False, 'error': 'Password minimal 6 karakter'}), 400
        
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'error': 'Username sudah terdaftar'}), 400
        
        user = User(username=username, email=email if email else None, is_guest=False)
        if password:
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session.permanent = True
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'error': 'Username atau password salah'}), 401
        
        session['user_id'] = user.id
        session.permanent = True
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Login error'}), 500

@app.route('/api/guest', methods=['POST'])
def guest_login():

    try:

        print('GUEST LOGIN START')

        data = request.json

        print('REQUEST DATA:', data)

        guest_name = data.get(
            'guest_name',
            ''
        ).strip()

        print('GUEST NAME:', guest_name)

        if not guest_name or len(guest_name) < 2:

            return jsonify({
                'success': False,
                'error': 'Nama minimal 2 karakter'
            }), 400

        existing_guest = User.query.filter_by(
            username=f"guest_{guest_name}",
            is_guest=True
        ).first()

        print('EXISTING GUEST:', existing_guest)

        if existing_guest:

            session['user_id'] = existing_guest.id
            session.permanent = True

            return jsonify({
                'success': True
            })

        guest_user = User(
            username=f"guest_{guest_name}",
            is_guest=True
        )

        print('CREATED USER OBJECT')

        db.session.add(guest_user)

        print('ADDED TO DB')

        db.session.commit()

        print('DB COMMIT SUCCESS')

        session['user_id'] = guest_user.id
        session.permanent = True

        return jsonify({
            'success': True
        })

    except Exception as e:

        db.session.rollback()

        import traceback

        print('========== GUEST LOGIN ERROR ==========')
        print(str(e))
        traceback.print_exc()
        print('=======================================')

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth_page'))

# ========================================
# ROUTES: MODE SELECTION
# ========================================

@app.route('/mode')
@require_login
def mode_selector():
    user = get_current_user()
    return render_template('mode_selector.html', user=user)

# ========================================
# ROUTES: SINGLEPLAYER
# ========================================

@app.route('/singleplayer')
@require_login
def singleplayer_setup():
    user = get_current_user()
    return render_template('singleplayer.html', user=user)

@app.route('/game/singleplayer')
@require_login
def singleplayer_game():
    user = get_current_user()
    count = request.args.get('count', 10)
    mode = request.args.get('mode', 'CLASSIC')
    return render_template('quiz.html', user=user, is_multiplayer=False, game_mode=mode, question_count=count)

# ========================================
# ROUTES: MULTIPLAYER
# ========================================

@app.route('/multiplayer')
@require_login
def multiplayer_page():
    user = get_current_user()
    return render_template('multiplayer.html', user=user)

@app.route('/host')
@require_login
def host_setup():
    user = get_current_user()
    return render_template('host_setup.html', user=user)

@app.route('/join')
@require_login
def join_setup():
    user = get_current_user()
    return render_template('join_setup.html', user=user)

@app.route('/api/room/create', methods=['POST'])
@require_login
def create_room():
    try:
        user = get_current_user()
        data = request.json
        
        mode = data.get('mode', 'CLASSIC')
        game_type = data.get('game_type', 'LOCAL')
        max_players = int(data.get('max_players', 2))
        music_source = data.get('music_source', 'LOCAL')
        youtube_url = data.get('youtube_url', '')
        question_count = int(data.get('question_count', 10))
        
        if max_players not in [2, 4, 6]:
            return jsonify({'success': False, 'error': 'Invalid player count'}), 400
        
        room_code = generate_room_code()
        
        room = GameRoom(
            room_code=room_code,
            host_id=user.id,
            mode=mode,
            game_type=game_type,
            max_players=max_players,
            music_source=music_source,
            youtube_playlist_url=youtube_url if music_source == 'YOUTUBE' else None,
            question_count=question_count
        )
        
        db.session.add(room)
        db.session.commit()
        
        player = RoomPlayer(room_id=room.id, user_id=user.id)
        db.session.add(player)
        db.session.commit()
        
        session['current_room_id'] = room.id
        
        return jsonify({
            'success': True,
            'room_id': room.id,
            'room_code': room_code
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/room/join', methods=['POST'])
@require_login
def join_room():
    try:
        user = get_current_user()
        data = request.json
        room_code = data.get('room_code', '').strip().upper()
        
        room = GameRoom.query.filter_by(room_code=room_code).first()
        
        if not room:
            return jsonify({'success': False, 'error': 'Room tidak ditemukan'}), 404
        
        if room.is_started:
            return jsonify({'success': False, 'error': 'Game sudah dimulai'}), 400
        
        player_count = RoomPlayer.query.filter_by(room_id=room.id).count()
        if player_count >= room.max_players:
            return jsonify({'success': False, 'error': 'Room penuh'}), 400
        
        existing = RoomPlayer.query.filter_by(room_id=room.id, user_id=user.id).first()
        if not existing:
            player = RoomPlayer(room_id=room.id, user_id=user.id)
            db.session.add(player)
            db.session.commit()
        
        session['current_room_id'] = room.id
        
        return jsonify({
            'success': True,
            'room_id': room.id
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/game/multiplayer')
@require_login
def multiplayer_game():
    user = get_current_user()
    room_id = session.get('current_room_id')
    
    if not room_id:
        return redirect(url_for('multiplayer_page'))
    
    room = GameRoom.query.get(room_id)
    if not room:
        return redirect(url_for('multiplayer_page'))
    
    return render_template('quiz.html', user=user, is_multiplayer=True, room_id=room_id)

@app.route('/api/room/<int:room_id>')
@require_login
def get_room_info(room_id):
    try:
        room = GameRoom.query.get(room_id)
        if not room:
            return jsonify({'error': 'Room not found'}), 404
        
        players = RoomPlayer.query.filter_by(room_id=room_id).all()
        
        return jsonify({
            'room_code': room.room_code,
            'host_id': room.host_id,
            'mode': room.mode,
            'max_players': room.max_players,
            'question_count': room.question_count,
            'is_started': room.is_started,
            'music_source': room.music_source,
            'players': [
                {
                    'id': p.user_id,
                    'username': p.user.username,
                    'is_ready': p.is_ready,
                    'is_host': p.user_id == room.host_id
                }
                for p in players
            ]
        })
    except:
        return jsonify({'error': 'Error'}), 500

@app.route('/api/room/<int:room_id>/ready', methods=['POST'])
@require_login
def set_ready(room_id):
    try:
        user = get_current_user()
        data = request.json
        is_ready = data.get('is_ready', False)
        
        player = RoomPlayer.query.filter_by(room_id=room_id, user_id=user.id).first()
        if player:
            player.is_ready = is_ready
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'success': False}), 404
    except:
        db.session.rollback()
        return jsonify({'success': False}), 500

@app.route('/api/room/<int:room_id>/start', methods=['POST'])
@require_login
def start_multiplayer_game(room_id):
    try:
        user = get_current_user()
        room = GameRoom.query.get(room_id)
        
        if not room or room.host_id != user.id:
            return jsonify({'success': False, 'error': 'Not authorized'}), 403
        
        players = RoomPlayer.query.filter_by(room_id=room_id).all()
        
        all_ready = all(p.is_ready for p in players)
        if not all_ready:
            return jsonify({'success': False, 'error': 'Not all players ready'}), 400
        
        room.is_started = True
        room.started_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True})
    except:
        db.session.rollback()
        return jsonify({'success': False}), 500

# ========================================
# ROUTES: QUIZ/GAME
# ========================================

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('mode_selector'))
    return redirect(url_for('auth_page'))

@app.route('/api/bgm')
def get_bgm():
    try:
        songs = get_all_songs()
        if not songs:
            return jsonify({'error': 'No songs'}), 404
        
        song = random.choice(songs)
        clean_name = get_clean_name(song)
        dur = get_duration(song)
        start = random.uniform(0, max(0, dur - 40))
        
        session['bgm_path'] = song
        
        return jsonify({
            'title': clean_name,
            'start': start,
            'token': hashlib.md5(str(time.time()).encode()).hexdigest()
        })
    except:
        return jsonify({'error': 'Error loading music'}), 500

@app.route('/api/question')
def get_question():
    try:
        room_id = request.args.get('room_id')
        is_multiplayer = request.args.get('is_multiplayer', 'false').lower() == 'true'
        youtube_url = request.args.get('youtube_url', '')
        
        user = get_current_user()
        
        # If YouTube URL is provided (singleplayer with YouTube)
        if youtube_url:
            return get_youtube_question_from_url(youtube_url)
        
        # If multiplayer room with YouTube source
        if is_multiplayer and room_id:
            room = GameRoom.query.get(int(room_id))
            if room and room.music_source == 'YOUTUBE':
                return get_youtube_question(room)
        
        target = get_smart_random_song()
        if not target:
            return jsonify({'error': 'Empty DB'}), 404
        
        if user:
            update_history(target, user.id)
        
        session['quiz_path'] = target
        dur = get_duration(target)
        
        roll = random.random()
        start, mode = 0, "RANDOM"
        if roll <= 0.2:
            start, mode = 0, "INTRO"
        elif roll <= 0.4:
            start, mode = max(0, dur - 30), "OUTRO"
        else:
            drop = analyze_drop(target, dur)
            start, mode = max(0, drop - 5), "CLIMAX"
        
        session['start_time'] = start
        
        clean_name = get_clean_name(target)
        folder_name = os.path.basename(os.path.dirname(target))
        
        all_songs = get_all_songs()
        options = [clean_name]
        while len(options) < 4:
            s = random.choice(all_songs)
            n = get_clean_name(s)
            if n not in options:
                options.append(n)
        random.shuffle(options)
        
        is_foreign_file = is_foreign(clean_name)
        artist, title = parse_artist_title(clean_name)
        has_separator = artist is not None
        
        typing_type = "NORMAL"
        if is_foreign_file or not has_separator:
            typing_type = "FOLDER"
        
        return jsonify({
            'clue': folder_name,
            'options': options,
            'mode': mode,
            'start_time': start,
            'duration': dur,
            'typing_type': typing_type,
            'source': 'LOCAL'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_youtube_question(room):
    """Generate question from YouTube playlist"""
    try:
        if not room.youtube_playlist_url:
            return jsonify({'error': 'No playlist configured'}), 400
        
        songs = get_youtube_playlist_songs(room.youtube_playlist_url, limit=50)
        if not songs:
            return jsonify({'error': 'Could not fetch playlist'}), 400
        
        selected = random.choice(songs)
        duration = selected.get('duration', 180)
        max_timestamp = int(duration * 0.8)
        start_time = random.randint(0, max(0, max_timestamp - 15))
        
        session['quiz_url'] = selected['url']
        session['start_time'] = start_time
        
        all_titles = [s['title'] for s in songs]
        options = [selected['title']]
        while len(options) < 4 and len(all_titles) > len(options):
            opt = random.choice(all_titles)
            if opt not in options:
                options.append(opt)
        random.shuffle(options)
        
        return jsonify({
            'clue': 'YOUTUBE PLAYLIST',
            'options': options,
            'mode': 'YOUTUBE',
            'start_time': start_time,
            'duration': min(15, duration - start_time),
            'typing_type': 'NORMAL',
            'source': 'YOUTUBE',
            'youtube_url': selected['url'],
            'title': selected['title']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_youtube_question_from_url(youtube_url):
    """Generate question from a single YouTube URL"""
    try:
        if not youtube_url:
            return jsonify({'error': 'No YouTube URL provided'}), 400
        
        # Check if it's a playlist
        if 'playlist' in youtube_url.lower():
            songs = get_youtube_playlist_songs(youtube_url, limit=50)
            if not songs:
                return jsonify({'error': 'Could not fetch playlist'}), 400
            
            selected = random.choice(songs)
            duration = selected.get('duration', 180)
            max_timestamp = int(duration * 0.8)
            start_time = random.randint(0, max(0, max_timestamp - 15))
            
            session['quiz_url'] = selected['url']
            session['start_time'] = start_time
            
            all_titles = [s['title'] for s in songs]
            options = [selected['title']]
            while len(options) < 4 and len(all_titles) > len(options):
                opt = random.choice(all_titles)
                if opt not in options:
                    options.append(opt)
            random.shuffle(options)
            
            return jsonify({
                'clue': 'YOUTUBE PLAYLIST',
                'options': options,
                'mode': 'YOUTUBE',
                'start_time': start_time,
                'duration': min(15, duration - start_time),
                'typing_type': 'NORMAL',
                'source': 'YOUTUBE',
                'youtube_url': selected['url'],
                'title': selected['title']
            })
        else:
            # Single video
            video_info = get_youtube_video_info(youtube_url)
            if not video_info:
                return jsonify({'error': 'Could not fetch video'}), 400
            
            duration = video_info.get('duration', 180)
            max_timestamp = int(duration * 0.8)
            start_time = random.randint(0, max(0, max_timestamp - 15))
            
            session['quiz_url'] = youtube_url
            session['start_time'] = start_time
            
            title = video_info.get('title', 'Unknown Video')
            options = [title, 'Unknown Video 1', 'Unknown Video 2', 'Unknown Video 3']
            random.shuffle(options)
            
            return jsonify({
                'clue': 'YOUTUBE VIDEO',
                'options': options,
                'mode': 'YOUTUBE',
                'start_time': start_time,
                'duration': min(15, duration - start_time),
                'typing_type': 'NORMAL',
                'source': 'YOUTUBE',
                'youtube_url': youtube_url,
                'title': title
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stream_audio')
def stream_audio():
    try:
        mode = request.args.get('type', 'quiz')
        
        if mode == 'bgm':
            path = session.get('bgm_path')
        else:
            path = session.get('quiz_path')
        
        if path and os.path.exists(path):
            return send_file(path)
        
        return jsonify({'error': 'File not found'}), 404
    except:
        return jsonify({'error': 'Error'}), 500

@app.route('/submit_answer', methods=['POST'])
def check_answer():
    try:
        data = request.json
        game_mode = data.get('game_mode', 'CLASSIC')
        user_answer = data.get('answer', '').strip().lower()
        source = data.get('source', 'LOCAL')
        
        response = {'correct': False, 'score': 0, 'correct_answer': ''}
        
        if source == 'YOUTUBE':
            correct_title = data.get('correct_title', '').strip().lower()
            if user_answer in correct_title or correct_title in user_answer:
                if len(user_answer) > 2:
                    response['correct'] = True
                    response['score'] = 100
            response['correct_answer'] = data.get('correct_title', '')
        else:
            target_path = session.get('quiz_path')
            if not target_path:
                return jsonify(response), 400
            
            clean_name = get_clean_name(target_path)
            folder_name = os.path.basename(os.path.dirname(target_path))
            
            if game_mode == 'CLASSIC':
                if user_answer == clean_name.lower():
                    response['correct'] = True
                    response['score'] = 100
                response['correct_answer'] = clean_name
                
            elif game_mode == 'TYPING':
                typing_type = data.get('typing_type', 'NORMAL')
                
                if typing_type == 'FOLDER':
                    if user_answer in folder_name.lower() and len(user_answer) > 2:
                        response['correct'] = True
                        response['score'] = 100
                    response['correct_answer'] = folder_name
                else:
                    artist, title = parse_artist_title(clean_name)
                    score = 0
                    
                    if user_answer in title.lower() or title.lower() in user_answer:
                        if len(user_answer) > 3:
                            score += 50
                    
                    target_artists = split_artists(artist)
                    points_per_artist = 50 / len(target_artists) if target_artists else 0
                    
                    for t_art in target_artists:
                        if t_art.lower() in user_answer:
                            score += points_per_artist
                    
                    response['score'] = int(score)
                    response['correct'] = score > 0
                    response['correct_answer'] = f"{artist} - {title}" if artist else title
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'correct': False, 'score': 0, 'error': str(e)}), 500

# ========================================
# ERROR HANDLING
# ========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

# ========================================
# INITIALIZATION
# ========================================

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

@app.route('/api/room/<int:room_id>/score', methods=['POST'])
@require_login
def submit_room_score(room_id):

    try:

        user = get_current_user()

        room = GameRoom.query.get(room_id)

        if not room:
            return jsonify({
                'success': False,
                'error': 'Room not found'
            }), 404

        data = request.json

        final_score = int(
            data.get('score', 0)
        )

        # cek apakah sudah ada score
        existing = PlayerScore.query.filter_by(
            room_id=room_id,
            user_id=user.id
        ).first()

        if existing:

            existing.score = final_score

        else:

            score = PlayerScore(
                room_id=room_id,
                user_id=user.id,
                score=final_score
            )

            db.session.add(score)

        db.session.commit()

        return jsonify({
            'success': True
        })

    except Exception as e:

        db.session.rollback()

        print('GUEST LOGIN ERROR:')
        print(str(e))

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    
@app.route('/api/room/<int:room_id>/leaderboard')
@require_login
def room_leaderboard(room_id):

    try:

        room = GameRoom.query.get(room_id)

        if not room:
            return jsonify({
                'error': 'Room not found'
            }), 404

        scores = (
            db.session.query(PlayerScore)
            .filter_by(room_id=room_id)
            .order_by(PlayerScore.score.desc())
            .all()
        )

        leaderboard = []

        for s in scores:

            leaderboard.append({
                'username': s.user.username,
                'score': s.score
            })

        return jsonify({
            'leaderboard': leaderboard
        })

    except Exception as e:

        return jsonify({
            'error': str(e)
        }), 500
    
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except:
            pass
    
    threading.Timer(1.5, open_browser).start()
    app.run(host='0.0.0.0', debug=False, port=5000)