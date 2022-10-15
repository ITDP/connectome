import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
import shapely
from shapely.geometry import Polygon
import rasterstats
#import utm

def build_grid(city_crs, bounds_poly_utm, low_resolution, exception_gdf_utm=None, high_resolution=None):
    xmin,ymin,xmax,ymax =  bounds_poly_utm.bounds
    # thank you Faraz (https://gis.stackexchange.com/questions/269243/creating-polygon-grid-using-geopandas)
    rows = int(np.ceil((ymax-ymin) /  low_resolution))
    cols = int(np.ceil((xmax-xmin) / low_resolution))
    XleftOrigin = xmin
    XrightOrigin = xmin + low_resolution
    YtopOrigin = ymax
    YbottomOrigin = ymax - low_resolution
    lowres_cells = []
    exception_cells = []
    for i in range(cols):
        Ytop = YtopOrigin
        Ybottom = YbottomOrigin
        for j in range(rows):
            cell = Polygon([(XleftOrigin, Ytop), (XrightOrigin, Ytop), (XrightOrigin, Ybottom), (XleftOrigin, Ybottom)])
            cell = cell.intersection(bounds_poly_utm)
            if exception_gdf_utm is not None:
                if not cell.intersects(exception_gdf_utm.unary_union):
                    lowres_cells.append(cell)
                else:
                    exception_cells.append(cell)
            else:
                lowres_cells.append(cell)
            Ytop = Ytop - low_resolution
            Ybottom = Ybottom - low_resolution
        XleftOrigin = XleftOrigin + low_resolution
        XrightOrigin = XrightOrigin + low_resolution
    highres_cells = []
    if exception_gdf_utm is not None:
        for exception_cell in exception_cells:
            highres_cells += build_grid(exception_cell, high_resolution)
    grid = gpd.GeoDataFrame(geometry=lowres_cells + highres_cells, crs=city_crs)
    grid = grid[grid.area > 0]
    grid.reset_index(inplace=True)
    grid.drop('index', axis=1, inplace=True)
    return grid


def populate_grid(grid, 
                  ghsl_fileloc,
                  ghsl_crs,
                  save_loc = ('pop_points.csv','grid_pop.geojson'), #.csv, .geojson
                  car_distribution = { #default values are estimates for Nairobi
                      'pct_carfree' : 0.8,
                      'pct_onecar': 0.15,
                      'pct_twopluscars': 0.05,
                      },
                  ):
    grid['area_m2'] = grid.geometry.area
    grid_gdf_proj= grid.to_crs(ghsl_crs)
    pop_densities = rasterstats.zonal_stats(grid_gdf_proj, 
                                            ghsl_fileloc, 
                                            stats=['mean'])
    for idx in grid_gdf_proj.index:
        if pop_densities[idx]['mean'] == None:
            mean_dens = 0
        else:
            mean_dens = pop_densities[idx]['mean']
        mean_dens_per_m2 = (mean_dens / 0.0625) / 1000000
        grid_gdf_proj.loc[idx,'pop_dens'] = mean_dens_per_m2
        grid_gdf_proj.loc[idx,'population'] = mean_dens_per_m2 * grid_gdf_proj.loc[idx,'area_m2']
    points = pd.DataFrame()
    for idx in grid_gdf_proj.index:
        grid_gdf_proj.loc[idx,'id'] = idx
        for var in car_distribution:
            points.loc[idx, var] = car_distribution[var]
            grid_gdf_proj.loc[idx, var] = car_distribution[var]

        points.loc[idx,'id'] = idx
        points.loc[idx,'population'] = grid_gdf_proj.loc[idx,'population']
        centroid = grid_gdf_proj.loc[idx,'geometry'].centroid
        points.loc[idx,'lat'] = centroid.y
        points.loc[idx,'lon'] = centroid.x
    #TODO: remove cells with 0 population (eg water)
    grid_gdf_latlon = grid_gdf_proj.to_crs(4326)
    return points, grid_gdf_latlon


#for some reason, the total pop of the grid may be different from the total pop of the area
#I must have made some mistake above
#but for now, this will even things out
#TODO figure out what causes this discrepancy
def adjust_population(grid_gdf_latlon, ghsl_crs, ghsl_fileloc):
    grid_gdf_proj = grid_gdf_latlon.to_crs(ghsl_crs)
    pop_sum = rasterstats.zonal_stats([grid_gdf_proj.unary_union], 
                                            ghsl_fileloc, 
                                            stats='sum')
    total_pop=pop_sum[0]['sum']
    df_sum = grid_gdf_latlon.population.sum()
    ratio = total_pop / df_sum
    grid_gdf_latlon.population = grid_gdf_latlon.population * ratio
    return grid_gdf_latlon    
    
#TODO: save only grid_pop, not poo_points, now that we're using r5py
def setup_grid(bounds_poly_latlon, 
               low_resolution, 
               ghsl_fileloc,
               ghsl_crs,
               adjust_pop = True, #False if you don't want to adjust the populations
               save_loc = ['pop_points.csv','grid_pop.geojson'], #.csv, .geojson or None
               car_distribution = { #default values are estimates for Brazil
                   'pct_carfree' : 0.8,
                   'pct_onecar': 0.2,
                   'pct_twopluscars': 0,
                   },
               ):
    bounds_gdf_latlon = gpd.GeoDataFrame(geometry=[bounds_poly_latlon],crs=4326)
    bounds_gdf_utm = ox.project_gdf(bounds_gdf_latlon)
    city_crs = bounds_gdf_utm.crs
    grid = build_grid(city_crs, bounds_gdf_utm.unary_union, low_resolution)
    points, grid_gdf_latlon = populate_grid(grid, ghsl_fileloc, ghsl_crs)
    if adjust_pop:
        #points = adjust_population(grid_gdf_latlon, total_pop)
        grid_gdf_latlon = adjust_population(grid_gdf_latlon, ghsl_crs, ghsl_fileloc)
    if save_loc is not None:
        points.to_csv(save_loc[0])
        grid_gdf_latlon.to_file(save_loc[1],driver='GeoJSON')


#TODO remove? If I'm just going to be calling from setup.py anyway.
def grid_from_bbox(
        bbox, #lat-lon, [xmin,ymin,xmax,ymax]
        ghsl_fileloc,
        resolution = 1000,
        out_file_dir = 'scenarios/existing_conditions/',
        car_distribution = { #default values are estimates for Brazil
            'pct_carfree' : 0.8,
            'pct_onecar': 0.2,
            'pct_twopluscars': 0,
            },
        ):
    bounds_ll = shapely.geometry.box(*bbox)
    df = gpd.GeoDataFrame(geometry=[bounds_ll], crs=4326)
    df_utm = ox.project_gdf(df)
    save_loc = [f'{out_file_dir}pop_points.csv',f'{out_file_dir}grid_pop.geojson']
    setup_grid(df_utm.crs,
               df_utm.geometry.unary_union,
               resolution,
               ghsl_fileloc,
               adjust_pop = True,
               save_loc = save_loc,
               car_distribution = car_distribution,
               )


