"""
Author: Nina del Rosario
Date: 7/19/2020
Script for merging SMAP L3 data using xarray
UPDATE_DESCRIPTION
"""
import os
import xarray as xr
import sm_tools as tools

product = "SMAP L3"
output_dir = r"..\test_output_data"
in_dir = r"D:\sm_backup\native\SPL3SMP_smap-L3_36km_clipped_geographic_nc"

export_ds = False

# first file for creating lat and lon dimensions
first_file = r"D:\sm_backup\native\SPL3SMP_smap-L3_36km_clipped_geographic_nc\SMAP_L3_SM_P_20150401_R16510_001_HEGOUT.nc"
first_ds = xr.open_dataset(first_file, group='Soil_Moisture_Retrieval_Data_AM')
lon = first_ds['longitude'][0, :].values
lat = first_ds['latitude'][:, 0].values
local_time_utc = 5

ds_list = []

for filename in os.listdir(in_dir):
    file = os.path.join(in_dir, filename)
    datestamp = tools.get_filename_timestamp(file, r"P_[0-9]{8}_R")
    datestamp = datestamp.replace(hour=local_time_utc)
    print(file)
    ds = xr.open_dataset(file, group='Soil_Moisture_Retrieval_Data_AM')
    soil_moisture = ds['soil_moisture'].values
    soil_moisture_da = xr.DataArray(soil_moisture, coords=[lat, lon], dims=["lat", "lon"], name="soil_moisture")
    surface_flag = ds['surface_flag'].values
    surface_flag_da = xr.DataArray(surface_flag, coords=[lat, lon], dims=["lat", "lon"], name="surface_flag")
    retrieval_qual_flag = ds['retrieval_qual_flag'].values
    retrieval_qual_flag_da = xr.DataArray(retrieval_qual_flag, coords=[lat, lon], dims=["lat", "lon"],
                                          name="retrieval_qual_flag")
    out_ds = xr.merge([soil_moisture_da, surface_flag_da, retrieval_qual_flag_da])
    out_ds["time"] = datestamp
    out_ds = out_ds.expand_dims('time').set_coords('time')
    ds_list.append(out_ds)

concat_ds = xr.concat(ds_list, dim="time")
print(concat_ds)
print(concat_ds.lat)
print(concat_ds.lon)
print(concat_ds.time)
concat_ds.to_netcdf(os.path.join(output_dir, "smap-L3-36km-subset-nofilter.nc"))