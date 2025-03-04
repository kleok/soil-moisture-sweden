function output_path = etc_kaighin(input_path, output_path)
%     etc_kaighin('C:\git\soil-moisture-sweden\analysis_output\tc_analysis_20210314104637\matched_data', 'C:\git\soil-moisture-sweden\analysis_output\tc_analysis_20210314104637\tc_matlab_results.csv');
%     input_path = 'C:\git\soil-moisture-sweden\analysis_output\tc_analysis_20210314104637\matched_data'
%     result_path = 'C:\git\soil-moisture-sweden\analysis_output\tc_analysis_20210314104637'
    files = dir(strcat(input_path,'\*.csv'))
    file_count = length(files);
    disp(file_count);
    result_matrix = [];

    % get product names from filename
    for i=1:file_count
        fparts = strrep(files(i).name, ".csv", "");         
        fparts = strrep(fparts, "matched_", "");
        uscore = strfind(fparts, "_", 'ForceCellOutput', true);
        loc = extractBetween(fparts, uscore{1}(length(uscore{1}))+1, strlength(fparts));
        anomaly = extractBetween(fparts, uscore{1}(length(uscore{1})-1)+1, uscore{1}(length(uscore{1}))-1);
        triplet = extractBetween(fparts, 1, uscore{1}(length(uscore{1})-1)-1);
        f = strcat(input_path,'\',files(i).name);
        fid = fopen(f);
        varNames = strsplit(fgetl(fid), ',');
        fclose(fid);
        prod1 = varNames{2};
        prod2 = varNames{3};
        prod3 = varNames{4};
        t = readtable(f);

        % get product names from columns

        rho2_1 = NaN;
        rho2_2 = NaN;
        rho2_3 = NaN;

        errvar_1 = NaN;
        errvar_2 = NaN;
        errvar_3 = NaN;

        if height(t) > 1
            % isolate columns in array
            a = t(:,2:4);
            % convert table to matrix
            a = a{:,:};

            % kaighin
            Q_hat = cov(a);

            rho_ETC = [sqrt(Q_hat(1,2)*Q_hat(1,3)/Q_hat(1,1)/Q_hat(2,3)); ...
                    sign(Q_hat(1,3)*Q_hat(2,3))*sqrt(Q_hat(1,2)*Q_hat(2,3)/Q_hat(2,2)/Q_hat(1,3)); ...
                    sign(Q_hat(1,2)*Q_hat(2,3))*sqrt(Q_hat(1,3)*Q_hat(2,3)/Q_hat(3,3)/Q_hat(1,2))];

            rho2_ETC = rho_ETC.^2;

            errVar_ETC = [(Q_hat(1,1) - Q_hat(1,2)*Q_hat(1,3)/Q_hat(2,3)); ...
                    (Q_hat(2,2) - Q_hat(1,2)*Q_hat(2,3)/Q_hat(1,3)); ...
                    (Q_hat(3,3) - Q_hat(1,3)*Q_hat(2,3)/Q_hat(1,2))];

            % get rho squared for each product in triplet
            rho2_1 = rho2_ETC(1);
            rho2_2 = rho2_ETC(2);
            rho2_3 = rho2_ETC(3);

            % get err var for each product in triplet
            errvar_1 = errVar_ETC(1);
            errvar_2 = errVar_ETC(2);
            errvar_3 = errVar_ETC(3);
        end
        
        % location	lat	lon	location_veg_class	prod_name	triplet	anomaly	n	cov_0	cov_1	cov_2	snr	err_std	beta	r
        result_matrix = [result_matrix; loc, prod1, triplet, anomaly, height(t), errvar_1, rho2_1, sqrt(rho2_1)];
%         disp(height(result_matrix))
        result_matrix = [result_matrix; loc, prod2, triplet, anomaly, height(t), errvar_2, rho2_2, sqrt(rho2_2)];
        result_matrix = [result_matrix; loc, prod3, triplet, anomaly, height(t), errvar_3, rho2_3, sqrt(rho2_3)];
        result_table = array2table(result_matrix);
        result_table.Properties.VariableNames(1:8) = ["location", "prod_name", "triplet", "anomaly", "n", "err_std", "rho2", "r"];

%         result_matrix = [result_matrix; loc, triplet, anomaly, prod1, prod2, prod3, rho2_1, rho2_2, rho2_3, errvar_1, errvar_2, errvar_3];
%         result_table = array2table(result_matrix);
%         result_table.Properties.VariableNames(1:12) = ["location", "triplet", "anomaly", "prod1", "prod2", "prod3", "rho2_1", "rho2_2", "rho2_3", "errvar_1", "errvar_2", "errvar_3"];
        disp(height(result_table))
        writetable(result_table, output_path);
end