import csv
import geojson
from bng_latlon import WGS84toOSGB36, OSGB36toWGS84

def makeBoundsIntoGeoJsonFormatPolygon(topLeft,bottomRight):
    topLat = topLeft[0]
    bottomLat = bottomRight[0]
    leftLon = topLeft[1]
    rightLon = bottomRight[1]

    return [[leftLon,topLat], [rightLon,topLat], [rightLon, bottomLat], [leftLon, bottomLat]] # lat and lon are arranged backwards here, because that's how geojson expects them

BNG_TOPLEFT_EASTING_NORTHING = [378392,316066]
BNG_BOTTOMRIGHT_EASTING_NORTHING = [438836,260377]
GRID_INTERVAL_METRES = 500

e = BNG_TOPLEFT_EASTING_NORTHING[0]

grid_squares = []

while e < BNG_BOTTOMRIGHT_EASTING_NORTHING[0]:
    n  = BNG_TOPLEFT_EASTING_NORTHING[1]
    while n >= BNG_BOTTOMRIGHT_EASTING_NORTHING[1]:
        topleft_of_square_as_latlon = OSGB36toWGS84(e,n)
        bottomright_of_square_as_latlon = OSGB36toWGS84(e + GRID_INTERVAL_METRES, n - GRID_INTERVAL_METRES)
        grid_squares.append(geojson.Feature(geometry=geojson.Polygon([makeBoundsIntoGeoJsonFormatPolygon(topleft_of_square_as_latlon, bottomright_of_square_as_latlon)]),
                                            properties={"TL":[e,n], "BR":[e+500,n-500], "sectorFrequencies":{}, "businesses_in_this_grid_square_str":"", "_modal_sector":None}))
        n -= GRID_INTERVAL_METRES
    e += GRID_INTERVAL_METRES

def get_my_grid_square(eastingNorthing):

    for grid_square in grid_squares:
        if eastingNorthing[0] >= grid_square.properties.get("TL")[0] and eastingNorthing[0] < grid_square.properties.get("BR")[0]:
            if eastingNorthing[1] <= grid_square.properties.get("TL")[1] and eastingNorthing[1] > grid_square.properties.get("BR")[1]:
                return grid_square
    return None

def print_percentage_complete(i, len):
    print(str(i/len*100)+"% complete overall")

def process():
    with open('input.csv', newline='', encoding="utf-8") as csvfile:
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
    
        grid_square.properties["businesses_in_this_grid_square_str"] += row[company_name_column_index].replace("\"","")+ "; "

        num_processed_since_last_skip += 1

        unique_sectors_for_row = []

        for sector in row[broad_industry_column_index].strip().split(";"):
            sector = sector.strip().upper()
            if not sector in unique_sectors_for_row and not sector == "":
                unique_sectors_for_row.append(sector)

        for j in range(len(unique_sectors_for_row)):
            sector = unique_sectors_for_row[j]
            if not sector in grid_square.properties.get("sectorFrequencies"):
                grid_square.properties.get("sectorFrequencies")[sector] = 1
            else:
                grid_square.properties.get("sectorFrequencies")[sector] += 1


    for grid_square in grid_squares:
        biggest_freq = 0
        sectorFrequencies = grid_square.properties.get("sectorFrequencies")

        for sector in sectorFrequencies:
            freq = sectorFrequencies[sector]
            if freq > biggest_freq:
                biggest_freq = freq
        
        mode = ""

        for sector in sectorFrequencies:
            grid_square.properties[sector] = sectorFrequencies[sector]
            freq = sectorFrequencies[sector]
            if freq == biggest_freq:
                mode += str(sector) + "; "

        mode = mode.strip()
        grid_square.properties["_modal_sector"] = mode
        grid_square.properties["_freq_of_modal_sector"] = biggest_freq
        grid_square.properties["businesses_in_this_grid_square_str"] = grid_square.properties["businesses_in_this_grid_square_str"].strip()
        if hasattr(grid_square.properties, "sectorFrequencies"):
            delattr(grid_square.properties,"sectorFrequencies")

    open("OUTPUT_MODAL_GRID_WITH_INTERVAL_"+str(GRID_INTERVAL_METRES)+".geojson", mode="w", encoding="utf-8").write(geojson.dumps(geojson.FeatureCollection(grid_squares)))

    print("Processing complete; OUTPUT_MODAL_GRID.geojson should contain the new output.")

process()