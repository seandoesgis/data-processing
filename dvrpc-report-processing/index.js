#!/usr/bin/env node

//**********************************************************************
//  Node.js tool to extract first page from entire folder of pdfs and
//  convert them to PNGs. This tool is untested on large documents
//  and large batches. Resolution will impact the output size for the 
//  PNG documents and paths must be manually set.
//
//  ----------------------------------------------
//  Dependencies
//  ----------------------------------------------
//
//  PDFtk - PDF toolkit  (https://www.pdflabs.com/tools/pdftk-server/#download)
//  node.js 
//  pdf2png-mp  (npm install pdf2png-mp)
//  node-walker (npm install node-walker)
//
//  Author: Michael Ruane
//  Last modified: November 19, 2015
//
//	required params: node report_convert.js [location of reports (./reports/)] [location of output (creates a covers and pngs directory)]
//
//*************************************************************************


// include the module
    var walker = require('node-walker');
    var pdf2png = require('pdf2png-mp');
    var fs = require('fs');

    var util = require('util');
    var log_file = fs.createWriteStream(__dirname + '/debug.log', {flags : 'w'});
    var log_stdout = process.stdout;

    	
    if (process.argv.length <= 2) {
	    console.log('Give me data! The following command should be used:');
	    console.log('')
	    console.log('node report_convert.js [input directory] [output directory (optional)]');
	    process.exit(-1);
	}
	 
	var input_location = process.argv[2];
	var output_location = (typeof process.argv[3] === 'undefined') ? '.' : process.argv[3];


    var dirs = ['/covers','/pngs'];


    logFile = function(d) { //
      log_file.write(util.format(d) + '\n');
      log_stdout.write(util.format(d) + '\n');
    };



	// start walking over all pdf files in pdf folder
    function extractPDFs(){
    	for (i = 0, len = dirs.length; i < len; i++){
	    	if (!fs.existsSync(output_location + dirs[i])){
	    		fs.mkdirSync(output_location + dirs[i]);
	    	}
	    }
        walker( input_location, 

            function (errorObject, fileName, fnNext) {
               
                // an error occurred
                if (errorObject) throw errorObject;

                // a filename has been provided
                if (fileName !== null) {
                    var nameStr = fileName.split(".");
                    var fileType = nameStr.slice(-1)[0];
                    var name = nameStr[1].split("/").splice(-1)[0];
                    //for each pdf document export the cover to a folder named covers
                        if(fileType === 'pdf'){
                           var exec = require('child_process').exec,
                                child;

                          child = exec('pdftk '+ input_location +'/'+ name+'.pdf cat 1 output '+ output_location +'/covers/'+ name +'.pdf',
                              function (error, stdout, stderr) {
                                console.log('Report #'+name+' cover exported.');
                                
                                if (error === null){
                                	pdf2png.convert(output_location +"/covers/"+ name +".pdf", { quality: 300 }, function(resp){
			                            if(!resp.success)
			                            {
			                                //console.log("Something went wrong: " + resp.error);
			                                logFile('Something went wrong: ' + resp.error);
			                                return;
			                            }
			                         
			                         
			                            
			                         
			                            resp.data.forEach(function(item, index) {
			                                if(index === 1){
			                                    fs.writeFile(output_location +"/pngs/"+name+".png", item, function (err) {
			                                        if (err) {
			                                           logFile(err); //console.log(err);
			                                        }
			                                        else {
			                                            console.log("Report #"+name+" cover converted.");
			                                        }
			                                    });
			                                }
			                            });
			                        });

                                }// convertPDFs(name);
                                
                                if (error !== null) {
                                  logFile('exec error: ' + error);
                                }
                            });
                        }

                }

                // all files have been read, fileName is null
                if (fileName === null) {
                   
                    // continue with some other task
                    return;
                }

                // call next(); when you want to proceed
                if (fnNext) {
                    fnNext();
                }
            }
        );   
    }

    var extract = extractPDFs();