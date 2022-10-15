
#functions to set up an instance of the connectome measurement tool for a geographic area

import glob
import os
import string
import geopandas as gpd
import shapely
import shapely.geometry
import osmnx as ox
import geojson
import json
import wget
import requests
import zipfile
import shutil
import subprocess
import sys
from tqdm import tqdm

import prep_bike_osm
import prep_pop_ghsl

def bar_progress(current, total, width=80):
  progress_message = "Downloading: %d%% [%d / %d] bytes" % (current / total * 100, current, total)
  # Don't use print() as it will print in new line every time.
  sys.stdout.write("\r" + progress_message)
  sys.stdout.flush()

def setup_from_poly(poly, 
                    base_data_dir = 'base_data/', 
                    buffer = 0, #meters
                    prep_osm=True,
                    ghsl_fileloc=None,
                    ghsl_crs=None,
                    ghsl_download_res='low',
                    grid_resolution=1000, #meters
                    car_distribution = { #default values are estimates for Brazil
                        'pct_carfree' : 0.8,
                        'pct_onecar': 0.2,
                        'pct_twopluscars': 0,
                        },
                    ):
    #setup base_data folder
    setup_folders(base_data_dir = base_data_dir)
    
    if buffer > 0:
        bounds_gdf_latlon = gpd.GeoDataFrame(geometry=[poly], crs=4326)
        bounds_gdf_utm = ox.project_gdf(bounds_gdf_latlon)
        bounds_gdf_utm = bounds_gdf_utm.buffer(buffer)
        bounds_gdf_latlon = bounds_gdf_utm.to_crs(4326)
        poly = bounds_gdf_latlon.unary_union
    
    geom_in_geojson = geojson.Feature(geometry=poly, properties={})
    with open(base_data_dir+'boundaries.geojson', 'w') as out:
        out.write(json.dumps(geom_in_geojson))
    #OSM
    files = os.listdir(base_data_dir)
    if prep_osm:
        osmfiles = []
        for file in files:
            if file[-4:] == '.pbf':
                osmfiles.append(file)
        if len(osmfiles) == 0:
            print(f'''
                  ERROR: No .osm.pbf file found.
                  To measure a connectome, we need data from OpenStreetMap
                  that covers the entire geographic analysis area.
                  Download a .osm.pbf file from https://download.geofabrik.de/
                  (preferably the smallest one that covers your area)
                  And put that file in {base_data_dir}.
                  ''')
            raise ValueError
        elif len (osmfiles) > 1:
            print(f'''
                  ERROR: More than one .osm.pbf file found in {base_data_dir}.
                  There should only be one file there from which to 
                  extract the data for the connectome measurement.
                  ''')
            raise ValueError
        #crop OSM
        osmfile = base_data_dir + osmfiles[0]
        command = f"osmium extract {osmfile} -p {base_data_dir}boundaries.geojson -s complete_ways -v -o {base_data_dir}study_area.pbf"
        subprocess.check_call(command.split(' '))
        if os.path.getsize(f'{base_data_dir}study_area.pbf') < 300:
            print(f'''
                  ERROR: The OSM file you provided does not seem to 
                  include your study area.
                  ''')
            raise ValueError
        #add LTS tags for biking
        #TODO -- move to pre-scenario-run?
        prep_bike_osm.add_lts_tags(base_data_dir+"study_area.pbf",
                                   base_data_dir+"study_area_LTS.pbf")
        #make a JOSM-editable .osm file for users to make new scenarios
        command = f"osmconvert {base_data_dir}study_area_LTS.pbf -o={base_data_dir}study_area_LTS_editable.osm"
        subprocess.check_call(command.split(' '))
        shutil.copy(base_data_dir+"study_area_LTS.pbf", 'scenarios/existing_conditions/study_area_LTS.pbf')
    #prep population data
    #TODO add a function to check if the city is in the USA 
    #(or in another country with good census data)
    #and populate existing_conditions with that data instead of GHSL
    if ghsl_fileloc is None:
        if 'GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.tif' in files:
            ghsl_fileloc = base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.tif'
            ghsl_crs = 'ESRI:54009'
        elif 'GHS_POP_E2020_GLOBE_R2022A_54009_100_V1_0.tif' in files:
            ghsl_fileloc = base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_100_V1_0.tif'
            ghsl_crs = 'ESRI:54009'
        else:
            print(f'DOWNLOADING GLOBAL HUMAN SETTLEMENT LAYER: {ghsl_download_res} resolution')
            if ghsl_download_res == 'high':
                wget.download(
                    'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2022A/GHS_POP_E2020_GLOBE_R2022A_54009_100/V1-0/GHS_POP_E2020_GLOBE_R2022A_54009_100_V1_0.zip',
                    base_data_dir+'GHS_POP_P2020_GLOBE_R2022A_54009_100_V1_0.zip',
                    bar=bar_progress)
                with zipfile.ZipFile(base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_100_V1_0.zip') as z:
                    z.extractall(base_data_dir)
                ghsl_fileloc = base_data_dir+'GHS_SMOD_E2020_GLOBE_R2022A_54009_1000_V1_0.tif'
                ghsl_crs = 'ESRI:54009'
                #TODO - test when I'm not on a hotspot
            elif ghsl_download_res == 'low':
                wget.download(
                    'https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2022A/GHS_POP_E2020_GLOBE_R2022A_54009_1000/V1-0/GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.zip',
                    base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.zip',
                    bar=bar_progress)
                with zipfile.ZipFile(base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.zip') as z:
                    z.extractall(base_data_dir)
                ghsl_fileloc = base_data_dir+'GHS_POP_E2020_GLOBE_R2022A_54009_1000_V1_0.tif'
            else:
                raise ValueError
    prep_pop_ghsl.setup_grid(poly,
                     grid_resolution,
                     ghsl_fileloc,
                     ghsl_crs,
                     save_loc = [
                         base_data_dir+'pop_points.csv',
                         base_data_dir+'grid_pop.geojson'],
                     car_distribution = car_distribution,
                     )
    shutil.copy(base_data_dir+'grid_pop.geojson', 'scenarios/existing_conditions/grid_pop.geojson')
    
    GTFS_filenames = get_GTFS_from_mobility_database(poly, base_data_dir)
    print('downloaded GTFS:')
    for filename in GTFS_filenames:
        print(filename)
        shutil.copy(f'{base_data_dir}{filename}', f'scenarios/existing_conditions/{filename}')
        

def setup_from_bbox(minx, miny, maxx, maxy, **kwargs):
    poly = shapely.geometry.box(minx, miny, maxx, maxy)
    return setup_from_poly(poly, **kwargs)
    
def setup_from_name(name, **kwargs):
    gdf = ox.geocode_to_gdf(name)
    return setup_from_poly(gdf.unary_union, **kwargs)
    
def setup_from_osmid():
    pass
    
def setup_folders(base_data_dir = 'base_data/', scenarios_dir = 'scenarios/'):
    if not os.path.isdir(base_data_dir):
        os.mkdir(base_data_dir)
    if not os.path.isdir(scenarios_dir):
        os.mkdir(scenarios_dir)
    if not os.path.isdir(scenarios_dir+'existing_conditions/'):
        os.mkdir(scenarios_dir+'existing_conditions/')
        if not os.path.isdir(scenarios_dir+'existing_conditions/results/'):
            os.mkdir(scenarios_dir+'existing_conditions/results/')
    
def clean_scenarios():
    for scenario in os.listdir('scenarios/'):
        sc_dir = 'scenarios/'+scenario+'/'
        try:
            os.remove(sc_dir+'network.dat')
        except:
            pass
        filelist = glob.glob(sc_dir+'*.mapdb')
        for filepath in filelist:
            try:
                os.remove(filepath)
            except:
                pass
        filelist = glob.glob(sc_dir+'*.mapdb.p')
        for filepath in filelist:
            try:
                os.remove(filepath)
            except:
                pass
        filelist = glob.glob(sc_dir+'travel_times/*')
        for filepath in filelist:
            try:
                os.remove(filepath)
            except:
                pass
            
def get_GTFS_from_mobility_database(poly, base_data_dir):
    files = os.listdir(base_data_dir)
    if not 'sources.csv' in files:
        url = 'https://bit.ly/catalogs-csv'
        r = requests.get(url, allow_redirects=True)  # to get content after redirection
        with open(f'{base_data_dir}sources.csv', 'wb') as f:
            f.write(r.content)
    sources = gpd.read_file(f'{base_data_dir}sources.csv')
    filenames = []
    for idx in tqdm(list(sources.index)):
        if not sources.loc[idx,'location.bounding_box.minimum_longitude'] == '':
            sources.loc[idx,'geometry'] = shapely.geometry.box(
                float(sources.loc[idx,'location.bounding_box.minimum_longitude']),
                float(sources.loc[idx,'location.bounding_box.minimum_latitude']),
                float(sources.loc[idx,'location.bounding_box.maximum_longitude']),
                float(sources.loc[idx,'location.bounding_box.maximum_latitude']),
                )
            if sources.loc[idx,'geometry'].intersects(poly):
                overlap = sources.loc[idx,'geometry'].intersection(poly)
                if overlap.area * 1000 > sources.loc[idx,'geometry'].area:
                    url = sources.loc[idx,'urls.latest']
                    name = sources.loc[idx,'provider']
                    if sources.loc[idx,'name'] != '':
                        name = name+'_'+ sources.loc[idx,'name']
                    name = name.translate(str.maketrans('', '', string.punctuation))
                    name = name.replace(' ','_')
                    if name != '' and url != '':
                        filename=name+'.zip'
                        filenames.append(filename)
                        r = requests.get(url, allow_redirects=True)  # to get content after redirection
                        with open(f'{base_data_dir}{filename}', 'wb') as f:
                            f.write(r.content)
    return filenames

        