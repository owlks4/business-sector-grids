import time
import csv
from scipy.spatial import distance, ConvexHull
from geojson import Polygon, Feature, FeatureCollection, dumps
from bng_latlon import WGS84toOSGB36
import copy
from enum import Enum

RADIUS_EASTING_NORTHING_ETC = 150 #METRES??? I GUESS???
MINIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 20
MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER = 120

class DistanceComparisonResult(Enum):
    FAIL = 0
    HONOURABLE_MENTION = 1
    SUCCESS = 2

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
            self.bng = (0,0)
        else:
            self.lat = float(row[lat_index])
            self.lon = float(row[lon_index])
            self.bng = WGS84toOSGB36(self.lat, self.lon)

        self.sectors = row[sector_index]

def process():
    global businesses, name_index, lat_index, lon_index, sector_index, businesses_that_have_yet_to_be_processed_for_each_sector

    print("Starting step 5.")

    with open('files/2_COMPARE/output.csv', newline='', encoding="utf-8") as csvfile: #yes, we're still operating on the output of step 2, which has also been modified by step 3 in the meantime - this is intentional.
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')

        rows = []

        for row in reader:
            rows.append(row)

        headers = rows[0]
        name_index = headers.index("company_name")
        lat_index = headers.index("Latitude")
        lon_index = headers.index("Longitude")
        sector_index = headers.index("broad_industry")

        print("Setting up...")

        for i in range(len(rows)):
            if i == 0:
                continue
            businesses.append(Business(rows[i]))

        print("Performing preliminary array sort by Latitude (this will make clustering much, much faster)...")

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

        for sector in businesses_that_have_yet_to_be_processed_for_each_sector.keys():
            businesses_that_have_yet_to_be_processed_for_each_sector[sector].sort(key = lambda business : business.lat)

        clusters = {}

        current_cluster = []

        start_time = time.time()
        
        for sector in businesses_that_have_yet_to_be_processed_for_each_sector.keys():
            print("Processing sector: "+sector)
            before = copy.copy(businesses_that_have_yet_to_be_processed_for_each_sector[sector])
            for business in before:
                if business in businesses_that_have_yet_to_be_processed_for_each_sector[sector]:
                    if business.lat == 0 or business.lon == 0:
                        continue
                    current_cluster = get_uncompleted_points_of_same_sector_within_radius_of_this_business_and_its_neighbours(business, sector)
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
        open("files/5_BUSINESS_CLUSTER_FINDER/business_clusters.geojson",mode="w",encoding="utf-8").write(dumps(feature_collection, sort_keys=True))

def get_uncompleted_points_of_same_sector_within_radius_of_this_business_and_its_neighbours(src_business,sector):
    global RADIUS_EASTING_NORTHING_ETC, businesses, businesses_that_have_yet_to_be_processed_for_each_sector

    businesses_to_include = [src_business]

    yet_to_be_processed_businesses_in_sector = businesses_that_have_yet_to_be_processed_for_each_sector[sector]

    keep_going = True

    current_array_dist_away_from_original_position = 0 #immediately becomes 1 when incremented at the start of the first loop, so we never see the 0 value - as intended.

    start_index = yet_to_be_processed_businesses_in_sector.index(src_business)

    while keep_going:
        keep_going = False

        current_array_dist_away_from_original_position += 1
        
        for i in range(2):
            match (i):
                case 0:
                    current_search_position = start_index + current_array_dist_away_from_original_position
                case 1:
                    current_search_position = start_index - current_array_dist_away_from_original_position
            
            if current_search_position < 0 or current_search_position >= len(yet_to_be_processed_businesses_in_sector):
                continue

            business = yet_to_be_processed_businesses_in_sector[current_search_position]

            if business in businesses_to_include or business.lat == 0 or business.lon == 0:
                continue
            
            result_of_distance_check = is_within_distance_of_any_of_these_businesses(business, RADIUS_EASTING_NORTHING_ETC, businesses_to_include)

            if not result_of_distance_check == DistanceComparisonResult.FAIL: 
                keep_going = True #so that we get told to keep going, even if it's an honourable mention (only lat within the specified distance, lon could be anything). This means it evaluates a big vertical zone in the data with an infinite north-south dimension, like the centre gap that forms during the opening of some curtains, and means that rogue businesses with longitudes way out of range won't stop the search dead just because they had latitudes that were closer in the array to the source business than actual valid businesses within the radius that simply have a slightly bigger latitude difference.
                if result_of_distance_check == DistanceComparisonResult.SUCCESS:
                    businesses_to_include.append(business)
                    if len(businesses_to_include) >= MAXIMUM_NUMBER_OF_BUSINESSES_IN_CLUSTER: #if we've hit the maximum cluster size
                        print("Max cluster size reached for this cluster")
                        keep_going = False
                        break

    for business in businesses_to_include:
        businesses_that_have_yet_to_be_processed_for_each_sector[sector].remove(business)

    return businesses_to_include

def is_within_distance_of_any_of_these_businesses(my_business, dist, businesses_to_compare_BNGs_with):

    could_be_honourable_mention = False

    for other_business in businesses_to_compare_BNGs_with:
        if distance.euclidean(my_business.bng, other_business.bng) <= dist:
            return DistanceComparisonResult.SUCCESS
        if abs(other_business.bng[1] - my_business.bng[1]) <= dist: #if northing (so latitude) is within range even when easting isn't, give a half-success, otherwise one rogue faraway longitude will stop the search dead, even when there are actual valid longitudes behind it that haven't come up yet due to latitude being the sort key (and no, using two sort keys isn't the solution, I tried that already.)
            could_be_honourable_mention = True
    
    if could_be_honourable_mention:
        return DistanceComparisonResult.HONOURABLE_MENTION
    else:
        return DistanceComparisonResult.FAIL

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
        is_a_dupe_of_an_existing_point = False
        for existing_p in points:
            if existing_p.bng[0] == business.bng[0] or existing_p.bng[1] == business.bng[1]:
                is_a_dupe_of_an_existing_point = True
                break
        if not is_a_dupe_of_an_existing_point:
            points.append(business)

    for i in range(len(points)):
        points[i] = (points[i].lat, points[i].lon)

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