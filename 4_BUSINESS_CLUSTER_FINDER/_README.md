
# WORKFLOW FOR THIS PROGRAM AND FRIENDS

This program is part of a group of programs intended to be used in order.

The programs are:

1. ch-spreadsheet updater (obtains company data from companies house)
2. very-polite-nominatim-query-machine (on the addresses from the company data above - to locate them and turn them into latlongs.)
3. SIC-code-translator (on the sectors and industries from the company data obtained in step 1 - to turn them into their respective textual descriptions)
4. business-cluster-finder (on the three outputs from the above stuck together - identifies clusters of the same business type, according to your distance parameters, and outputs geojson polyons)

Epilogue step: Take the geojson output from step 4 and import it into QGIS, to view it as a map.