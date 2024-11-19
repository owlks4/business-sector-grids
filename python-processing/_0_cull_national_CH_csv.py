import os
import csv
import time
from datetime import datetime

path = "files/0_CULL_CH_CSV/input.csv"

output_path = "files/2_COMPARE/data_for_step_2.csv"

print("Loading Companies House CSV from "+path)

BUSINESSES_MUST_BE_ACTIVE = True

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

        print("Because the CSV is a national one, we're going to have to reduce it right down to a particular postcode, e.g. 'B' for Birmingham. You can also put 'B2' if you only want postcodes such as B25, B26, B27. Reducing the scope like this is extremely useful because it will massively cut down on processing time later on.")
        requiredPostcodePrefix = input("Please specify that letter prefix here and press enter:").upper()
        print("\nGreat, we'll chug away at it. Just remember that this is going to check every business in the country so it might take a little bit, but in my experience this step shouldn't take more than two minutes.")

        with open(path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            new_headers = ["CompanyName","CompanyNumber","RegAddress.CareOf","RegAddress.POBox","RegAddress.AddressLine1","RegAddress.AddressLine2","RegAddress.PostTown",
                           "RegAddress.County","RegAddress.Country","RegAddress.PostCode","CompanyCategory","CompanyStatus","DissolutionDate","IncorporationDate",
                           "SICCode.SicText_1","SICCode.SicText_2","SICCode.SicText_3","SICCode.SicText_4"]
            indices_of_columns_to_preserve = []
            new_rows = []
            is_first_row = True
            rows_complete = 0
            index_of_postcode_column = -1
            index_of_company_status = -1

            def char_following_prefix_is_numeric_or_a_space(row):
                c = row[index_of_postcode_column][len(requiredPostcodePrefix)]
                if c == " " or c.isnumeric():
                    return True
                return False
            
            for row in reader:
                if is_first_row:
                    for i in range(len(row)):
                        row[i] = row[i].strip().replace("\"","").replace(",","")
                    headers = row
                    for new_col_header in new_headers:
                        indices_of_columns_to_preserve.append(headers.index(new_col_header))
                    new_rows.append(new_headers)
                    is_first_row = False
                    index_of_postcode_column = headers.index("RegAddress.PostCode")
                    index_of_company_status = headers.index("CompanyStatus")
                    index_of_company_category = headers.index("CompanyCategory")
                    continue
                if row[index_of_postcode_column].startswith(requiredPostcodePrefix) and char_following_prefix_is_numeric_or_a_space(row) and not row[index_of_company_category] == "Overseas Entity" and (not BUSINESSES_MUST_BE_ACTIVE or "Active" in row[index_of_company_status]):
                    new_row = []
                    for i in range(len(row)):
                        if i in indices_of_columns_to_preserve:
                            new_row.append(row[i].strip().replace("\"","").replace(",",""))
                    new_rows.append(new_row)
                    rows_complete += 1
                    print(str(rows_complete)+" suitable rows identified", end='\r')
            new_rows.sort(key = lambda x : "0" if x[0] == "CompanyName" else x[index_of_postcode_column]) #sort by postcode, with a hack to keep the header row at the top
            with open(output_path, newline='', encoding="utf-8", mode="w") as output:
                writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerows(new_rows)
            if os.path.isfile("files/2_COMPARE/timestamp.txt"):
                os.remove("files/2_COMPARE/timestamp.txt")
            timestamp = open("files/2_COMPARE/timestamp.txt", encoding="utf-8", mode="w")
            date = datetime.now().strftime("%m/%d/%Y")
            print("\n")
            print(date)
            timestamp.write(date)
            timestamp.close()
    else:
        print("Couldn't find it! Aborting step 0.\n\nYou need to obtain the giant CSV from https://download.companieshouse.gov.uk/en_output.html and place it relative to this script with the following relative filename: "+path)
        print("The other steps will now attempt to take place, but may fail.")
        time.sleep(2)
print("\n")