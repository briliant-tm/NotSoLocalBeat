import os
import random
import json
import time
import hashlib
import threading
import webbrowser
import re
import numpy as np
import librosa
from flask import Flask, render_template, jsonify, send_file, request, session

app = Flask(__name__)
app.secret_key = 'localbeat_vr1l_secure_key'

# ==========================================
# KONFIGURASI PATH DATABASE (EDIT DI SINI)
# ==========================================
MUSIC_FOLDER = r"E:\Kakak\Music\Music"
# ==========================================

CACHE_FILE = 'audio_cache.json'
HISTORY_FILE = 'game_history.json'

# --- UTILITY FUNCTIONS ---

def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

def get_clean_name(path):
    # Hapus ekstensi (.mp3, .wav, dll)
    filename = os.path.basename(path)
    return os.path.splitext(filename)[0]

def is_foreign(text):
    # Cek karakter non-ASCII (Jepang, Korea, dll)
    return bool(re.search(r'[^\x00-\x7F]', text))

def parse_artist_title(clean_name):
    # Cek separator " - "
    if ' - ' in clean_name:
        parts = clean_name.split(' - ', 1)
        return parts[0].strip(), parts[1].strip() # Artist, Title
    return None, clean_name # No Artist, Only Title/Filename

def split_artists(artist_string):
    # Pecah artis berdasarkan koma, &, feat, vs
    delimiters = r',|&|\sfeat\.?|\sft\.?|\svs\.?'
    raw_list = re.split(delimiters, artist_string, flags=re.IGNORECASE)
    return [x.strip() for x in raw_list if x.strip()]

def get_all_songs():
    songs = []
    if not os.path.exists(MUSIC_FOLDER): return []
    for root, dirs, files in os.walk(MUSIC_FOLDER):
        for file in files:
            if file.lower().endswith(('.mp3', '.flac', '.wav', '.ogg', '.m4a')):
                songs.append(os.path.join(root, file))
    return songs

def get_smart_random_song():
    songs = get_all_songs()
    if not songs: return None
    history = load_json(HISTORY_FILE)
    recent = history.get('recent', [])

    # Retry logic (15% chance repeat)
    for _ in range(10):
        selected = random.choice(songs)
        if selected in recent:
            if random.random() < 0.15: return selected
        else:
            return selected
    return selected

def update_history(song_path):
    history = load_json(HISTORY_FILE)
    recent = history.get('recent', [])
    if song_path in recent: recent.remove(song_path)
    recent.append(song_path)
    if len(recent) > 30: recent.pop(0)
    save_json(HISTORY_FILE, {'recent': recent})

def analyze_drop(file_path, duration):
    cache = load_json(CACHE_FILE)
    if file_path in cache: return cache[file_path]
    try:
        scan_dur = min(45, duration)
        offset = (duration - scan_dur) / 2
        y, sr = librosa.load(file_path, sr=22050, offset=offset, duration=scan_dur, mono=True)
        rms = librosa.feature.rms(y=y)[0]
        max_frame = np.argmax(rms)
        drop_time = offset + librosa.frames_to_time(max_frame, sr=sr)
        cache[file_path] = drop_time
        save_json(CACHE_FILE, cache)
        return drop_time
    except: return duration / 2

def get_duration(path):
    try: return librosa.get_duration(path=path)
    except: return 0

# --- ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quiz')
def quiz_page():
    return render_template('quiz.html')

@app.route('/api/bgm')
def get_bgm():
    song = get_smart_random_song()
    if not song: return jsonify({'error': 'No songs'})
    
    clean_name = get_clean_name(song)
    dur = get_duration(song)
    start = random.uniform(0, max(0, dur - 40))
    
    session['bgm_path'] = song
    return jsonify({'title': clean_name, 'start': start, 'token': hashlib.md5(str(time.time()).encode()).hexdigest()})

@app.route('/api/question')
def get_question():
    target = get_smart_random_song()
    if not target: return jsonify({'error': 'Empty DB'})
    
    update_history(target)
    session['quiz_path'] = target
    dur = get_duration(target)
    
    # 20-20-60 Logic
    roll = random.random()
    start, mode = 0, "RANDOM"
    if roll <= 0.2: start, mode = 0, "INTRO"
    elif roll <= 0.4: start, mode = max(0, dur - 30), "OUTRO"
    else:
        drop = analyze_drop(target, dur)
        start, mode = max(0, drop - 5), "CLIMAX"
    
    session['start_time'] = start
    
    clean_name = get_clean_name(target)
    folder_name = os.path.basename(os.path.dirname(target))
    
    # Logic Pilihan Ganda (Classic)
    all_songs = get_all_songs()
    options = [clean_name]
    while len(options) < 4:
        s = random.choice(all_songs)
        n = get_clean_name(s)
        if n not in options: options.append(n)
    random.shuffle(options)
    
    # Logic Typing (Hardcore)
    is_foreign_file = is_foreign(clean_name)
    artist, title = parse_artist_title(clean_name)
    has_separator = artist is not None
    
    # Determine Typing Type
    typing_type = "NORMAL" # Default: Artist + Title
    if is_foreign_file or not has_separator:
        typing_type = "FOLDER" # Fallback to Folder Guess
    
    return jsonify({
        'clue': folder_name,
        'options': options,
        'mode': mode,
        'start_time': start,
        'duration': dur,
        'typing_type': typing_type
    })

@app.route('/stream_audio')
def stream_audio():
    mode = request.args.get('type')
    path = session.get('bgm_path') if mode == 'bgm' else session.get('quiz_path')
    if path and os.path.exists(path): return send_file(path)
    return "Error", 404

@app.route('/submit_answer', methods=['POST'])
def check_answer():
    data = request.json
    game_mode = data.get('game_mode') # 'CLASSIC' or 'TYPING'
    user_answer = data.get('answer', '').strip().lower()
    
    target_path = session.get('quiz_path')
    clean_name = get_clean_name(target_path)
    folder_name = os.path.basename(os.path.dirname(target_path))
    
    response = {'correct': False, 'score': 0, 'correct_answer': clean_name}

    if game_mode == 'CLASSIC':
        if user_answer == clean_name.lower():
            response['correct'] = True
            response['score'] = 100
            
    elif game_mode == 'TYPING':
        typing_type = data.get('typing_type')
        
        if typing_type == 'FOLDER':
            # Fuzzy match folder name
            if user_answer in folder_name.lower() and len(user_answer) > 2:
                response['correct'] = True
                response['score'] = 100
                response['correct_answer'] = folder_name # Show folder as answer
            else:
                 response['correct_answer'] = folder_name

        else: # NORMAL (Artist + Title)
            artist, title = parse_artist_title(clean_name)
            score = 0
            
            # 1. Check Title (50 Pts) - Fuzzy contains
            if user_answer in title.lower() or title.lower() in user_answer:
                # Basic check, user must type significant part
                if len(user_answer) > 3: score += 50
            
            # 2. Check Artist (50 Pts - Split)
            target_artists = split_artists(artist)
            points_per_artist = 50 / len(target_artists) if target_artists else 0
            
            artist_score = 0
            for t_art in target_artists:
                if t_art.lower() in user_answer:
                    artist_score += points_per_artist
            
            score += artist_score
            
            response['score'] = int(score) # Round down
            response['correct'] = score > 0
            response['correct_answer'] = f"{artist} - {title}"

    return jsonify(response)

@app.route('/shutdown', methods=['POST'])
def shutdown():
    os._exit(0)

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000")

if __name__ == '__main__':
    threading.Timer(1.5, open_browser).start()
    app.run(host='0.0.0.0', debug=False)