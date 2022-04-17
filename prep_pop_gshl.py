import pandas as pd
import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import Polygon
import rasterstats
#import utm


city_crs = 32737 

bounds_gdf_latlon = gpd.GeoDataFrame(geometry = [
    shapely.geometry.box(36.648331,-1.342269,36.918526,-1.196050)],
    crs = 4326)


bounds_gdf_crs = bounds_gdf_latlon.to_crs(city_crs)

low_resolution = 1250

#eventually need to build _ghls and _usa together
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

grid_cells = build_grid(bounds_gdf_crs.unary_union, low_resolution)
grid_gdf_crs = gpd.GeoDataFrame(geometry=grid_cells, crs=city_crs)
grid_gdf_crs['area'] = grid_gdf_crs.geometry.area
grid_gdf_latlon = grid_gdf_crs.to_crs(4326)

pop_sums = rasterstats.zonal_stats(grid_gdf_latlon, 'prep_pop/clipped.tif', stats=['sum'])

for idx in grid_gdf_latlon.index:
    grid_gdf_latlon.loc[idx, 'POP10'] = pop_sums[idx]['sum']
    if grid_gdf_latlon.loc[idx, 'POP10'] == None:
        grid_gdf_latlon.loc[idx, 'POP10'] = 0

grid_gdf_latlon['pop_dens'] = grid_gdf_latlon['POP10'] / grid_gdf_latlon.area
points = pd.DataFrame()

for idx in grid_gdf_latlon.index:
    grid_gdf_latlon.loc[idx,'id'] = idx
    points.loc[idx,'id'] = idx
    points.loc[idx,'POP10'] = grid_gdf_latlon.loc[idx,'POP10']
    centroid = grid_gdf_latlon.loc[idx,'geometry'].centroid
    points.loc[idx,'lat'] = centroid.y
    points.loc[idx,'lon'] = centroid.x
    points.loc[idx,'pct_carfree'] = 0.8
    points.loc[idx,'pct_onecar'] = 0.15
    points.loc[idx,'pct_twopluscars'] = 0.05
    
    
points.to_csv('prep_pop/pop_points.csv')
grid_gdf_latlon.to_file('prep_pop/grid_pop.geojson',driver='GeoJSON')