import os
import geojson

print("Loading giant file as json object... this will take ages... but probably less than 10 minutes...")

file = open("Birmingham.osm.geojson", mode="r", encoding="utf-8")

g = geojson.load(file)

preserve_these_features = []

features = g.get("features")

i = 0
featuresLen = str(len(features))

for f in features:
	print("assessing feature "+str(i)+" of "+featuresLen)
	i += 1
	properties = f.get("properties")
	if not properties == None:
		for p in properties:
			p_str = str(p)
			if "addr:" in p_str:
				print("Preserving this feature, because it had at least the following property: "+p_str)
				preserve_these_features.append(f)
				break

g = geojson.FeatureCollection(preserve_these_features)

output_string = geojson.dumps(g)

if os.path.exists("ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson"):
    os.remove("ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson")
  
open("ONLY_THE_FEATURES_THAT_HAVE_ADDRESSES.geojson", mode="w", encoding="utf-8").write(output_string)