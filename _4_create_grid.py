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

TIMESTAMP_STRING = open("files/2_COMPARE/timestamp.txt", encoding="utf-8").read()

#TEMPLATE THAT THE REAL ONE MAY DERIVE FROM LATER
ENTIRE_BHAM_TOPLEFT_EASTING_NORTHING = WGS84toOSGB36(52.625, -2.15)
ENTIRE_BHAM_BOTTOMRIGHT_EASTING_NORTHING = WGS84toOSGB36(52.3, -1.575)

#TEMPLATE THAT THE REAL ONE MAY DERIVE FROM LATER
EASTBHAM_TOPLEFT_EASTING_NORTHING = [407884,295228]
EASTBHAM_BOTTOMRIGHT_EASTING_NORTHING = [419948,276214]

print("\nStarting step 4.\n")

interval_response = 0
print("We're going to make some sector grids; what should be the resolution (metres) of the grid? A good value is 1000, but you might also want to go to 500 or 250.")

while (interval_response == 0):
    interval_response = input("Input it here: ")
    if not interval_response.isnumeric():
        print("\nInput must be a number (no units; they are always metres!)\n")
        interval_response = 0
    elif int(interval_response) > 2000:
        print("\nPlease don't go higher than 2000.\n")
        interval_response = 0
    elif int(interval_response) < 250:
        print("\nPlease don't go lower than 2000.\n")
        interval_response = 0

GRID_INTERVAL_METRES = int(interval_response)

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

        indexified_sectors_for_business = ""

        for sector in row[broad_industry_column_index].strip().split(";"):
            if not sector == "":
                sector = sector.strip().upper()         
                if not sector in sectors_all:
                    sectors_all.append(sector)
                sectorID = sectors_all.index(sector)
                indexified_sectors_for_business += str(sectorID) + ";"
                if not sectorID in unique_sectors_for_row:
                    unique_sectors_for_row.append(sectorID)

        row[broad_industry_column_index] = indexified_sectors_for_business.strip(";")

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

    efficient_grid_squares = []

    for grid_square in grid_squares:
        biggest_freq = 0
        sectorFrequencies = grid_square.properties.get("sectorFrequencies")

        for sector in sectorFrequencies:
            freq = sectorFrequencies[sector]
            if freq > biggest_freq:
                biggest_freq = freq
        
        if biggest_freq > 0:
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
            efficient_grid_squares.append(efficient_grid_square)
        else:
            pass #(the highest frequency among all sectors in that square was zero, so there cannot be any businesses either and it therefore is not worth storing in the array)

    featureCollection = geojson.FeatureCollection(
        features = efficient_grid_squares,
        properties = {
            "timestamp":TIMESTAMP_STRING,
            "row_headers":rows[0],
            "businesses_all":businesses_all, #must not sort these, because the indices are important
            "sectors_all":sectors_all  #must not sort these, because the indices are important
            }
        );

    output_path = "files/4_CREATE_GRID_SHOWING_BUSINESS_SECTOR_FREQUENCIES/output_grid_with_interval_"+str(GRID_INTERVAL_METRES)+".geojson"

    if os.path.isfile(output_path):
        os.remove(output_path)
        
    open(output_path, mode="w", encoding="utf-8").write(geojson.dumps(featureCollection))
    print("Processing complete; "+output_path+" should contain the new output.")

process()