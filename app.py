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

app = Flask(__name__, instance_path='/tmp')

app.secret_key = os.environ.get(
    'SECRET_KEY',
    'localbeat_vr1l_secure_key_2024'
)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:////tmp/localbeat.db'
)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

app.config['SESSION_COOKIE_SECURE'] = (
    os.environ.get('FLASK_ENV') == 'production'
)

app.config['SESSION_COOKIE_HTTPONLY'] = True

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)

with app.app_context():
    db.create_all()

bcrypt.init_app(app)

CORS(app)

# ========================================
# MUSIC FOLDER
# ========================================

MUSIC_FOLDER = os.environ.get(
    'MUSIC_FOLDER',
    r"D:\Music"
)

CACHE_FILE = 'audio_cache.json'
HISTORY_FILE = 'game_history.json'

# ========================================
# SONG FUNCTIONS
# ========================================

def get_all_songs():

    songs = []

    if not os.path.exists(MUSIC_FOLDER):
        return []

    try:

        for root, dirs, files in os.walk(MUSIC_FOLDER):

            for file in files:

                if file.lower().endswith(
                    (
                        '.mp3',
                        '.flac',
                        '.wav',
                        '.ogg',
                        '.m4a'
                    )
                ):

                    songs.append(
                        os.path.join(root, file)
                    )

    except Exception as e:

        print(
            "Song Scan Error:",
            str(e)
        )

    return songs


def get_smart_random_song():

    songs = get_all_songs()

    if not songs:
        return None

    try:

        recent = db.session.query(
            PlayHistory.file_path
        ).order_by(
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

# ========================================
# YOUTUBE FUNCTIONS
# ========================================

def get_youtube_playlist_songs(
    url,
    limit=50
):

    try:

        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=False
            )

            songs = []

            entries = info.get(
                'entries',
                []
            )

            for i, entry in enumerate(entries[:limit]):

                songs.append({
                    'title': entry.get(
                        'title',
                        f'Song {i + 1}'
                    ),

                    'url': (
                        "https://www.youtube.com/watch?v="
                        f"{entry.get('id')}"
                    ),

                    'duration': entry.get(
                        'duration',
                        180
                    )
                })

            return songs

    except Exception as e:

        print(
            "YouTube Playlist Error:",
            str(e)
        )

        return []


def get_youtube_question_logic(
    playlist_url
):

    try:

        songs = get_youtube_playlist_songs(
            playlist_url,
            limit=50
        )

        if not songs:

            return jsonify({
                'error': 'Could not fetch playlist'
            }), 400

        selected = random.choice(songs)

        duration = selected.get(
            'duration',
            180
        )

        max_timestamp = int(duration * 0.8)

        start_time = random.randint(
            0,
            max(0, max_timestamp - 15)
        )

        session['quiz_url'] = selected['url']

        session['start_time'] = start_time

        all_titles = [
            s['title']
            for s in songs
        ]

        options = [selected['title']]

        while (
            len(options) < 4 and
            len(all_titles) > len(options)
        ):

            opt = random.choice(all_titles)

            if opt not in options:
                options.append(opt)

        random.shuffle(options)

        return jsonify({

            'clue': 'YOUTUBE PLAYLIST',

            'options': options,

            'mode': 'YOUTUBE',

            'start_time': start_time,

            'duration': min(
                15,
                max(1, duration - start_time)
            ),

            'typing_type': 'NORMAL',

            'source': 'YOUTUBE',

            'youtube_url': selected['url'],

            'title': selected['title']

        })

    except Exception as e:

        print(
            "YouTube Question Error:",
            str(e)
        )

        return jsonify({
            'error': str(e)
        }), 500


def get_youtube_question(room):

    try:

        if not room.youtube_playlist_url:

            return jsonify({
                'error': 'No playlist configured'
            }), 400

        songs = get_youtube_playlist_songs(
            room.youtube_playlist_url,
            limit=50
        )

        if not songs:

            return jsonify({
                'error': 'Could not fetch playlist'
            }), 400

        selected = random.choice(songs)

        duration = selected.get(
            'duration',
            180
        )

        max_timestamp = int(duration * 0.8)

        start_time = random.randint(
            0,
            max(0, max_timestamp - 15)
        )

        session['quiz_url'] = selected['url']

        session['start_time'] = start_time

        all_titles = [
            s['title']
            for s in songs
        ]

        options = [selected['title']]

        while (
            len(options) < 4 and
            len(all_titles) > len(options)
        ):

            opt = random.choice(all_titles)

            if opt not in options:
                options.append(opt)

        random.shuffle(options)

        return jsonify({

            'clue': 'YOUTUBE PLAYLIST',

            'options': options,

            'mode': 'YOUTUBE',

            'start_time': start_time,

            'duration': min(
                15,
                max(1, duration - start_time)
            ),

            'typing_type': 'NORMAL',

            'source': 'YOUTUBE',

            'youtube_url': selected['url'],

            'title': selected['title']

        })

    except Exception as e:

        print(
            "YouTube Multiplayer Error:",
            str(e)
        )

        return jsonify({
            'error': str(e)
        }), 500

# ========================================
# QUESTION API
# ========================================

@app.route('/api/question')
def get_question():

    try:

        room_id = request.args.get(
            'room_id'
        )

        is_multiplayer = (
            request.args.get(
                'is_multiplayer',
                'false'
            ).lower() == 'true'
        )

        # ========================================
        # SINGLEPLAYER
        # ========================================

        if not is_multiplayer:

            default_playlist = (
                "https://youtube.com/playlist?"
                "list=PLW37nsP-pBsN4ZqHR52Iulo6tWRe8U1GE"
            )

            return get_youtube_question_logic(
                default_playlist
            )

        # ========================================
        # MULTIPLAYER
        # ========================================

        if is_multiplayer and room_id:

            room = GameRoom.query.get(
                int(room_id)
            )

            if not room:

                return jsonify({
                    'error': 'Room not found'
                }), 404

            return get_youtube_question(room)

        return jsonify({
            'error': 'Invalid setup'
        }), 400

    except Exception as e:

        print(
            "Question Route Error:",
            str(e)
        )

        return jsonify({
            'error': str(e)
        }), 500

# ========================================
# BGM API
# ========================================

@app.route('/api/bgm')
def get_bgm():

    try:

        songs = get_all_songs()

        if not songs:

            return jsonify({
                'error': 'No songs found'
            }), 404

        song = random.choice(songs)

        clean_name = get_clean_name(song)

        dur = get_duration(song)

        start = random.uniform(
            0,
            max(0, dur - 40)
        )

        session['bgm_path'] = song

        return jsonify({

            'title': clean_name,

            'start': start,

            'token': hashlib.md5(
                str(time.time()).encode()
            ).hexdigest()

        })

    except Exception as e:

        print(
            "BGM Error:",
            str(e)
        )

        return jsonify({
            'error': 'Error loading music'
        }), 500
    
    # ========================================
    # UTILITY FUNCTIONS
    # ========================================

    def generate_room_code():
        return "ABCD"