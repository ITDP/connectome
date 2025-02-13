

'''
notes

folder structure (during/after a sucessful run)
xxxxxx/
    codefiles.py # python files to be hidden in an installed library in future
    temp/ #should be automatically deleted in most cases
    scenario_comparison_results/
        summary_nongeospatial.csv
        detailed_nongeospatial.csv
        summary_geospatial.gpkg   
        detailed_geospatial.gpkg # consider dividing into multiple files
    existing_conditions/ #rename? base? no_build? 
        input_data/
            analysis_geometry.gpkg
            subdemo_categories.csv
            subdemo_statistics.csv
            routing/
                study_area_LTS_editable.osm
                study_area_LTS.osm
                operator1_gtfs.zip
                operator2_gtfs.zip
                ** r5py files **
        travel_matrices/
            travel_time_matrices/
            full_impedance_matrices/
                subdemo_001_impedance.csv
                subdemo_001_mode.csv
                subdemo_002_impedance.csv
                subdemo_002_mode.csv
                subdemo_003_impedance.csv
                subdemo_003_mode.csv
                ...
        results/
            summary_nongeospatial.csv
            detailed_nongeospatial.csv
            summary_geospatial.gpkg   
            detailed_geospatial.gpkg # consider dividing into multiple files
    scenario1/
        [same as existing_conditions]
        
        
TODO next time i work on cxome
- check / debug my edits to setup_pop_usa
- fix up routing per new folder structure
- fix up routing to deliver many ttms, one per subgroup
- build impedance_matrices.py
- build evaluation.py
- build summarize_results.py
        
'''