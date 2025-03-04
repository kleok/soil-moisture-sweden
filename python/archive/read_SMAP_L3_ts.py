"""
Author: Nina del Rosario
Date: 6/2/2020
Script for reading SMAP L3 reshuffle TS generated by repurpsoe
"""
import os
import numpy
import json
from smap_io import SMAPTs
from datetime import datetime
import sm_config as config

# dictionary for dataset parameters, for each reader in this dictionary, make sure the class is imported
print_sample = False

ts_reader = SMAPTs(config.dict_product_inputs['SMAP L3']['ts_dir'])

# Degero: 19.556539 64.182029
ts = ts_reader.read(19.556539, 64.182029)

print(ts)
print(ts.columns)

if print_sample:
    ts.to_csv('..\\product_sample_data\\SMAP-L3_sample.csv')