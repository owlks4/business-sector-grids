import os
import geojson
import csv
from difflib import SequenceMatcher
import difflib
import requests
from urllib.parse import quote
import time
import numpy
import lzma
import json

headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}

NOMINATIM_COOLDOWN_TIME = 7
STARTING_INDEX_IN_INPUT = 0

postcode_centroids = None
postcode_centroid_keys = None

last_nominatim_request_time = 0

def make_address_from_row(row, address_column_indices):
    return ", ".join(map(lambda x : row[x], address_column_indices)) 

def binarysearch(arr, target):
    lower = 0
    upper = len(arr) - 1

    while lower < upper:
        i = int(numpy.floor((upper + lower) / 2))
        if arr[i] == target or arr[upper] == target or arr[lower] == target:
            return target
        elif target < arr[i]: # if target is below our midpoint
            upper = i   #set a new upper bound
        else:           #but if it's above
            lower = i   #set a new lower bound
        if upper - 1 == lower and not (arr[upper] == target or arr[lower] == target): # sanity check; we have converged on nothing and should break the loop
            break
    return None

def try_for_a_postcode_centroid_match(postcode):
    if not binarysearch(postcode_centroid_keys, postcode) == None:
        return postcode_centroids[postcode]
    return None

def get_string_similarity(str1, str2):
    return SequenceMatcher(None, str1, str2).ratio()
    
def get_string_similarity_2(input_string, reference_string):
#The ndiff method returns a list of strings representing the differences between the two input strings.
    diff = difflib.ndiff(input_string, reference_string)
    diff_count = 0
    for line in diff:
      # a "-", indicating that it is a deleted character from the input string.
        if line.startswith("-"):
            diff_count += 1
    # calculates the similarity by subtracting the ratio of the number of deleted characters to the length of the input string from 1
    return 1 - (diff_count / len(input_string)) 
   
def print_best_match_summary(best_scorer, original_address):
    print("From string similarity comparison with the Bham address list, we have reckoned that "+best_scorer+" was the best match for "+original_address) 
   
def query_nominatim(address):
    json = construct_and_query_nominatim_url(address)
    
    if json == None or len(json) == 0:
        # if it failed, then try again but with the address limited to begin with the house number
        time.sleep(1)    
        json = construct_and_query_nominatim_url(isolate_address_beginning_with_house_number(address))
        if json == None or len(json) == 0:    
            # if it failed again, then try again but with just the postcode

            #first naively comparing to the list (but saves us from making a nomatim query if it succeeds)
            isolated_postcode = isolate_postcode(address)
            postcode_centroid_list_entry = try_for_a_postcode_centroid_match(isolated_postcode)

            if not postcode_centroid_list_entry == None:
                return {"Latitude": postcode_centroid_list_entry[1], "Longitude": postcode_centroid_list_entry[0]}
            
            #and if that failed, via nominatim
            time.sleep(1)
            json = construct_and_query_nominatim_url(isolated_postcode)
    
    if not (json == None or len(json) == 0):
        return {"Latitude":json[0]["lat"], "Longitude":json[0]["lon"]}
    else:
        return {"Latitude":0, "Longitude":0}
   
def construct_and_query_nominatim_url(address):
    global last_nominatim_request_time, NOMINATIM_COOLDOWN_TIME
    
    time_since_last_nominatim_request = time.time() - last_nominatim_request_time
    
    if time_since_last_nominatim_request < NOMINATIM_COOLDOWN_TIME:
        print("Sleeping for "+str(NOMINATIM_COOLDOWN_TIME - time_since_last_nominatim_request)+" seconds to allow nominatim search to cool down...")
        print("By the way... we're "+str((i-1)/len(rows) * 100) + "% complete overall")
        time.sleep(NOMINATIM_COOLDOWN_TIME - time_since_last_nominatim_request)

    last_nominatim_request_time = time.time()

    x = requests.get('https://nominatim.openstreetmap.org/search.php?q='+quote(address)+'&format=jsonv2', headers=headers)
    try:
        return x.json()
    except:
        print("FAILED TO GET JSON")
        return None

def isolate_postcode(address_string):
    address_string = address_string.strip()
    pos = len(address_string) - 1
    while not address_string[pos].isnumeric():
        pos -= 1
    #at this point, we are at the number at the start of the second half of the postcode.
    end_of_postcode = pos + 3
    pos -= 2 #skip back in such a way that we are definitely before the space in the middle of the postcode
    while not address_string[pos] == " ": #now go back until we encounter the space preceding the entire postcode
        pos -= 1
    print("Used to be: "+address_string)
    address_string = address_string[pos:end_of_postcode].strip()
    print("Corrected to: "+address_string)
    return address_string

def isolate_address_beginning_with_house_number(address_string):
    address_string = address_string.strip()
    pos = len(address_string) - 1
    while not address_string[pos].isnumeric():
        pos -= 1
    #at this point, we are at the number at the start of the second half of the postcode.
    pos -= 5
    # at this point we are definitely before the postcode

    while not address_string[pos].isnumeric() and pos > 0:
        pos -= 1

    while address_string[pos].isnumeric() and pos > 0:
        pos -= 1

    print("Used to be: "+address_string)
    address_string = address_string[pos:].strip()
    print("Corrected to: "+address_string)
    return address_string

def get_full_address_from_feature(f):
    output = ""
    
    properties = f.get("properties")
    
    for_concat = [
        properties.get("addr:housename"),
        properties.get("addr:housenumber"),
        properties.get("addr:street"),
        properties.get("addr:city"),
        properties.get("addr:postcode")
    ]
       
    num_items_used = 0
    
    for item in for_concat:
        if not item == None:
            output += item + " "
            num_items_used += 1
    
    if num_items_used >= 2:
        return output.strip().upper()
    else:
        return None #no way we're matching with a feature that only has one address component

def get_closest_feature_match(row, postcode_leeway, banned_features, address_we_want_to_find):
    best_scorer = None
    best_score = 0
    
    split_postcode = row[postcode_column_index].split(" ")
    
    if not len(split_postcode) == 2:
        if len(split_postcode[0]) > 3: #if it's just a postcode without the space in the middle. Otherwise, we just take the postcode as read because we assume it's already just the first part (B1 etc.) either way, it should be ok if this misreads, because it'll fall through to either the mega feature list or to a nominatim query, and will only happen once in a blue moon anyway
            split_postcode[0] = split_postcode[0].strip()[:-3].strip()
        
    list = None
    
    if split_postcode[0].upper() in feature_dict:    
        list = feature_dict[split_postcode[0].upper()]
    
    if list == None:
        list = features # search the long list if we didn't find our postcode in the separate lists
    
    for f in list:      #compare its address to each feature in the massive Birmingham OSM
        feature_postcode = f.get("properties").get("addr:postcode")
        if feature_postcode == None:
            continue
        else:
            feature_postcode = feature_postcode.upper()
        row_postcode = row[postcode_column_index].upper()
        if not feature_postcode[0:len(feature_postcode)-postcode_leeway] == row_postcode[0:len(row_postcode)-postcode_leeway]:
            continue
        feature_full_addr = get_full_address_from_feature(f)
        if feature_full_addr == None:
            continue
        #print("Going to compare "+feature_full_addr+ " and "+address_we_want_to_find)
        score = get_string_similarity(feature_full_addr, address_we_want_to_find)
        if score > best_score and not f in banned_features:
            best_score = score
            best_scorer = f
            
    return [best_scorer, best_score]

abort = False

CH_INPUT_PATH = "files/2_COMPARE/data_for_step_2.csv"
OSM_INPUT_PATH = "files/2_COMPARE/ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson"

if os.path.isfile(OSM_INPUT_PATH+".xz") and not os.path.isfile(OSM_INPUT_PATH):
    print("Couldn't find "+OSM_INPUT_PATH+", but we did find its compressed XZ version. Decompressing...")
    interim_decompressed_input = lzma.open(OSM_INPUT_PATH+".xz", mode='rt', encoding='utf-8').read()
    print("Obtained decompressed XZ version of input. Writing...")
    open(OSM_INPUT_PATH, mode="w", encoding="utf-8").write(interim_decompressed_input)

if not os.path.isfile(OSM_INPUT_PATH):
    print(OSM_INPUT_PATH + " still didn't exist! Aborting step 2.")
    abort = True

if not abort and not os.path.isfile(CH_INPUT_PATH):
    print("\nCouldn't find "+CH_INPUT_PATH+". You should have obtained this from the companies house downloader.")
    abort = True

if not abort:
    print("Loading postcode centroids for step 2...")
    postcode_centroids = json.loads(open("files/2_COMPARE/postcode_centroids.json").read())
    postcode_centroid_keys = sorted(list(postcode_centroids.keys()))

    print("Loading the user's CSV data (obtained from companies house)")

    companies_house_data_csv = open(CH_INPUT_PATH, newline='', encoding="utf-8")
    reader = csv.reader(companies_house_data_csv, delimiter=',', quotechar='"')
    rows = []
    for row in reader:
        rows.append(row)

    company_name_column_index = rows[0].index("CompanyName")
    company_number_column_index = rows[0].index("CompanyNumber")
    address_column_indices = [
        rows[0].index('RegAddress.AddressLine1'),
        rows[0].index(' RegAddress.AddressLine2'),
        rows[0].index('RegAddress.PostTown'),
        rows[0].index('RegAddress.County'),
        rows[0].index('RegAddress.PostCode')
    ]
    postcode_column_index = rows[0].index("RegAddress.PostCode")

    if "Latitude" in rows[0] or "Longitude" in rows[0]:
        print ("\nStopped early, because the input file already had the columns we were going to add using this program. If you're sure this is the file you want to be operating on, delete those columns from the csv with an external tool like Excel, then come back.")
        exit()

    output_name = "files/2_COMPARE/output.csv"
    output = None

    start_anew = True

    ask_if_user_wants_to_use_fast_mode = True

    if os.path.isfile(output_name):
        if input("\nAn output file for step 2 already exists. Would you like to resume where you left off? (Y/N)").strip().lower() == "y":
            start_anew = False
            print("\nOk. We will resume using the file that already exists.")
            existing_output_reader = csv.reader(open(output_name, newline='', encoding="utf-8"), delimiter=',', quotechar='"')
            existing_output_rows = []
            print("Looking for resume point...\n")
            for row in existing_output_reader:
                existing_output_rows.append(row)
            most_recently_processed_existing_row = existing_output_rows[len(existing_output_rows)-1]
            for row in rows:
                if row[company_number_column_index].strip() == most_recently_processed_existing_row[company_number_column_index].strip():
                    STARTING_INDEX_IN_INPUT = rows.index(row) + 1
                    if STARTING_INDEX_IN_INPUT < 0:
                        STARTING_INDEX_IN_INPUT = 0
                    if STARTING_INDEX_IN_INPUT < len(rows) and rows[STARTING_INDEX_IN_INPUT][company_name_column_index] == "META_DATE_STRING":
                        STARTING_INDEX_IN_INPUT += 1 # if the next item after the resume point was just the meta date string, increment the starting row because we were finished anyway                        
                        ask_if_user_wants_to_use_fast_mode = False
                    else:
                        print("Resume point found. We will resume after: "+row[company_name_column_index])
                    break
        else:
            print("Ok. The existing output been deleted.")
            os.remove(output_name)

    if start_anew:
        output = open(output_name, mode="w", encoding="utf-8")
        topline = ""
        for item in rows[0]:
            topline += "\"" + item + "\","
        topline += "\"Latitude\",\"Longitude\"\n"
        output.write(topline)
        output.close()

    IS_FAST_MODE = True #must be initialised here because otherwise it won't exist in the proper scope... found this out the hard way when everything slowed to a crawl lol

    if ask_if_user_wants_to_use_fast_mode:
        print("\n* Would you like to use fast mode? *\n")
        print("Fast mode is less spatially accurate but will complete faster (the principle is that it tries to use postcode centroids whenever it can, instead of nominatim). If you intend to use this data for low resolution mosaics then it will probably be sufficient.")
        IS_FAST_MODE = True if input("Use fast mode? (Y/N)").strip().lower() == "y" else False

        if IS_FAST_MODE:
            print("\nFast mode activated.")
        else:
            print("\nRemaining in slow mode.")

    if STARTING_INDEX_IN_INPUT < len(rows):
        print("Loading addresses from OSM geojson... will take a few minutes...\n")
        print("Also, just so you know, once the processing starts in full, we will only print messages for:")
        print("* nominatim requests")
        print("* if something goes wrong")
        print("* if the index of the current item is a multiple of 1000 (just so that we get the occasional print so that you know it's working!)")

        file = open(OSM_INPUT_PATH, mode="r", encoding="utf-8")

        g = geojson.load(file)
        features = g.get("features")

        print("Generating per-postcode prefix dictionary of features (i.e. a list of features for B1, a list of features for B2... and eventually a catch-all list of unpostcoded features too. This greatly reduces the per-feature overhead, because each feature searches a drastically smaller list!")

        feature_dict = {}
    
        for f in features:
            properties = f.get("properties")
            if "addr:postcode" in properties:
                split_postcode = properties["addr:postcode"].strip().split(" ")
                if not len(split_postcode) == 2:
                    if len(split_postcode[0]) > 4: #if it can't possibly be just the front half (which we allow to stand because we're looking for front halves anyway)
                        split_postcode[0] = properties["addr:postcode"].strip()[:-3].strip()
                        print("Replaced an errant spaceless postcode with "+split_postcode[0])
                postcode_prefix = split_postcode[0].upper()
                if postcode_prefix in feature_dict:
                    feature_dict[postcode_prefix].append(f)
                else:
                    feature_dict[postcode_prefix] = [f]
                    print("Adding new feature dict for postcode prefix: "+postcode_prefix)
            else:
                if "catchall" in feature_dict:
                    feature_dict["catchall"].append(f)
                else:
                    feature_dict["catchall"] = [f]
        print("Starting...")
    else:
        print("\nIt seems that the resume point is at the end of the data anyway; step 2 should now automatically complete.")

    i = 0
    rowslen = str(len(rows) - 1)

    address_cache = {}

    for row in rows:    #for each row in the companies house data
        if i == 0:
            i += 1
            row.append("Latitude")
            row.append("Longitude")
            continue

        verbose = (i % 1000) == 0

        if i < STARTING_INDEX_IN_INPUT or row[company_name_column_index] == "META_DATE_STRING":        
            i += 1
            #print("Will not process "+row[address_column_index] + "("+str(i)+")")
            continue
            
        i += 1 # this is just the generic incrementing of i that happens each loop. The only time we actually use this variable is at the start of the loop anyway, we don't actually use it for indexing after this point. So basically don't worry about the idea of i going out of range; if it ever does, it's probably because there won't BE a next loop anyway.
        
        row[postcode_column_index] = row[postcode_column_index].replace(" ","").upper() #remove any spaces anywhere in the postcode
        row[postcode_column_index] = row[postcode_column_index][:-3] + " " +  row[postcode_column_index][-3:]

        if verbose:
            print("Postcode reprocessed into "+row[postcode_column_index] + " to hopefully make sure the space is in the right place.")

        first_letter_of_postcode = row[postcode_column_index].strip().split(" ")[0].upper().strip()[0]
        
        if (not first_letter_of_postcode == "B" and not first_letter_of_postcode.isnumeric()) or not row[postcode_column_index].strip()[1].isnumeric():
            if verbose:
                print(row[postcode_column_index] + " doesn't look like a Birmingham postcode...")
            row.append("")
            row.append("")
            continue
    
        full_addr_for_row = make_address_from_row(row, address_column_indices)

        if full_addr_for_row in address_cache:
            if verbose:
                print("Address was already in the cache! Using cached address for ")
                print(full_addr_for_row)        
            best_scorer = address_cache[full_addr_for_row]
            best_score = 1
            row.append(best_scorer.get("Latitude"))
            row.append(best_scorer.get("Longitude"))
        else:
            [best_scorer, best_score] = get_closest_feature_match(row, 0, [], full_addr_for_row)

            if best_scorer == None:
                [best_scorer, best_score] = get_closest_feature_match(row, 1, [], full_addr_for_row)
                if best_scorer == None:
                    if verbose:
                        print("Couldn't find any matches within the postcode...")
            else:
                if verbose:
                    print_best_match_summary(get_full_address_from_feature(best_scorer), full_addr_for_row)

            if best_score < 0.62:
                if verbose:
                    print("Hmmm... best score was "+str(best_score)+".")
                    print(row[postcode_column_index])       
                if IS_FAST_MODE:
                    if verbose:
                        print("Will try to use fast mode... but if we can't find the postcode in the keys of the postcode centroids object, we'll have use to nominatim...") 
                if IS_FAST_MODE and not binarysearch(postcode_centroid_keys, row[postcode_column_index]) == None:
                    if verbose:
                        print("Match found in postcode centroids list...")
                    centroid_longlat = postcode_centroids[row[postcode_column_index]]
                    latitude = centroid_longlat[1]
                    longitude = centroid_longlat[0]
                else:
                    if verbose:
                        print("Asking nominatim as a fallback...")
                    best_scorer = query_nominatim(full_addr_for_row)
                    if verbose:
                        print("Here's what we got from nominatim: "+str(latitude) +" "+str(longitude)+" for "+full_addr_for_row)
                    latitude = best_scorer.get("Latitude")
                    longitude = best_scorer.get("Longitude")
                    if verbose:
                        print(best_scorer)           
                row.append(latitude)
                row.append(longitude)
                address_cache[full_addr_for_row] = {"Latitude":latitude, "Longitude":longitude}
            else:                  # then we got it from the geojson, so process accordingly... we're collapsing building vertices into one pair of coordinates btw
                if verbose:
                    print("Good string match score! Score was:"+str(best_score))
                latitude = 0
                longitude = 0
                count = 0
                coords = best_scorer.get("geometry").get("coordinates") # Okay, these stacked for loops are a self-confessed abomination... but most of the time it'll only go down two iterations or so, which is probably more acceptable. The only reason it has so many extra levels is to deal with any weirdly complex edge-case polygons. But I didn't feel it was worth changing the overall technique just for that.
                if isinstance(coords[0], list): # then there's a nested list
                    for L1 in coords:
                        if isinstance(L1[0], list): #then each item in L is ANOTHER list
                            for L2 in L1:
                                if isinstance(L2[0], list): #then each item in L is ANOTHER list
                                    for L3 in L2:
                                        if isinstance(L3[0], list): #then each item in L is ANOTHER list
                                            for L4 in L3:
                                                if isinstance(L4[0], list): #then each item in L is ANOTHER list
                                                    for L5 in L4:
                                                        if isinstance(L5[0], list): #then each item in L is ANOTHER list
                                                            for L6 in L5:
                                                                if isinstance(L6[0], list): #then each item in L is ANOTHER list
                                                                    for L7 in L6:
                                                                        if isinstance(L7[0], list): #then each item in L is ANOTHER list
                                                                            print("EIGHT STACKED LISTS??????? AWGHHHHH")
                                                                        else: #then each item in L is a coordinate pair
                                                                            longitude += L7[0] #[sic]
                                                                            latitude += L7[1] #[sic]
                                                                            count += 1
                                                                else: #then each item in L is a coordinate pair
                                                                    longitude += L6[0] #[sic]
                                                                    latitude += L6[1] #[sic]
                                                                    count += 1
                                                        else: #then each item in L is a coordinate pair
                                                            longitude += L5[0] #[sic]
                                                            latitude += L5[1] #[sic]
                                                            count += 1
                                                else: #then each item in L is a coordinate pair
                                                    longitude += L4[0] #[sic]
                                                    latitude += L4[1] #[sic]
                                                    count += 1
                                        else: #then each item in L is a coordinate pair
                                            longitude += L3[0] #[sic]
                                            latitude += L3[1] #[sic]
                                            count += 1
                                else: #then each item in L is a coordinate pair
                                    longitude += L2[0] #[sic]
                                    latitude += L2[1] #[sic]
                                    count += 1
                        else: #then each item in L is a coordinate pair
                            longitude += L1[0] #[sic]
                            latitude += L1[1] #[sic]
                            count += 1
                else: #then it's just a point and only consists of coordinates (great!)
                    longitude = coords[0] #[sic]
                    latitude = coords[1] #[sic]
                    count = 1
                
                latitude /= count
                longitude /= count

                row.append(latitude)
                row.append(longitude)
                
                address_cache[full_addr_for_row] = {"Latitude":latitude, "Longitude":longitude}
        
        if verbose:
            print("Row "+str(i-1)+" of "+rowslen+" complete")
            print(str((i-1)/len(rows) * 100) + "% complete overall")

        output = open(output_name, mode="a", encoding="utf-8")

        for row_item_index in range(len(row)):
            row[row_item_index] = "\"" + str(row[row_item_index]).replace("\"","").replace(",","") + "\""

        s = (",".join(row)) + "\n"

        output.write(s)
        output.close()

    if os.path.isfile("files/2_COMPARE/timestamp.txt"):
        os.remove("files/2_COMPARE/timestamp.txt")

    timestamp_from_CH_data = "Timestamp did not process correctly"

    for row in rows:
        if row[company_name_column_index] == "META_DATE_STRING":
            timestamp_from_CH_data = " ".join(row[company_number_column_index].split(" ")[0:4])
            break

    open("files/2_COMPARE/timestamp.txt", mode="w", encoding="utf-8").write(timestamp_from_CH_data)

    print("Step 2 complete.")