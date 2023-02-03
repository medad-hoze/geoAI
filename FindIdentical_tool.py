
# -*- coding: utf-8 -*-

import arcpy,os

arcpy.env.overwriteOutput = True

def convert_to_string(value):
    if isinstance(value, int):
        return str(value)
    elif isinstance(value, float):
        return str(round(value, 2))
    elif isinstance(value, str):
        return value
    elif isinstance(value, tuple):
        return '(' + str(round(value[0],3)) + ',' + str(round(value[1],3)) + ')'
    else:
        return str(value)


def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:arcpy.AddField_management (fc, field, Type, "", "", 500)
        

def Find_Identical_Byfield(path,fields):

    arcpy.RepairGeometry_management(path)

    keys = [row for row in arcpy.da.SearchCursor(path,fields)]
    keys = ['-'.join([convert_to_string(i) for i in key]) for key in keys]

    add_field(path,'Count_Identical','LONG')

    fields = fields + ['Count_Identical']


    with arcpy.da.UpdateCursor(path,fields) as cursor:
        for row in cursor:
            key     = '-'.join([convert_to_string(i) for i in row[:-1]])
            count   = keys.count(key)
            row[-1] = count
            cursor.updateRow(row)

    del cursor


