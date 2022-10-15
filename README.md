# Connectome
A set of scripts for a two-step procedure to measure the value of access to destinations across several modes of travel within a geographic area.

Currently a minimally-functional prototype developed by D. Taylor Reich at the Institute for Transportation and Development Policy

For more description and background, see [this document](https://docs.google.com/document/d/17rCy1cYkj9zRU4JSCJibOw4XfM2vkdfga9oHldlX6aY/edit#)

![bikehope](https://user-images.githubusercontent.com/57543011/146093135-71144c2a-fe48-46ca-ad92-a35eb5f9b378.png)

Steps to use: 
1. Create a base_data/ folder in the connectome/ script directory.
2. Put a [geofabrik](https://download.geofabrik.de/) OSM extract in that folder (use the smallest one you can that includes your area)
3. Run one of the setup_from_x() functions in setup.py
4. Copy the scenarios/existing_conditions/ to scenarios/???/ and then make whatever edits to represent your scenario
5. Run routing.py route_scenario() for each of those scenarios
6. Run summarize.py


Dependencies include:
- [r5py](https://github.com/r5py/r5py) (DEV VERSION)
- [osmnx](https://osmnx.readthedocs.io/en/stable/) 
- [rasterstats](https://pythonhosted.org/rasterstats/)
