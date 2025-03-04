"""
Author: Nina del Rosario
Date: UPDATE_DATE
UPDATE_DESCRIPTION
"""

import datetime
import os
import pandas
import re
import sm_config as config
import sm_dictionaries as dicts
import sm_tools as tools
from netCDF4 import Dataset


write_ts_to_file = True
product = "SMOS-BEC"
# input_dir = config.dict_product_inputs[product]['raw_dir']
input_dir = r"D:\sm_backup\smos-bec-reprocessed-01km-euro\ASC"
output_dir = "../test_output_data/smos_bec_rewrite"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
file_list = os.listdir(input_dir)
file_list.sort()
export_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
sm_key = dicts.dict_product_fields[product]['sm_field']
qf_key = 'quality_flag'
time_key = 'time'
product_lon = dicts.dict_product_fields[product]['lon_field']
product_lat = dicts.dict_product_fields[product]['lat_field']

ref_locations = {}
icos_stations = dicts.dict_icos
hobe_stations = dicts.dict_hobe
ref_locations.update(dicts.dict_icos)
ref_locations.update(dicts.dict_hobe)

# # TEST: SM value range
# for filename in os.listdir(input_dir):
#     file = os.path.join(input_dir, filename)
#     counts = tools.get_nc_parameter_count(file, sm_key)
#     print(counts.shape)

# dict to store station ts dataframes
station_ts = {}
# dict used for get_values function
ref_locations_len = len(list(ref_locations.keys()))
location_idx = 0
for location, metadata in ref_locations.items():
    location_idx += 1
    print("*** processing location {} of {} ***".format(location_idx, ref_locations_len))
    network = metadata["network"]
    station = metadata["station"]
    lon = metadata['longitude']
    lat = metadata['latitude']
    station_ts[location] = {}
    station_ts[location]["filename"] = tools.get_station_ts_filename(station_object=None, station_name=station,
                                                                     network_name=network)
    print(station_ts[location]["filename"])
    # def get_nc_series(input_root, parameters, date_search_str, datetime_format, lon_loc=None, lat_loc=None, loc_dict=None,
    #                   time_dim=True, lon_field="lon", lat_field="lat"):
    # station_ts[location]["data"] = tools.get_nc_series(
    #     input_root=input_dir, location=(lat, lon), parameters=[sm_key, qf_key], date_search_str=r"[0-9]{8}T[0-9]{4}",
    #     datetime_format=((0, 4), (4, 6), (6, 8), (9, 11), (11, 13)))
    data = tools.get_nc_series(input_root=input_dir, location=(lat, lon), parameters=[sm_key, qf_key],
                               date_search_str=r"[0-9]{8}T", date_only=True)
    # Force shift time to 5 AM (local overpass time in UTC)
    # product_data = product_data.shift(value, freq=interval)
    data = data.shift(5, "H")
    station_ts[location]["data"] = data
    print(station_ts[location]["data"].head())
    station_ts[location]["data"].to_csv(os.path.join(output_dir, station_ts[location]["filename"]), sep=",")