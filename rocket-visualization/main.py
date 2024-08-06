import os
import threading

from flask import Flask, render_template
from flask_socketio import SocketIO
import time
from quixstreams import Application, State

# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv

import queue

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode="threading")

queues = {}
threads = {}

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
    socketio.run(app, host='0.0.0.0', port=80) ## changing this port to 80 can cause issues running the app locally

def send_telemetry(data: dict, key, timestamp, headers):

    telemetry = {
        'key': key.decode('utf-8'),
        'name': data["name"],
        'stage': data["stage"],
        'x': data["X"],
        'y': data["Y"],
        'angle': data["angle"] * -1,
        'velocity': data["velocity"],
        'velocity_x': data["velocity_x"],
        'velocity_y': data["velocity_y"],
        'acceleration': data["acceleration"],
        'altitude': data["altitude"],
        'youtube_id': data["youtube_id"],
        'offset_youtube_seconds': data["time"] + data["offset_youtube_seconds"],
        'time': data["time"]
    }
    
    print(telemetry)

    socketio.emit('telemetry', telemetry)

if __name__ == '__main__':
    # Start the SocketIO server in a separate thread
    thread = threading.Thread(target=run_socketio_app)
    thread.start()

    load_dotenv(override=False)

    quix_app = Application()

    input_topic = quix_app.topic(os.environ["input"])


    def consume_queue(key:str):
        global queues
        
    
        
        q = queues[key]
        
        state_value = {}
        
        while True:
            row = q.get()
            if row is None:
                break
            
            last_value = {**state_value}
            
            state_value["last_time"] = row["time"]
            state_value["last_epoch"] = time.time()
            
            if "last_time" not in last_value:
                continue
            
            step_delay = row["time"] - last_value["last_time"]
            wall_clock_delay = time.time() - last_value["last_epoch"]
        
            sleep_delay = step_delay - wall_clock_delay
            if sleep_delay > 0:
                print("Delaying " + str(sleep_delay))
                
                time.sleep(sleep_delay)
                print(row["time"])

                send_telemetry(row, key, None, None)



    

    def sink_to_queue(row: dict, key, *_):
        global queues
        global threads
        
        if key not in queues:
            q = queue.Queue(100)
            queues[key] = q
            t = threading.Thread(target=consume_queue, args=[key])
            t.start()
            threads[key] = t
            
            
        else:
            q = queues[key]

        q.put(row)

    sdf = quix_app.dataframe(input_topic)
    
    sdf.update(sink_to_queue, metadata=True)
    
    #sdf = sdf.update(send_telemetry, metadata=True)
    quix_app.run(sdf)