# Companies house businesses as sector grids

This is a processor and viewer for companies house data, allowing you to view the distribution of businesses in an area according to sector. The processor produces a 'mosaic' at a user-specified resolution in geojson format - which can be duly placed in the frontend files for an updated view. It also generates polygons for clusters, though the distance metric and number of businesses required for a 'cluster' to form is arbitary and subject to the user's choice, so it may be better to just judge from the mosaic whether a group of businesses is a 'cluster' for your purposes or not.

E.g. you would be able to use this program to find a seeming hub of Manufacturing businesses in a city.

You can also adjust the time slider to a past data, to ensure that the businesses revealed to you were also active in the same location at the selected time. Remember, though, that this doesn't constitute a complete picture of the businesses in the area at the selected time - because it's only ones that are still in the same place today. So it could be thought of as showing stalwart/mainstay businesses that have been in the area since at least 2010.


## Caveats to be aware of

The business density portrayed by this program can sometimes be skewed by many similar or near-duplicate business registrations in one area. For example, if a large business has many departments registered as different companies but in the same office, it may artificially inflate the presence of the relevant sector in that grid square. This can be a problem because the colour range will become unnecessarily blown out by these high frequency squares, for no good reason.

To combat this, consider right-clicking any offending squares to exclude them from the colour calculations.


## How to regenerate the dataset

The python scripts in the /python-processing/ folder can be used to regenerate the geojson grids that are fed into the map. You should run them by running the master script, and hopefully the scripts themselves provide adequate advice/error catching for you to be able to run them or at least find out where errors have occurred. This program was designed for Birmingham, UK, and as such uses a pared down version of Birmingham.osm, but OSM files for other locations are easily found on the internet.

One unfortunate fact is that the processing is very slow, so you'll have to leave it to run while you do something else. For Birmingham it takes around 6 hours - and that's in 'fast mode'. The reason for this is the fact that this program, while using the local OSM resource as often as it can, uses Nominatim's API as a fallback with a time delay so that it does not encumber it. If you want to use this for another purpose I strongly suggest setting up a local nominatim instance, which I have not done here because its installation process is a bit more complicated and creates a barrier to entry for any novice who might want to run this (having to build a wheel etc).

Another good way to reduce the time taken is by limiting your postcode requirements when _0_cull_national_CH_csv.py runs.

If you do want to incorporate an alternative fallback geolocation process for your own purposes, the relevant function is query_nominatim(), in /python-processing/_2_compare.py


## How to run the frontend

The javascript frontend is a Vite SPA that uses Node Package Manager.

You can install it by running the command 'npm install' in the root folder and can then run it on localhost by running 1_RUN.bat.

To webpack it for deployment elsewhere, run 'npm build'.

To deploy it straight to github pages, run 2_DEPLOY.bat, but remember to change the relevant URLs in vite.config.js and package.json first.