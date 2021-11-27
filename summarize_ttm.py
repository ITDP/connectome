#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import numpy as np
from tqdm import tqdm
import os

# SETTINGS

#existing conditions or reference scenario should be first
scenarios = ['sc_pvd_existing_conditions','sc_pvd_bikeaxes', 'sc_pvd_notransit']

# see http://www1.coe.neu.edu/~pfurth/Other%20papers/Dill%202013%204%20types%20of%20cyclists%20TRR.pdf
# this could be replaced by something more nuanced in the prep_pop_points.py script
cyclist_distribution = [
    (0.04, ['bike_lts4']),
    (0.09, ['bike_lts2']),
    (0.56, ['bike_lts1']),
    (0.31, []),
]
assert sum([category[0] for category in cyclist_distribution]) == 1

#END SETTINGS

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
    for cyclist_category in cyclist_distribution:
        mode_abilities.append([people_with_cars * cyclist_category[0], *['car','walk','transit']+cyclist_category[1]])
    for cyclist_category in cyclist_distribution:
        mode_abilities.append([people_without_cars * cyclist_category[0], *['walk','transit']+cyclist_category[1]])
    return mode_abilities

#TODO: replace with a better gravity function after literature review
def value_of_cxn(from_pop, to_pop, traveltime_min):
    return (from_pop*to_pop)/((traveltime_min/30)**2)

def sum_scenario_value(pop_points, scenario_ttms):
    modes = scenario_ttms.keys()
    out_df = pop_points.copy()
    total_value = 0
    for from_point in tqdm(pop_points.iterrows(), total=len(pop_points)):
        from_pop = from_point[1]['POP10']
        for mode in modes:
            out_df.loc[from_point[0],f'val_from_{mode}'] = 0
        if from_pop > 0:
            value_of_from = 0
            for to_point in pop_points.iterrows():
                to_pop = to_point[1]['POP10']
                if to_pop > 0 and not (from_point[0] == to_point[0]):
                    mode_times = {}
                    for mode in modes:
                        mode_times[mode] = scenario_ttms[mode].loc[from_point[0], to_point[0]]
                        if mode_times[mode] == 0:
                            mode_times[mode] += 1
                        if mode == 'car':
                            mode_times[mode] += 1 #ASSUMPTION: +1 for parking
                        if mode == 'transit':
                            mode_times[mode] += 1 #ASSUMPTION: +1 for waiting
                        if np.isnan(mode_times[mode]):
                            mode_times[mode] = 1000000000
                        
                    mode_abilities = get_mode_abilities(from_point)
                    
                    for ability_category in mode_abilities:
                        mode_choice = min(ability_category[1:], key = lambda k: mode_times[k])
                        time = mode_times[mode_choice]
                        cxn_val = value_of_cxn(ability_category[0],to_pop,time)
                        out_df.loc[from_point[0],f'val_from_{mode_choice}'] += cxn_val
                        value_of_from += cxn_val
                    if np.inf == value_of_from:
                        import pdb; pdb.set_trace()
                        
            out_df.loc[from_point[0],'value_from_all'] = value_of_from 
            out_df.loc[from_point[0],'value_per_person'] = value_of_from / from_pop
            for mode in modes:
                out_df.loc[from_point[0],f'prop_from_{mode}'] = out_df.loc[from_point[0],f'val_from_{mode}'] / value_of_from 
            
            if np.isnan(value_of_from):
                import pdb; pdb.set_trace()
            total_value += value_of_from
                    
    return total_value, out_df



#load specific inputs for all scenarios
scenario_ttms = {}
out_gdfs = {}
out = {}

for scenario in scenarios:
    print(f'loading data for {scenario}')
    pop_points = pd.read_csv(f'{scenario}/pop_points.csv')
    pop_points.index = pop_points.id.astype(int)
    pop_points.index.rename('id_number',inplace=True)

    grid_pop = gpd.read_file(f'{scenario}/grid_pop.geojson')
    scenario_ttms[scenario] = {}
    for mode in ['car','walk','transit','bike_lts4','bike_lts2','bike_lts1']:
        mode_wide = load_wide_ttm(scenario, mode)
        scenario_ttms[scenario][mode] = mode_wide
    print(f'calculating value for for {scenario}')
    total_val, out_df = sum_scenario_value(pop_points, scenario_ttms[scenario])
    out[scenario] = total_val
    scenario_gdf = grid_pop.merge(out_df, how='left', on='id')
    if not scenario == scenarios[0]:
        for from_idx in scenario_gdf.index:
            val_change = scenario_gdf.loc[from_idx, 'value_from_all'] - out_gdfs[scenarios[0]].loc[from_idx, 'value_from_all'] 
            scenario_gdf.loc[from_idx, 'value_change'] = val_change
            scenario_gdf.loc[from_idx, 'rel_value_change'] = val_change /  out_gdfs[scenarios[0]].loc[from_idx, 'value_from_all'] 
    scenario_gdf.to_file(f'{scenario}_grid.geojson', driver='GeoJSON')
    out_gdfs[scenario] = scenario_gdf
print(out)


def compare_points(out_gdfs, rowid):
    comparison = pd.DataFrame()
    for scenario in out_gdfs.keys():
        comparison[scenario] = out_gdfs[scenario].loc[rowid]
    return comparison

def check_car(pop_points, scenario_ttms):
    for from_id in pop_points.index:
        for to_id in pop_points.index:
            if scenario_ttms['sc_pvd_notransit']['transit'].loc[from_id, to_id] < (scenario_ttms['sc_pvd_existing_conditions']['transit'].loc[from_id, to_id]-1):
                print(from_id, to_id)