from quixstreams import Application  # import the Quix Streams modules for interacting with Kafka
# (see https://quix.io/docs/quix-streams/v2-0-latest/api-reference/quixstreams.html for more details)

# import additional modules as needed
import requests
import os
import json
import time
from concurrent.futures import ThreadPoolExecutor

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="data_source", auto_create_topics=True)  # create an Application

# Load environment variables
topic_name = os.environ["output"]
num_missions = int(os.environ.get("num_missions", 10))  # Default to 10 if not set
replica_id = int(os.environ.get("Quix__Deployment__ReplicaName", 0))  # Default to 0 if not set

# Define the topic using the "output" environment variable
topic = app.topic(topic_name)

# Define the endpoint URLs
missions_url = "http://api.launchdashboard.space/v2/launches/spacex"
youtube_url_template = "https://api.spacexdata.com/v3/launches/{flight_number}"

def get_all_missions():
    """
    A function to fetch all missions from the specified endpoint.
    It returns a list of missions.
    """
    response = requests.get(missions_url)
    response.raise_for_status()  # Raise an HTTPError for bad responses
    return response.json()

def get_youtube_data(flight_number):
    """
    A function to fetch youtube_id and webcast_liftoff for a specific flight number.
    """
    youtube_url = youtube_url_template.format(flight_number=flight_number)
    response = requests.get(youtube_url)
    
    try:
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()  # Parse JSON response

        youtube_id = data.get("links", {}).get("youtube_id", "")
        offset_youtube_seconds = data.get("timeline", {}).get("webcast_liftoff", 0)
        return youtube_id, offset_youtube_seconds

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred for flight_number: {flight_number} - {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred for flight_number: {flight_number} - {req_err}")
    except ValueError as json_err:
        print(f"JSON decode error occurred for flight_number: {flight_number} - {json_err}")

    return "", 0

def get_telemetry_data(mission):
    """
    A function to fetch telemetry data for a specific mission.
    It returns a list of tuples containing mission_id, stage, and telemetry data for each stage.
    """
    mission_id = mission["mission_id"]
    flight_number = mission["flight_number"]
    telemetry_url = f"http://api.launchdashboard.space/v2/launches/spacex?mission_id={mission_id}"
    response = requests.get(telemetry_url)

    try:
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()  # Parse JSON response

        # Check if the required keys are present in the response
        if "mission_id" not in data or "name" not in data or "flight_number" not in data or "analysed" not in data:
            print(f"Missing required data for mission_id: {mission_id}")
            return None

        # extract the mission_id, name, and flight_number
        mission_id = data["mission_id"]
        name = data["name"]
        flight_number = data["flight_number"]

        # Get youtube_id and offset_youtube_seconds
        youtube_id, offset_youtube_seconds = get_youtube_data(flight_number)

        telemetry_data_list = []
        for analysed_data in data["analysed"]:
            # extract the telemetry data for each stage
            if "telemetry" not in analysed_data or "stage" not in analysed_data:
                print(f"Missing telemetry data for mission_id: {mission_id}")
                continue

            telemetry_data = analysed_data["telemetry"]
            stage = analysed_data["stage"]

            # add mission_id, name, flight_number, stage, youtube_id, and offset_youtube_seconds to each telemetry entry
            for entry in telemetry_data:
                entry["mission_id"] = mission_id
                entry["name"] = name
                entry["flight_number"] = flight_number
                entry["stage"] = stage
                entry["youtube_id"] = youtube_id
                entry["offset_youtube_seconds"] = offset_youtube_seconds

            telemetry_data_list.append((mission_id, stage, telemetry_data))

        return telemetry_data_list

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred for mission_id: {mission_id} - {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception occurred for mission_id: {mission_id} - {req_err}")
    except ValueError as json_err:
        print(f"JSON decode error occurred for mission_id: {mission_id} - {json_err}")

    return None

def publish_telemetry(mission_id, stage, telemetry_data):
    """
    A function to publish telemetry data to Kafka with delays between timestamps.
    """
    key = f"{mission_id}-stage-{stage}"
    start_loop = time.time()
    first_time = telemetry_data[0]['time']

    with app.get_producer() as producer:
        for i in range(len(telemetry_data)):
            row_data = telemetry_data[i]
            json_data = json.dumps(row_data)  # convert the row to JSON

            # publish the data to the topic
            producer.produce(
                topic=topic.name,
                key=key,  # using mission_id and stage as the key
                value=json_data,
            )

            print(f"Published row {i+1}/{len(telemetry_data)}: {json_data}")

            if i < len(telemetry_data) - 1:
                next_time = telemetry_data[i + 1]['time']
                time_diff = next_time - first_time

                time_to_wait = max(0.0, time_diff - (time.time() - start_loop))
                time.sleep(time_to_wait)

        print(f"All rows for mission {mission_id} stage {stage} published")

def main():
    """
    Fetch data for all missions and publish telemetry data concurrently.
    """
    missions = get_all_missions()
    
    # Determine offset and limit for missions based on replica_id and num_missions
    offset = replica_id * num_missions
    limited_missions = missions[offset:offset + num_missions]

    with ThreadPoolExecutor(max_workers=num_missions) as executor:
        futures = []
        for mission in limited_missions:
            futures.append(executor.submit(get_telemetry_data, mission))

        telemetry_data_results = [future.result() for future in futures if future.result() is not None]
        
        publish_futures = []
        for telemetry_data_list in telemetry_data_results:
            for mission_id, stage, telemetry_data in telemetry_data_list:
                publish_futures.append(executor.submit(publish_telemetry, mission_id, stage, telemetry_data))

        for future in publish_futures:
            future.result()  # ensure all publishing is done

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
