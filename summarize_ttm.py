#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pandas as pd
import geopandas as gpd
import numpy as np
from tqdm import tqdm
import os
import glob

# SETTINGS

#existing conditions or reference scenario should be first

#for the scenarios and modes in this dictionary, 
#override the scenario-specific TTMs with the TTMs from the existing conditions scenario
keep_ec_ttms = {
    'new_highways':'transit',
    'secondary_cycleways':'transit',}


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

def load_wide_ttm(directory, mode):
    wide_ttm = pd.read_csv(f'scenarios/{directory}/travel_times/{mode}_wide.csv', index_col='fromId')
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
    #the idea is that everyone in each category will pick the same mode for a given O-D,
    #for the same reasons
    #??how??
    #also, how to make into a dataframe?
    people_with_cars = (from_pop * pop_points.loc[from_point[0], 'pct_twopluscars']) + (0.75 * from_pop * pop_points.loc[from_point[0], 'pct_onecar'])
    people_without_cars = (from_pop * pop_points.loc[from_point[0], 'pct_carfree']) + (0.25 * from_pop * pop_points.loc[from_point[0], 'pct_onecar'])
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

def sum_scenario_value(pop_points, scenario_ttms, ec_modes = [], ec_ttms = None):
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
                        if mode in ec_modes:
                            mode_times[mode] = ec_ttms[mode].loc[from_point[0], to_point[0]]
                        else:
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
                        
            out_df.loc[from_point[0],'value_from_all'] = int(value_of_from)
            out_df.loc[from_point[0],'value_per_person'] = int(value_of_from / from_pop)
            out_df.loc[from_point[0],'val_from_allbike'] = sum([out_df.loc[from_point[0],f'val_from_bike_lts{n}'] for n in [1,2,4]])
            for mode in list(modes) + ['allbike']:
                out_df.loc[from_point[0],f'prop_from_{mode}'] = out_df.loc[from_point[0],f'val_from_{mode}'] / value_of_from
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
        val_per_cap = round(total_val / gdf['POP10_x'].sum())
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
    

#load specific inputs for all scenarios
scenario_ttms = {}
out_gdfs = {}
out = {}


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
        mode_wide = load_wide_ttm(scenario, mode)
        scenario_ttms[scenario][mode] = mode_wide
    print(f'calculating value for for {scenario}')
    if scenario == scenarios[0]:
        #is existing conditions / BAU
        total_val, out_df = sum_scenario_value(pop_points, scenario_ttms[scenario])
    else: 
        if scenario in keep_ec_ttms.keys():
            ec_ttms = keep_ec_ttms[scenario]
        else:
            ec_ttms = []
        total_val, out_df = sum_scenario_value(pop_points, 
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
    scenario_gdf.to_file(f'results/{scenario}_grid.geojson', driver='GeoJSON')
    out_gdfs[scenario] = scenario_gdf
summarize_output(out_gdfs).to_csv('results/summary.csv')
print(out)