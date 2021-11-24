options(java.parameters = "-Xmx2G")

library(r5r)
library(sf)
library(data.table)
library(ggplot2)
library(mapview)
mapviewOptions(platform = 'leafgl')

#TODO: import these and other settings from a settings file
max_walk_dist <- 5000
max_trip_duration <- 120
departure_datetime <- as.POSIXct("11-11-2021 14:00:00",
                                 format = "%d-%m-%Y %H:%M:%S")

#TODO: rewrite this as a set of nested for loops:
#for scenario in scenarios
#for mode in modes
#generate ttm

#SC: existing conditions
setwd("~/access/providence/sc_existing_conditions")
data_path <-getwd()

points <- fread('pop_points.csv')
r5r_core <- setup_r5(data_path = data_path, verbose = FALSE)

mode <- c("CAR")
ttm_car <- travel_time_matrix(r5r_core = r5r_core,
                              origins = points,
                              destinations = points,
                              mode = mode,
                              departure_datetime = departure_datetime,
                              max_walk_dist = max_walk_dist,
                              max_trip_duration = max_trip_duration,
                              verbose = FALSE)
setDT(ttm_car)
car_wide <- dcast(ttm_car, fromId ~ toId, value.var='travel_time')
write.csv(car_wide, 'travel_times/car_wide.csv')

mode <- c("WALK")
ttm_walk <- travel_time_matrix(r5r_core = r5r_core,
                                       origins = points,
                                       destinations = points,
                                       mode = mode,
                                       departure_datetime = departure_datetime,
                                       max_walk_dist = max_walk_dist,
                                       max_trip_duration = max_trip_duration,
                                       verbose = FALSE)
setDT(ttm_walk)
walk_wide <- dcast(ttm_walk, fromId ~ toId, value.var='travel_time')
write.csv(walk_wide, 'travel_times/walk_wide.csv')

mode <- c("TRANSIT")
ttm_transit <- travel_time_matrix(r5r_core = r5r_core,
                                       origins = points,
                                       destinations = points,
                                       mode = mode,
                                       departure_datetime = departure_datetime,
                                       max_walk_dist = max_walk_dist,
                                       max_trip_duration = max_trip_duration,
                                       verbose = FALSE)
setDT(ttm_transit)
transit_wide <- dcast(ttm_transit, fromId ~ toId, value.var='travel_time')
write.csv(transit_wide, 'travel_times/transit_wide.csv')


#SC: new bridge
setwd("~/access/providence/sc_new_bridge")
data_path <-getwd()


points <- fread('pop_points.csv')
r5r_core <- setup_r5(data_path = data_path, verbose = FALSE)

mode <- c("CAR")
ttm_car <- travel_time_matrix(r5r_core = r5r_core,
                              origins = points,
                              destinations = points,
                              mode = mode,
                              departure_datetime = departure_datetime,
                              max_walk_dist = max_walk_dist,
                              max_trip_duration = max_trip_duration,
                              verbose = FALSE)
setDT(ttm_car)
car_wide <- dcast(ttm_car, fromId ~ toId, value.var='travel_time')
write.csv(car_wide, 'travel_times/car_wide.csv')

mode <- c("WALK")
ttm_walk <- travel_time_matrix(r5r_core = r5r_core,
                               origins = points,
                               destinations = points,
                               mode = mode,
                               departure_datetime = departure_datetime,
                               max_walk_dist = max_walk_dist,
                               max_trip_duration = max_trip_duration,
                               verbose = FALSE)
setDT(ttm_walk)
walk_wide <- dcast(ttm_walk, fromId ~ toId, value.var='travel_time')
write.csv(walk_wide, 'travel_times/walk_wide.csv')

mode <- c("TRANSIT")
ttm_transit <- travel_time_matrix(r5r_core = r5r_core,
                                  origins = points,
                                  destinations = points,
                                  mode = mode,
                                  departure_datetime = departure_datetime,
                                  max_walk_dist = max_walk_dist,
                                  max_trip_duration = max_trip_duration,
                                  verbose = FALSE)
setDT(ttm_transit)
transit_wide <- dcast(ttm_transit, fromId ~ toId, value.var='travel_time')
write.csv(transit_wide, 'travel_times/transit_wide.csv')

