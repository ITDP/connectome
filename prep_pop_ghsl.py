import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
import shapely
from shapely.geometry import Polygon
import rasterstats
#import utm

#eventually need to build _ghls and _usa together
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
                  save_loc = ('pop_points.csv','grid_pop.geojson'), #.csv, .geojson
                  car_distribution = { #default values are estimates for Nairobi
                      'pct_carfree' : 0.8,
                      'pct_onecar': 0.15,
                      'pct_twopluscars': 0.05,
                      },
                  ):
    grid['area_m2'] = grid.geometry.area
    grid_gdf_latlon = grid.to_crs(4326)
    pop_densities = rasterstats.zonal_stats(grid_gdf_latlon, 
                                            ghsl_fileloc, 
                                            stats=['mean'])
    for idx in grid_gdf_latlon.index:
        if pop_densities[idx]['mean'] == None:
            mean_dens = 0
        else:
            mean_dens = pop_densities[idx]['mean']
        mean_dens_per_m2 = (mean_dens / 0.0625) / 1000000
        grid_gdf_latlon.loc[idx,'pop_dens'] = mean_dens_per_m2
        grid_gdf_latlon.loc[idx,'population'] = mean_dens_per_m2 * grid_gdf_latlon.loc[idx,'area_m2']
    points = pd.DataFrame()
    for idx in grid_gdf_latlon.index:
        grid_gdf_latlon.loc[idx,'id'] = idx
        for var in car_distribution:
            points.loc[idx, var] = car_distribution[var]
            grid_gdf_latlon.loc[idx, var] = car_distribution[var]

        points.loc[idx,'id'] = idx
        #points.loc[idx,'population'] = grid_gdf_latlon.loc[idx,'population']
        centroid = grid_gdf_latlon.loc[idx,'geometry'].centroid
        points.loc[idx,'lat'] = centroid.y
        points.loc[idx,'lon'] = centroid.x
    
    return points, grid_gdf_latlon


#for some reason, the total pop of the grid may be different from the total pop of the area
#I must have made some mistake above
#but for now, this will even things out
def adjust_population(grid_gdf_latlon, ghsl_fileloc):
    pop_sum = rasterstats.zonal_stats([grid_gdf_latlon.unary_union], 
                                            ghsl_fileloc, 
                                            stats='sum')
    total_pop=pop_sum[0]['sum']
    df_sum = grid_gdf_latlon.population.sum()
    ratio = total_pop / df_sum
    grid_gdf_latlon.population = grid_gdf_latlon.population * ratio
    return grid_gdf_latlon    
    

def setup_grid(city_crs, 
               bounds_poly_utm, 
               low_resolution, 
               ghsl_fileloc,
               adjust_pop = True, #False if you don't want to adjust the populations
               save_loc = ('pop_points.csv','grid_pop.geojson'), #.csv, .geojson or None
               car_distribution = { #default values are estimates for Nairobi
                   'pct_carfree' : 0.8,
                   'pct_onecar': 0.15,
                   'pct_twopluscars': 0.05,
                   },
               ):
    grid = build_grid(city_crs, bounds_poly_utm, low_resolution)
    points, grid_gdf_latlon = populate_grid(grid, ghsl_fileloc)
    if adjust_pop:
        #points = adjust_population(grid_gdf_latlon, total_pop)
        grid_gdf_latlon = adjust_population(grid_gdf_latlon, ghsl_fileloc)
    if save_loc is not None:
        points.to_csv(save_loc[0])
        grid_gdf_latlon.to_file(save_loc[1],driver='GeoJSON')


if __name__ == '__main__':
    flz_areas = gpd.read_file('flz_analysis_areas.gpkg')
    flz_utm = ox.project_gdf(flz_areas)
    setup_grid(flz_utm.crs, flz_utm.loc[0,'geometry'], 1000, 'flz_pop_dens.tif', 3204985.581)



