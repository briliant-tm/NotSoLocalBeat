from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(200), nullable=True)
    is_guest = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    game_sessions = db.relationship('GameSession', backref='user', lazy=True)
    player_scores = db.relationship('PlayerScore', backref='user', lazy=True)
    
    def set_password(self, password):
        if password:
            self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

class GameRoom(db.Model):
    __tablename__ = 'game_rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_code = db.Column(db.String(6), unique=True, nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    mode = db.Column(db.String(20), default='CLASSIC')  # CLASSIC or TYPING
    game_type = db.Column(db.String(20), default='LOCAL')  # LOCAL or INTERNET
    max_players = db.Column(db.Integer, default=2)
    music_source = db.Column(db.String(20), default='LOCAL')  # LOCAL or YOUTUBE
    youtube_playlist_url = db.Column(db.String(500), nullable=True)
    question_count = db.Column(db.Integer, default=10)
    is_started = db.Column(db.Boolean, default=False)
    is_finished = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    
    host = db.relationship('User', backref='hosted_rooms')
    players = db.relationship('RoomPlayer', backref='room', cascade='all, delete-orphan')
    game_session = db.relationship('GameSession', backref='room', uselist=False)

    scores = db.relationship(
    'PlayerScore',
    backref='room',
    cascade='all, delete-orphan'
)

class RoomPlayer(db.Model):
    __tablename__ = 'room_players'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('game_rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_ready = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')

class GameSession(db.Model):
    __tablename__ = 'game_sessions'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('game_rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_question = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime, nullable=True)
    

class PlayerScore(db.Model):
    __tablename__ = 'player_scores'
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey('game_rooms.id')
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id')
    )

    score = db.Column(
        db.Integer,
        default=0
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


class QuestionCache(db.Model):
    __tablename__ = 'question_cache'
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500), unique=True, nullable=False)
    drop_time = db.Column(db.Float, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlayHistory(db.Model):
    __tablename__ = 'play_history'
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User')
