"""
Author: Nina del Rosario
Date: UPDATE_DATE
UPDATE_DESCRIPTION
"""

import datetime
import os
import pandas
import sm_config as config
import sm_dictionaries as dicts
import sm_tools as tools
from sentinel import SentinelImg


write_ts_to_file = True
product = "Sentinel-1"
input_dir = config.dict_product_inputs[product]['raw_dir']
output_dir = r"../test_output_data/sentinel-rewrite"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
file_list = os.listdir(input_dir)
file_list.sort()
export_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

sm_key = dicts.dict_product_fields[product]['sm_field']
# hours_shift = config.dict_timeshifts[product]['hours_shift']

ref_locations = {}
icos_stations = dicts.dict_icos
hobe_stations = dicts.dict_hobe
ref_locations.update(dicts.dict_icos)
ref_locations.update(dicts.dict_hobe)

# dict to store station ts dataframes
station_ts = {}
# dict used for get_values function
locations = {}
for location, metadata in ref_locations.items():
    if "network" in metadata.keys():
        filename = "{}_{}.csv".format(metadata["network"], metadata["station"].replace(".", "-"))
    else:
        filename = "quarterdeg_{}.csv".format(location)
    station_ts[location] = {}
    station_ts[location]["filename"] = filename
    station_ts[location]["data"] = None
    locations[location] = {}
    locations[location]['lon'] = metadata['longitude']
    locations[location]['lat'] = metadata['latitude']


# extract data for locations from images
for filename in file_list:
    print(filename)
    file = os.path.join(input_dir, filename)
    image = SentinelImg(file, parameter=['ssm', 'ssm_noise'])
    timestamp = image.timestamp
    data_dict = image.get_values(locations)
    for key, value in data_dict.items():
        if key == "metadata":
            metadata = value
            # sm_fill_value = metadata[sm_key]['_FillValue']
        else:
            location = key
            data = value['data']
             # sm_value = data[sm_key]
            # # only add valid values (invalid values were set to fill value by image reader class)
            # if sm_value != sm_fill_value:
            loc_df = station_ts[location]['data']
            # if timestamp defaults to midnight, shift time to UTC of local overpass time
            # obs_timestamp = timestamp + datetime.timedelta(hours=hours_shift)
            obs_timestamp = timestamp + datetime.timedelta(hours=18)
            # obs_df = pandas.DataFrame([[obs_timestamp, sm_value]], columns=['timestamp', 'sm'])
            # station_ts[location]['data'] = pandas.concat([loc_df, obs_df])
            # cell_locations.append({'loc': int(ds['location_id'].data[i]), 'lon': ds['lon'].data[i], 'lat': ds['lat'].data[i]}, ignore_index=True)
            # station_ts[location]["data"] = pandas.DataFrame(columns=['timestamp', 'sm'])
            if station_ts[location]['data'] is None:
                columns = ['timestamp'] + list(data.keys())
                station_ts[location]['data'] = pandas.DataFrame(columns=columns)
            data['timestamp'] = obs_timestamp
            station_ts[location]['data'] = station_ts[location]['data'].append(data, ignore_index=True)

for location, metadata in station_ts.items():
    filename = metadata['filename']
    df = metadata['data']
    df.set_index('timestamp', drop=True)
    # df = df.shift(18, freq='H')
    tools.write_log(os.path.join(output_dir, "results_log_{}.txt".format(export_timestamp)),
                    "{}: {} rows".format(filename, df.shape[0]))
    if write_ts_to_file:
        df.to_csv(os.path.join(output_dir, filename), index=False)