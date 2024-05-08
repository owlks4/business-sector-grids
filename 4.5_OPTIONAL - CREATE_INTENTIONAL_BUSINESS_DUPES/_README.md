Instead of creating polygon clusters, you might want to portray the data as a raster mosaic.

However, in order to do that, the businesses with multiple different sector prefixes must be separated into separate entries - otherwise, QGIS won't be able to derive the categories properly and will assume that there are hundreds, or even thousands of unique sectors - when in reality they're all just combinations of multiple different sectors.

To overcome this issue, this section separates all the multi-sector businesses into different entries  and make the data more suitable for the mosaic.

It accepts the file from step 3 (CONVERT_SIC_CODES_TO_TEXT) as an input.