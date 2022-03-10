class CinemaOdsReader {
    constructor(cdb_url) {
        this.cdb_url = cdb_url;
        this.fields = [];
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
    
    getRowByIndex(index) {
        if (index < this.data.length) {
            return this.data[index];
        }
        return null;
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

    testRead(){
        return new Promise((resolve, reject) => {
            let xhr = new XMLHttpRequest();
            xhr.onreadystatechange = () => {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    let i, j;
                    let lines = xhr.responseText.split('\n');
                    if (lines[lines.length - 1] === '') {
                        lines.pop();
                    }
                    if (lines[0][lines[0].length - 1] === '\r') {
                        lines[0] = lines[0].substring(0, lines[0].length - 1);
                    }
                    let header = lines[0].split(',');
                    for (i = 0; i < header.length; i++) {
                        let property = {};
                        //parse column names
                        property.name = header[i];
                    }

                    //read lines 1-N, split into columns,
                        // but leave as strings

                        //no idea how to do this :P

                    property.name.forEach(element => {

                    });

                    for (let i = 0; i < property.name.length; i++){
                        if (property.name[i].every(this.isFieldBoolean)){
                            //checkbox
                            property.name[i].type = "CHECK";
                        } else if (property.name[i].every(this.isInt)){
                            //slider
                            property.name[i].type = "RANGE";
                        } else {
                            //radio buttons
                            property.name[i].type = "RADIO";
                            let values = {};
                        }
                    }

                        /*
                        for (j = 0; j < this.data.fields.length; j++){
                            if (header[i][j] === "0" || header[i][j] == 'false'){
                                //checkbox
                                header[i].type = "CHECK";
                            } else if ()
                        } */
                        {
                        let type_start = header[i].indexOf('[');
                        if (type_start >= 0) {
                            property.name = header[i].substring(0, type_start);
                            let type_end = header[i].indexOf(']');
                            let type = header[i].substring(type_start + 1, type_end);
                            let values_start = type.indexOf('|');
                            if (values_start >= 0) {
                                let values = type.substring(values_start + 1, type.length).split(':');
                                type = type.substring(0, values_start);
                                property.type = type;
                                if (type === 'RADIO') {
                                    property.options = values;
                                }
                                else if (type === 'RANGE') {
                                    property.start = parseInt(values[0]);
                                    property.end = parseInt(values[1]);
                                }
                            }
                            else {
                                property.type = type;
                            }
                        }
                        else if (header[i].indexOf('FILE') == 0) {
                            property.name = header[i];
                            property.type = 'FILE';
                        }
                        else {
                            reject({status: 200, message: 'Error parsing response - CSV header not properly formatted'});
                            return;
                        }
                        this.fields.push(property);
                    }
                    for (i = 1; i < lines.length; i++) {
                        let row = lines[i];
                        if (row[row.length - 1] === '\r') {
                            row = row.substring(0, row.length - 1);
                        }
                        let row_values = row.split(',');
                        let entry = {};
                        for (j = 0; j < this.fields.length; j++) {
                            if (this.fields[j].type === 'CHECK') {
                                if (row_values[j] === '0' || row_values[j] === 'false' || row_values[j] === 'False') {
                                    entry[this.fields[j].name] = false;
                                }
                                else {
                                    entry[this.fields[j].name] = true;
                                }
                            }
                            else if (this.fields[j].type == 'RADIO') {
                                entry[this.fields[j].name] = row_values[j];
                            }
                            else if (this.fields[j].type == 'RANGE') {
                                entry[this.fields[j].name] = parseInt(row_values[j]);
                            }
                            else if (this.fields[j].type == 'FILE') {
                                entry[this.fields[j].name] = row_values[j];
                            }
                        }
                        this.data.push(entry);
                    }
                    
                    resolve();
                }
                else if (xhr.readyState == 4) {
                    reject({status: xhr.status, message: xhr.statusText});
                }
            };
            xhr.open('GET', this.cdb_url + '/data.csv', true);
            xhr.send();
        });
    }

    
    isFieldBoolean(data_array, field_name) {
        let is_field_bool = data_array.every((element) => {
             if (element[field_name] === "True" || element[field_name] === "False" 
             || element[field_name] === "true" || element[field_name] === "false" ||
             element[field_name] === "0" || element[field_name] === "1") {
                return true;
             }
             return false;
         });
         return is_field_bool;
    } 

    isFieldInt(data_array, field_name) {
        let is_field_int = data_array.every((element) => {
            //isNaN => is this element not a number?
            // want isNan to be false since that would mean that the string is an int,
            // then convert into an actual int
             if (!isNaN(element[field_name]) && Number.isInteger(parseFloat(element[field_name]))) {
                return true;
             }
             return false;
         });
         return is_field_int;
    }


    isInt(str){
        
        return !isNaN(str) && Number.isInteger(parseFloat(str));
    }
    
    read() {
        return new Promise((resolve, reject) => {
            let xhr = new XMLHttpRequest();
            xhr.onreadystatechange = () => {
                if (xhr.readyState == 4 && xhr.status == 200) {
                    let i, j;
                    let lines = xhr.responseText.split('\n');
                    if (lines[lines.length - 1] === '') {
                        lines.pop();
                    }
                    if (lines[0][lines[0].length - 1] === '\r') {
                        lines[0] = lines[0].substring(0, lines[0].length - 1);
                    }
                    let header = lines[0].split(',');
                    for (i = 0; i < header.length; i++) {
                        let property = {};
                        let type_start = header[i].indexOf('[');
                        if (type_start >= 0) {
                            property.name = header[i].substring(0, type_start);
                            let type_end = header[i].indexOf(']');
                            let type = header[i].substring(type_start + 1, type_end);
                            let values_start = type.indexOf('|');
                            if (values_start >= 0) {
                                let values = type.substring(values_start + 1, type.length).split(':');
                                type = type.substring(0, values_start);
                                property.type = type;
                                if (type === 'RADIO') {
                                    property.options = values;
                                }
                                else if (type === 'RANGE') {
                                    property.start = parseInt(values[0]);
                                    property.end = parseInt(values[1]);
                                }
                            }
                            else {
                                property.type = type;
                            }
                        }
                        else if (header[i].indexOf('FILE') == 0) {
                            property.name = header[i];
                            property.type = 'FILE';
                        }
                        else {
                            reject({status: 200, message: 'Error parsing response - CSV header not properly formatted'});
                            return;
                        }
                        this.fields.push(property);
                    }
                    for (i = 1; i < lines.length; i++) {
                        let row = lines[i];
                        if (row[row.length - 1] === '\r') {
                            row = row.substring(0, row.length - 1);
                        }
                        let row_values = row.split(',');
                        let entry = {};
                        for (j = 0; j < this.fields.length; j++) {
                            if (this.fields[j].type === 'CHECK') {
                                if (row_values[j] === '0' || row_values[j] === 'false' || row_values[j] === 'False') {
                                    entry[this.fields[j].name] = false;
                                }
                                else {
                                    entry[this.fields[j].name] = true;
                                }
                            }
                            else if (this.fields[j].type == 'RADIO') {
                                entry[this.fields[j].name] = row_values[j];
                            }
                            else if (this.fields[j].type == 'RANGE') {
                                entry[this.fields[j].name] = parseInt(row_values[j]);
                            }
                            else if (this.fields[j].type == 'FILE') {
                                entry[this.fields[j].name] = row_values[j];
                            }
                        }
                        this.data.push(entry);
                    }
                    
                    resolve();
                }
                else if (xhr.readyState == 4) {
                    reject({status: xhr.status, message: xhr.statusText});
                }
            };
            xhr.open('GET', this.cdb_url + '/data.csv', true);
            xhr.send();
        });
    }
}
