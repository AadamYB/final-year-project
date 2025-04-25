from app import socketio, app

if __name__ != "__main__":
    application = socketio  # for Gunicorn

def run():
    socketio.run(app, host="0.0.0.0", port=5000)