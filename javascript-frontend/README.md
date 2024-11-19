# Tyseley GIS Tool

A GIS tool for parsing CSV / geojson files, allowing the user to intuitively display the data on a Leaflet map of Tyseley, East Birmingham.

## Instructions for devs if this needs hosting from another website in the future

Clone the project and run the command 'npm install' in its directory. Then, change both the home address in package.json, and the route in vite.config.js, to reflect the desired new web address. Running 'npm build' should bundle up the files in the /dist/ directory, ready to be taken away and deployed elsewhere.