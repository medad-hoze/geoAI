


import arcpy



def Multi_to_single(layer):
    
    multi = False
    len_before = int(str(arcpy.GetCount_management(layer)))
    temp_lyer = layer  + 'Temp'
    save_name = layer
    arcpy.MultipartToSinglepart_management (layer,temp_lyer)
    arcpy.Delete_management                (layer)
    arcpy.Rename_management                (temp_lyer,save_name)
    len_after = int(str(arcpy.GetCount_management(layer)))
    if len_after > len_before:
        multi = True

    return multi

def Simplify_Polygons(layer,Out_put,simplify = 10 ):

    arcpy.Copy_management (layer,Out_put)
    Multi_to_single       (Out_put)

    with arcpy.da.UpdateCursor(Out_put,["SHAPE@"]) as cursor:
        for row in cursor:
            row[0]   = row[0].generalize(float(simplify))
            cursor.updateRow(row)

    del cursor


