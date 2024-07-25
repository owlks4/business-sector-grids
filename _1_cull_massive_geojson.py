import os
import geojson
import lzma

#culls the massive Birmingham OSM geojson to only features with at least one address property

INPUT_PATH = "files/1_PREPROCESS/Birmingham.osm.geojson"
OUTPUT_PATH = "files/2_COMPARE/ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson"

abort = False

if os.path.isfile(OUTPUT_PATH) or os.path.isfile(OUTPUT_PATH+".xz"):
	print("Step 1 will not take place because the output we require is already present (either as xz or uncompressed) in the 2_COMPARE directory. If you really want to reconstruct it for whatever reason, go and delete that file in the 2_COMPARE directory first ("+OUTPUT_PATH+"(.xz))")
	abort = True
elif not os.path.isfile(INPUT_PATH):
	print("Input was not available for step 1 at "+INPUT_PATH+". Could it be that you haven't yet decompressed that file from its .xz form?")
	if os.path.isfile(INPUT_PATH+".xz"):
		print("Looking for XZ version...")
		interim_decompressed_input = lzma.open(INPUT_PATH+".xz", mode='rt', encoding='utf-8').read()
		print("Obtained decompressed XZ version. Writing...")
		open(INPUT_PATH, mode="w", encoding="utf-8").write(interim_decompressed_input)
	else:
		print("Even after looking for the xz version, we still couldn't find it! Aborting step 1.")
		print("This seems like a pretty bad error. The file in question should be obtained from openstreetmap's OSM resources - the OSM file provided by them that encompasses Birmingham.")
		abort = True

if not abort:
	print("Commencing step 1; loading giant file as json object... this will take ages... but probably less than 10 minutes...")

	file = open(INPUT_PATH, mode="r", encoding="utf-8")

	print("Loading giant geojson...")
	g = geojson.load(file)

	preserve_these_features = []

	features = g.get("features")

	i = 0
	featuresLen = str(len(features))

	print("Analysing features and preserving the features that have address data:")

	for f in features:
		if i % 5000 == 0 and not i == 0:
			print("Multiple-of-5000 check-in: assessing feature "+str(i)+" of "+featuresLen)
		i += 1
		properties = f.get("properties")
		if not properties == None:
			for p in properties:
				p_str = str(p)
				if "addr:" in p_str:
					#print("Preserving this feature, because it had at least the following property: "+p_str)
					preserve_these_features.append(f)
					break

	g = geojson.FeatureCollection(preserve_these_features)

	print("Dumping to geojson string...")

	output_string = geojson.dumps(g)

	if os.path.exists(OUTPUT_PATH):
		os.remove(OUTPUT_PATH)
	if os.path.exists(OUTPUT_PATH+".xz"):
		os.remove(OUTPUT_PATH+".xz")
		
	open(OUTPUT_PATH, mode="w", encoding="utf-8").write(output_string) #write the output
	print("Creating compressed version")
	open(OUTPUT_PATH+".xz", mode="wb").write(lzma.compress(output_string.encode("utf-8"), format=lzma.FORMAT_XZ)) #and also write the compressed version of the output, which is NOT gitignored, and thus can be preserved
	print("Step 1 complete")