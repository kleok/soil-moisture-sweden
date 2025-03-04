clc,clear,close all
lonlat_ext=load('lonlat_ext.txt');

lon_=ncread(['C:\git\soil-moisture-sweden\sm_sample_files\NordicESACCICombined2014to2019\ClipESACCICombined2015.nc'],'lon');
lat_=ncread(['C:\git\soil-moisture-sweden\sm_sample_files\NordicESACCICombined2014to2019\ClipESACCICombined2015.nc'],'lat');

ID=knnsearch([lon_,lat_],lonlat_ext);
D=(datenum('1-apr-2015'):datenum('31-dec-2018'))';
Psim_CCISM = [];

for ii = 2015:2018
    ii
    PP=ncread(['C:\git\soil-moisture-sweden\sm_sample_files\NordicESACCICombined2014to2019\ClipESACCICombined',num2str(ii),'.nc'],'sm');
    Psim_CCISM=[Psim_CCISM,PP(:,ID)'];
end

% Plotting the figure
plot(D,Psim_CCISM)
grid on, box on
datetick
ylabel('sm [m3/m3]')
title(['CCISM ',num2str(size(lonlat_ext,1)),' points'])