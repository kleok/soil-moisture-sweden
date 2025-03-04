"""
Author: Nina del Rosario, nina.del@gmail.com
Date: 7/23/2020
Script for downloading ERA5 data for the region and timeframe of interest through the CDS API service:
https://confluence.ecmwf.int/display/CKB/How+to+download+ERA5
This script downloads data at 0.1 degree resolution
"""

import cdsapi

def main():
    c = cdsapi.Client()
    c.retrieve(
        'reanalysis-era5-land',
        {
            'format': 'netcdf',
            'variable': 'volumetric_soil_water_layer_1',
            'year': [
                '2015', '2016', '2017',
                '2018',
            ],
            'month': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
            ],
            'day': [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
                '13', '14', '15',
                '16', '17', '18',
                '19', '20', '21',
                '22', '23', '24',
                '25', '26', '27',
                '28', '29', '30',
                '31',
            ],
            'time': [
                '00:00', '01:00', '02:00',
                '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00',
                '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00',
                '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00',
                '21:00', '22:00', '23:00',
            ],
            'grid': [0.1, 0.1],
            'area': [
                70.87, 4.87, 54.87,
                31.37,
            ],
        },
        '0-1_ERA5-Land_hourly.nc')


if __name__ == '__main__':
    main()
