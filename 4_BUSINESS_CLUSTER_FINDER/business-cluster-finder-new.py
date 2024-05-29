import time
import csv
from scipy.spatial import distance, ConvexHull
from geojson import Polygon, Feature, FeatureCollection, dumps
from bng_latlon import WGS84toOSGB36, OSGB36toWGS84
import copy

RADIUS_EASTING_NORTHING_ETC = 150 #METRES??? I GUESS???
MINIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 20
MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 120

businesses = []
name_index = 0
lat_index = 0
lon_index = 0
sector_index = 0
businesses_that_have_yet_to_be_processed_for_each_sector = {}

class Business:
    def __init__(self, row):
        self.name = row[name_index]
        if row[lat_index] == "" or row[lon_index] == "":
            self.lat = 0
            self.lon = 0
            self.easting = 0
            self.northing = 0
        else:
            self.lat = float(row[lat_index])
            self.lon = float(row[lon_index])
            self.bng = WGS84toOSGB36(self.lat, self.lon)

        self.sectors = row[sector_index]

def process():
    global businesses, name_index, lat_index, lon_index, sector_index, businesses_that_have_yet_to_be_processed_for_each_sector

    with open('input.csv', newline='', encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')

        rows = []

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
            businesses.append(Business(rows[i]))

        businesses.sort(key = lambda business : business.lat) # sort businesses by latitude

        for business in businesses:
            if i == 0:
                continue
            sectors = business.sectors.split("; ")
            sectors_already_processed_for_this_business = [] #in case a business has lots of duplicate sectors on it
            for sector in sectors:
                sector = sector.strip().upper()
                if not sector in sectors_already_processed_for_this_business:
                    sectors_already_processed_for_this_business.append(sector)
                    if sector in businesses_that_have_yet_to_be_processed_for_each_sector:
                        businesses_that_have_yet_to_be_processed_for_each_sector[sector].append(business)
                    else:
                        businesses_that_have_yet_to_be_processed_for_each_sector[sector] = [business]

        clusters = {}

        current_cluster = []

        start_time = time.time()
        
        for sector in businesses_that_have_yet_to_be_processed_for_each_sector.keys():
            print("Processing sector: "+sector)
            before = copy.copy(businesses_that_have_yet_to_be_processed_for_each_sector[sector])
            for business in before:
                if business in businesses_that_have_yet_to_be_processed_for_each_sector[sector]:
                    businesses_that_have_yet_to_be_processed_for_each_sector[sector].remove(business)
                    if business.lat == 0 or business.lon == 0:
                        continue
                    bng = business.bng
                    current_cluster = get_uncompleted_points_of_same_sector_within_radius_of_this_BNG_and_its_neighbours(bng,sector)
                    if len(current_cluster) >= MINIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER:
                        cluster_name = "Cluster "+str(len(clusters.keys()))+": "+sector
                        clusters[cluster_name] = current_cluster
                        print("Cluster of len "+str(len(current_cluster))+" pushed: "+cluster_name)
                        print("Number of as yet unclustered businesses: "+str(len(businesses_that_have_yet_to_be_processed_for_each_sector[sector])))
                        fraction_complete = 1 - (len(businesses_that_have_yet_to_be_processed_for_each_sector[sector])/len(businesses))
                        print(str(float(int(fraction_complete*10000))/100)+"% complete")
                        time_elapsed = time.time() - start_time
                        print("ETA in "+str((((1/fraction_complete) * (time_elapsed)) - time_elapsed))[:4] + " seconds")
                    current_cluster = []

        print(clusters)
        print("Coolio. But "+str(len(businesses_that_have_yet_to_be_processed_for_each_sector)) + " businesses could not be clustered. This may be due to lack of proximity to other businesses, or lack of data (do they have a latitude and longitude in the input data?)")
        print("Making convex hulls...")

        features = []
        for key in clusters.keys():
            businesses_for_hull = clusters[key]
            polygon = make_convex_hull_around_BNG_points_of_these_businesses(businesses_for_hull)
            features.append(Feature(geometry=polygon, properties={"name":str(key),
                                                                  "sector":str(key).replace(str(key).split(": ")[0]+": ",""),
                                                                  "names_of_businesses_in_cluster":get_names_for_businesses(businesses_for_hull),
                                                                  "total_number_of_businesses_in_cluster":len(businesses_for_hull)}))
    
        feature_collection = FeatureCollection(features)
        open("output.geojson",mode="w",encoding="utf-8").write(dumps(feature_collection, sort_keys=True))

def get_uncompleted_points_of_same_sector_within_radius_of_this_BNG_and_its_neighbours(src_BNG,sector):
    global RADIUS_EASTING_NORTHING_ETC, businesses, businesses_that_have_yet_to_be_processed_for_each_sector

    businesses_to_include = []

    business_BNGs_to_compare_with = [src_BNG]

    yet_to_be_processed_businesses_in_sector = businesses_that_have_yet_to_be_processed_for_each_sector[sector]

    keep_going = True

    while keep_going:
        keep_going = False
    
        to_be_removed_from_queue_at_end_of_loop = []

        for business in yet_to_be_processed_businesses_in_sector:            
            if business.lat == 0 or business.lon == 0:
                continue

            if is_within_distance_of_any_of_these_businesses(business.bng, RADIUS_EASTING_NORTHING_ETC, business_BNGs_to_compare_with):
                keep_going = True
                to_be_removed_from_queue_at_end_of_loop.append(business)
                businesses_to_include.append(business)
                business_BNGs_to_compare_with.append(business.bng)
                if len(businesses_to_include) >= MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER: #if we've hit the maximum cluster size
                    print("Max cluster size reached for this cluster")
                    keep_going = False
                    break
        
        for business in to_be_removed_from_queue_at_end_of_loop:
            yet_to_be_processed_businesses_in_sector.remove(business)

    return businesses_to_include

def is_within_distance_of_any_of_these_businesses(my_BNG, dist, business_BNGs_to_compare_with):
    for BNG in business_BNGs_to_compare_with:
        if distance.euclidean(my_BNG, BNG) <= dist:
            return True
    return False

def get_names_for_businesses(businesses_to_get_names_for):
    global businesses, name_index

    names = ""

    for business in businesses_to_get_names_for:
        if len(names) == 0:
            names += business.name
        else:
            names += "; " + business.name
          
    return names

def make_convex_hull_around_BNG_points_of_these_businesses(businesses_to_include_in_hull):
    points = []
    for business in businesses_to_include_in_hull:
        if business.lat == 0 or business.lon == 0:
            continue
        p = business.bng
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