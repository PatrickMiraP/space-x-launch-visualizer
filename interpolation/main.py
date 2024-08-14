import os

from quixstreams import Application, State
# import the dotenv module to load environment variables from a file
from dotenv import load_dotenv
load_dotenv(override=False)

app = Application(consumer_group="interpolation-v1", auto_offset_reset="latest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)
sdf.print()
fgfg
def last_value(row: dict, state: State):
    state_value = state.get("last_value", None)
    
    state.set("last_value", row)
    
    return state_value

sdf["last_value"] = sdf.apply(last_value, stateful=True)

def interpolate(row: dict):
    
    if row["last_value"] is None:
        return []
    
    delta_ms = (row["time"] - row["last_value"]["time"]) * 1000
    steps = delta_ms / 100
    
    result = []
    
    for i in range(int(steps)):
        new_row = {}
        for key in row.keys():
            if isinstance(row[key], (int, float)):
                value_delta = row[key] - row["last_value"][key]
                step = value_delta / steps
                new_row[key] = row["last_value"][key] + (step * i)
            if isinstance(row[key], (str)):
                new_row[key] = row[key]
        result.append(new_row)
    
    return result

sdf = sdf.apply(interpolate, expand=True)


# publish the updated row to the output topic
sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)
