# Companies house businesses as sector grids

This is a processor and viewer for companies house data, allowing you to view the distribution of businesses in an area according to sector. The processor produces a 'mosaic' at a user-specified resolution in geojson format - which can be duly placed in the frontend files for an updated view. It also generates polygons for clusters, though the distance metric and number of businesses required for a 'cluster' to form is arbitary and subject to the user's choice, so it may be better to just judge from the mosaic whether a group of businesses is a 'cluster' for your purposes or not.

E.g. you would be able to use this program to find a seeming hub of Manufacturing businesses in a city.

You can also adjust the time slider to a past date, which reveals which businesses in the present day timeslice were also active at that time in the past. However, this should only be thought of as showing stalwart/mainstay businesses that have existed since at least 2010 - it doesn't necessarily mean that they existed *in that place* at that time (they may have, but it isn't guaranteed).


## Caveats to be aware of

The business density portrayed by this program can sometimes be skewed by many similar or near-duplicate business registrations in one area. For example, if a large business has many departments registered as different companies but in the same office, it may artificially inflate the presence of the relevant sector in that grid square. This can be a problem because the colour range will become unnecessarily blown out by these high frequency squares, for no good reason.

To combat this, consider right-clicking any offending squares to exclude them from the colour calculations.


## How to regenerate the dataset

The python scripts in the /python-processing/ folder can be used to regenerate the geojson grids that are fed into the map. You should run them by running the master script, and hopefully the scripts themselves provide adequate advice/error catching for you to be able to run them or at least find out where errors have occurred. This program was designed for Birmingham, UK, and as such uses a pared down version of Birmingham.osm, but OSM files for other locations are easily found on the internet.

The file 'files/2_COMPARE/persistent_cache.json' is a cache of addresses generated during the previous geolocation. Since the vast majority of addresses from a previous Companies House bulk download will likely still be present in future bulk downloads of that same area, this *massively* speeds things up. The one initially present here is for Birmingham. If you're starting fresh with a different city, I recommend you delete the Birmingham persistent_cache.json, otherwise you'll be loading up that dictionary for no reason.

If you're completely fresh without a cache, the processing is very slow, so you'll have to leave it to run while you do something else. For Birmingham it takes around 6 hours - and that's in 'fast mode' where it's only approximating the locations by using postcode centroids. The reason for the slow speed is the fact that this program, while using the local OSM resource as often as it can, uses Nominatim's API as a fallback, with a time delay so that it does not encumber it. You can set up a local nominatim instance as a fallback, although I didn't personally find that it helped because the local instance seemed less capable and geolocating than the remote API. If you do want to try this, though, see the Linux section of this readme.

Another way to reduce the time taken is by limiting your postcode requirements when _0_cull_national_CH_csv.py runs. For example, asking only for B2 postcode prefixes, rather than B postcode prefixes, will massively reduce the processing time, by only retrieving B20, B21, B22, etc.


## How to run the frontend

The javascript frontend is a Vite SPA that uses Node Package Manager.

You can install it by running the command 'npm install' in the root folder and can then run it on localhost by running 1_RUN.bat.

To webpack it for deployment elsewhere, run 'npm build'.

To deploy it straight to github pages, run 2_DEPLOY.bat, but remember to change the relevant URLs in vite.config.js and package.json first.


## Running on linux for local nominatim geocoding

In practice, I didn't find that using a local nominatim instance particularly sped things up, because it seems to be less capable at geocoding than the nominatim web API, even when provided with the exact same address query. All the 'easy' address matches were hoovered up by the regular string similarity metric comparison, leaving any remaining ones too obscure for the local nominatim library to identify - they were all forced to use the web API fallback, defeating the point.

But if you want to try using this feature anyway for some reason, I used the following steps:

1. Make sure you have the modules nominatim-db and nominatim-api installed in your pip venv. The code specifically checks that nominatim-api is installed before it even attempts to use a local nominatim database. Make sure you have also followed the instructions on this page https://nominatim.org/release-docs/latest/admin/Installation/#installing-the-latest-release to make sure you have the prequisites installed.)

2. You may have to create sql database users if it's your first time running. For example, in bash:
> sudo -u postgres createuser -s nominatim

3. Use nominatim to import your OSM file into the database - for example:
> nominatim import --osm-file Birmingham.osm

Obviously please try not to use anything too large - stay away from Planet.osm! - the smaller it is, the faster it will be.
This step will take a few minutes, but you will only have to perform it once to create the database.

If it stops early, or you later have reason to believe that the import was incomplete, consider using the following command:
> nominatim import --continue indexing

4. Go into the database and make sure the postgis extension is enabled (and don't forget the semicolon to make sure the command actually runs!):
> psql nominatim
> CREATE EXTENSION postgis;
> \q

At this point, you should be able to run main.py with the venv's python3. However, as stated above, I didn't find it significantly faster. If you do want to incorporate an alternative fallback geolocation process for your own purposes, the relevant function is query_nominatim(), in /python-processing/_2_compare.py