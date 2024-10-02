import os
import csv
import time

path = "files/0_CULL_CH_CSV/input.csv"

output_path = "files/2_COMPARE/data_for_step_2.csv"

print("Loading Companies House CSV from "+path)

failed_checks = False

if os.path.isfile(output_path):
    print("The condensed version of the companies house CSV already exists, so we won't waste time re-condensing it.")
    if os.path.isfile(path):
        print("If you DO want to recondense it, delete the condensed version at "+output_path+" and run the script again.")
        print("This script will continue with the existing data for now.")
        failed_checks = True
    else:
        print("You also haven't brought a new version with you to recondense anyway! It should've been located at "+path+", but there was nothing there.")
        failed_checks = True

def getLeadingLetters(postcode):
    subsection_end = 0
    postcode = postcode.strip()
    for char in postcode:
        if char.isalpha():
            subsection_end += 1
        else:
            break
    return postcode[:subsection_end]

if not failed_checks:
    if os.path.isfile(path):

        print("Because the CSV is a national one, we're going to have to reduce it right down to a particular postcode, e.g. 'B' for Birmingham.")
        requiredPostcodePrefix = input("Please specify that letter prefix here and press enter:").upper()
        print("\nGreat, we'll chug away at it. Just remember that this is going to check every business in the country so it might take a little bit, but in my experience it shouldn't take more than two minutes for a city.")

        with open(path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            new_rows = []
            is_first_row = True
            rows_complete = 0
            index_of_postcode_column = -1
            for row in reader:
                if is_first_row:
                    headers = row
                    new_rows.append(row)
                    is_first_row = False
                    index_of_postcode_column = headers.index("RegAddress.PostCode")
                    continue
                if getLeadingLetters(row[index_of_postcode_column]) == requiredPostcodePrefix:
                    new_rows.append(row)
                    rows_complete += 1
                    print(str(rows_complete)+" suitable rows identified", end='\r')
            with open(output_path, newline='', encoding="utf-8", mode="w") as output:
                writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerows(new_rows)
    else:
        print("Couldn't find it! Aborting step 0.\n\nYou need to obtain the giant CSV from https://download.companieshouse.gov.uk/en_output.html and place it relative to this script with the following relative filename: "+path)
        print("The other steps will now attempt to take place, but may fail.")
        time.sleep(2)