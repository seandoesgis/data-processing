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
//  
//  node.js 
//  pdf2png  (npm install pdf2png)
//  node-walker (npm install node-walker)
//
//  Author: Michael Ruane
//  Last modified: November 19, 2015
//
//*************************************************************************


// include the module
    var walker = require('node-walker');
    var pdf2png = require('pdf2png');
    var fs = require('fs');

    var util = require('util');
    var log_file = fs.createWriteStream(__dirname + '/png_debug.log', {flags : 'w'});
    var log_stdout = process.stdout;


    logFile = function(d) { //
      log_file.write(util.format(d) + '\n');
      log_stdout.write(util.format(d) + '\n');
    };



// start walking over all pdf files in pdf folder
    function extractPDFs(){
        walker( './covers', 

            function (errorObject, fileName, fnNext) {
               
                // an error occurred
                if (errorObject) throw errorObject;

                // a filename has been provided
                if (fileName !== null) {
                    var nameStr = fileName.split(".");
                    var fileType = nameStr.slice(-1)[0];
                    var name = nameStr[1].split("/").splice(-1)[0];
                    //for each pdf document export the cover to a folder named covers
                        pdf2png.convert("./covers/"+name+".pdf", { quality: 300 }, function(resp){
                            if(!resp.success)
                            {
                                //console.log("Something went wrong: " + resp.error);
                                logFile('Something went wrong: ' + resp.error);
                                return;
                            }
                         
                         
                            
                         
                            resp.data.forEach(function(item, index) {
                                if(index === 1){
                                    fs.writeFile("./pngs/"+name+".png", item, function (err) {
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

                }

                // all files have been read, fileName is null
                if (fileName === null) {
                   
                    // continue with some other task
                    return;
                }

                // call next(); when you want to proceed
                if (fnNext) {
                    //setTimeout(fnNext(), 1000);
                    //console.log('move to next');
                    fnNext();
                }
            }
        );
        
    }

    extractPDFs();