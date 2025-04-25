from app import socketio, app

application = socketio.wsgi_app  # for Gunicorn

# def run():
#     socketio.run(app, host="0.0.0.0", port=5000)