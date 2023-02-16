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


def del_columns(data_all,drop_fields):
    '''
    delete columns from dataframe
    '''
    for i in drop_fields:
        if i in data_all.columns:
            print ('droping column: {}'.format(i))
            data_all       = data_all.drop(i,axis = 1)
        else:
            print ('didnt find: {} in dataframe'.format(i))
    return data_all


def create_compilation(path,date_field,out_put,ascending = False):

    '''
        [INFO] : create a continuous layer, based in priority of date

        [INPUT] : path       = path to layer
                  date_field = field with date

        [OUTPUT] : out_put   = path to output layer
    '''
    if not ascending:
        ascending = False

    intersect = r'in_memory' + '\\' + 'intersect'

    if arcpy.Exists(intersect):
        arcpy.Delete_management(intersect)

    arcpy.Intersect_analysis([path], intersect, 'ALL', '', 'INPUT')
    field_id   = 'FID_' + os.path.basename(path)
    df         = Read_Fc(intersect)
    df['rank'] = df.groupby('SHAPE@WKT')[date_field].rank(method='first', ascending=ascending)
    df_del     = df[df['rank'] != 1][[field_id,'SHAPE@WKT']]
    list_del   = df_del[[field_id,'SHAPE@WKT']].values.tolist()

    arcpy.Delete_management(intersect)
    arcpy.Select_analysis  (path,out_put)

    with arcpy.da.UpdateCursor(out_put, ['OBJECTID','SHAPE@']) as cursor:
        for row in cursor:
            for del_lyr in list_del:
                geom_del = arcpy.FromWKT(del_lyr[1])
                id_del   = del_lyr[0]
                if row[0] == del_lyr[0]:
                    row[1] = row[1].difference(geom_del)
                    cursor.updateRow(row)
        del cursor

