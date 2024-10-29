import os

from quixstreams import Application, State

# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv
load_dotenv(override=False)

app = Application()

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

def calculate_XY(row: dict, state: State):

    if any(key not in row for key in ["velocity_x", "velocity_y"]):    
        return

    # get previous row
    previous_row = state.get("previous_row")

    row["X"] = 0
    row["Y"] = 0

    if previous_row is None or any(key not in previous_row for key in ["velocity_x", "velocity_y"]):    
        state.set("previous_row", row)
        return row

    # Check if the current time is less than the previous time, reset state if true
    if row["time"] < previous_row["time"]:
        state.set("previous_row", row)
        return row

    # Calculate time elapsed in nanoseconds
    time_elapsed_seconds = row["time"] - previous_row["time"]

    # average velocity M/S
    velocity_x_per_second = ((row["velocity_x"] + previous_row["velocity_x"]) / 2)
    velocity_y_per_second = ((row["velocity_y"] + previous_row["velocity_y"]) / 2)

    # Calculate distance traveled in X and Y
    distance_x = velocity_x_per_second * time_elapsed_seconds / 1000
    distance_y = velocity_y_per_second * time_elapsed_seconds / 1000

    # Update X and Y values in the current row
    row["X"] = previous_row["X"] + distance_x
    row["Y"] = previous_row["Y"] + distance_y

    # store state
    state.set("previous_row", row)

    # return the updated row so more processing can be done on it
    return row

# apply the result of the count_names function to the row
sdf = sdf.apply(calculate_XY, stateful=True)

# sdf = sdf[["time", "velocity", "velocity_x", "velocity_y", "acceleration", "altitude", "angle", "X", "Y"]]

# print the row with this inline function
sdf = sdf.update(lambda row: print(row))

# publish the updated row to the output topic
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)
