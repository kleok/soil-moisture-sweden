"""
Author: Nina del Rosario
Date: 2/10/2021
Status: This script contains functions used for evaluation, some functions that are specific to analyzing csv files have
been split out to sm_csv_evaluation.py
UPDATE_DESCRIPTION
"""
from datetime import datetime
import os
import pandas
import warnings
import sm_dictionaries as dicts

from pytesmo import metrics, temporal_matching
from pytesmo.scaling import scale
from pytesmo.time_series.anomaly import calc_anomaly
import sm_tools as tools
import sm_config as config


# function to evaluate time series for two datasets for one location
# input: dictionary datasets, ref = tuple of name, data, eval = tuple of name, data
# output: dictionary of location metrics, dictionary of metrics, matched data
# evaluate location
def evaluate_gridcell_xr(evaluation_dict, lon, lat):
    # reference: tuple of reference dataset name and reference dataset
    # reference name is a string, reference_dataset is an xarray dataset
    ref_dataset_name, ref_dataset = evaluation_dict['reference']
    # evaluation: a tuple of evaluation dataset name and evaluation dataset
    # evaluation_name is a string, evaluation_dataset is an xarray dataset
    eval_dataset_name, eval_dataset = evaluation_dict['evaluation']
    # start_date is a datetime.datetime object
    start_date = evaluation_dict['start_date']
    # end_date is a datetime.datetime object
    end_date = evaluation_dict['end_date']
    # anomaly: boolean which determines if absolute or anomaly values are calculated
    anomaly = evaluation_dict['anomaly']
    # match window: number value for temporal matching (1 hour = 1/24.)
    match_window = evaluation_dict['match_window']
    # evaluate_timeframes: a boolean - if True, matched data will be split into timeframes and a separate metrics table and inventory table
    # will be returned
    evaluate_timeframes = evaluation_dict['evaluate_timeframes']
    data = {}
    metrics = {}
    ref_sm_field = dicts.dict_product_fields[ref_dataset_name]['sm_field']
    eval_sm_field = dicts.dict_product_fields[eval_dataset_name]['sm_field']
    ref_ts = ref_dataset[ref_sm_field]
    eval_ts = eval_dataset[eval_sm_field]
    ref_ts = ref_ts.sel(time=slice(start_date, end_date), lat=lat, lon=lon).to_pandas()
    eval_ts = eval_ts.sel(time=slice(start_date, end_date), lat=lat, lon=lon).to_pandas()
    ref_ts.rename('ref_sm', inplace=True)
    ref_ts = ref_ts.to_frame()
    eval_ts.rename('eval_ts', inplace=True)
    eval_ts = eval_ts.to_frame()
    matched_data = temporal_matching.matching(ref_ts, eval_ts, window=match_window)
    data['matched_data'] = matched_data
    data['ref_ts'] = ref_ts
    data['eval_ts'] = eval_ts
    metrics['all'] = tools.get_metrics(data=matched_data, anomaly=anomaly, return_dict=True)
    if evaluate_timeframes:
        timeframe_data_dict, timeframe_counts = tools.split_by_timeframe(matched_data, (2015,2018))
        for timeframe, timeframe_data in timeframe_data_dict.items():
            # unresolved reference, is this supposed to be tools.get_metrics()?
            # changing from get_evaluation_metrics_xr(timeframe_data, anomaly)
            # metrics[timeframe] = tools.get_metrics(data=timeframe_data, anomaly=anomaly)
            metrics[timeframe] = tools.get_metrics(data=timeframe_data, anomaly=anomaly, return_dict=True)
    return metrics, data


# function to cycle through each in-situ station in a network, evaluate network-level timeframes
# input: folder for in-situ station data
# output: dictionary of
# evaluate station network
def evaluate_insitu_network_xr(evaluation_dict):
    # evaluation: a tuple of evaluation dataset name and evaluation dataset
    # evaluation_name is a string, evaluation_dataset is an xarray dataset
    evaluation_name, evaluation_dataset = evaluation_dict['evaluation']
    # network: a tuple of the network name and the folder where network in-situ data is located
    network_name, network_data = evaluation_dict['network']
    # start_date is a datetime.datetime object
    start_date = evaluation_dict['start_date']
    # end_date is a datetime.datetime object
    end_date = evaluation_dict['end_date']
    # match window: number value for temporal matching (1 hour = 1/24.)
    match_window = evaluation_dict['match_window']
    # evaluate_timeframes: a boolean - if True, matched data will be split into timeframes and a separate metrics table and inventory table
    # will be returned
    evaluate_timeframes = evaluation_dict['evaluate_timeframes']
    # export_ts: a boolean - if True, time series data (reference, evaluation, matched) will be exported as csv to output_folder,
    # but metrics and inventory will be exported
    export_ts = evaluation_dict['export_ts']
    # output_root: a folder location to output metrics table, inventory table, and datasets (if export_datasets = True)
    # if None, output will be returned by function but not saved to file
    output_root = evaluation_dict['output_root']
    # cycle through each location
        # metrics, matched_data = evaluate_location_xr(dataset_dict)
        # get metrics and add to df
        # get inventory and add to df
        # for each timeframe
            # add matched data to
    # build dataframe of all matched data
    pass


# function for evaluating a set of grid cells in a region
def evaluate_grid_xr(evaluation_dict):
    def get_new_grid_metrics_df():
        metrics_df = pandas.DataFrame(columns=['ref_dataset', 'eval_dataset', 'timefilter', 'anomaly', 'loc',
                                               'lon', 'lat', 'veg_class', 'pearson_r', 'pearson_r_p-value', 'bias',
                                               'rmsd', 'ubrmsd', 'n', 'pearson_sig'])
        return metrics_df
    def get_grid_metrics_row():
        metrics_row = {'ref_dataset': ref_dataset_name, 'eval_dataset': eval_dataset_name, 'timefilter': timeframe,
                       'anomaly': anomaly, 'loc': loc, 'lon': lon, 'lat': lat, 'veg_class': veg_class}
        return metrics_row
    # locations: a dictionary where each key is a location name,
    # the value is another dictionary with "longitude" and "latitude" keys that have numeric coordinate values
    locations = evaluation_dict['locations']
    # reference: tuple of reference dataset name and reference dataset
    # reference name is a string, reference_dataset is an xarray dataset
    ref_dataset_name, ref_dataset = evaluation_dict['reference']
    # evaluation: a tuple of evaluation dataset name and evaluation dataset
    # evaluation_name is a string, evaluation_dataset is an xarray dataset
    eval_dataset_name, eval_dataset = evaluation_dict['evaluation']
    # anomaly: boolean which determines if absolute or anomaly values are calculated
    anomaly = evaluation_dict['anomaly']
    # export_ts: a boolean - if True, time series data (reference, evaluation, matched) will be exported as csv to output_folder,
    # but metrics and inventory will be exported
    export_ts = evaluation_dict['export_ts']
    # output_root: a folder location to output metrics table, inventory table, and datasets (if export_datasets = True)
    # a subfolder for each evaluation dataset will be created
    output_root = evaluation_dict['output_root']
    # verbose: boolean which determines if log messages are printed (if false, warnings will still be printed)
    verbose = evaluation_dict['verbose']
    metrics_dict = {}
    if anomaly:
        anomaly_str = "anomaly"
    else:
        anomaly_str = "absolute"
    evaluation_str = "{} {} {}".format(eval_dataset_name, ref_dataset_name, anomaly_str)
    output_folder = os.path.join(output_root, evaluation_str)
    os.makedirs(output_folder)
    if export_ts:
        ts_folder = os.path.join(output_folder, "ts_folder")
        os.mkdir(ts_folder)
    logfile = os.path.join(output_folder, "{} log.txt".format(evaluation_str))
    tools.write_log(logfile, evaluation_str, print_string=verbose)
    for loc, loc_data in locations.items():
        loc_evaluation_str = "{} {}".format(evaluation_str, loc)
        try:
            lon = loc_data['longitude']
            lat = loc_data['latitude']
            veg_class = loc_data['veg_class_name']
            loc_metrics_dict, loc_data_dict = evaluate_gridcell_xr(evaluation_dict=evaluation_dict, lon=lon, lat=lat)
            for timeframe, timeframe_metrics in loc_metrics_dict.items():
                timeframe_evaluation_str = "{} {}".format(loc_evaluation_str, timeframe)
                n = timeframe_metrics['n']
                sig = timeframe_metrics['pearson_sig']
                pearson_r = timeframe_metrics['pearson_r']
                tools.write_log(logfile, "{}, rows: {}".format(timeframe_evaluation_str, n), print_string=verbose)
                tools.write_log(logfile, "{}, pearson_r: {}".format(timeframe_evaluation_str, pearson_r),
                                print_string=verbose)
                tools.write_log(logfile, "{}, significant: {}".format(timeframe_evaluation_str, sig),
                                print_string=verbose)
                loc_metrics_row = get_grid_metrics_row()
                loc_metrics_row.update(timeframe_metrics)
                if timeframe not in metrics_dict.keys():
                    metrics_dict[timeframe] = get_new_grid_metrics_df()
                metrics_dict[timeframe] = metrics_dict[timeframe].append(loc_metrics_row, ignore_index=True)
            if export_ts:
                loc_ref_data = loc_data_dict['ref_ts']
                loc_ref_data.to_csv(os.path.join(os.path.join(ts_folder, "{} {} ts.csv".format(ref_dataset_name, loc))))
                loc_eval_data = loc_data_dict['eval_ts']
                loc_eval_data.to_csv(os.path.join(os.path.join(ts_folder, "{} {} ts.csv".format(eval_dataset_name, loc))))
                loc_matched_data = loc_data_dict['matched_data']
                loc_matched_data.to_csv(os.path.join(os.path.join(ts_folder, "{} matched.csv".format(loc_evaluation_str))))
        except:
            message = "WARNING! could not process {}".format(loc_evaluation_str)
            warnings.warn(message)
            tools.write_log(logfile, message, print_string=verbose)
    for timeframe, metrics_df in metrics_dict.items():
        metrics_df.to_csv(os.path.join(output_folder, "{} {} metrics.csv".format(evaluation_str, timeframe)),
                          index=False)
    return metrics_dict


def evaluate_shuffle(references, products, output_folder, startdate=datetime(2015, 4, 1), enddate=datetime(2018, 12, 31, 23, 59),
             export_ts=True, evaluate_timeframes=True, anomaly=False, metrics_df=None):
    """""
    Function to compare soil moisture product to reference data
    Reference data supported: ICOS and ISMN (GLDAS forthcoming)

    Parameters
    ----------
    references: list of ICOS or ISMN time series objects (adding GLDAS soon)
    products:   dictionary of product(s) to analyze, examples:
                evaluation_dict = {"ASCAT 12.5 TS": True}
                see product_parameters_dict in sm_config.py for dataset names and to set dataset parameters
    output_folder: directory where metrics and ts data will be saved
    startdate:  datetime used to filter product data to be analyzed (default 4/1/2015)
    enddate:    datetime used to filter product data to be analyzed (default 12/31/2018 23:59)
    export_ts: whether ts data (reference, product, and matched) should be exported as csv files to output_folder
    evaluate_timeframes: boolean, if true config.years_timeframes and config.seasons_timeframes will be evaluated
    metrics_df: df of metrics. if None, new metrics_df will be created. otherwise existing metrics_df will be extended.
    """""
    log_file = os.path.join(output_folder, "analysis_log.txt")
    data_output_folder = os.path.join(output_folder, "data_output")

    # in case analysis fails, get an empty metrics row to indicate that something failed
    def get_empty_metrics_df():
        empty_df = pandas.DataFrame([[network_name, station_name, product_str, timeframe, anomaly, n, None, None,
                                      None, None, None]], columns=config.metrics_df_columns)
        return empty_df

    if not os.path.exists(data_output_folder):
        os.mkdir(data_output_folder)
    if metrics_df is None:
        metrics_df = pandas.DataFrame(columns=config.metrics_df_columns)
    else:
        metrics_df = metrics_df
    product_list = tools.get_product_list(products)
    if anomaly:
        anomaly_str = "anomaly"
    else:
        anomaly_str = "absolute"
    matched_data_dict = {}
    tools.write_log(
        log_file,
        "*** EVALUATION STARTING: {} - {}, evaluate_timeframes: {}, anomaly: {} ***".format(
            startdate, enddate, evaluate_timeframes, anomaly))
    for product in product_list:
        tools.write_log(log_file, "*** STARTING {} ({}) ANALYSIS ***".format(product, anomaly_str))
        timeframe = "all-dates"
        product_str = product.replace(' ', '-')
        product_reader = tools.get_product_reader(product, config.dict_product_inputs[product])
        # product_sm_col = dicts.dict_product_fields[product]['sm_field']
        matched_data_dict = {}
        for station in references:
            station_name = station.station
            network_name = station.network
            ref_data_str = 'ref_data_{}_{}_{}_{}.csv'.format(network_name, station_name, timeframe, anomaly_str)
            product_data_str = 'product_data_{}_{}_{}_{}_{}.csv'.format(product_str, network_name, station_name,
                                                                        timeframe, anomaly_str)
            matched_data_str = 'station_matched_data_{}_{}_{}_{}_{}.csv'.format(product_str, network_name,
                                                                                station_name, timeframe, anomaly_str)
            # scaled_data_str = 'station_scaled_data_{}_{}_{}_{}_{}.csv'.format(product_str, network_name,
            #                                                                   station_name, timeframe, anomaly_str)
            if network_name not in matched_data_dict.keys():
                matched_data_dict[network_name] = pandas.DataFrame()
            tools.write_log(log_file, "*** analyzing {} x {} {} ({}) ***".format(product, network_name,
                                                                                 station_name, anomaly_str))
            ref_data = tools.get_ref_data(station, anomaly=anomaly)
            tools.write_log(log_file, 'ref_data.shape: {}'.format(ref_data.shape))
            if export_ts:
                ref_data.to_csv(os.path.join(data_output_folder, ref_data_str))
            # ref_sm_col = tools.get_ref_data(station)[1]
            ref_data.rename('ref_sm', inplace=True)
            product_data = tools.get_product_data(lon=station.longitude, lat=station.latitude, product=product,
                                                  reader=product_reader, anomaly=anomaly, station=station)
            product_data.rename('product_sm', inplace=True)
            tools.write_log(log_file, 'product_data.shape: {}'.format(product_data.shape))
            product_data = product_data.loc[startdate:enddate]
            tools.write_log(log_file, 'product_data.shape (with date filter): {}'.format(product_data.shape))
            product_data = tools.get_timeshifted_data(product, product_data)
            if export_ts:
                product_data.to_csv(os.path.join(data_output_folder, product_data_str))
            matched_data = pandas.DataFrame()
            if product_data.shape[0] > 0:
                matched_data = temporal_matching.matching(product_data, ref_data, window=1 / 24.)
                n = matched_data.shape[0]
                if export_ts:
                    matched_data.to_csv(os.path.join(data_output_folder, matched_data_str))
                network_matched_data = matched_data_dict[network_name]
                matched_data_dict[network_name] = pandas.concat([network_matched_data, matched_data])
                tools.write_log(log_file, '{} matched data shape: {}'.format(
                    network_name, matched_data_dict[network_name].shape))
                tools.write_log(log_file, 'matched_data.shape: {}'.format(matched_data.shape))
            # insert scaling conditional here
            else:
                n = 0
                tools.write_log(log_file, 'insufficient data for matching: {}'.format(product))
            try:
                metric_values = tools.get_metrics(matched_data, 'product_sm', 'ref_sm', anomaly)
                station_metrics_df = pandas.DataFrame([[network_name, station_name, product_str, timeframe,
                                                        anomaly, n] + metric_values], columns=config.metrics_df_columns)
                tools.write_log(log_file, str(station_metrics_df))
                metrics_df = pandas.concat([metrics_df, station_metrics_df])
                tools.write_log(log_file, '{} x {} {} ({}) analysis complete'.format(product, network_name,
                                                                                     station_name, anomaly_str))
                tools.write_log(log_file, '')
            except:
                empty_metrics_df = get_empty_metrics_df()
                metrics_df = pandas.concat([metrics_df, empty_metrics_df])
                message = "Could not calculate metrics. Skipping to next station."
                warnings.warn(message)
                tools.write_log(log_file, message)
                # write break here?
        # network level analysis
        tools.write_log(log_file, '*** analyzing networks ({}) ***'.format(anomaly_str))
        for network, network_matched_data in matched_data_dict.items():
            station_name = "All"
            # network_matched_data.dropna
            data_output_str = 'network_{}_{}_{}_{}_matched_data.csv'.format(
                product, network_name, timeframe, anomaly_str)
            if export_ts:
                network_matched_data.to_csv(os.path.join(data_output_folder, data_output_str))
            tools.write_log(log_file, '*** analyzing {} ({}) ***'.format(network, anomaly_str))
            try:
                metric_values = tools.get_metrics(network_matched_data, 'product_sm', 'ref_sm', anomaly)
                n = network_matched_data.shape[0]
                network_metrics_df = pandas.DataFrame(
                    [[network_name, station_name, product_str, timeframe, anomaly, n] + metric_values],
                    columns=config.metrics_df_columns)
                tools.write_log(log_file, str(network_metrics_df))
                metrics_df = pandas.concat([metrics_df, network_metrics_df])
            except:
                empty_metrics_df = get_empty_metrics_df()
                metrics_df = pandas.concat([metrics_df, empty_metrics_df])
                message = "Could not calculate network metrics."
                warnings.warn(message)
                tools.write_log(log_file, message)
                # write break here?
            if evaluate_timeframes:
                if len(config.year_timeframes) > 0:
                    for year in config.year_timeframes:
                        timeframe = year
                        data_output_str = 'network_{}_{}_{}_matched_data.csv'.format(network_name, timeframe,
                                                                                     anomaly_str)
                        tools.write_log(log_file, '*** analyzing {} {} for {} ({}) ***'.format(network, timeframe,
                                                                                               product, anomaly_str))
                        tf_network_matched_data = tools.timefilter_data(network_matched_data, year_filter=year)
                        if export_ts:
                            tf_network_matched_data.to_csv(os.path.join(data_output_folder, data_output_str))
                        tools.write_log(log_file, '{} {} matched data shape: {}'.format(network_name, timeframe,
                                                                                        tf_network_matched_data.shape))
                        try:
                            metric_values = tools.get_metrics(tf_network_matched_data, 'product_sm', 'ref_sm', anomaly)
                            n = tf_network_matched_data.shape[0]
                            tf_network_metrics_df = pandas.DataFrame(
                                [[network_name, "All", product_str, timeframe, anomaly, n] + metric_values],
                                columns=config.metrics_df_columns)
                            tools.write_log(log_file, str(tf_network_metrics_df))
                            metrics_df = pandas.concat([metrics_df, tf_network_metrics_df])
                        except:
                            empty_metrics_df = get_empty_metrics_df()
                            metrics_df = pandas.concat([metrics_df, empty_metrics_df])
                            message = "Could not calculate timeframe metrics."
                            warnings.warn(message)
                            tools.write_log(log_file, message)
                            # write break here?
                if len(config.season_timeframes) > 0:
                    for season in config.season_timeframes:
                        timeframe = season
                        data_output_str = 'network_{}_{}_{}_matched_data.csv'.format(network_name, timeframe,
                                                                                     anomaly_str)
                        tools.write_log(log_file, '*** analyzing {} {} for {} ***'.format(network, timeframe, product))
                        tf_network_matched_data = tools.timefilter_data(network_matched_data,
                                                                               season_filter=season)
                        if export_ts:
                            tf_network_matched_data.to_csv(os.path.join(data_output_folder, data_output_str))
                        tools.write_log(log_file, '{} {} matched data shape: {}'.format(network_name, timeframe,
                                                                                        tf_network_matched_data.shape))
                        try:
                            metric_values = tools.get_metrics(tf_network_matched_data, 'product_sm', 'ref_sm', anomaly)
                            n = tf_network_matched_data.shape[0]
                            tf_network_metrics_df = pandas.DataFrame(
                                [[network_name, "All", product_str, timeframe, anomaly, n] + metric_values],
                                columns=config.metrics_df_columns)
                            tools.write_log(log_file, str(tf_network_metrics_df))
                            metrics_df = pandas.concat([metrics_df, tf_network_metrics_df])
                        except:
                            empty_metrics_df = get_empty_metrics_df()
                            metrics_df = pandas.concat([metrics_df, empty_metrics_df])
                            message = "Could not calculate timeframe metrics."
                            warnings.warn(message)
                            tools.write_log(log_file, message)
                            # write break here?
        tools.write_log(log_file, '*** {} ({}) ANALYSIS COMPLETE ***'.format(product, anomaly_str))
        tools.write_log(log_file, '')
        metrics_df.reset_index(drop=True, inplace=True)
    return metrics_df
