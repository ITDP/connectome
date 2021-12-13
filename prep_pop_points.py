import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
import shapely.geometry
from shapely.geometry import Polygon, Point
from tqdm import tqdm
import maup
import os

#INTRO - need to edit values here for new city deployment

city_crs = 32130 

blocks_gdf_crs = gpd.read_file('prep_pop/RI_blocks.zip').to_crs(city_crs)
block_groups_gdf_crs = gpd.read_file('prep_pop/RI_block_groups.zip').to_crs(city_crs)
veh_avail = pd.read_csv('prep_pop/B25044.csv', index_col=0).iloc[1:,]

bounds_gdf_latlon = gpd.GeoDataFrame(geometry = [
    shapely.geometry.box(-71.471901,41.764142,-71.347961,41.888733)],
    crs = 4326)
bounds_gdf_crs = bounds_gdf_latlon.to_crs(city_crs)

#define exception polygon 
#this is the are within which the grid will be higher-resolution
point = Point(-71.411479,41.823544)
point_latlon = gpd.GeoDataFrame(geometry=[point], crs = 4326)
point_crs = point_latlon.to_crs(city_crs)
poly_crs = point_crs.buffer(1000).unary_union
exception_gdf_crs = gpd.GeoDataFrame(geometry = [poly_crs], crs=city_crs)

high_res = 250 #m to a side
low_res = 1000 #m to a side

# END INTRO actual code

def summarize_veh_avail(row):
    total_pop = int(row['B25044_001E'])
    if total_pop < 1:
        return 0,0,1 #if no population, assume all 0 households have 2 cars
    pct_carfree = (int(row['B25044_003E']) + int(row['B25044_010E'])) / total_pop
    pct_onecar = (int(row['B25044_004E']) + int(row['B25044_011E'])) / total_pop
    pct_twopluscars = 1 - pct_carfree - pct_onecar
    return pct_carfree, pct_onecar, pct_twopluscars

def build_grid(bounds_poly_crs, low_resolution, exception_gdf_crs=None, high_resolution=None):
    xmin,ymin,xmax,ymax =  bounds_poly_crs.bounds
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
            cell = cell.intersection(bounds_poly_crs)
            if exception_gdf_crs is not None:
                if not cell.intersects(exception_gdf_crs.unary_union):
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
    if exception_gdf_crs is not None:
        for exception_cell in exception_cells:
            highres_cells += build_grid(exception_cell, high_resolution)
    return lowres_cells + highres_cells

def populate_grid(grid, blocks, block_groups):
    #blocks first, for simple population
    blocks_pieces = maup.intersections(blocks, grid, area_cutoff=0)
    blocks_weights = blocks['POP10'].groupby(maup.assign(blocks, blocks_pieces)).sum()
    blocks_weights = maup.normalize(blocks_weights, level=0)
    grid['POP10'] = maup.prorate(
        blocks_pieces,
        blocks['POP10'],
        weights=blocks_weights,
    )
    
    #then block groups for car ownership
    bg_pieces = maup.intersections(block_groups, grid)
    bg_weights = grid['POP10'].groupby(maup.assign(grid, bg_pieces)).sum()
    bg_weights = maup.normalize(bg_weights, level=0)
    columns = ['pct_carfree', 'pct_onecar','pct_twopluscars']
    grid[columns] = maup.prorate(
        bg_pieces,
        block_groups[columns],
        weights=bg_weights,
        aggregate_by='mean',
    )
    return grid
    

 
#clip blocks and block groups
blocks_gdf_crs = gpd.clip(blocks_gdf_crs, bounds_gdf_crs)
block_groups_gdf_crs = gpd.clip(block_groups_gdf_crs, bounds_gdf_crs)

#assign veh_avail and block_groups the same index
block_groups_gdf_crs.index = block_groups_gdf_crs.GEOID
newidx = []
for bgidx in veh_avail.index:
    newidx.append(bgidx[9:])
veh_avail.index = newidx

for bgidx in block_groups_gdf_crs.index:
    pct_carfree, pct_onecar, pct_twopluscars = summarize_veh_avail(veh_avail.loc[bgidx])
    total_pop = float(veh_avail.loc[bgidx,'B25044_001E'])
    block_groups_gdf_crs.loc[bgidx,'total_pop'] = total_pop
    block_groups_gdf_crs.loc[bgidx,'pct_carfree'] = pct_carfree
    block_groups_gdf_crs.loc[bgidx,'pct_onecar'] = pct_onecar
    block_groups_gdf_crs.loc[bgidx,'pct_twopluscars'] = pct_twopluscars
    
grid_cells = build_grid(bounds_gdf_crs.unary_union, 1000, exception_gdf_crs, 250)
grid_gdf_crs = gpd.GeoDataFrame(geometry=grid_cells, crs=city_crs)
grid_gdf_latlon = grid_gdf_crs.to_crs(4326)
grid_pop_gdf_crs = populate_grid(
    grid_gdf_crs, 
    blocks_gdf_crs, 
    block_groups_gdf_crs, 
)
grid_pop_gdf_crs['pop_dens'] = grid_pop_gdf_crs['POP10'] / grid_pop_gdf_crs.geometry.area
grid_pop_gdf_latlon = grid_pop_gdf_crs.to_crs(4326)

points = pd.DataFrame()
for idx in grid_pop_gdf_latlon.index:
    grid_pop_gdf_latlon.loc[idx,'id'] = idx
    points.loc[idx,'id'] = idx
    centroid = grid_pop_gdf_latlon.loc[idx,'geometry'].centroid
    points.loc[idx,'lat'] = centroid.y
    points.loc[idx,'lon'] = centroid.x
    for col in ['POP10','pct_carfree','pct_onecar','pct_twopluscars','pop_dens']:
        points.loc[idx, col] = grid_pop_gdf_latlon.loc[idx, col]

points.to_csv('pop_points.csv')
grid_pop_gdf_latlon.to_file('grid_pop.geojson',driver='GeoJSON')
