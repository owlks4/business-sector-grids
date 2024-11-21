let map = L.map('map').setView([52.4625,-1.6], 11);
let MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

let sectorSelector = document.getElementById("sector-selector");
let sectors_all = null;

function set_sectors_all(value){
    sectors_all = value;
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

function fractionalYearToYearAndMonth(fractionalYear){
    let year = Math.floor(fractionalYear);
    let fractionalMonth = fractionalYear - year;
    return MONTHS[Math.floor(fractionalMonth * 12)] + " " + year;
}

let changeSelectedSectorTo = null;

function setChangeSelectedSectorTo(f){
    changeSelectedSectorTo = f;
}

export {map, sectors_all, findChildElementWithIdRecursive, fractionalYearToYearAndMonth,
        setChangeSelectedSectorTo, changeSelectedSectorTo, sectorSelector, set_sectors_all}