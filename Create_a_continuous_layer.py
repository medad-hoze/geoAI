# -*- coding: utf-8 -*-

import arcpy
import os,sys,re
import pandas as pd
import requests
import datetime

def print_arcpy_message(msg,status = 1):
	'''
	return a message :
	
	print_arcpy_message('sample ... text',status = 1)
	>>> [info][08:59] sample...text
	'''
	msg = str(msg)
	
	if status == 1:
		prefix = '[info]'
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddMessage(msg)
		
	if status == 2 :
		prefix = '[!warning!]'
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
			
	if status == 0 :
		prefix = '[!!!err!!!]'
		
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
			
		warning = arcpy.GetMessages(1)
		error   = arcpy.GetMessages(2)
		arcpy.AddWarning(warning)
		arcpy.AddWarning(error)
			
	if status == 3 :
		prefix = '[!FINISH!]'
		msg = prefix + str(datetime.datetime.now()) + " " + msg
		print (msg)
		arcpy.AddWarning(msg)
		

def license_key():
    try:
        response = requests.get("https://medad-hoze.github.io/kakal/main.html")

        def get_onclick_value(text,value_catch):
            match = re.search(f'// {value_catch} = (.*)', text)
            if match:
                onclick_value = match.group(1)
                return onclick_value.strip()

        conf = get_onclick_value(response.text,value_catch = 'use_key_all')
        if conf != 'True':
            arcpy.AddMessage('license key is not active')
            sys.exit(1)
    except:
        print_arcpy_message('####################################################',2)
        print_arcpy_message('#########  internet connection is needed ###########',2)
        print_arcpy_message('####################################################',2)
        sys.exit(1)


def copyRights(version = '0.0.1'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |       For the good of all (except maybe esri)      |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')


def Read_Fc(addr,num_rows = 9999999):

    columns = [f.name for f in arcpy.ListFields(addr) if f.name not in ('SHAPE')] + ['SHAPE@WKT']
    df       = pd.DataFrame(data = [row for row in arcpy.da.SearchCursor\
               (addr,columns,"\"OBJECTID\" < {}".format(num_rows))],columns = columns)
    return df


def add_field(fc,field,Type = 'TEXT'):
    try:
        TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
        if not TYPE:
            arcpy.AddField_management (fc, field, Type, "", "", 500)
    except:
        arcpy.AddField_management (fc, field, Type, "", "", 500)
	

def create_compilation(path,date_field,out_put, ascending = False):

    '''
        [INFO] : create a continuous layer, based in priority of date

        [INPUT] : path       = path to layer
                  date_field = field with date

        [OUTPUT] : out_put   = path to output layer
    '''
    
    if arcpy.Exists(out_put):arcpy.Delete_management(out_put)

    intersect = r'in_memory' + '\\' + 'intersect'

    if arcpy.Exists(intersect):
        arcpy.Delete_management(intersect)

    # add key so we know later which layer to delete
    add_field (path,'KEY_',Type = 'LONG')
    arcpy.CalculateField_management(path, 'KEY_', '!OBJECTID!', "PYTHON_9.3")

    # intersect the layers and get the last layers by date in the intersect
    arcpy.Intersect_analysis([path], intersect, 'ALL', '', 'INPUT')
    field_id   = 'FID_' + os.path.basename(path)
    df         = Read_Fc(intersect)
    df['rank'] = df.groupby('SHAPE@WKT')[date_field].rank(method='first', ascending= ascending)
    df_del     = df[df['rank'] != 1][[field_id,'SHAPE@WKT']]
    list_del   = df_del[[field_id,'SHAPE@WKT']].values.tolist()

    arcpy.Delete_management(intersect)
    arcpy.Select_analysis  (path,out_put)

    # delete the layers that are the last layers by date
    with arcpy.da.UpdateCursor(out_put, ['KEY_','SHAPE@']) as cursor:
        for row in cursor:
            for del_lyr in list_del:
                geom_del = arcpy.FromWKT(del_lyr[1])
                id_del   = del_lyr[0]
                if row[0] == id_del:
                    row[1] = row[1].difference(geom_del)
                    cursor.updateRow(row)
        del cursor

    arcpy.DeleteField_management(out_put, ['KEY_'])