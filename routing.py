import os
import datetime

import sys
sys.argv.append(["--max-memory", "80%"])

import pandas as pd
import geopandas as gpd
from r5py import TransportNetwork, TravelTimeMatrixComputer
from r5py import TransitMode, LegMode
import osmnx as ox


#TODO: import from settings file instead of hardcoding
def prepare_mode_settings(**kwargs):
    mode_settings = {}
    general_settings = {
        'departure': datetime.datetime(2022,10,13,8,30),
        'departure_time_window': datetime.timedelta(hours=1),
        'percentiles': [50],
        'max_time':datetime.timedelta(hours=2),
        'max_time_walking':datetime.timedelta(hours=2),
        'max_time_cycling':datetime.timedelta(hours=2),
        'max_time_driving':datetime.timedelta(hours=2),
        'speed_walking':3.6,
        'speed_cycling':12.0,
        'max_public_transport_rides':4,
    }
    general_settings.update(kwargs)
    
    walk_settings = general_settings.copy()
    walk_settings.update({
        'transport_modes':[LegMode.WALK],
        'access_modes':[LegMode.WALK],
        })
    mode_settings['WALK'] = walk_settings
    
    transit_settings = general_settings.copy()
    transit_settings.update({
        'transport_modes':[TransitMode.TRANSIT],
        'access_modes':[LegMode.WALK],
         })
    mode_settings['TRANSIT'] = transit_settings
    
    bike_lts1_settings = general_settings.copy()
    bike_lts1_settings.update({
        'transport_modes':[LegMode.WALK, LegMode.BICYCLE],
        'access_modes':[LegMode.WALK, LegMode.BICYCLE],
        'max_time_walking':datetime.timedelta(minutes=10),
        'speed_walking':1.8,
        'max_bicycle_traffic_stress':1
        })
    mode_settings['BIKE_LTS1'] = bike_lts1_settings
    
    bike_lts2_settings = general_settings.copy()
    bike_lts2_settings.update({
         'transport_modes':[LegMode.WALK, LegMode.BICYCLE],
         'access_modes':[LegMode.WALK, LegMode.BICYCLE],
         'max_time_walking':datetime.timedelta(minutes=10),
         'speed_walking':1.8,
         'max_bicycle_traffic_stress':2
         })
    mode_settings['BIKE_LTS2'] = bike_lts2_settings
    
    bike_lts4_settings = general_settings.copy()
    bike_lts4_settings.update({
        'transport_modes':[LegMode.WALK, LegMode.BICYCLE],
        'access_modes':[LegMode.WALK, LegMode.BICYCLE],
        'max_time_walking':datetime.timedelta(minutes=10),
        'speed_walking':1.8,
        'max_bicycle_traffic_stress':4
        })
    mode_settings['BIKE_LTS4'] = bike_lts4_settings
    
    car_settings = general_settings.copy()
    car_settings.update({
        'transport_modes':[LegMode.CAR],
        'access_modes':[LegMode.CAR],
        })
    mode_settings['CAR'] = car_settings
    
    return mode_settings



def route_scenario(folder_name, mode_settings=prepare_mode_settings()):
    files = os.listdir(folder_name)
    gtfs_files = []
    osm_files = []
    for filename in files:
        if filename[-4:] == '.pbf':
            osm_files.append(folder_name+filename)
        if filename[-4:] == '.zip':
            gtfs_files.append(folder_name+filename)
    if len(osm_files) < 1:
        print(f'osm .pbf file not found in {folder_name}')
        raise ValueError
    if len(osm_files) > 1:
        print(f'more than one osm .pbf file found in {folder_name}')
        raise ValueError
    if len(gtfs_files) < 1:
        print('WARNING: no GTFS files found')
    pop_grid = gpd.read_file(folder_name+'grid_pop.geojson')
    grid_utm = ox.project_gdf(pop_grid)
    pop_points_utm = gpd.GeoDataFrame(
        {'id':pop_grid.id,
         'population':pop_grid.population},
        geometry = grid_utm.centroid,
        crs=grid_utm.crs)
    pop_points = pop_points_utm.to_crs(4326)
    print('building network')
    scenario_transport_network = TransportNetwork(
        osm_files[0],
        gtfs_files
        )
    for mode in mode_settings.keys():
        print(f'computing for {mode}')
        ttm_computer = TravelTimeMatrixComputer(
            scenario_transport_network, 
            pop_points,
            **mode_settings[mode]
            )
        ttm_long = ttm_computer.compute_travel_times()
        ttm = pd.pivot(ttm_long, index='from_id', columns='to_id', values='travel_time')
        ttm.to_csv(f'{folder_name}/results/{mode}_ttm.csv')
    

            
            
            