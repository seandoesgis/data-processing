# !/usr/bin/env python

##################################################
##
##  Data intake tool for port activity across the
##  Top 25 MSA regions. Hard-coded for 2014 ACS
##  calculation of top MSA's by population. 
##
##  Author: Michael Ruane, DVRPC
##
###################################################

import arcpy
import StringIO
import urllib, csv
import urllib2
from operator import itemgetter
import yaml

#global variables
national = 0
csa_data = []
top_twofive = []
port_lookup = []
port_totals = {}

# delaware valley regional ports
port_codes = ['C0552', 'C5252', 'C5251', 'C0551', 'C0298', 'C0297', 'C0553']
ports = set(port_codes)

prefixes = ['pport', 'pports', 'PPORT', 'PPORTS']
years = ['00','01','02','03','04','05','06','07','08','09','10','11','12','13']
# years = ['13']

#retrieve top 25 MSAs --->  !!!!!!    only for 2014 data    !!!!!! 
#--------------------------------------------------------------------
url = 'http://api.census.gov/data/2014/acs5?get=NAME,B01001_001E&for=metropolitan+statistical+area/micropolitan+statistical+area:*&key=f1ebba0078fa76b9794f7070402b4b72095564b1'
response = urllib2.urlopen(url).read()
parsed_json = yaml.safe_load(response)

for msa in parsed_json[1:]:
	csa_data.append([msa[0],int(msa[1]),msa[2]])

sorted_msa = sorted(csa_data, key=itemgetter(1), reverse=True)

for msa in sorted_msa[:25]:
	top_twofive.append(msa[2])

with open('port-msa-match.csv', 'rb') as f:
    reader = csv.reader(f)
    for row in reader:
    	if row[5] in top_twofive:
    		port_lookup.append(row)

#-----------------------------------------------------------
## -- finish MSA 

# edit session
workspace = r"C:\Users\mruane\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\FREIGHT_OWNER@PRODAUTH.sde"
edit = arcpy.da.Editor(workspace)
			
edit.startEditing()
edit.startOperation()

#principal port cursor
principal_port_layer = "C:\Users\mruane\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\FREIGHT_OWNER@PRODAUTH.sde\FREIGHT.dvrpc_principal_ports" 
p_port_cursor = arcpy.da.InsertCursor(principal_port_layer, ["NDC_PORT","YEAR","DOMESTIC","IMPORT","EXPORT"])

#msa data cursor
msa_port_activity = "C:\Users\mruane\AppData\Roaming\ESRI\Desktop10.3\ArcCatalog\FREIGHT_OWNER@PRODAUTH.sde\FREIGHT.msa_port_activity"
msa_act_cursor = arcpy.da.InsertCursor(msa_port_activity, ["MSA_ID","YEAR", "RANK", "DOMESTIC","IMPORT","EXPORT"])


def get_data(y):
	dwn_data = []
	#loop the possible prefixes because NDC is not consistent
	for prefix in prefixes:
		try:
			# access data from navigation data center
			# for current year
			# data = urllib2.urlopen("http://www.navigationdatacenter.us/db/pport/data/"+ prefix + y +".txt").read()
			data = urllib2.urlopen("http://www.navigationdatacenter.us/db/pport/archive/"+ prefix + y +".txt").read() 		
			f = StringIO.StringIO(data)
			dwn_data = csv.reader(f, delimiter=',')

			return dwn_data
		except:
			pass

for year in years:

	# store naitonal summary data ['domestic', 'import', 'export']
	national_data = [0,0,0]
	# dictionaries for storing MSA port summary data
	port_totals = {}
	port_domestic = {}
	port_import = {}
	port_export = {}
	try:
		ndc_data = get_data(year)
		
		#hack to skip the header then loop all rows
		next(ndc_data)
		for port in ndc_data:
			if len(port) > 1:
				#add dvrpc port data to the pff database
				if port[0] in ports:
					# print ('row added to dvrpc_principal_ports table: ' + port[0], '20'+year, port[5], port[7], port[8])
					p_port_cursor.insertRow([port[0], '20'+year, port[5], port[7], port[8]])
				
				#match port to top 25 msa
				for item in port_lookup:
					if port[0] == item[0]:
						msa_id = item[5]
						try:
						    port_totals[msa_id] += int(port[4].split('.')[0].replace(',',''))
						    port_domestic[msa_id] += int(port[5].split('.')[0].replace(',',''))
						    port_import[msa_id] += int(port[7].split('.')[0].replace(',',''))
						    port_export[msa_id] += int(port[8].split('.')[0].replace(',',''))
						except KeyError:
						    port_totals[msa_id] = int(port[4].split('.')[0].replace(',',''))
						    port_domestic[msa_id] = int(port[5].split('.')[0].replace(',',''))
						    port_import[msa_id] = int(port[7].split('.')[0].replace(',',''))
						    port_export[msa_id] = int(port[8].split('.')[0].replace(',',''))	

				#calculates total national trade volume in tons
				national_data[0] += int(port[5].split('.')[0].replace(',',''))
				national_data[1] += int(port[7].split('.')[0].replace(',',''))
				national_data[2] += int(port[8].split('.')[0].replace(',',''))

		
		sorted_total = sorted(port_totals.items(), key=itemgetter(1), reverse=True)
		
		# add national summary data to Top 25 MSA Port Activity table [msa_port_activity]\
		# print ('row added to msa_port_activity table: ' + 'us_all', '20'+year, '0', national_data[0], national_data[1], national_data[2])
		msa_act_cursor.insertRow(['us_all', '20'+year, '0', national_data[0], national_data[1], national_data[2]])
		
		count = 0
		for p in sorted_total:
			count += 1
			# insert MSA values for this year to Top 25 MSA Port Activity table [msa_port_activity]
			# print ('row added to msa_port_activity table: ' + p[0], '20'+year, count, port_domestic[p[0]], port_import[p[0]], port_export[p[0]])
			msa_act_cursor.insertRow([p[0], '20'+year, count, port_domestic[p[0]], port_import[p[0]], port_export[p[0]]])

		print "Principal Ports data successfully added to the PFF database for 20"+year+" data"
		
	except Exception as e:
		#script failed. print message and set script to wait.
		print "error for 20"+year+" data"
		print e
		# print "This data is not available yet. Boo U.S. Army Corps of Engineers! Let's try again next week."

edit.stopOperation()
edit.stopEditing(True)