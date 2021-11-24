#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import numpy as np
from tqdm import tqdm
import os

scenarios = ['sc_existing_conditions','sc_new_bridge']

#these function definitions shouldn't change between experiment runs,
#or even between cities

def load_wide_ttm(directory, mode):
    wide_ttm = pd.read_csv(f'{directory}/travel_times/{mode}_wide.csv', index_col='fromId')
    del wide_ttm["Unnamed: 0"]
    wide_ttm.columns = pd.to_numeric(wide_ttm.columns)
    return wide_ttm

#TODO: consider replacing with a logsum model for mode choice?
def get_mode_abilities(from_point):
    from_pop = from_point[1]['POP10']
    mode_abilities = []
    #this is a weird data structure -- a list of lists. 
    #The first element of each list is the number of people in that category,
    #the remaining elements are the modes they can use. 
    #at some point this will have to be refined to deal with incomes that impact variable cost impedance
    #the idea is that everyone in each category will pick the same mode, for the same reasons
    #??how??
    people_with_cars = (from_pop * pop_points.loc[from_point[0], 'pct_twopluscars']) + (0.75 * from_pop * pop_points.loc[from_point[0], 'pct_onecar'])
    people_without_cars = (from_pop * pop_points.loc[from_point[0], 'pct_carfree']) + (0.25 * from_pop * pop_points.loc[from_point[0], 'pct_onecar'])
    mode_abilities.append([people_with_cars, 'car','walk','transit'])
    mode_abilities.append([people_without_cars, 'walk','transit'])
    return mode_abilities

#TODO: replace with a better gravity function after literature review
def value_of_cxn(from_pop, to_pop, traveltime_min):
    if traveltime_min == 0: #TODO: come up with a size-dependent way of handling this
        return 0
    return (from_pop*to_pop)/((traveltime_min/30)**2)

def sum_scenario_value(pop_points, scenario_ttms):
    modes = scenario_ttms.keys()
    out_df = pop_points.copy()
    total_value = 0
    for from_point in tqdm(pop_points.iterrows(), total=len(pop_points)):
        from_pop = from_point[1]['POP10']
        additional_value = 0
        for mode in modes:
            out_df.loc[from_point[0],f'val_from_{mode}'] = 0
        if from_pop > 0:
            for to_point in pop_points.iterrows():
                to_pop = to_point[1]['POP10']
                if to_pop > 0:
                    mode_times = {}
                    for mode in modes:
                        try:
                            mode_times[mode] = scenario_ttms[mode].loc[from_point[0], to_point[0]]
                            if mode == 'car' and mode_times['car'] != 0:
                                mode_times[mode] += 1 #ASSUMPTION: +1 for parking
                        except KeyError:
                            mode_times[mode] = 1000000000
                        if np.isnan(mode_times[mode]):
                            mode_times[mode] = 1000000000
                        
                    #total hack for now! Some points in providence has population but not car data.
                    #this should go into prep_pop
                    if np.isnan(pop_points.loc[from_point[0], 'pct_twopluscars']):
                        pop_points.loc[from_point[0], 'pct_twopluscars'] = .9
                        pop_points.loc[from_point[0], 'pct_onecar'] = .05
                        pop_points.loc[from_point[0], 'pct_carfree'] = .05
                    
                    mode_abilities = get_mode_abilities(from_point)
                    
                    for ability_category in mode_abilities:
                        mode_choice = min(ability_category[1:], key = lambda k: mode_times[k])
                        time = mode_times[mode_choice]
                        cxn_val = value_of_cxn(ability_category[0],to_pop,time)
                        out_df.loc[from_point[0],f'val_from_{mode_choice}'] += cxn_val
                        additional_value += cxn_val
                        
                    out_df.loc[from_point[0],f'value_from_all'] = additional_value 
                    out_df.loc[from_point[0],f'value_per_person'] = additional_value / from_pop
                    for mode in modes:
                        out_df.loc[from_point[0],f'prop_from_{mode}'] = out_df.loc[from_point[0],f'val_from_{mode}'] / additional_value 
                    
                    if np.isnan(additional_value):
                        import pdb; pdb.set_trace()
                    total_value += additional_value
                    
    return total_value, out_df


# for now, assume no change in pop distribution between scenarios
#TODO: fix this -- population distribution should be an attribute of a scenario
print('loading pop data')
pop_points = pd.read_csv('pop_points.csv')
pop_points.index = pop_points.id.astype(int)
pop_points.index.rename('id_number',inplace=True)

grid_pop = gpd.read_file('grid_pop.geojson')

#load specific inputs for all scenarios
scenario_ttms = {}
out_gdfs = {}
out = {}

for scenario in scenarios:
    print(f'loading data for {scenario}')
    scenario_ttms[scenario] = {}
    for mode in ['car','walk','transit']:
        mode_wide = load_wide_ttm(scenario, mode)
        scenario_ttms[scenario][mode] = mode_wide
    print(f'calculating value for for {scenario}')
    total_val, out_df = sum_scenario_value(pop_points, scenario_ttms[scenario])
    out[scenario] = total_val
    scenario_gdf = grid_pop.merge(out_df, how='left', on='id')
    out_gdfs[scenario] = scenario_gdf
    if not scenario == 'sc_existing_conditions':
        for from_idx in scenario_gdf.index:
            val_change = scenario_gdf.loc[from_idx, 'value_from_all'] - out_gdfs['sc_existing_conditions'].loc[from_idx, 'value_from_all'] 
            scenario_gdf.loc[from_idx, 'value_change'] = val_change
            scenario_gdf.loc[from_idx, 'rel_value_change'] = val_change /  out_gdfs['sc_existing_conditions'].loc[from_idx, 'value_from_all'] 
    scenario_gdf.to_file(f'{scenario}_grid.geojson', driver='GeoJSON')
print(out)



