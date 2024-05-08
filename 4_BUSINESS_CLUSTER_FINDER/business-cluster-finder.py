import time
import csv
from scipy.spatial import distance, ConvexHull
from geojson import Polygon, Feature, FeatureCollection, dumps
from bng_latlon import WGS84toOSGB36, OSGB36toWGS84
import copy

RADIUS_EASTING_NORTHING_ETC = 150 #METRES??? I GUESS???
MINIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 20
MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 120

rows = []
name_index = 0
lat_index = 0
lon_index = 0
sector_index = 0
indices_that_have_yet_to_be_processed_for_each_sector = {}

def process():
    global rows, name_index, lat_index, lon_index, sector_index, indices_that_have_yet_to_be_processed_for_each_sector

    with open('input.csv', newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
      
        for row in reader:
            rows.append(row)

        headers = rows[0]
        name_index = headers.index("company_name")
        lat_index = headers.index("Latitude")
        lon_index = headers.index("Longitude")
        sector_index = headers.index("broad_industry")

        for i in range(len(rows)):
            if i == 0:
                continue
            row = rows[i]
            sectors = row[sector_index].split("; ")
            sectors_already_processed_for_this_business = [] #in case a business has lots of duplicate sectors on it
            for sector in sectors:
                sector = sector.strip().upper()
                if not sector in sectors_already_processed_for_this_business:
                    sectors_already_processed_for_this_business.append(sector)
                    if sector in indices_that_have_yet_to_be_processed_for_each_sector:
                        indices_that_have_yet_to_be_processed_for_each_sector[sector].append(i)
                    else:
                        indices_that_have_yet_to_be_processed_for_each_sector[sector] = [i]

        clusters = {}

        current_cluster = []

        start_time = time.time()
        
        for sector in indices_that_have_yet_to_be_processed_for_each_sector.keys():
            print("Processing sector: "+sector)
            before = copy.deepcopy(indices_that_have_yet_to_be_processed_for_each_sector[sector])
            for i in before:
                if i in indices_that_have_yet_to_be_processed_for_each_sector[sector]:
                    indices_that_have_yet_to_be_processed_for_each_sector[sector].remove(i)
                    row = rows[i]
                    latstr = row[lat_index]
                    lonstr = row[lon_index]
                    if latstr == "" or lonstr == "":
                        continue
                    bng = WGS84toOSGB36(float(latstr),float(lonstr))
                    current_cluster = get_uncompleted_points_of_same_sector_within_radius_of_this_BNG_and_its_neighbours(bng,sector)
                    if len(current_cluster) >= MINIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER:
                        cluster_name = "Cluster "+str(len(clusters.keys()))+": "+sector
                        clusters[cluster_name] = current_cluster
                        print("Cluster of len "+str(len(current_cluster))+" pushed: "+cluster_name)
                        print("Number of as yet unclustered businesses: "+str(len(indices_that_have_yet_to_be_processed_for_each_sector[sector])))
                        fraction_complete = 1 - (len(indices_that_have_yet_to_be_processed_for_each_sector[sector])/(len(rows)-1))
                        print(str(float(int(fraction_complete*10000))/100)+"% complete")
                        time_elapsed = time.time() - start_time
                        print("ETA in "+str((((1/fraction_complete) * (time_elapsed)) - time_elapsed))[:4] + " seconds")
                    current_cluster = []

        print(clusters)
        print("Coolio. But "+str(len(indices_that_have_yet_to_be_processed_for_each_sector)) + " businesses could not be clustered. This may be due to lack of proximity to other businesses, or lack of data (do they have a latitude and longitude in the input data?)")
        print("Making convex hulls...")

        features = []
        for key in clusters.keys():
            indices = clusters[key]
            polygon = make_convex_hull_around_BNG_points_of_these_rows(indices)
            features.append(Feature(geometry=polygon, properties={"sector":str(key).replace(str(key).split(": ")[0]+": ",""),
                                                                  "names_of_businesses_in_cluster":get_names_for_indices(indices),
                                                                  "total_number_of_businesses_in_cluster":len(indices)}))
    
        feature_collection = FeatureCollection(features)
        open("output.geojson","w").write(dumps(feature_collection, sort_keys=True))

def get_uncompleted_points_of_same_sector_within_radius_of_this_BNG_and_its_neighbours(src_BNG,sector):
    global RADIUS_EASTING_NORTHING_ETC, rows, indices_that_have_yet_to_be_processed_for_each_sector

    business_indices = []

    business_BNGs_to_compare_with = [src_BNG]

    yet_to_be_processed_businesses_in_sector = indices_that_have_yet_to_be_processed_for_each_sector[sector]

    keep_going = True

    while keep_going:
        keep_going = False
    
        to_be_removed_from_queue_at_end_of_loop = []

        for i in yet_to_be_processed_businesses_in_sector:            
            row = rows[i]
            latstr = row[lat_index]
            lonstr = row[lon_index]
            if latstr == "" or lonstr == "":
                continue
            row_BNG = WGS84toOSGB36(float(latstr),float(lonstr))

            if is_within_distance_of_any_of_these_row_indices(row_BNG, RADIUS_EASTING_NORTHING_ETC, business_BNGs_to_compare_with):
                keep_going = True
                to_be_removed_from_queue_at_end_of_loop.append(i)
                business_indices.append(i)
                business_BNGs_to_compare_with.append(row_BNG)
                if len(business_indices) >= MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER: #if we've hit the maximum cluster size
                    print("Max cluster size reached for this cluster")
                    keep_going = False
                    break
        
        for i in to_be_removed_from_queue_at_end_of_loop:
            yet_to_be_processed_businesses_in_sector.remove(i)

    return business_indices

def is_within_distance_of_any_of_these_row_indices(my_BNG, dist, business_BNGs_to_compare_with):
    for BNG in business_BNGs_to_compare_with:
        if distance.euclidean(my_BNG, BNG) <= dist:
            return True
    return False

def get_names_for_indices(row_indices):
    global rows, name_index

    names = ""

    for index in row_indices:
        if len(names) == 0:
            names += rows[index][name_index]
        else:
            names += "; " + rows[index][name_index]
          
    return names

def make_convex_hull_around_BNG_points_of_these_rows(row_indices):
    points = []
    for index in row_indices:
        row = rows[index]
        latstr = row[lat_index]
        lonstr = row[lon_index]
        if latstr == "" or lonstr == "":
            continue
        p = WGS84toOSGB36(float(latstr),float(lonstr))
        is_a_dupe_of_an_existing_point = False
        for existing_p in points:
            if existing_p[0] == p[0] or existing_p[1] == p[1]:
                is_a_dupe_of_an_existing_point = True
                break
        if not is_a_dupe_of_an_existing_point:
            points.append(p)

    for i in range(len(points)):
        points[i] = OSGB36toWGS84(points[i][0],points[i][1])

    if len(points) >= 3:
        hull = ConvexHull(points)
        output = []
        for index in hull.vertices:
            output.append((points[index][1],points[index][0])) # flips it around here because geojson stores latlon coordinates as lonlat
        return Polygon([output])
    else:
        output = []
        for point in points:
            output.append((point[1],point[0])) # flips it around here because geojson stores latlon coordinates as lonlat
        return Polygon([output])

process()