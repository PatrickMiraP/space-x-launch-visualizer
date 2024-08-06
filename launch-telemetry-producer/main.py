from quixstreams import Application  # import the Quix Streams modules for interacting with Kafka
# (see https://quix.io/docs/quix-streams/v2-0-latest/api-reference/quixstreams.html for more details)

# import additional modules as needed
import requests
import os
import json
import time

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="data_source", auto_create_topics=True)  # create an Application

# define the topic using the "output" environment variable
topic_name = os.environ["output"]
topic = app.topic(topic_name)

# define the endpoint URL
url = "http://api.launchdashboard.space/v2/launches/spacex?mission_id=spacex crs-16"

def get_data():
    """
    A function to fetch data from the specified endpoint and extract the telemetry data.
    It returns the mission_id, stage, and a list of updated telemetry data.
    """

    # make a GET request to the endpoint
    response = requests.get(url)
    data = response.json()

    # extract the mission_id, name, and flight_number
    mission_id = data["mission_id"]
    name = data["name"]
    flight_number = data["flight_number"]

    # extract the telemetry data from the "analysed" section
    telemetry_data = data["analysed"][0]["telemetry"]
    stage = data["analysed"][0]["stage"]

    # add mission_id, name, flight_number, and stage to each telemetry entry
    for entry in telemetry_data:
        entry["mission_id"] = mission_id
        entry["name"] = name
        entry["flight_number"] = flight_number
        entry["stage"] = stage

    return mission_id, stage, telemetry_data

def main():
    """
    Fetch data from the endpoint and publish it to Kafka with delays between timestamps
    """

    # create a pre-configured Producer object.
    with app.get_producer() as producer:
        # fetch the telemetry data from the endpoint
        mission_id, stage, telemetry_data = get_data()
        key = f"{mission_id}-stage-{stage}"
        start_loop = time.time()
        first_time = telemetry_data[0]['time']

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

        print("All rows published")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Exiting.")
