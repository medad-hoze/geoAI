
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
        

def Delete_Identical_Byfield(path,fields,Out_put):

    arcpy.CopyFeatures_management  (path,Out_put)
    arcpy.RepairGeometry_management(path)

    keys = [row for row in arcpy.da.SearchCursor(path,fields)]
    keys = ['-'.join([convert_to_string(i) for i in key]) for key in keys]

    to_delete = set()
    del_count = 0
    with arcpy.da.UpdateCursor(Out_put,fields) as cursor:
        for row in cursor:
            key   = '-'.join([convert_to_string(i) for i in row])
            count = keys.count(key)
            if count > 1:               # delete Identical
                if key in to_delete:
                    del_count += 1
                    cursor.deleteRow()
            to_delete.add(key)

    arcpy.AddMessage('Total deleted: {}'.format(del_count))

    del cursor


