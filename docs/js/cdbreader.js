class CdbReader {
    constructor(cdb_url) {
        this.url = cdb_url;
        this.specification = '';
        this.fields = [];
        this.layers = []
        this.channels = [];
        this.data = [];
    }
    
    getRow(index_or_fieldvalsobj) {
        if (Number.isInteger(index_or_fieldvalsobj)) {
            return this.getRowByIndex(index_or_fieldvalsobj);
        }
        else if (typeof index_or_fieldvalsobj === 'object' && !Array.isArray(index_or_fieldvalsobj) && index_or_fieldvalsobj !== null) {
            return this.getRowByFieldValues(index_or_fieldvalsobj);
        }
        return null;
    }
    
    getRows(indexarray_or_fieldvalsobj) {
        if (Array.isArray(indexarray_or_fieldvalsobj)) {
            return this.getRowsByIndex(indexarray_or_fieldvalsobj);
        }
        else if (typeof indexarray_or_fieldvalsobj === 'object' && indexarray_or_fieldvalsobj !== null) {
            return this.getRowsByFieldValues(indexarray_or_fieldvalsobj);
        }
        return null;
    }
    
    getRowByIndex(index) {
        if (index < this.data.length) {
            return this.data[index];
        }
        return null;
    }
    
    getRowsByIndex(indices) {
        let i;
        let rows = [];
        for (i = 0; i < indices.length; i++) {
            if (indices[i] < this.data.length) {
                rows.push(this.data[indices[i]]);
            }
        }
        return rows;
    }
    
    getRowByFieldValues(field_values) {
        let i, j, alltrue;
        for (i = 0; i < this.data.length; i++) {
            alltrue = true;
            for (j in field_values) {
                if (field_values.hasOwnProperty(j) && this.data[i][j] !== field_values[j]) {
                    alltrue = false;
                }
            }
            if (alltrue) {
                return this.data[i];
            }
        }
        return null;
    }
    
    getRowsByFieldValues(field_values) {
        let i, j, alltrue;
        let rows = [];
        for (i = 0; i < this.data.length; i++) {
            alltrue = true;
            for (j in field_values) {
                if (field_values.hasOwnProperty(j) && this.data[i][j] !== field_values[j]) {
                    alltrue = false;
                }
            }
            if (alltrue) {
                rows.push(this.data[i]);
            }
        }
        return rows;
    }
    
    read() {
        // function to check if all elements are strings representing boolean values
        let allAreBoolean = (arr, key) => {
            return arr.every((elem) => {
                return (elem[key] === 'true' || elem[key] === 'false' || elem[key] === 'True' ||
                        elem[key] === 'False' || elem[key] === '0' || elem[key] === '1');
            });
        };
        
        // function to check if all elements are strings representing integer values
        let allAreInteger = (arr, key) => {
            return arr.every((elem) => {
                return /^-?\d+$/.test(elem[key]);
            });
        };
        
        // function to convert boolean strings to bool values
        let toBoolean = (str) => {
            return (str === 'true' || str === 'True' || str === '1');
        }
        
        return new Promise((resolve, reject) => {
            let xhr = new XMLHttpRequest();
            xhr.onreadystatechange = () => {
                // data.csv successfully finished downloading
                if (xhr.readyState === 4 && xhr.status === 200) {
                    let i, j;
                    let lines = xhr.responseText.split('\n');
                    // remove last line if blank
                    if (lines[lines.length - 1] === '') {
                        lines.pop();
                    }
                    // remove '\r' at end of first line if it exists
                    if (lines[0][lines[0].length - 1] === '\r') {
                        lines[0] = lines[0].substring(0, lines[0].length - 1);
                    }
                    // parse header (column names)
                    let header = lines[0].split(',');
                    for (i = 0; i < header.length; i++) {
                        this.fields.push({name: header[i]});
                    }
                    // parse each row of data
                    for (i = 1; i < lines.length; i++) {
                        let row = lines[i];
                        // remove '\r' at end of line if it exists
                        if (row[row.length - 1] === '\r') {
                            row = row.substring(0, row.length - 1);
                        }
                        // create object of key-value pairs
                        let row_values = row.split(',');
                        let entry = {};
                        for (j = 0; j < this.fields.length; j++) {
                            entry[this.fields[j].name] = row_values[j];
                        }
                        this.data.push(entry);
                    }
                    // check data types of each field
                    let cis_headers = {CISVersion: false, CISCImage: false, CISCImageWidth: false, CISImageHeight: false, CISLayer: false, CISChannel: false,
                                       CISLayerWidth: false, CISLayerHeight: false, CISLayerOffsetX: false, CISLayerOffsetY: false, CISChannelVarType: false};
                    let file_idx = -1;
                    for (i = 0; i < this.fields.length; i++) {
                        if (this.fields[i].name === 'CISVersion') {
                            this.fields[i].type = 'VERSION';
                            cis_headers.CISVersion = true;
                        }
                        else if (this.fields[i].name === 'CISImage') {
                            this.fields[i].type = 'IMAGE_ID';
                            cis_headers.CISImage = true;
                        }
                        else if (this.fields[i].name === 'CISLayer') {
                            this.fields[i].type = 'LAYER_ID';
                            cis_headers.CISLayer = true;
                        }
                        else if (this.fields[i].name === 'CISChannel') {
                            this.fields[i].type = 'CHANNEL_ID';
                            cis_headers.CISChannel = true;
                        }
                        else if (this.fields[i].name === 'CISImageWidth') {
                            this.fields[i].type = 'IMAGE_WIDTH';
                            cis_headers.CISImageWidth = true;
                        }
                        else if (this.fields[i].name === 'CISImageHeight') {
                            this.fields[i].type = 'IMAGE_HEIGHT';
                            cis_headers.CISImageHeight = true;
                        }
                        else if (this.fields[i].name === 'CISLayerWidth') {
                            this.fields[i].type = 'LAYER_WIDTH';
                            cis_headers.CISLayerWidth = true;
                        }
                        else if (this.fields[i].name === 'CISLayerHeight') {
                            this.fields[i].type = 'LAYER_HEIGHT';
                            cis_headers.CISLayerHeight = true;
                        }
                        else if (this.fields[i].name === 'CISLayerOffsetX') {
                            this.fields[i].type = 'LAYER_OFFSETX';
                            cis_headers.CISLayerOffsetX = true;
                        }
                        else if (this.fields[i].name === 'CISLayerOffsetY') {
                            this.fields[i].type = 'LAYER_OFFSETY';
                            cis_headers.CISLayerOffsetY = true;
                        }
                        else if (this.fields[i].name === 'CISChannelVar') {
                            this.fields[i].type = 'CHANNEL_NAME';
                        }
                        else if (this.fields[i].name === 'CISChannelVarType') {
                            this.fields[i].type = 'CHANNEL_DATATYPE';
                            cis_headers.CISChannelVarType = true;
                        }
                        else if (this.fields[i].name === 'CISChannelVarMin') {
                            this.fields[i].type = 'CHANNEL_MIN';
                        }
                        else if (this.fields[i].name === 'CISChannelVarMax') {
                            this.fields[i].type = 'CHANNEL_MAX';
                        }
                        else if (this.fields[i].name === 'CISChannelColormap') {
                            this.fields[i].type = 'CHANNEL_COLORMAP';
                        }
                        else if (allAreBoolean(this.data, this.fields[i].name)) {
                            this.fields[i].type = 'BOOLEAN';
                        }
                        else if (allAreInteger(this.data, this.fields[i].name)) {
                            this.fields[i].type = 'RANGE';
                        }
                        else if (this.fields[i].name.indexOf('FILE') === 0) {
                            this.fields[i].type = 'FILE';
                            if (file_idx === -1) {
                                file_idx = i;
                            }
                        }
                        else {
                            this.fields[i].type = 'SELECT';
                        }
                    }
                    // check specification
                    if (cis_headers.CISVersion && cis_headers.CISImage && cis_headers.CISLayer && cis_headers.CISChannel &&
                        cis_headers.CISImageWidth && cis_headers.CISImageHeight) {
                        this.specification = 'CIS';
                    }
                    else {
                        this.specification = 'SpecD';
                    }
                    // add defaults if not present and specification is CIS
                    if (this.specification === 'CIS') {
                        if (!cis_headers.CISLayerWidth) {
                            this.fields.splice(file_idx, 0, {name: 'CISLayerWidth', type: 'LAYER_WIDTH'});
                            file_idx++;
                        }
                        if (!cis_headers.CISLayerHeight) {
                            this.fields.splice(file_idx, 0, {name: 'CISLayerHeight', type: 'LAYER_HEIGHT'});
                            file_idx++;
                        }
                        if (!cis_headers.CISLayerOffsetX) {
                            this.fields.splice(file_idx, 0, {name: 'CISLayerOffsetX', type: 'LAYER_OFFSETX'});
                            file_idx++;
                        }
                        if (!cis_headers.CISLayerOffsetY) {
                            this.fields.splice(file_idx, 0, {name: 'CISLayerOffsetY', type: 'LAYER_OFFSETY'});
                            file_idx++;
                        }
                        if (!cis_headers.CISChannelVarType) {
                            this.fields.splice(file_idx, 0, {name: 'CISChannelVarType', type: 'CHANNEL_DATATYPE'});
                            file_idx++;
                        }
                    }
                    // convert data if needed and calculate min/max or options
                    for (i = 0; i < this.data.length; i++) {
                        for (j = 0; j < this.fields.length; j++) {
                            if (this.fields[j].type === 'BOOLEAN') {
                                this.data[i][this.fields[j].name] = toBoolean(this.data[i][this.fields[j].name]);
                            }
                            else if (this.fields[j].type === 'SELECT') {
                                if (this.fields[j].hasOwnProperty('options')) {
                                    if (this.fields[j].options.indexOf(this.data[i][this.fields[j].name]) < 0) {
                                        this.fields[j].options.push(this.data[i][this.fields[j].name]);
                                    }
                                }
                                else {
                                    this.fields[j].options = [this.data[i][this.fields[j].name]];
                                }
                            }
                            else if (['RANGE', 'IMAGE_WIDTH', 'IMAGE_HEIGHT', 'LAYER_WIDTH', 'LAYER_HEIGHT', 'LAYER_OFFSETX', 'LAYER_OFFSETY'].indexOf(this.fields[j].type) >= 0) {
                                if (this.data[i].hasOwnProperty(this.fields[j].name)) {
                                    this.data[i][this.fields[j].name] = parseInt(this.data[i][this.fields[j].name], 10);
                                }
                                else if (this.fields[j].name === 'CISLayerWidth') {
                                    this.data[i][this.fields[j].name] = parseInt(this.data[i].CISImageWidth, 10);
                                }
                                else if (this.fields[j].name === 'CISLayerHeight') {
                                    this.data[i][this.fields[j].name] = parseInt(this.data[i].CISImageHeight, 10);
                                }
                                else if (this.fields[j].name === 'CISLayerOffsetX' || this.fields[j].name === 'CISLayerOffsetY') {
                                    this.data[i][this.fields[j].name] = 0;
                                }
                                if (this.fields[j].type === 'RANGE') {
                                    if (this.fields[j].hasOwnProperty('min')) {
                                        this.fields[j].min = Math.min(this.fields[j].min, this.data[i][this.fields[j].name]);
                                    }
                                    else {
                                        this.fields[j].min = this.data[i][this.fields[j].name];
                                    }
                                    if (this.fields[j].hasOwnProperty('max')) {
                                        this.fields[j].max = Math.max(this.fields[j].max, this.data[i][this.fields[j].name]);
                                    }
                                    else {
                                        this.fields[j].max = this.data[i][this.fields[j].name];
                                    }
                                    let delta_min = this.data[i][this.fields[j].name] - this.fields[j].min;
                                    if (this.fields[j].hasOwnProperty('step') && delta_min > 0 && delta_min < this.fields[j].step) {
                                        this.fields[j].step = delta_min;
                                    }
                                    else if (delta_min > 0) {
                                        this.fields[j].step = delta_min;
                                    }
                                }
                            }
                            else if (this.fields[j].type === 'CHANNEL_DATATYPE' && !this.data[i].hasOwnProperty(this.fields[j].name)) {
                                this.data[i][this.fields[j].name] = 'float';
                            }
                            else if (this.fields[j].type === 'LAYER_ID' && this.specification === 'CIS') {
                                if (this.layers.indexOf(this.data[i][this.fields[j].name]) < 0) {
                                    this.layers.push(this.data[i][this.fields[j].name])
                                }
                            }
                            else if (this.fields[j].type === 'CHANNEL_ID' && this.specification === 'CIS') {
                                if (this.channels.indexOf(this.data[i][this.fields[j].name]) < 0) {
                                    this.channels.push(this.data[i][this.fields[j].name])
                                }
                            }
                        }
                    }
                    for (i = 0; i < this.fields.length; i++) {
                        if (this.fields[i].type === 'RANGE' && !this.fields[i].hasOwnProperty('step')) {
                            this.fields[i].step = 1;
                        }
                    }
                    // success
                    resolve();
                }
                else if (xhr.readyState == 4) {
                    reject({status: xhr.status, message: xhr.statusText});
                }
            };
            xhr.open('GET', this.url + '/data.csv', true);
            xhr.send();
        });
    }
}
