import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

# Initialize database on startup
with app.app_context():
    try:
        db.create_all()
    except:
        pass

# For Vercel WSGI compatibility
app_instance = app

if __name__ == '__main__':
    app.run()
