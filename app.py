from flask import Flask
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
import jwt
from datetime import datetime
import time
from threading import Thread
import eventlet
eventlet.monkey_patch()
app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///user_locations.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

print("Flask app and SocketIO initialized.")

# Database Model for User Locations
class UserLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserLocation {self.user_id}: ({self.latitude}, {self.longitude})>"

print("Database model defined.")

# Create the database and tables
with app.app_context():
    db.create_all()
    print("Database and tables created.")

# Mock function to validate the token
def validate_token(token):
    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

print("Token validation function defined.")

# Function to broadcast user locations periodically
def broadcast_user_locations():
    with app.app_context():  # Push application context
        while True:
            time.sleep(5)
            users = UserLocation.query.all()
            socketio.emit("userLocationUpdate", [{
                "user_id": user.user_id,
                "position": [user.latitude, user.longitude],
                "timestamp": user.timestamp.isoformat()
            } for user in users])

print("Broadcast function defined.")

# WebSocket event for updating user location
@socketio.on("update_location")
def handle_update_location(data):
    token = data.get("token")
    latitude = data.get("latitude")
    longitude = data.get("longitude")

    user_id = validate_token(token)
    if not user_id:
        emit("error", {"message": "Invalid or expired token"})
        return

    user = UserLocation.query.filter_by(user_id=user_id).first()
    if user:
        user.latitude = latitude
        user.longitude = longitude
        user.timestamp = datetime.utcnow()
    else:
        user = UserLocation(user_id=user_id, latitude=latitude, longitude=longitude)
        db.session.add(user)
    db.session.commit()

    print(f"Updated location for user {user_id}: ({latitude}, {longitude})")

print("WebSocket event handlers defined.")

if __name__ == "__main__":
    print("Starting server...")
    thread = Thread(target=broadcast_user_locations)
    thread.daemon = True
    thread.start()
    print("Starting SocketIO server...")
    socketio.run(app, debug=False)