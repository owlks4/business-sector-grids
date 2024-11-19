import './style.css'
import "leaflet/dist/leaflet.css"
import 'leaflet'
import "leaflet-providers";
import Color from "colorjs.io/dist/color.js";
import grid_250 from "./BusinessSectorGrids/output_grid_with_interval_250.geojson?url"
import grid_500 from "./BusinessSectorGrids/output_grid_with_interval_500.geojson?url"
import grid_1000 from "./BusinessSectorGrids/output_grid_with_interval_1000.geojson?url"
//import grid_scratchpad from "./BusinessSectorGrids/olivers_scratchpad.geojson?url"

var map = L.map('map').setView([52.4625,-1.6], 11);
let currentBasemapTileLayer = null;

let cached = {};

let PRESENT_DATE = null;
let DEFAULT_YEAR = null;

let currentViewingYear = DEFAULT_YEAR;

//document.getElementById("basemap-selector").onchange = (e) => {switchToBasemap(e.target.value)};

switchToBasemap("OpenStreetMap.Mapnik")
//L.tileLayer.provider("OpenStreetMap.Mapnik").addTo(map);
map.setMinZoom(10)

function switchToBasemap(key){
    if (currentBasemapTileLayer != null){
        map.removeLayer(currentBasemapTileLayer);
    }
    currentBasemapTileLayer = L.tileLayer.provider(key).addTo(map);
}

function getColumnValueForBusiness(business, columnName){
    return business[business_info_row_headers.indexOf(columnName)];
}

function findChildElementWithIdRecursive(node, idToFind){
    if (node.id == idToFind){
        return node;
    }
    for (let i = 0; i < node.children.length; i++){
        let result = findChildElementWithIdRecursive(node.children[i], idToFind)
        if (result != null){
            return result;
        }
    }
    return null;
}

let MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

function fractionalYearToYearAndMonth(fractionalYear){
    let year = Math.floor(fractionalYear);
    let fractionalMonth = fractionalYear - year;
    return MONTHS[Math.floor(fractionalMonth * 12)] + " " + year;
}

let TimeRange = L.Control.extend({ 
    _container: null,
    options: {position: 'bottomleft', },

    onAdd: function (map) {
        var div = L.DomUtil.create('div');
        this._div = div;
        div.appendChild(document.getElementById("time-range-template").content.cloneNode(true))
        this.currentTimeLabel = findChildElementWithIdRecursive(div,"time-range-current-label");
        this.range = findChildElementWithIdRecursive(div,"time-range-slider")
        this.desc = findChildElementWithIdRecursive(div,"time-range-description")
        this.range.oninput = (e) => {
            currentViewingYear = e.target.value;
            this.currentTimeLabel.innerText = fractionalYearToYearAndMonth(currentViewingYear);
            changeSelectedSectorTo(sectorSelector.value);
        };
        L.DomEvent.disableClickPropagation(this._div);
        L.DomEvent.disableScrollPropagation(this._div);
        return this._div;
    },

    updateMaxYear: function (newMaxYear){
        if (this._div == null){
            return;
        }
        this.range.setAttribute("max",newMaxYear);
        this.range.value = currentViewingYear;
        findChildElementWithIdRecursive(this._div,"time-range-start-label").innerText = "Min: "+fractionalYearToYearAndMonth(this.range.min);
        this.currentTimeLabel.innerText = fractionalYearToYearAndMonth(this.range.value);
        findChildElementWithIdRecursive(this._div,"time-range-end-label").innerText = "Max: "+fractionalYearToYearAndMonth(this.range.max);
        changeSelectedSectorTo(sectorSelector.value);
    },

    updateDesc: function (){
        if (this._div == null){
            return;
        }
        this.desc.innerHTML = "Showing "+sectors_all[sectorSelector.value]+" businesses<br>that were active at timeslice:";
    }
  });

let timeRange = new TimeRange();
//timeRange.addTo(map);

let gridSelector = document.getElementById("grid-selector");
let sectorSelector = document.getElementById("sector-selector");

document.getElementById("grid-from-file-button").onclick = () => {
    let upload = document.createElement("input");
    upload.setAttribute("type","file");
    upload.setAttribute("accept",".geojson");
    upload.onchange = (e) => {
        let reader = new FileReader();
        let files = e.target.files;
        for (let i = 0; i < files.length; i++){            
            reader.onload = function() {
                let name = files[i].name;
                cached[name] = JSON.parse(reader.result);
                streamlineSectorsString(cached[name])
                let newOption = document.createElement("option");
                newOption.innerText = name;
                newOption.value = name;
                gridSelector.appendChild(newOption);
            };
            reader.readAsText(files[i]);
        }
    };
    upload.click();
};

document.getElementById("download-current-sector-in-red-box-region").onclick = () => {
    let data = prepareData(true);
    downloadAsFile(data.trim(), "text/plain", "businesses.csv");
}

document.getElementById("download-all-in-red-box-region").onclick = () => {
    let data = prepareData(false);
    downloadAsFile(data.trim(), "text/plain", "businesses.csv");
}

function prepareData(matchSector) {
    
    let csv = "";

    let headerAliases = {
        "CompanyName":"Name",
        "CompanyNumber":"Company Number",
        "CompanyStatus":"Status",
        "CompanyCategory":"Type",
        "RegAddress.CareOf":"Address", //RegAddress.CareOf is actually a placeholder and we handle the address construction later in the function
        "RegAddress.PostCode":"Postcode",
        "sector":"Sector",
        "industry":"Nature of business",
        "Latitude":"Rough latitude",
        "Longitude":"Rough longitude",
        "IncorporationDate":"Incorporation date",
        "DissolutionDate":"Dissolution date",
        //"nature_of_business":"SIC codes",        
    };

    let headerAliasKeys = Object.keys(headerAliases); //this is to make sure we always read the keys in a consistent order

    headerAliasKeys.forEach((colHeader, index) => {
        csv += headerAliases[colHeader];
        
        if (index < headerAliasKeys.length - 1){
            csv += ",";
        }
    });
    csv += "\n";

    businesses_all.forEach((business, bIndex) => {
        
        let lat = parseFloat(getColumnValueForBusiness(business, "Latitude"));
        let lon = parseFloat(getColumnValueForBusiness(business, "Longitude"));

        if (lat < rangeBounds[0].lat || lat > rangeBounds[1].lat || lon > rangeBounds[0].lng || lon < rangeBounds[1].lng){
            return;
        }
        
        if (matchSector){
            let sectorIndicesForBusiness = getColumnValueForBusiness(business, "sector");
            let passes = false;
            let compareTo = sectors_all[sectorSelector.value].trim().toUpperCase();
            for (let i = 0; i < sectorIndicesForBusiness.length; i++){
                if (sectorIndicesForBusiness[i] == ""){
                    continue;
                }
                let testValue = sectors_all[parseInt(sectorIndicesForBusiness[i].trim())].toUpperCase();

                if (testValue == compareTo){
                    passes = true;
                    break;
                }
            }
            if (!passes){
                return;
            }
        }

        let address = getColumnValueForBusiness(business,"RegAddress.CareOf").trim();
        address += " "+getColumnValueForBusiness(business,"RegAddress.POBox").trim();
        address += " "+getColumnValueForBusiness(business,"RegAddress.AddressLine1").trim();
        address += " "+getColumnValueForBusiness(business,"RegAddress.AddressLine2").trim();
        address += " "+getColumnValueForBusiness(business,"RegAddress.PostTown").trim();
    
        headerAliasKeys.forEach((colHeader, index) => {
            let contentsForCell = getColumnValueForBusiness(business,colHeader);
            switch(colHeader){
                case "CompanyNumber":
                    contentsForCell = contentsForCell.padStart(8, '0');
                break;
                case "RegAddress.CareOf":
                    contentsForCell = address;
                break;
                case "sector":
                    if (contentsForCell != null){
                        contentsForCell = contentsForCell.map((sectorIndex)=>{return sectors_all[parseInt(sectorIndex)]}).join("; ");
                    }
                break;
                case "industry":
                    if (contentsForCell != null){
                        contentsForCell = contentsForCell.map((industryIndex)=>{return industries_all[parseInt(industryIndex)]}).join("; ");
                    }
                break;
            }
            if (contentsForCell == null){
                contentsForCell = "";
            }
            csv += "\"" + contentsForCell.replace(",","").replace("\"","") + "\"";
            if (index < headerAliasKeys.length - 1){
                csv += ",";
            }
        });
        csv += "\n";
    })

   return csv
};

function downloadAsFile(data, type, name) {
    let blob = new Blob([data], {type});
    let url = window.URL.createObjectURL(blob);
    let anchor = document.createElement("a");
    anchor.download = name;
    anchor.href = url;
    anchor.click();
    window.URL.revokeObjectURL(url);
}

let currentGeoJsonFeature = null;
let hasCompletedFirstTimeSetup = false;

let selectedSquare = null;

let businesses_all = null;
let sectors_all = null;
let industries_all = null;

let business_info_row_headers = ["CompanyName", "CompanyNumber", "RegAddress.CareOf", "RegAddress.POBox", "RegAddress.AddressLine1", "RegAddress.AddressLine2", "RegAddress.PostTown", "RegAddress.County", "RegAddress.Country", "RegAddress.PostCode", "CompanyCategory", "CompanyStatus", "DissolutionDate", "IncorporationDate", "SICCode.SicText_1", "SICCode.SicText_2", "SICCode.SicText_3", "SICCode.SicText_4", "Latitude", "Longitude", "sector", "industry"];
//^ is overridden by imported geojson, if the geojson contains its own examples.

const LOW_COLOUR = new Color("#00204c");
const HIGH_COLOUR = new Color("#ffe945");

let currentPin = null;

function makeRangeCornerMarkerAt(latlong, cornerIndex){

    let marker = new L.Marker(latlong,{
        icon: new L.DivIcon({className: "circle-div", iconSize:17}),
        draggable: true
    }).addTo(map);

    (marker.getElement()).onmouseup = () => {changeSelectedSectorTo(sectorSelector.value);};

    marker.cornerIndex = cornerIndex;

    marker.on("drag", function(e) {
        var position = this.getLatLng();
        if (marker.cornerIndex == 0){
            rangeBounds[0] = position;
        } else if (marker.cornerIndex == 1){
            rangeBounds[1] = position;
        }
        rangePolygon.remove();
        rangePolygon = getRangePolygonFromBounds().addTo(map);
        
    });

    return marker;
}

function streamlineSectorsString(json){
    let sectors_index_in_row = json.properties.row_headers.indexOf("sector");
    let industries_index_in_row = json.properties.row_headers.indexOf("industry");
    json.properties.businesses_all.forEach(business => {
        business[sectors_index_in_row] = business[sectors_index_in_row].trim(" ").trim(";").split(";");
        business[industries_index_in_row] = business[industries_index_in_row].trim(" ").trim(";").split(";");
    })
}

function getRangePolygonFromBounds(){
    return L.rectangle(rangeBounds, {color: "#ff0000", weight: 3, fillColor:"transparent", interactive:false});
}
let rangeBounds = [new L.LatLng(52.448583332530795, -1.8199856452665157), new L.LatLng(52.46712385493207, -1.860969796670761)];
let rangePolygon = getRangePolygonFromBounds().addTo(map);
let rangeTLCorner = makeRangeCornerMarkerAt(rangeBounds[0], 0)
let rangeBRCorner = makeRangeCornerMarkerAt(rangeBounds[1], 1)

function getColourSteppedBetweenValues(val, lowest, highest, low_colour, high_colour){
    let step = (val - lowest) / (highest - lowest);
    let interpolatedColour = null;

    interpolatedColour = low_colour.range(high_colour, {
        space: "lab", // interpolation space
        outputSpace: "srgb"
    });

    return interpolatedColour(step);
}

function makeClickableListOfBusinessesInThisSquare(gridSquareFeature, requiredSectorId){
    let div = document.createElement("div");
    div.style = "max-height:20em;"; 
    
    let ul = document.createElement("ul");
    ul.style = "font-size:0.9em; padding-left: 20px; padding-top:5px; padding-bottom:5px;"

    let count_active = 0;

    let listElements = []

    let curRangeTime = Date.UTC(Math.floor(currentViewingYear), (currentViewingYear-Math.floor(currentViewingYear))*12);

    if (gridSquareFeature.properties.Businesses != null){
        gridSquareFeature.properties.Businesses.forEach((businessId) => {
                let business = businesses_all[businessId];
                if (isBusinessActiveAtTimeAndOfSector(business, curRangeTime, String(requiredSectorId))){
                    let li = document.createElement("li");
                    li.style = "margin-top:0.2em; cursor:pointer;";
                    li.onclick = (e)=>{showInformationAboutBusiness(businessId)};
                    li.innerHTML = "<a href=\"javascript:void(0)\">"+getColumnValueForBusiness(business,"CompanyName")+"</a>";
                    listElements.push(li)
                    count_active++;
                }
        });
    }
  
    let listTitle = document.createElement("div");
    listTitle.innerHTML = "<strong>"+sectors_all[requiredSectorId]+"<br>"+(currentViewingYear < DEFAULT_YEAR ? "<span class='red-timeslice-notice'>"+fractionalYearToYearAndMonth(currentViewingYear)+" timeslice: </span>":"")+count_active+" active businesses registered in this square:</strong>";
    div.appendChild(listTitle)

    gridSquareFeature.desc = count_active;

    listElements.sort((a,b) => {return (a.innerHTML == b.innerHTML ? 0 : (a.innerHTML < b.innerHTML ? -1 : 1))});

    listElements.forEach(li => {
        ul.appendChild(li);
    });

    div.appendChild(ul);

    return div;
}

function updateTimeFromTimestamp(timestamp){
    PRESENT_DATE = new Date(Date.parse(timestamp))
    DEFAULT_YEAR = PRESENT_DATE.getFullYear() + ((PRESENT_DATE.getMonth() + 1) / 12);
    currentViewingYear = DEFAULT_YEAR;    
    timeRange.updateMaxYear(DEFAULT_YEAR);
}

async function swapOutCurrentGeojson(value){
    let geojson = await loadJson(value);

    if (currentGeoJsonFeature != null){
        currentGeoJsonFeature.remove();
    }

    sectorSelector.innerHTML = "";

    businesses_all = geojson.properties.businesses_all;
    sectors_all = geojson.properties.sectors_all;
    industries_all = geojson.properties.industries_all;

    document.getElementById("retrieval-timestamp").innerText = geojson.properties.timestamp;
    updateTimeFromTimestamp(geojson.properties.timestamp);

    if (geojson.properties.row_headers != null){
        business_info_row_headers = geojson.properties.row_headers;
    }

    let opts = [];

    sectors_all.forEach((sector, sectorIndex) => {
        let newOption = document.createElement("option");
        newOption.innerText = sector;
        newOption.value = sectorIndex;
        opts.push(newOption)
    })

    opts.sort((a,b)=>{return (a.innerText == b.innerText ? 0 : (a.innerText < b.innerText ? -1 : 1))})

    opts.forEach(option => {
        sectorSelector.appendChild(option);
    })    

    currentGeoJsonFeature = L.geoJSON(geojson);
    currentGeoJsonFeature.addTo(map);

    if (!hasCompletedFirstTimeSetup){
        hasCompletedFirstTimeSetup = true;
        changeSelectedSectorTo(sectorSelector.children[0].value)
    } else {
        changeSelectedSectorTo(sectorSelector.value)
    }
}

function makeAnchorTagString(content, link, targetBlank){
    return "<a "+ (targetBlank ? "target=\"_blank\"" : "") + "href=\""+link+"\">"+content+"</a>";
}

function roundToDP(input,dp){
    let powerOf10 = Math.pow(10.0,dp);
    return Math.round(input * powerOf10) / powerOf10;
}

function showInformationAboutGridSquare(feature,sectorId){
    selectedSquare = feature;
    let gridSquareInfoTable = document.getElementById("grid-square-info-table")
    gridSquareInfoTable.style = "";
    document.getElementById("business-info-table").style = "display:none";
    
    gridSquareInfoTable.innerHTML = "";
    gridSquareInfoTable.appendChild(makeClickableListOfBusinessesInThisSquare(feature, sectorId))
    gridSquareInfoTable.scrollTop = 0;
}

function showInformationAboutBusiness(businessId){
    document.getElementById("scrolling-list").scrollTop = 0;
    document.getElementById("grid-square-info-table").style = "display:none";
    document.getElementById("business-info-table").style = "";
    let business = businesses_all[businessId];
    let company_number = getColumnValueForBusiness(business,"CompanyNumber");

    let address = getColumnValueForBusiness(business,"RegAddress.CareOf");
    address += " "+getColumnValueForBusiness(business,"RegAddress.POBox");
    address += " "+getColumnValueForBusiness(business,"RegAddress.AddressLine1");
    address += " "+getColumnValueForBusiness(business,"RegAddress.AddressLine2");
    address += " "+getColumnValueForBusiness(business,"RegAddress.PostTown");
    document.getElementById("back-to-grid-square-info").innerHTML = makeAnchorTagString("← Back...", "javascript:void(0)", false)
    document.getElementById("back-to-grid-square-info").onclick = () => {
    document.getElementById("grid-square-info-table").style = "";
    document.getElementById("business-info-table").style = "display:none";};
    document.getElementById("name-td").innerText = getColumnValueForBusiness(business,"CompanyName");
    document.getElementById("link-td").innerHTML = makeAnchorTagString(company_number, "https://find-and-update.company-information.service.gov.uk/company/" + (company_number+"").padStart(8, '0') +"\"", true);
    document.getElementById("nature-of-business-td").innerText = industries_all[parseInt(getColumnValueForBusiness(business,"industry"))];
    document.getElementById("incorporated-td").innerText = getColumnValueForBusiness(business,"IncorporationDate")
    document.getElementById("address-td").innerHTML = makeAnchorTagString(address,"https://www.google.co.uk/maps/search/"+address.replaceAll(" ","+"), true);
    document.getElementById("position-td").innerText = roundToDP(getColumnValueForBusiness(business,"Latitude"),6) + ", " + roundToDP(getColumnValueForBusiness(business,"Longitude"),6);
    document.getElementById("type-td").innerText = getColumnValueForBusiness(business,"CompanyCategory");
    document.getElementById("status-td").innerText = getColumnValueForBusiness(business,"CompanyStatus");
    //document.getElementById("sic-codes-td").innerText = getColumnValueForBusiness(business,"nature_of_business");
}

function isBusinessActiveAtTime(business,time){
    let incorporated = new Date(getColumnValueForBusiness(business, "IncorporationDate"));
    let dissolved = getColumnValueForBusiness(business, "DissolutionDate");
    if (dissolved == null || dissolved == ""){
        return time >= incorporated;
    }
    dissolved = new Date(dissolved);
    return time >= incorporated && time < dissolved;
}

function isBusinessActiveAtTimeAndOfSector(business, time, sector){
    if (isBusinessActiveAtTime(business,time)){
        let sectors_of_business = getColumnValueForBusiness(business,"sector");
        for (let i = 0; i < sectors_of_business.length; i++){
            if (sectors_of_business[i].trim() == String(sector)){
                return true;
            }
        }
    }
    return false;
}

async function changeSelectedSectorTo(sector){
    let min = 99999999
    let max = -99999999

    let mean = 0;
    let count_for_mean = 0;

    let layersToInclude = []

    if (currentGeoJsonFeature == null){
        return;
    }

    currentGeoJsonFeature.eachLayer(function(layer){
        let sectorFrequencies = layer.feature.properties["Sector frequencies"];
        if (!Object.keys(sectorFrequencies).includes(sector) || !rangePolygon.getBounds().contains(layer.getBounds().getCenter())){ //if the grid square doesn't represent any businesses from the chosen sector OR doesn't have its centrepoint within the red rectangle
            layer.setStyle({opacity:'0', fillOpacity:'0', interactive:false});
            layer.off('click'); //zero out the onclick function for layers that aren't included in the current view
            return;
        } else {
            layersToInclude.push(layer);
            layer.setStyle({opacity:'1', fillOpacity:'0.8', interactive:true}); 
        }
    });

    let curRangeTime = Date.UTC(Math.floor(currentViewingYear), (currentViewingYear-Math.floor(currentViewingYear))*12);

    layersToInclude.forEach(function(layer){
        let layerFreq = 0;
        layer.feature.properties.Businesses.forEach(businessId => {
            let business = businesses_all[businessId];
            if (isBusinessActiveAtTimeAndOfSector(business, curRangeTime, sector)){
                layerFreq++;
            }
        })
        
        mean += layerFreq;
        count_for_mean++;

        if (layerFreq < min){
            min = layerFreq;
        }
        if (layerFreq > max){
            max = layerFreq;
        }

        layer.layerFreq = layerFreq;
    });

    mean /= count_for_mean;
    let sum = 0;

    layersToInclude.forEach(function(layer){
        sum += Math.pow(count_for_mean - mean, 2);
    });

    let SD = Math.sqrt(sum /= count_for_mean)
    let SD3 = SD * 3;
    
    let limit = SD3;

    if (max > mean + limit){
        max = mean + limit;
    }
    if (min < mean - limit){
        min = mean - limit;
    }

    //console.log(mean + SD)

    layersToInclude.forEach(function(layer) {
        
        if (Math.abs(layer.layerFreq - mean) > limit){
            if (layer.layerFreq > mean){
                layer.layerFreq = mean + limit;
            } else {
                layer.layerFreq = mean - limit;
            }
        }

        let c = getColourSteppedBetweenValues(layer.layerFreq, min, max, LOW_COLOUR, HIGH_COLOUR);
        layer.setStyle({          
             color: c.toString({format: "rgb"}),
             fillColor: c.toString({format: "rgb"}),
            }
        );

        layer.on('click', () => {
            if (currentPin != null){
                currentPin.remove();
            }
            currentPin = L.marker(layer.getBounds().getCenter(), {}).addTo(map);
            showInformationAboutGridSquare(layer.feature, sector)
        });

        if (selectedSquare != null){
            showInformationAboutGridSquare(selectedSquare, sector)
        }
    });
    
    document.getElementById("downloads-section").style = "";
    timeRange.updateDesc();
}

gridSelector.onchange = async (e) => {
    alert("Just so you know, if you have selected a fine resolution and have the red box set to a large area, there may be a bit of a wait (up to 20 seconds) while it loads.")
   await swapOutCurrentGeojson(e.target.value)
};

sectorSelector.onchange = async (e) => {
    await changeSelectedSectorTo(e.target.value)
};

async function loadJson(value) {
    let path = "";
    
    if (Object.keys(cached).includes(value)){
        return cached[value];
    }

    switch (value){
        case "250":
            path = grid_250;
            break;
        case "500":
            path = grid_500;
            break;
        case "1000":
            path = grid_1000;
            break;
        case "scratchpad":
            path = grid_scratchpad;
            break;
        default:
            alert("Don't have a grid for that select element option ("+value+")")
        break;
    }
    console.log("Working to retrieve json...");
    let timeStarted = Date.now();
    const response = await fetch(path);
    let json = await response.json();
    console.log("Done. Took "+ ((Date.now() - timeStarted) / 1000) + " seconds");
    cached[value] = json;
    streamlineSectorsString(json)
    return json;
  }

  swapOutCurrentGeojson(gridSelector.children[0].value)
  gridSelector.value = gridSelector.children[0].value;