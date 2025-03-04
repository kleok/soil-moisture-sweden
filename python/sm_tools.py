"""
Author: Nina del Rosario
Date: 5/25/2020
Functions for analyzing soil moisture datasets
UPDATE_DESCRIPTION
"""
import sm_config as config
import sm_dictionaries as dicts

from datetime import datetime, timedelta
import json
import netCDF4
import numpy as np
import os
import pandas as pd
import re
import warnings
import math
from pytesmo import temporal_matching

try:
    import icos
    import ismn
    from ascat import H115Ts
    from esa_cci_sm.interface import CCITs
    from gldas.interface import GLDASTs
    from icos import ICOSTimeSeries
    from ismn.interface import ISMN_Interface
    from smap_io import SMAPTs
    from smos.smos_ic.interface import SMOSTs
    from pytesmo import metrics
    from pytesmo.time_series.anomaly import calc_anomaly
except:
    warnings.warn("could not import product packages")


def write_log(log_file, string, print_string=True, write_output=True):
    if write_output:
        with open(log_file, "a") as logfile:
            logfile.write(string + "\n")
    if print_string:
        print(string)


def create_output_dir(output_folder):
    data_output_folder = os.path.join(output_folder, "data_output")
    os.mkdir(data_output_folder)
    log_file = os.path.join(output_folder, "analysis_log.txt")
    metrics_file = os.path.join(output_folder, "analysis_metrics.csv")
    return log_file, metrics_file, data_output_folder


def get_icos_files(input_dir):
    data_dict = {}
    for filename in os.listdir(input_dir):
        filename_parts = filename.split(".")
        station = filename_parts[0]
        data_dict[station] = os.path.join(input_dir, filename)
    return data_dict


def get_icos_readers(input_dir):
    with open("dict_icos.json", "r") as f:
        dict_icos = json.load(f)
    readers = []
    for filename in os.listdir(input_dir):
        filename_parts = filename.split(".")
        station = filename_parts[0]
        metadata = dict_icos[station]
        data = pd.read_csv(os.path.join(input_dir, filename), index_col=0)
        reader = ICOSTimeSeries(metadata, data)
        readers.append(reader)
    return readers


def get_ismn_readers(input_dir):
    ismn_readers = []
    ismn_stations = []
    interface = ISMN_Interface(input_dir)
    for station_object in interface.stations_that_measure("soil moisture"):
        for ISMN_time_series in station_object.data_for_variable("soil moisture", min_depth=0, max_depth=0.1):
            # appends only the first TS of the station in the case where there are multiple sensors per station
            if ISMN_time_series.station not in ismn_stations:
                ismn_readers.append(ISMN_time_series)
                ismn_stations.append(ISMN_time_series.station)
    return ismn_readers


def get_product_list(products):
    product_list = []
    if type(products) == dict:
        for product, analyze in products.items():
            if analyze:
                product_list.append(product)
    elif type(products) == list:
        product_list = products
    elif type(products) == str:
        product_list = [products]
    return product_list


def get_product_reader(product, product_metadata):
    if product == "ASCAT 12.5 TS":
        ts_dir = product_metadata["ts_dir"]
        grid_dir = product_metadata["grid_dir"]
        grid_file = product_metadata["grid_file"]
        static_layers_dir = product_metadata["static_layers_dir"]
        reader = H115Ts(cdr_path=ts_dir, grid_path=grid_dir, grid_filename=grid_file,
                        static_layer_path=static_layers_dir)
    elif product == "CCI Active":
        ts_dir = product_metadata["ts_dir"]
        reader = CCITs(ts_path=ts_dir)
    elif product == "CCI Passive":
        ts_dir = product_metadata["ts_dir"]
        reader = CCITs(ts_path=ts_dir)
    elif product == "CCI Combined":
        ts_dir = product_metadata["ts_dir"]
        reader = CCITs(ts_path=ts_dir)
    elif product == "ERA5":
        ts_dir = None
        reader = None
    elif product == "GLDAS":
        ts_dir = product_metadata["ts_dir"]
        reader = GLDASTs(ts_path=ts_dir)
    elif product == "SMAP L3":
        ts_dir = product_metadata["ts_dir"]
        reader = SMAPTs(ts_path=ts_dir)
    elif product == "SMAP L4":
        ts_dir = product_metadata["ts_dir"]
        reader = SMAPTs(ts_path=ts_dir)
    elif product == "SMOS-IC":
        ts_dir = product_metadata["ts_dir"]
        reader = SMOSTs(ts_path=ts_dir)
    else:
        reader = None
    return reader


def get_ref_data(ts, filter_ref=False, anomaly=False):
    if type(ts) == icos.ICOSTimeSeries:
        ref_data = ts.data
        if filter_ref:
            ref_data = ref_data.loc[ref_data["qc_ssm"] == 0]
        sm_field = "soil moisture"
        sm_data = ref_data[sm_field]
        sm_data.dropna()
        # return sm_data, sm_field
    elif type(ts) == ismn.readers.ISMNTimeSeries:
        ref_data = ts.data
        sm_field = "soil moisture"
        sm_data = ref_data[sm_field]
        sm_data.dropna()
        # return sm_data, sm_field
    sm_data = ref_data[sm_field]
    if anomaly:
        sm_data = calc_anomaly(sm_data)
    return sm_data


def get_product_data(product, reader=None, lon=None, lat=None, station=None, anomaly=False, filter_prod=True, sm_only=True):
    if station is not None:
        lon = station.longitude
        lat = station.latitude
    # if CSV station data exists, get and return data from CSV files
    if station is not None and config.dict_product_inputs[product]['csv_stations'] is not None:
        data = get_csv_station_series(product, station)
    # if station isn't provided or CSV station data does not exist, get data from reader
    else:
        ts = reader.read(lon, lat)
        if product == "ASCAT 12.5 TS":
            data = ts.data
        else:
            data = ts
    if filter_prod:
        data = get_filtered_data(product, data)
    sm_field = dicts.dict_product_fields[product]['sm_field']
    if sm_only and len(data.shape) > 1:
        data = data[sm_field]
    if sm_only and anomaly:
        data = calc_anomaly(data)
    elif (not sm_only) and anomaly:
        data['sm_anomaly'] = calc_anomaly(data[sm_field])
        warnings.warn(
            "new column added to df: sm_anomaly")
    return data


def get_metrics(data, xcol=None, ycol=None, anomaly=False, return_dict=False, sig_level=0.05):
    """""
    Calculate metrics for a pair of TS
    data: temporally matched dataset
    metrics: list of metrics to calculate on matched dataset
        default: "pearsonr", "bias", "rmsd", "ubrmsd"
    """""
    columns = data.columns
    if xcol is None:
        x = data[columns[0]].values
    else:
        x = data[xcol].values
    if ycol is None:
        y = data[columns[1]].values
    else:
        y = data[ycol].values

    metrics_dict = {'pearson_r': None, 'pearson_r_p-value': None, 'bias': None, 'rmsd': None, 'ubrmsd': None,
                    'n': data.shape[0], 'pearson_sig': None}

    try:
        # if anomaly is False:
        metrics_dict['bias'] = metrics.bias(x, y)
        metrics_dict['rmsd'] = metrics.rmsd(x, y)
        metrics_dict['ubrmsd'] = metrics.ubrmsd(x, y)
    except:
        message = "could not calculate bias, rmsd, ubrmsd"
        warnings.warn(message)

    try:
        pearson_r, pearson_r_p = metrics.pearsonr(x, y)
        metrics_dict['pearson_r'] = pearson_r
        metrics_dict['pearson_r_p-value'] = pearson_r_p
        metrics_dict['pearson_sig'] = pearson_r_p < sig_level
    except:
        message = "could not calculate pearson r"
        warnings.warn(message)

    if return_dict:
        return metrics_dict
    else:
        return [metrics_dict['bias'], metrics_dict['rmsd'], metrics_dict['ubrmsd'], metrics_dict['pearson_r'],
                metrics_dict['pearson_r_p-value']]


def convert_tab_comma(filename):
    """""
    Converts tab delimited to comma separated
    filename: tab delimited file
    """""
    file_df = pd.read_csv(filename, sep="\t")
    output_file = filename[:-4]+"_commareformat"+filename[-4:]
    file_df.to_csv(output_file, sep=",")


# given an NC file and coordinate fields, return lower left coordinate and upper right coordinate
def get_geo_extent(nc_file, lon_field="lon", lat_field="lat"):
    """""
    Finds the minimum and maxiumum lat/lon of a netcdf file
    Returns tuple of lower-left and upper-right coordinates
    nc_file: netcdf filename
    lon_field: name of longitude field (default 'lon')
    lat_field: name of latitude field (default 'lat')
    """""
    nc = netCDF4.Dataset(nc_file, "r")
    try:
        lon_array = nc[lon_field][:]
        lat_array = nc[lat_field][:]
        ll = (np.amin(lat_array), np.amin(lon_array))
        ur = (np.amax(lat_array), np.amax(lon_array))
        return ll, ur
    except:
        print("cant\' read file")


# for a value, find the nearest value and its index
def find_nearest(array, value):
    """""
    For an array and value, finds the nearest member of array
    Returns tuple of array index
    """""
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


def get_nc_series(input_root, location, parameters, date_search_str, datetime_format=None, time_dim=True,
                  lon_field="lon", lat_field="lat", date_only=True):
    """""
    Parameters
    input_root: directory of nc files
    location: tuple or dictionary of locations. 
        if tuple of a single location, [format (lat, lon)], a single ts dataframe will be returned. 
        if a dict, a dict of ts dataframes will be returned
            dictionary should be a set of locations. e.g.
                {"City 1": {
                    "longitude": 15,
                    "latitude": 15
                    },
                "City 2": {
                    "longitude": 25,
                    "latitude": 10
                    }
                }
    parameters: parameters to return
    date_search_str: regex expression for finding timestamp e.g. r"[0-9]{8}T[0-9]{4}", must be unique enough to occur 
        only once in filename
    time_dim: boolean, whether the data is organized with 3 dimensions (time, lat, lon) (default: True)
    lon_field: the name of the longitude field in the dataset (default: 'lon')
    lat_field: the name of the latitude field in the dataset (default: 'lat')
    """""
    warnings.filterwarnings("ignore")
    # function to get ts row for a single location
    def get_loc_data(ln_array, lt_array, ln, lt):
        nr_lon_idx = find_nearest(ln_array, ln)[0]
        nr_lat_idx = find_nearest(lt_array, lt)[0]
        vs = {}
        vs['timestamp'] = timestamp
        for p in parameters:
            if time_dim:
                v = ds[p][:][:, nr_lat_idx, nr_lon_idx]
            else:
                v = ds[p][nr_lat_idx, nr_lon_idx]
            v = np.asscalar(np.asarray(v))
            vs[p] = v
        return vs
    # turn parameters into a column list
    if type(parameters) != list:
        parameters = [parameters]
    columns = ["timestamp"]
    for p in parameters:
        columns.append(p)
    # check location type and create output shells
    loc_ts_dict = {}
    if type(location) == dict:
        loc_meta_dict = location
    elif type(location) == tuple:
        loc_meta_dict = {}
        loc_meta_dict["loc"] = {"longitude": location[1], "latitude": location[0]}
    else:
        print("invalid location. should be a tuple or dictionary.")
        return None
    # start processing files
    files = os.listdir(input_root)
    for loc, metadata in loc_meta_dict.items():
        loc_ts_dict[loc] = pd.DataFrame(columns=columns)
    for filename in files:
        file = os.path.join(input_root, filename)
        ds = netCDF4.Dataset(file, mode="r")
        timestamp = get_filename_timestamp(filename=filename, date_search_str=date_search_str, date_only=date_only)
        lon_array = ds[lon_field][:]
        lat_array = ds[lat_field][:]
        # for each file, process all locations and store results in dictionary
        for loc, metadata in loc_meta_dict.items():
            # loc_ts_dict[loc] = pd.DataFrame(columns=columns)
            lon_loc = metadata['longitude']
            lat_loc = metadata['latitude']
            if check_extent(lon_loc, lat_loc, file):
                loc_data = get_loc_data(lon_array, lat_array, lon_loc, lat_loc)
                loc_ts_dict[loc] = loc_ts_dict[loc].append(loc_data, ignore_index=True)
    for loc, ts in loc_ts_dict.items():
        ts = ts.set_index("timestamp")
    if len(loc_ts_dict.keys()) == 1:
        return ts
    else:
        return loc_ts_dict


def get_nc_summary(file, lon_field=None, lat_field=None, sm_field=None, time_field=None, show_field_data=True):
    dataset = netCDF4.Dataset(file, 'r')
    print("Attributes in dataset:")
    print(dataset.ncattrs())
    print("\nDimensions in dataset:")
    for dimension in dataset.dimensions.items():
        print(dimension)
    print("\nVariables in dataset:")
    for variable in dataset.variables.items():
        print(variable)
    if lon_field is not None:
        print("\nLongitude field:")
        print("shape:", dataset[lon_field][:].shape)
        if show_field_data:
            print(dataset[lon_field][:])
    if lat_field is not None:
        print("\nLatitude field:")
        print("shape:", dataset[lat_field][:].shape)
        if show_field_data:
            print(dataset[lat_field][:])
    if sm_field is not None:
        print("\nSM field:")
        print("shape:", dataset[sm_field][:].shape)
        if show_field_data:
            print(dataset[sm_field][:])
    if time_field is not None:
        print("\nTime field:")
        print("shape:", dataset[time_field][:].shape)
        if show_field_data:
            print(dataset[time_field][:])


# given a product with a suffle reader and a dictionary of locations, write TS to csv files
def write_grid_shuffle_ts(product, output_dir, locations, filter=True, anomaly=False, loc_only_filename=False):
    product_str = product.replace(' ', '-')
    reader = get_product_reader(product, config.dict_product_inputs[product])
    if filter:
        filter_str = "filtered"
    else:
        filter_str = "unfiltered"
    if anomaly:
        anomaly_str = "anomaly"
    else:
        anomaly_str = "absolute"
    location_count = len(locations)
    index_count = 0
    for location, coordinate in locations.items():
        lat = coordinate['latitude']
        lat_str = str(lat).replace('.', '-')
        lon = coordinate['longitude']
        lon_str = str(lon).replace('.', '-')
        if loc_only_filename:
            output_filename = "{}.csv".format(location)
        else:
            output_filename = "{}_{}_{}_{}_{}_{}.csv".format(product_str, location, lat_str, lon_str, filter_str,
                                                             anomaly_str)
        data = get_product_data(lon=lon, lat=lat, product=product, reader=reader, filter=filter,
                                anomaly=anomaly)
        output_file = os.path.join(output_dir, output_filename)
        data.to_csv(output_file, sep=',', encoding='latin-1')
        del data
        index_count += 1
        print("{} of {} locations processed".format(index_count, location_count))
    else:
        index_count += 1


# for text-driven datasets, generate filename
def get_station_ts_filename(station_object=None, station_name=None, network_name=None):
    if station_object is not None:
        network = station_object.network
        station = station_object.station
        #     product_str = product.replace(' ', '-')
        filename = "{}_{}.csv".format(network, station.replace(".", "-"))
        return filename
    elif station_name is not None and network_name is not None:
        filename = "{}_{}.csv".format(network_name, station_name.replace(".", "-"))
        return filename


# for text-driven datasets, retrieve time series
def get_csv_station_series(product, station, filter_prod=True, sm_only=True):
    csv_dir = config.dict_product_inputs[product]["csv_stations"]
    filename = get_station_ts_filename(station)
    file = os.path.join(csv_dir, filename)
    data = pd.read_csv(file)
    first_col = data.columns[0]
    data = data.set_index(pd.DatetimeIndex(data[first_col]), drop=True)
    return data


# filters dataframe by date, assuming index is a datetimeindex
def timefilter_data(df, year_filter=None, season_filter=None, month_filter=None, day_filter=None):
    if year_filter is not None:
        df = df[df.index.year == year_filter]
    if season_filter is not None:
        if season_filter == 'non-winter':
            df = df[(df.index.month != 12) & (df.index.month != 1) & (df.index.month != 2)]
        if season_filter == 'winter':
            df = df[(df.index.month == 12) | (df.index.month == 1) | (df.index.month == 2)]
        if season_filter == 'spring':
            df = df[(df.index.month == 3) | (df.index.month == 4) | (df.index.month == 5)]
        if season_filter == 'summer':
            df = df[(df.index.month == 6) | (df.index.month == 7) | (df.index.month == 8)]
        if season_filter == 'fall':
            df = df[(df.index.month == 9) | (df.index.month == 10) | (df.index.month == 11)]
    if month_filter is not None:
        df = df[df.index.month == month_filter]
    if day_filter is not None:
        df = df[df.index.day == day_filter]
    return df


def get_triplet_list(triplets):
    triplet_list = []
    for triplet, analyze in triplets.items():
        if analyze:
            triplet_list.append(triplet)
    return triplet_list


# function for changing time series by shifting existing time by a specified value
def get_timeshifted_data(product, product_data):
    if config.dict_timeshifts[product] is not None:
        value, interval = config.dict_timeshifts[product]
        product_data = product_data.shift(value, freq=interval)
        return product_data
    else:
        return product_data


def get_nc_parameter_count(file, parameter):
    ds = netCDF4.Dataset(file, mode="r")
    param_values = np.asarray(ds[parameter][:]).ravel()
    (unique, counts) = np.unique(param_values, return_counts=True)
    frequencies = np.asarray((unique, counts)).T
    return frequencies


# function to find timestamps from a filename, given a searchsting and format
def get_filename_timestamp(filename, date_search_str, date_only=True, return_int=False):
    """""
    Parameters
    filename: filename string
    date_search_str: regex expression for finding timestamp e.g. r"[0-9]{8}T[0-9]{4}", must be unique enough to occur 
        only once in filename
    date_only: boolean, if false, look for time as well. 
    return_int: boolean, if true, converts timestamp into a number. 
    """""
    result_str = re.findall(date_search_str, filename)[-1]
    date_str = re.findall(r"[0-9]{8}", result_str)[0]
    # assumes timestamp is always after datestamp and timestamp is 6 digits long
    if not date_only:
        time_str = re.findall(r"[0-9]{6}", result_str)[-1]
        timestamp = datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]), int(time_str[0:2]),
                             int(time_str[2:4]), int(time_str[4:6]))
    else:
        timestamp = datetime(int(date_str[0:4]), int(date_str[4:6]), int(date_str[6:8]))
    if return_int:
        timestamp = int(timestamp.timestamp())
    return timestamp


def check_extent(lon_loc, lat_loc, file, lon_field="lon", lat_field="lat"):
    ll, ur = get_geo_extent(file, lon_field, lat_field)
    return not any([lat_loc < ll[0], lat_loc > ur[0], lon_loc < ll[1], lon_loc > ur[1]])


def get_nc_values(file, location, parameters, time_dim=True, lon_field="lon", lat_field="lat"):
    loc_values_dict = {}
    if type(location) == dict:
        loc_meta_dict = location
    else:
        loc_meta_dict = {}
        loc_meta_dict["loc"] = {
            "longitude": location[1],
            "latitude": location[0]
        }
    if type(parameters) != list:
        parameters = [parameters]
    ds = netCDF4.Dataset(file, mode="r")
    lon_array = ds[lon_field][:]
    lat_array = ds[lat_field][:]
    for loc, metadata in loc_meta_dict.items():
        ln = metadata["longitude"]
        lt = metadata['latitude']
        nr_lon_idx = find_nearest(lon_array, ln)[0]
        nr_lat_idx = find_nearest(lat_array, lt)[0]
        for p in parameters:
            if time_dim:
                v = ds[p][:][:, nr_lat_idx, nr_lon_idx]
            else:
                v = ds[p][nr_lat_idx, nr_lon_idx]
            v = np.asscalar(np.asarray(v))
            loc_values_dict[loc][p] = v
    return loc_values_dict


def get_nearest_half_hour(hour, minute):
    hour_fraction = minute/60
    if hour_fraction >= 0 and hour_fraction < 15:
        rounded_minute = 0
        rounded_hour = hour
    elif hour_fraction >=15 and hour_fraction < 45:
        rounded_minute = 30
        rounded_hour = hour
    else:
        if hour < 23:
            rounded_minute = 0
            rounded_hour = hour + 1
        # for simplicity, without knowing dates, round down to 23:30 when between 23:00 and 23:59
        else:
            rounded_minute = 30
            rounded_hour = hour
    return rounded_hour, rounded_minute


def get_date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def get_smap_retrieval_qual(flags):
    flags = int(flags)
    recommended = int(1)
    attempted = int(2)
    success = int(4)
    ft_success = int(8)
    qual_dict = {'recommended': ((flags & recommended) == 0), 'attempted': ((flags & attempted) == 0),
                 'success': ((flags & success) == 0), 'ft_success': ((flags & ft_success) == 0)}
    return qual_dict


def get_filtered_data(product, data, filter_counts=False):
    result_data = None
    sm_field = dicts.dict_product_fields[product]['sm_field']
    filter_count_dict = {'quality': None, 'valid': None, 'passed': None}
    if product == "ASCAT 12.5 TS":
        # Filter for unfrozen data
        quality_data = data.loc[data["ssf"] == 1]
        filter_count_dict['quality'] = quality_data.shape[0]
        # Filter for valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 100)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = data.loc[data["ssf"] == 1]
        result_data = result_data[(result_data[sm_field] >= 0) & (result_data[sm_field] < 100)]
    elif product == "CCI Active":
        # Filter for valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 100)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "CCI Passive":
        # Filter for valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "CCI Combined":
        # Filter for valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "ERA5 0-1" or product == "ERA5 0-25":
        result_data = data
    elif product == "GLDAS":
        # Filter for valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 100)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "SMAP L3" or product == "SMAP L3 Enhanced":
        # Filter based on valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        filter_count_dict['valid'] = valid_data.shape[0]
        # Filter based on retrieval_qual_flag
        quality_data = data[(data['retrieval_qual_flag'] == 0) | (data['retrieval_qual_flag'] == 1) |
                            (data['retrieval_qual_flag'] == 8)]
        filter_count_dict['quality'] = quality_data.shape[0]
        result_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        result_data = result_data[(result_data['retrieval_qual_flag'] == 0) |
                                  (result_data['retrieval_qual_flag'] == 1) |
                                  (result_data['retrieval_qual_flag'] == 8)]
    elif product == "SMAP L4":
        # Filter based on valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "SMOS-IC":
        # Quality_Flag field is already filtered to 0, 1 by reader
        # For now, no filters for SMOS-IC
        # See "Quality_Flag" field
        valid_data = data[data[sm_field] != 2]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "Sentinel-1":
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 100)]
        filter_count_dict['valid'] = valid_data.shape[0]
        result_data = valid_data
    elif product == "SMOS-BEC":
        # Filter product based on valid values
        valid_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        filter_count_dict['valid'] = valid_data.shape[0]
        # Filter product based on quality flag
        # 0: Good quality data;
        # 1: L1 brightness temperature corrected by sea-land contamination;
        # 2: L3 soil moisture with no data;
        # 4: L4 soil moisture without physical meaning";
        # quality_data = data[(data['quality_flag'] == 0) | (data['quality_flag'] == 1)]
        # filter_count_dict['quality'] = quality_data.shape[0]
        result_data = data[(data[sm_field] >= 0) & (data[sm_field] < 1)]
        # result_data = result_data[(result_data['quality_flag'] == 0) | (result_data['quality_flag'] == 1)]
    filter_count_dict['passed'] = result_data.shape[0]
    if filter_counts:
        return result_data, filter_counts
    else:
        return result_data


# function which converts date to seconds since 1/1/70
def unix_time_seconds(dt):
    epoch = datetime.utcfromtimestamp(0)
    seconds = int((dt - epoch).total_seconds())
    return seconds


# function which splits data into timeframe datasets
# input: dataframe or data series where index is date
def split_by_timeframe(df, years, seasons=True, months=True, ignore=[], am_only=True):
    if am_only:
        df = df[df.index.hour < 12]
    timefilter_data_dict = {'No-Timefilter': df}
    timefilters = get_timefilters(years, seasons=seasons, months=months, ignore=ignore)
    for filter in timefilters:
        filter_strs = []
        year_filter = filter[0]
        if year_filter is not None:
            filter_strs.append("Y{}".format(year_filter))
        season_filter = filter[1]
        if season_filter is not None:
            filter_strs.append("{}".format(season_filter))
        month_filter = filter[2]
        if month_filter is not None:
            filter_strs.append("M{:02}".format(month_filter))
        filter_data = timefilter_data(df, year_filter=year_filter, season_filter=season_filter,
                                      month_filter=month_filter)
        filter_str = "-".join(filter_strs)
        timefilter_data_dict[filter_str] = filter_data
    count_dict = {}
    for key in timefilter_data_dict.keys():
        count_dict[key] = timefilter_data_dict[key].shape[0]
    return timefilter_data_dict, count_dict


def get_timefilters(years, seasons=True, months=True, ignore=[]):
    # ignore = list of tuples where tuple represents timeframe in format (year, season, month)
    # year is a tuple of startyear *first year to include) and endyear (last year to include)
    # month is an integer
    # season is a string: "winter", "spring", "summer", "fall"
    if isinstance(ignore, tuple):
        ignore = [ignore]
    timefilters = []
    # timefilter format: (year, season, month)
    startyearrange = years[0]
    endyearrange = years[1] + 1
    for year in range(startyearrange, endyearrange):
        timefilter = (year, None, None)
        timefilters.append(timefilter)
    if seasons:
        for season in ["winter", "spring", "summer", "fall"]:
            timefilter = (None, season, None)
            timefilters.append(timefilter)
        for season in ["winter", "spring", "summer", "fall"]:
            for year in range(startyearrange, endyearrange):
                timefilter = (year, season, None)
                timefilters.append(timefilter)
    if months:
        for month in range(1,13):
            timefilter = (None, None, month)
            timefilters.append(timefilter)
        for month in range(1,13):
            for year in range(startyearrange, endyearrange):
                timefilter = (year, None, month)
                timefilters.append(timefilter)
    timefilters = [timefilter for timefilter in timefilters if timefilter not in ignore]
    return timefilters


def csv_to_pdseries(f):
    data = pd.read_csv(f)
    # assumes first column is a datestamp
    first_col = data.columns[0]
    data = data.set_index(pd.DatetimeIndex(data[first_col]))
    data = data.drop(first_col, axis=1)
    return data


def get_station_code(station):
    station_dict = {**dicts.dict_icos, **dicts.dict_hobe}
    network = station.network
    station_name = station.station
    station_key = " ".join([network, station_name])
    station_code = station_dict[station_key]["code"]
    return station_code


def get_station_cover(station):
    station_dict = {**dicts.dict_icos, **dicts.dict_hobe}
    network = station.network
    station_name = station.station
    station_key = " ".join([network, station_name])
    station_cover = station_dict[station_key]["cover"]
    return station_cover

def merge_tables(files):
    merged = None
    for file in files:
        df = pd.read_csv(file)
        if merged is None:
            merged = df
        else:
            merged = pd.concat([merged, df])
    return merged


def calc_tcol_cov(x, y, z):
    cov = np.cov(np.vstack((x, y, z)))

    ind = (0, 1, 2, 0, 1, 2)

    tcol_cov = np.array([
                            [cov[i, i],
                            cov[i, ind[i+1]],
                            cov[i, ind[i+2]]]
                        for i in np.arange(3)])

    return tcol_cov


def calc_tcol_snr(x, y, z, ref_ind=0):
    """
    adapted on pytesmo tcol_snr function (rewriting SNR formulate to match Gruber)

    triple collocation based estimation of signal-to-noise ratio, absolute errors,
    and rescaling coefficients

    Parameters
    ----------
    x: 1D numpy.ndarray
        first input dataset
    y: 1D numpy.ndarray
        second input dataset
    z: 1D numpy.ndarray
        third input dataset
    ref_ind: int
        index of reference data set for estimating scaling coefficients. default: 0 (x)

    Returns
    -------
    snr: numpy.ndarray
        signal-to-noise (variance) ratio [dB]
    err_std: numpy.ndarray
        **SCALED** error standard deviation
    beta: numpy.ndarray
         scaling coefficients (i_scaled = i * beta_i)

    Notes
    -----

    This function estimates the triple collocation errors, the scaling
    parameter :math:`\\beta` and the signal to noise ratio directly from the
    covariances of the dataset. For a general overview and how this function and
    :py:func:`pytesmo.metrics.tcol_error` are related please see [Gruber2015]_.

    Estimation of the error variances from the covariances of the datasets
    (e.g. :math:`\\sigma_{XY}` for the covariance between :math:`x` and
    :math:`y`) is done using the following formula:

    .. math:: \\sigma_{\\varepsilon_x}^2 = \\sigma_{X}^2 - \\frac{\\sigma_{XY}\\sigma_{XZ}}{\\sigma_{YZ}}
    .. math:: \\sigma_{\\varepsilon_y}^2 = \\sigma_{Y}^2 - \\frac{\\sigma_{YX}\\sigma_{YZ}}{\\sigma_{XZ}}
    .. math:: \\sigma_{\\varepsilon_z}^2 = \\sigma_{Z}^2 - \\frac{\\sigma_{ZY}\\sigma_{ZX}}{\\sigma_{YX}}

    :math:`\\beta` can also be estimated from the covariances:

    .. math:: \\beta_x = 1
    .. math:: \\beta_y = \\frac{\\sigma_{XZ}}{\\sigma_{YZ}}
    .. math:: \\beta_z=\\frac{\\sigma_{XY}}{\\sigma_{ZY}}

    The signal to noise ratio (SNR) is also calculated from the variances
    and covariances:

    .. math:: \\text{SNR}_X[dB] = -10\\log\\left(\\frac{\\sigma_{X}^2\\sigma_{YZ}}{\\sigma_{XY}\\sigma_{XZ}}-1\\right)
    .. math:: \\text{SNR}_Y[dB] = -10\\log\\left(\\frac{\\sigma_{Y}^2\\sigma_{XZ}}{\\sigma_{YX}\\sigma_{YZ}}-1\\right)
    .. math:: \\text{SNR}_Z[dB] = -10\\log\\left(\\frac{\\sigma_{Z}^2\\sigma_{XY}}{\\sigma_{ZX}\\sigma_{ZY}}-1\\right)

    It is given in dB to make it symmetric around zero. If the value is zero
    it means that the signal variance and the noise variance are equal. +3dB
    means that the signal variance is twice as high as the noise variance.

    References
    ----------
    .. [Gruber2015] Gruber, A., Su, C., Zwieback, S., Crow, W., Dorigo, W., Wagner, W.
       (2015). Recent advances in (soil moisture) triple collocation analysis.
       International Journal of Applied Earth Observation and Geoinformation,
       in review
    """

    cov = np.cov(np.vstack((x, y, z)))

    ind = (0, 1, 2, 0, 1, 2)
    no_ref_ind = np.where(np.arange(3) != ref_ind)[0]

    snr = (-10) * np.log10(
        [((cov[i, i] * cov[ind[i + 1], ind[i + 2]]) / (cov[i, ind[i + 1]] * cov[i, ind[i + 2]]) - 1)
                            for i in np.arange(3)])

    err_var = np.array([
        cov[i, i] -
        (cov[i, ind[i + 1]] * cov[i, ind[i + 2]]) / cov[ind[i + 1], ind[i + 2]]
        for i in np.arange(3)])

    beta = np.array([cov[ref_ind, no_ref_ind[no_ref_ind != i][0]] /
                     cov[i, no_ref_ind[no_ref_ind != i][0]] if i != ref_ind
                     else 1 for i in np.arange(3)])

    return snr, np.sqrt(err_var) * beta, beta


def calc_tcol_r(s):
    # 1/squareroot(1 + (1/SNR))
    # beta = np.array([cov[ref_ind, no_ref_ind[no_ref_ind != i][0]] /
    #                  cov[i, no_ref_ind[no_ref_ind != i][0]] if i != ref_ind
    #                  else 1 for i in np.arange(3)])
    # create numpy array
    print(s)
    r = np.array(
        # calculate r
        [1./math.sqrt(1. + (1./s[i]))
         # if s[i] is a number
         if isinstance(s[i], float) and 1. + (1./s[i]) >= 0
         else None
         for i in np.arange(len(s))])
    return r


def temporal_match_csv(dataset_csv, loc, anomaly=True, match_window=1):
    # dataset_csv is a list of tuples (dataset name, csv filename)
    ts_dfs = []
    for dataset, file in dataset_csv:
    # for dataset, file in csv_dict.items():
        ts = csv_to_pdseries(file)
        ts = ts.squeeze()
        if anomaly:
            ts = calc_anomaly(ts)
        ts.rename(dataset, inplace=True)
        ts.dropna()
        ts_dfs.append(ts)
    if anomaly:
        anomaly_str = "anomaly"
    else:
        anomaly_str = "absolute"
    if ts_dfs[0].size > 0 and ts_dfs[1].size > 0 and ts_dfs[2].size > 0:
        matched_data = temporal_matching.matching(ts_dfs[0], ts_dfs[1], ts_dfs[2],
                                                  window=match_window)
    else:
        matched_data = None
    triplet_str = "{}_{}_{}_{}_{}".format(dataset_csv[0][0], dataset_csv[1][0], dataset_csv[2][0], anomaly_str, loc)
    return matched_data, triplet_str
