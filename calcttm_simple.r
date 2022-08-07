options(java.parameters = "-Xmx2G")

#install.packages('devtools', repos="http://cran.rstudio.com/")
#devtools::install_github("ipeaGIT/r5r", subdir = "r-package")
#install.packages("r5r", repos="http://cran.rstudio.com/")
#install.packages('ggplot2',  repos="http://cran.rstudio.com/")
#install.packages('mapview', repos="http://cran.rstudio.com/")

library(r5r)
library(sf)
library(data.table)
library(ggplot2)

args = commandArgs(trailingOnly=TRUE)
data_path <- paste(getwd(),args[1],sep="/")

#TODO: import these and other settings from a settings file
max_walk_time <- 60
max_trip_duration <- 60
departure_datetime <- as.POSIXct("11-11-2021 14:00:00",
                                 format = "%d-%m-%Y %H:%M:%S")


points <- fread(paste(data_path,'pop_points.csv', sep="/"))
r5r_core <- setup_r5(data_path = data_path, verbose = FALSE)

mode <- c("CAR")
ttm_car <- travel_time_matrix(r5r_core = r5r_core,
                              origins = points,
                              destinations = points,
                              mode = mode,
                              departure_datetime = departure_datetime,
                              max_walk_time = max_walk_time,
                              max_trip_duration = max_trip_duration,
                              verbose = FALSE)
setDT(ttm_car)
car_wide <- dcast(ttm_car, from_id ~ to_id, value.var='travel_time_p50')
write.csv(car_wide, paste(data_path,'car_wide.csv', sep="/"))

mode <- c("WALK")
ttm_walk <- travel_time_matrix(r5r_core = r5r_core,
                                       origins = points,
                                       destinations = points,
                                       mode = mode,
                                       departure_datetime = departure_datetime,
                                       max_walk_time = max_walk_time,
                                       max_trip_duration = max_trip_duration,
                                       verbose = FALSE)
setDT(ttm_walk)
walk_wide <- dcast(ttm_walk, from_id ~ to_id, value.var='travel_time_p50')
write.csv(walk_wide, paste(data_path,'walk_wide.csv', sep="/"))

mode <- c("BICYCLE")
max_lts <- 1
ttm_bike_lts1 <- travel_time_matrix(r5r_core = r5r_core,
                                  origins = points,
                                  destinations = points,
                                  mode = mode,
                                  departure_datetime = departure_datetime,
                                  max_walk_time = max_walk_time,
                                  max_trip_duration = max_trip_duration,
                                  max_lts = max_lts,
                                  verbose = FALSE)
setDT(ttm_bike_lts1)
bike_lts1_wide <- dcast(ttm_bike_lts1, from_id ~ to_id, value.var='travel_time_p50')
write.csv(bike_lts1_wide, paste(data_path,'bike_lts1_wide.csv', sep="/"))

mode <- c("BICYCLE")
max_lts <- 2
ttm_bike_lts2 <- travel_time_matrix(r5r_core = r5r_core,
                                    origins = points,
                                    destinations = points,
                                    mode = mode,
                                    departure_datetime = departure_datetime,
                                    max_walk_time = max_walk_time,
                                    max_trip_duration = max_trip_duration,
                                    max_lts = max_lts,
                                    verbose = FALSE)
setDT(ttm_bike_lts2)
bike_lts2_wide <- dcast(ttm_bike_lts2, from_id ~ to_id, value.var='travel_time_p50')
write.csv(bike_lts2_wide, paste(data_path,'bike_lts2_wide.csv', sep="/"))

mode <- c("BICYCLE")
max_lts <- 4
ttm_bike_lts4 <- travel_time_matrix(r5r_core = r5r_core,
                                    origins = points,
                                    destinations = points,
                                    mode = mode,
                                    departure_datetime = departure_datetime,
                                    max_walk_time = max_walk_time,
                                    max_trip_duration = max_trip_duration,
                                    max_lts = max_lts,
                                    verbose = FALSE)
setDT(ttm_bike_lts4)
bike_lts4_wide <- dcast(ttm_bike_lts4, from_id ~ to_id, value.var='travel_time_p50')
write.csv(bike_lts4_wide, paste(data_path,'bike_lts4_wide.csv', sep="/"))
