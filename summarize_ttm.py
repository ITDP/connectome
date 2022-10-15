#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
from tqdm import tqdm
import os
import glob

# SETTINGS

#existing conditions or reference scenario should be first



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


def load_wide_ttm(file):
    wide_ttm = pd.read_csv(file, index_col='fromId')
    del wide_ttm["Unnamed: 0"]
    wide_ttm.columns = pd.to_numeric(wide_ttm.columns)
    return wide_ttm

#TODO: consider replacing with a logsum model for mode choice?
def get_mode_abilities(from_point):
    from_pop = from_point['population']
    mode_abilities = []
    #this is a weird data structure -- a list of lists. 
    #The first element of each list is the number of people in that category,
    #the remaining elements are the modes they can use. 
    #at some point this will have to be refined to deal with incomes that impact variable cost impedance
    #the idea is that everyone in each category will pick the same mode for a given O-D,
    #for the same reasons
    #??how??
    #also, how to make into a dataframe?
    #cars: assume that in a household with only 1 car, only 75% of trips can be made by car
    # may be an overestimation?
    people_with_cars = (from_pop * from_point['pct_twopluscars']) + (0.75 * from_pop * from_point['pct_onecar'])
    people_without_cars = (from_pop * from_point['pct_carfree']) + (0.25 * from_pop * from_point['pct_onecar'])
    #TODO make thi reference the point, not an absolute variable
    for cyclist_category in cyclist_distribution:
        mode_abilities.append([people_with_cars * cyclist_category[0], *['car','walk','transit']+cyclist_category[1]])
    for cyclist_category in cyclist_distribution:
        mode_abilities.append([people_without_cars * cyclist_category[0], *['walk','transit']+cyclist_category[1]])
    return mode_abilities


def value_of_cxn(from_pop, to_pop, t_min):
    #see SSTI's Measuring Accessibility, appendix (p.68)
    #rough average of work and non-work
    baseval = from_pop * to_pop
    return baseval * 1.14 * np.e ** (-0.05 * t_min)
    #return (from_pop*to_pop)/((traveltime_min/30)**2)

def evaluation(grid_pop, scenario_ttms, cumulative_time_lims = [], ec_modes = [], ec_ttms = None):
    modes = scenario_ttms.keys()
    out_df = grid_pop.copy()
    total_value = 0
    for from_id in tqdm(grid_pop.index, total=len(grid_pop)):
        from_pop = grid_pop.loc[from_id,'population']
        for mode in modes:
            out_df.loc[from_id,f'val_from_{mode}'] = 0
        cumulative_reach = {}
        for time_lim in cumulative_time_lims:
            cumulative_reach[time_lim] = {}
            for mode in modes:
                out_df.loc[from_id, f'cumsum_{mode}_{time_lim}'] = 0
                cumulative_reach[time_lim][mode] = []
        if from_pop > 0:
            value_of_from = 0
            for to_id in grid_pop.index:
                to_pop = grid_pop.loc[to_id,'population']
                #TODO: Include access to same area
                if to_pop > 0:
                    mode_times = {}
                    for mode in modes:
                        if False: #mode in ec_modes: Removing this for now.
                            pass
                            # try:
                            #     mode_times[mode] = ec_ttms[mode].loc[from_id, to_id]
                            # except KeyError:
                            #     mode_times[mode] = 1000000000
                        else:
                            try:
                                mode_times[mode] = scenario_ttms[mode].loc[from_id, to_id]
                            except KeyError:
                                mode_times[mode] = 1000000000
                        if mode_times[mode] == 0:
                            mode_times[mode] += 1
                        if mode == 'car':
                            mode_times[mode] += 3 #ASSUMPTION: +3min for parking
                        if mode == 'transit':
                            mode_times[mode] += 3 #ASSUMPTION: +3min for fare price
                        if np.isnan(mode_times[mode]):
                            mode_times[mode] = 1000000000
                            
                    for mode in modes:
                        for time_lim in cumulative_time_lims:
                            if mode_times[mode] <= time_lim:
                                out_df.loc[from_id, f'cumsum_{mode}_{time_lim}'] += to_pop
                                cumulative_reach[time_lim][mode].append(to_id) 
                        
                    mode_abilities = get_mode_abilities(grid_pop.loc[from_id])
                    
                    for ability_category in mode_abilities:
                        mode_choice = min(set(ability_category[1:]) & set(modes), key = lambda k: mode_times[k])
                        time = mode_times[mode_choice]
                        cxn_val = value_of_cxn(ability_category[0],to_pop,time)
                        out_df.loc[from_id,f'val_from_{mode_choice}'] += cxn_val
                        value_of_from += cxn_val
                            
                    if np.inf == value_of_from:
                        import pdb; pdb.set_trace()
            
            #
            
            for time_lim in cumulative_time_lims:
                for mode in modes:
                    reach = grid_pop.loc[cumulative_reach[time_lim][mode]].geometry.unary_union
                    out_df.loc[from_id, f"reach_{mode}_{time_lim}"] = reach.wkt
            
            out_df.loc[from_id,'value_from_all'] = int(value_of_from)
            out_df.loc[from_id,'value_per_person'] = int(value_of_from / from_pop)
            if 'bike_lts1' in modes:
                out_df.loc[from_id,'val_from_allbike'] = sum([out_df.loc[from_id,f'val_from_bike_lts{n}'] for n in [1,2,4]])
                modes = list(modes)
                modes.append('allbike')
            for mode in list(modes):
                out_df.loc[from_id,f'val_perperson_from_{mode}'] = out_df.loc[from_id,f'val_from_{mode}'] / from_pop
            for mode in list(modes):
                out_df.loc[from_id,f'prop_from_{mode}'] = out_df.loc[from_id,f'val_from_{mode}'] / value_of_from
            if np.isnan(value_of_from):
                import pdb; pdb.set_trace()
            total_value += value_of_from
                    
    return total_value, out_df

def compare_points(out_gdfs, rowid):
    comparison = pd.DataFrame()
    for scenario in out_gdfs.keys():
        comparison[scenario] = out_gdfs[scenario].loc[rowid].drop('geometry')
    return comparison

def check_val_diffs(pop_points, scenario_ttms, scenario1, scenario2, mode):
    out=pd.DataFrame(columns = ["origin","destination",scenario1, scenario2])
    for from_id in pop_points.index:
        for to_id in pop_points.index:
            val1 = scenario_ttms[scenario1][mode].loc[from_id, to_id]
            val2 = scenario_ttms[scenario2][mode].loc[from_id, to_id]
            if val1 != val2:
                if val1 > 1:
                    out.loc[len(out.index)] = [from_id, to_id, val1, val2]
    out['difference'] = out[scenario2] - out[scenario1]
    return out

def summarize_output(out_gdfs):
    summary = pd.DataFrame(index=out_gdfs.keys())
    for scenario in summary.index:
        gdf = out_gdfs[scenario]
        total_val = gdf['value_from_all'].sum()
        summary.loc[scenario, 'total_val'] = total_val
        val_per_cap = round(total_val / gdf['population_x'].sum())
        summary.loc[scenario, 'val_per_cap'] = val_per_cap
        for mode in ['walk','car','transit','allbike','bike_lts1','bike_lts2','bike_lts4']:
            prop_from_mode = round(gdf[f'val_from_{mode}'].sum() / total_val, 6)*100
            summary.loc[scenario, f'perc_from_{mode}'] = prop_from_mode
        if 'existing_conditions' in summary.index:
            perc_change = 100 * round(total_val / summary.loc['existing_conditions', 'total_val'],6)
            summary.loc[scenario, 'perc_change'] = perc_change
            perc_change_percap = 100 * round(val_per_cap / summary.loc['existing_conditions', 'val_per_cap'],6)
            summary.loc[scenario, 'perc_change_per_cap'] = perc_change_percap
            
    return summary



if __name__ == "__main__":
    #load specific inputs for all scenarios
    scenario_ttms = {}
    out_gdfs = {}
    out = {}
    
    #for the scenarios and modes in this dictionary, 
    #override the scenario-specific TTMs with the TTMs from the existing conditions scenario
    keep_ec_ttms = {
         'new_highways':'transit',
         'secondary_cycleways':'transit',}

    
    
    scenarios = os.listdir('scenarios/')
    if 'existing_conditions' in scenarios:
        scenarios.remove('existing_conditions')
        scenarios.insert(0, 'existing_conditions')
    
    for scenario in scenarios:
        print(f'loading data for {scenario}')
        pop_points = pd.read_csv(f'scenarios/{scenario}/pop_points.csv')
        pop_points.index = pop_points.id.astype(int)
        pop_points.index.rename('id_number',inplace=True)
    
        grid_pop = gpd.read_file(f'scenarios/{scenario}/grid_pop.geojson')
        scenario_ttms[scenario] = {}
        for mode in ['car','walk','transit','bike_lts4','bike_lts2','bike_lts1']:
            mode_wide = load_wide_ttm(f'scenarios/{scenario}/travel_times/{mode}_wide.csv')
            scenario_ttms[scenario][mode] = mode_wide
        print(f'calculating value for for {scenario}')
        if scenario == scenarios[0]:
            #is existing conditions / BAU
            total_val, out_df = evaluation(pop_points, scenario_ttms[scenario])
        else: 
            if scenario in keep_ec_ttms.keys():
                ec_ttms = keep_ec_ttms[scenario]
            else:
                ec_ttms = []
            total_val, out_df = evaluation(pop_points, 
                                                    scenario_ttms[scenario],
                                                    ec_ttms,
                                                    scenario_ttms[scenarios[0]])
            
        out[scenario] = total_val
        scenario_gdf = grid_pop.merge(out_df, how='left', on='id')
        for col in scenario_gdf.columns:
            if col[-2:] == '_y':
                scenario_gdf.drop(col, axis=1, inplace=True)
        if not scenario == scenarios[0]:
            for from_idx in scenario_gdf.index:
                val_change = scenario_gdf.loc[from_idx, 'value_from_all'] - out_gdfs[scenarios[0]].loc[from_idx, 'value_from_all'] 
                scenario_gdf.loc[from_idx, 'value_change'] = val_change
                scenario_gdf.loc[from_idx, 'rel_value_change'] = val_change /  out_gdfs[scenarios[0]].loc[from_idx, 'value_from_all'] 
        scenario_gdf.to_file(f'scenarios/{scenario}/results.geojson', driver='GeoJSON')
        out_gdfs[scenario] = scenario_gdf
    summarize_output(out_gdfs).to_csv('results_summary.csv')
    print(out)