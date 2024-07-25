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

headers={"User-Agent": "Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"}

NOMINATIM_COOLDOWN_TIME = 7
STARTING_INDEX_IN_INPUT = 0


last_nominatim_request_time = 0
postcode_centroid_keys = sorted(list(postcode_centroids.keys()))

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
    while not address_string[pos] == " ":
        pos -= 1
    if address_string[pos - 1].isnumeric(): #if the previous char to this one is numeric, it means we're only halfway through the postcode, so keep going back until we hit the next space
        pos -= 1
        while not address_string[pos] == " ":
            pos -= 1
    print("Used to be: "+address_string)
    address_string = address_string[pos:].strip()
    print("Corrected to: "+address_string)
    return address_string

def isolate_address_beginning_with_house_number(address_string):
    address_string = address_string.strip()
    pos = len(address_string) - 1
    while not address_string[pos] == " ":
        pos -= 1
    if address_string[pos - 1].isnumeric(): #if the previous char to this one is numeric, it means we're only halfway through the postcode, so keep going back until we hit the next space
        pos -= 1
        while not address_string[pos] == " ":
            pos -= 1
    # at this point we are at the beginning of the postcode, so go continue going back until we hit a number, and then until we hit something that isn't a number. At that point we will be at the beginning of the house number, if there is one.

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
        return output.strip()
    else:
        return None #no way we're matching with a feature that only has one address component

def get_closest_feature_match(row, postcode_leeway, banned_features):
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
    
    address_we_want_to_find = row[address_column_index]
    
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

CH_INPUT_PATH = "files/2_COMPARE/input.csv"
OSM_INPUT_PATH = "files/2_COMPARE/ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson"

if os.path.isfile(OSM_INPUT_PATH+".xz") and not os.path.isfile(OSM_INPUT_PATH):
    print("Couldn't find "+OSM_INPUT_PATH+", but we did find its compressed XZ version. Decompressing...")
    interim_decompressed_input = lzma.open(OSM_INPUT_PATH+".xz", mode='rt', encoding='utf-8').read()
    print("Obtained decompressed XZ version of input. Writing...")
    open(OSM_INPUT_PATH, mode="w", encoding="utf-8").write(interim_decompressed_input)

if not os.path.isfile(OSM_INPUT_PATH):
    print(OSM_INPUT_PATH + " still didn't exist! Aborting step 2.")
    abort = True

if not os.path.isfile(CH_INPUT_PATH):
    print("Couldn't find "+CH_INPUT_PATH+". You should have obtained this from the companies house downloader.")
    abort = True

if not abort:
    print("Loading the user's CSV data (obtained from companies house)")

    companies_house_data_csv = open(CH_INPUT_PATH, newline='', encoding="utf-8")
    reader = csv.reader(companies_house_data_csv, delimiter=',', quotechar='"')
    rows = []
    for row in reader:
        rows.append(row)

    address_column_index = rows[0].index("registered_office_address")
    postcode_column_index = rows[0].index("postcode")

    if "Latitude" in rows[0] or "Longitude" in rows[0]:
        print ("\nStopped early, because the input file already had the columns we were going to add using this program. If you're sure this is the file you want to be operating on, delete those columns from the csv with an external tool like Excel, then come back.")
        exit()

    output_name = "files/2_COMPARE/output_from_session_beginning_"+str(time.time())+".csv"
    output = open(output_name, mode="w", encoding="utf-8")

    topline = ""
    for item in rows[0]:
        topline += "\"" + item + "\","
    topline += "\"Latitude\",\"Longitude\"\n"

    output.write(topline)
    output.close()

    print("* Would you like to use fast mode? *")
    print("Fast mode is less accurate (the principle is that, when possible, it falls back on postcode centroids instead of nominatim) but will complete faster. If you intend to use this data for low resolution mosaics then it will probably be sufficient.")
    IS_FAST_MODE = True if input("Use fast mode? (Y/N)").strip().lower() == "y" else False

    if IS_FAST_MODE:
        print("Fast mode activated.")
    else:
        print("Remaining in slow mode.")

    print("Loading addresses from OSM geojson... will take a few minutes...")
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

    i = 0
    rowslen = str(len(rows) - 1)

    address_cache = {}

    for row in rows:    #for each row in the companies house data
        if i == 0:
            i += 1
            row.append("Latitude")
            row.append("Longitude")
            print("Starting...")
            continue

        verbose = (i % 1000) == 0

        if i < STARTING_INDEX_IN_INPUT:        
            i += 1
            #print("Will not process "+row[address_column_index] + "("+str(i)+")")
            continue
            
        i += 1
        
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
        
        if row[address_column_index] in address_cache:
            if verbose:
                print("Address was already in the cache! Using cached address for ")
                print(row[address_column_index])        
            best_scorer = address_cache[row[address_column_index]]
            best_score = 1
            row.append(best_scorer.get("Latitude"))
            row.append(best_scorer.get("Longitude"))
        else:
            [best_scorer, best_score] = get_closest_feature_match(row, 0, [])

            if best_scorer == None:
                [best_scorer, best_score] = get_closest_feature_match(row, 1, [])
                if best_scorer == None:
                    if verbose:
                        print("Couldn't find any matches within the postcode...")
            else:
                if verbose:
                    print_best_match_summary(get_full_address_from_feature(best_scorer), row[address_column_index])

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
                    best_scorer = query_nominatim(row[address_column_index])
                    if verbose:
                        print("Here's what we got from nominatim: "+str(latitude) +" "+str(longitude)+" for "+row[address_column_index])
                    latitude = best_scorer.get("Latitude")
                    longitude = best_scorer.get("Longitude")
                    if verbose:
                        print(best_scorer)           
                row.append(latitude)
                row.append(longitude)
                address_cache[row[address_column_index]] = {"Latitude":latitude, "Longitude":longitude}
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
                
                address_cache[row[address_column_index]] = {"Latitude":latitude, "Longitude":longitude}
        
        if verbose:
            print("Row "+str(i-1)+" of "+rowslen+" complete")
            print(str((i-1)/len(rows) * 100) + "% complete overall")

        output = open(output_name, mode="a", encoding="utf-8")
        s = ""

        for item in row:
            item_str_without_any_quotes = str(item).replace("\"","").replace(",","")
            s += "\"" + str(item) + "\","

        s += "\n"
        output.write(s)
        output.close()

            #user_response = ""
            #already_rejected_features = []
            #while not user_response.upper() == "Y":
            #   while not (user_response.upper() == "Y" or user_response.upper() == "N"):
            #       user_response = input("Respond by pressing 'Y' or 'N'")
            #   if not user_response.upper() == "Y":
            #       user_response = ""
            #       already_rejected_features.append(best_scorer)
            #       [best_scorer, best_score] = get_closest_feature_match(row, 0.7, already_rejected_features)
            #       print("How about this one?")
            #       print_best_match_summary(get_full_address_from_feature(best_scorer), row[address_column_index])       