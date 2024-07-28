import csv
import geojson
from bng_latlon import WGS84toOSGB36, OSGB36toWGS84
import datetime
import os

def makeBoundsIntoGeoJsonFormatPolygon(topLeft,bottomRight):
    topLat = topLeft[0]
    bottomLat = bottomRight[0]
    leftLon = topLeft[1]
    rightLon = bottomRight[1]

    return [[leftLon,topLat], [rightLon,topLat], [rightLon, bottomLat], [leftLon, bottomLat]] # lat and lon are arranged backwards here, because that's how geojson expects them

#TEMPLATE THAT THE REAL ONE MAY DERIVE FROM LATER
ENTIRE_BHAM_TOPLEFT_EASTING_NORTHING = [378392,316066]
ENTIRE_BHAM_BOTTOMRIGHT_EASTING_NORTHING = [438836,260377]

#TEMPLATE THAT THE REAL ONE MAY DERIVE FROM LATER
EASTBHAM_TOPLEFT_EASTING_NORTHING = [407884,295228]
EASTBHAM_BOTTOMRIGHT_EASTING_NORTHING = [419948,276214]

GRID_INTERVAL_METRES = 1000

#THE REAL ONE THAT IS ACTUALLY USED IN THE CALCULATION
BNG_TOPLEFT_EASTING_NORTHING = ENTIRE_BHAM_TOPLEFT_EASTING_NORTHING
BNG_BOTTOMRIGHT_EASTING_NORTHING = ENTIRE_BHAM_BOTTOMRIGHT_EASTING_NORTHING

e = BNG_TOPLEFT_EASTING_NORTHING[0]

businesses_all = []
sectors_all = []
grid_squares = []

while e < BNG_BOTTOMRIGHT_EASTING_NORTHING[0]:
    n  = BNG_TOPLEFT_EASTING_NORTHING[1]
    while n >= BNG_BOTTOMRIGHT_EASTING_NORTHING[1]:
        topleft_of_square_as_latlon = OSGB36toWGS84(e,n)
        bottomright_of_square_as_latlon = OSGB36toWGS84(e + GRID_INTERVAL_METRES, n - GRID_INTERVAL_METRES)

        propertiesObj = {"Position (TL)":[e,n], "Position (BR)":[e+GRID_INTERVAL_METRES,n-GRID_INTERVAL_METRES],
                         "sectorFrequencies":{}, "Businesses":"", "_Modal sector":None, "Business names":[], "BusinessesBySector":{}}        

        grid_squares.append(geojson.Feature(geometry=geojson.Polygon([makeBoundsIntoGeoJsonFormatPolygon(topleft_of_square_as_latlon, bottomright_of_square_as_latlon)]),
                                            properties=propertiesObj))
        n -= GRID_INTERVAL_METRES
    e += GRID_INTERVAL_METRES

def get_my_grid_square(eastingNorthing):

    for grid_square in grid_squares:
        if eastingNorthing[0] >= grid_square.properties.get("Position (TL)")[0] and eastingNorthing[0] < grid_square.properties.get("Position (BR)")[0]:
            if eastingNorthing[1] <= grid_square.properties.get("Position (TL)")[1] and eastingNorthing[1] > grid_square.properties.get("Position (BR)")[1]:
                return grid_square
    return None

def print_percentage_complete(i, len):
    print(str(i/len*100)+"% complete overall")

def process():
    with open('files/2_COMPARE/output.csv', newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        rows = []
        for row in reader:
            rows.append(row)

    company_name_column_index = rows[0].index("company_name")
    broad_industry_column_index = rows[0].index("broad_industry")
    latitude_column_index = rows[0].index("Latitude")
    longitude_column_index = rows[0].index("Longitude")

    num_processed_since_last_skip = 0

    for i in range(len(rows)):
        if i == 0: #don't process header
            continue
        
        row = rows[i]

        if "\"" in row[company_name_column_index]:
            print("WARNING: The company name in this row had a double quotation character in it. If you receive an error immediately after seeing this message, this is probably why - as it runs a high risk of throwing the columns of this csv row out of sync.")
            print("The company name was: "+row[company_name_column_index])

        latstr = row[latitude_column_index]
        lonstr = row[longitude_column_index]

        if latstr == "" or lonstr == "":
            print("Ignoring a buisness that had an empty latitude or longitude")
            print_percentage_complete(i,len(rows))
            continue

        grid_square = get_my_grid_square(WGS84toOSGB36(float(latstr), float(lonstr)))

        if grid_square == None:
            print("Ignoring a business that didn't fit in any of the grid squares")
            print("It was at: "+latstr + " "+ lonstr)
            print("But rest assured, we silently processed "+str(num_processed_since_last_skip)+" other businesses in the meantime")
            num_processed_since_last_skip = 0
            print_percentage_complete(i,len(rows))
            continue

        row[company_name_column_index] = row[company_name_column_index].replace("\"","")

        businesses_all.append(row)
        businessIndex = len(businesses_all) - 1;

        grid_square.properties["Business names"].append(businessIndex)

        num_processed_since_last_skip += 1

        unique_sectors_for_row = []

        for sector in row[broad_industry_column_index].strip().split(";"):
            if not sector == "":
                sector = sector.strip().upper()         
                if not sector in sectors_all:
                    sectors_all.append(sector)
                sectorID = sectors_all.index(sector)
                if not sectorID in unique_sectors_for_row:
                    unique_sectors_for_row.append(sectorID)

        for j in range(len(unique_sectors_for_row)):
            sectorID = unique_sectors_for_row[j]

            if sectorID in grid_square.properties.get("BusinessesBySector"):
                grid_square.properties.get("BusinessesBySector")[sectorID].append(businessIndex)
            else:
                grid_square.properties.get("BusinessesBySector")[sectorID] = [businessIndex]

            if sectorID in grid_square.properties.get("sectorFrequencies"):
                grid_square.properties.get("sectorFrequencies")[sectorID] += 1
            else:
                grid_square.properties.get("sectorFrequencies")[sectorID] = 1

    for grid_square in grid_squares:
        biggest_freq = 0
        sectorFrequencies = grid_square.properties.get("sectorFrequencies")

        for sector in sectorFrequencies:
            freq = sectorFrequencies[sector]
            if freq > biggest_freq:
                biggest_freq = freq
        
        modes = []

        for sector in sectorFrequencies:
            grid_square.properties["Business count for "+str(sector)] = sectorFrequencies[sector]
            freq = sectorFrequencies[sector]
            if freq == biggest_freq:
                modes.append(str(sector).strip())

        tl_latlong = OSGB36toWGS84(grid_square.properties["Position (TL)"][0], grid_square.properties["Position (TL)"][1])
        br_latlong = OSGB36toWGS84(grid_square.properties["Position (BR)"][0], grid_square.properties["Position (BR)"][1])

        efficient_grid_square = geojson.Feature(
            geometry=grid_square.geometry,
            properties = {
                "Sector frequencies":sectorFrequencies,
                "Freq of modal sector(s)":biggest_freq,                
                "Modal sector(s)":modes,
                "TL":tl_latlong,
                "BR":br_latlong,
                "Businesses":grid_square.properties.get("Business names"),
                "BusinessesBySector":grid_square.properties.get("BusinessesBySector")
            }
        )
        grid_squares[grid_squares.index(grid_square)] = efficient_grid_square

    print(grid_squares[0].properties.get("Businesses"))

    featureCollection = geojson.FeatureCollection(
        features = grid_squares,
        properties = {
            "timestamp": str(datetime.datetime.now()),
            "businesses_all":businesses_all, #must not sort these, because the indices are important
            "sectors_all":sectors_all  #must not sort these, because the indices are important
            }
        );

    output_path = "files/5 - CREATE_GRID_SHOWING_BUSINESS_SECTOR_FREQUENCIES/output_grid_with_interval_"+str(GRID_INTERVAL_METRES)+".geojson"

    if os.path.isfile(output_path):
        os.remove(output_path)
        
    open(output_path, mode="w", encoding="utf-8").write(geojson.dumps(featureCollection))
    print("Processing complete; "+output_path+" should contain the new output.")

process()