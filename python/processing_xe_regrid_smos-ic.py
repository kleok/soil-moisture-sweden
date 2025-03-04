"""
Author: Nina del Rosario
Date: 6/30/2020
Script for regridding SMOS-IC data
UPDATE_DESCRIPTION

"""
import os
import xarray as xr
import xtools as xt
import sm_config as config
import sm_dictionaries as dicts

product = "SMOS-IC"
sm_field = dicts.dict_product_fields[product]['sm_field']
output_dir = r"../test_output_data"
f = r"/Volumes/TOSHIBA EXT/sm_backup/xr/smos-ic_25km-subset-nofilter.nc"

ds = xr.open_dataset(f)
# filter out invalid data
ds = ds.where((ds['Quality_Flag'] != 2) & (ds[sm_field] >= 0) & (ds[sm_field] < 1))

dr_out = xt.regrid_multidate(ds, sm_field)
dr_out.to_netcdf(os.path.join(output_dir, "smos-ic_0-25-regrid.nc"))