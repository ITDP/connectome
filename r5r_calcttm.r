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
#for mode in modes (with stipulations)
#generate ttm

scenario_dirs = list.dirs(paste(getwd(),"/scenarios",sep=""), recursive=FALSE)

#SC: existing conditions

for (scenario_dir in scenario_dirs) {
  print(scenario_dir)
  data_path <- scenario_dir
  
  points <- fread(paste(scenario_dir,'pop_points.csv', sep="/"))
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
  write.csv(car_wide, paste(scenario_dir,'travel_times/car_wide.csv', sep="/"))
  
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
  write.csv(walk_wide, paste(scenario_dir,'travel_times/walk_wide.csv', sep="/"))
  
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
  write.csv(transit_wide, paste(scenario_dir,'travel_times/transit_wide.csv', sep="/"))
  
  mode <- c("BICYCLE")
  max_lts <- 1
  ttm_bike_lts1 <- travel_time_matrix(r5r_core = r5r_core,
                                    origins = points,
                                    destinations = points,
                                    mode = mode,
                                    departure_datetime = departure_datetime,
                                    max_walk_dist = max_walk_dist,
                                    max_trip_duration = max_trip_duration,
                                    max_lts = max_lts,
                                    verbose = FALSE)
  setDT(ttm_bike_lts1)
  bike_lts1_wide <- dcast(ttm_bike_lts1, fromId ~ toId, value.var='travel_time')
  write.csv(bike_lts1_wide, paste(scenario_dir,'travel_times/bike_lts1_wide.csv', sep="/"))
  
  mode <- c("BICYCLE")
  max_lts <- 2
  ttm_bike_lts2 <- travel_time_matrix(r5r_core = r5r_core,
                                      origins = points,
                                      destinations = points,
                                      mode = mode,
                                      departure_datetime = departure_datetime,
                                      max_walk_dist = max_walk_dist,
                                      max_trip_duration = max_trip_duration,
                                      max_lts = max_lts,
                                      verbose = FALSE)
  setDT(ttm_bike_lts2)
  bike_lts2_wide <- dcast(ttm_bike_lts2, fromId ~ toId, value.var='travel_time')
  write.csv(bike_lts2_wide, paste(scenario_dir,'travel_times/bike_lts2_wide.csv', sep="/"))
  
  mode <- c("BICYCLE")
  max_lts <- 4
  ttm_bike_lts4 <- travel_time_matrix(r5r_core = r5r_core,
                                      origins = points,
                                      destinations = points,
                                      mode = mode,
                                      departure_datetime = departure_datetime,
                                      max_walk_dist = max_walk_dist,
                                      max_trip_duration = max_trip_duration,
                                      max_lts = max_lts,
                                      verbose = FALSE)
  setDT(ttm_bike_lts4)
  bike_lts4_wide <- dcast(ttm_bike_lts4, fromId ~ toId, value.var='travel_time')
  write.csv(bike_lts4_wide, paste(scenario_dir,'travel_times/bike_lts4_wide.csv', sep="/"))
}
