import { map, findChildElementWithIdRecursive, fractionalYearToYearAndMonth,
        changeSelectedSectorTo, sectorSelector, sectors_all } from "./global.js";

let PRESENT_DATE = null;
let DEFAULT_YEAR = null;

const USE_TIME_RANGE = true;

let currentViewingYear = DEFAULT_YEAR;

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
        this.desc.innerHTML = "Showing "+sectors_all[sectorSelector.value]+" businesses that are currently active  (and that were also active at the given timeslice, though not necessarily in the same location):";
    }
  });

let timeRange = new TimeRange();

if(USE_TIME_RANGE){
    timeRange.addTo(map);
}

function updateTimeFromTimestamp(timestamp){
    PRESENT_DATE = new Date(Date.parse(timestamp))
    DEFAULT_YEAR = PRESENT_DATE.getFullYear() + ((PRESENT_DATE.getMonth() + 1) / 12);
    currentViewingYear = DEFAULT_YEAR;    
    timeRange.updateMaxYear(DEFAULT_YEAR);
}

export {updateTimeFromTimestamp, currentViewingYear, timeRange, DEFAULT_YEAR}