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

# define the topic using the "output" environment variable
topic_name = os.environ["output"]
topic = app.topic(topic_name)

# define the endpoint URL to get all missions
missions_url = "http://api.launchdashboard.space/v2/launches/spacex"

def get_all_missions():
    """
    A function to fetch all missions from the specified endpoint.
    It returns a list of missions.
    """
    response = requests.get(missions_url)
    response.raise_for_status()  # Raise an HTTPError for bad responses
    return response.json()

def get_telemetry_data(mission):
    """
    A function to fetch telemetry data for a specific mission.
    It returns the mission details and a list of updated telemetry data.
    """
    mission_id = mission["mission_id"]
    telemetry_url = f"http://api.launchdashboard.space/v2/launches/spacex?mission_id={mission_id}"
    response = requests.get(telemetry_url)

    try:
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()  # Parse JSON response

        # Check if the required keys are present in the response
        if "mission_id" not in data or "name" not in data or "flight_number" not in data or "analysed" not in data:
            print(f"Missing required data for mission_id: {mission_id}")
            return None

        # extract the mission_id, name, flight_number, and stage
        mission_id = data["mission_id"]
        name = data["name"]
        flight_number = data["flight_number"]

        # extract the telemetry data from the "analysed" section
        analysed_data = data["analysed"]
        if not analysed_data or "telemetry" not in analysed_data[0] or "stage" not in analysed_data[0]:
            print(f"Missing telemetry data for mission_id: {mission_id}")
            return None

        telemetry_data = analysed_data[0]["telemetry"]
        stage = analysed_data[0]["stage"]

        # Check if telemetry data has at least 1000 rows
        if len(telemetry_data) < 1000:
            print(f"Telemetry data for mission_id: {mission_id} has less than 1000 rows")
            return None

        # add mission_id, name, flight_number, and stage to each telemetry entry
        for entry in telemetry_data:
            entry["mission_id"] = mission_id
            entry["name"] = name
            entry["flight_number"] = flight_number
            entry["stage"] = stage

        return mission_id, stage, telemetry_data

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
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for mission in missions:
            futures.append(executor.submit(get_telemetry_data, mission))

        telemetry_data_results = [future.result() for future in futures if future.result() is not None]
        
        publish_futures = []
        for mission_id, stage, telemetry_data in telemetry_data_results:
            publish_futures.append(executor.submit(publish_telemetry, mission_id, stage, telemetry_data))

        for future in publish_futures:
            future.result()  # ensure all publishing is done

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
