import os
import threading

from flask import Flask, render_template
from flask_socketio import SocketIO

from quixstreams import Application

# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode="threading")

# Enabling auto-reloading of templates
@app.before_request
def before_request():
    app.jinja_env.cache = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Simulating rocket telemetry updates (replace this with your logic)
def simulate_telemetry():
    import time
    import random

def run_socketio_app():
    socketio.run(app, host='0.0.0.0', port=5000) ## changing this port to 80 can cause issues running the app locally

def send_telemetry(data: dict):

    telemetry = {
        'name': data["name"],
        'stage': data["stage"],
        'x': data["X"],
        'y': data["Y"],
        'angle': data["angle"] * -1,
        'velocity': data["velocity"],
        'velocity_x': data["velocity_x"],
        'velocity_y': data["velocity_y"],
        'acceleration': data["acceleration"],
        'altitude': data["altitude"]
    }

    socketio.emit('telemetry', telemetry)

if __name__ == '__main__':
    # Start the SocketIO server in a separate thread
    thread = threading.Thread(target=run_socketio_app)
    thread.start()

    load_dotenv(override=False)

    quix_app = Application()

    input_topic = quix_app.topic(os.environ["input"])

    sdf = quix_app.dataframe(input_topic)

    sdf = sdf.update(lambda row: print(row))

    sdf = sdf.update(send_telemetry)
    quix_app.run(sdf)