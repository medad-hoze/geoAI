

# -*- coding: utf-8 -*-



import arcpy

arcpy.env.overwriteOutput = True


def create_output(fc,Out_put):

    if not Out_put == '':
        arcpy.CopyFeatures_management(fc,Out_put)
        return Out_put
    return fc


def del_0_area(Out_put):
    try:
        up_cursor = arcpy.UpdateCursor(Out_put)
        for row in up_cursor:
            geom = row.shape
            if geom.area == 0:
                up_cursor.deleteRow(row)
        del up_cursor
    except:
        pass


def analysis_Erase(fc,del_layer,Out_put):

    '''
    fc        = השכבה הראשית- שכבה ממנה רוצים למחוק
    del_layer = שכבה שתמחק את השכבה הראשית
    Out_put   = שכבת הפלט, במידה ולא תוכנס שכבה, ימחק מהשכבה הראשית
    '''

    def del_is_point(del_layer,Out_put):
        del_layer_temp = r'in_memory' + '\\' + 'Temp'
        arcpy.Dissolve_management(del_layer,del_layer_temp)

        geom_del = [row.shape for row in arcpy.SearchCursor (del_layer_temp)][0]
        Ucursor  = arcpy.UpdateCursor (Out_put)
        for row in Ucursor:
            point_shape = row.shape.centroid
            if geom_del.distanceTo(point_shape)== 0:
                Ucursor.deleteRow(row)
            else:
                pass
        del Ucursor
        del del_layer_temp 

    def del_is_polygon(del_layer,Out_put):
        count_me = int(str(arcpy.GetCount_management(del_layer)))
        if count_me > 0:
            temp = r'in_memory' +'\\'+'_temp'
            arcpy.Dissolve_management(del_layer,temp)
            if int(str(arcpy.GetCount_management(temp))) > 0:
                geom_del = [row.shape for row in arcpy.SearchCursor (temp)][0]
                Ucursor  = arcpy.UpdateCursor (Out_put)
                for row in Ucursor:
                    geom_up     = row.shape
                    try:
                        new_geom    = geom_up.difference(geom_del)
                        row.shape = new_geom
                        Ucursor.updateRow (row)
                    except:
                        pass
                del Ucursor
            arcpy.Delete_management(temp)
                    

    desc    = arcpy.Describe(fc)
    Out_put = create_output(fc,Out_put)

    if desc.ShapeType == u'Point':
        del_is_point(del_layer,Out_put)
    else:
        del_is_polygon(del_layer,Out_put)

    if desc.ShapeType == u'Polygon':del_0_area(Out_put)
    arcpy.RepairGeometry_management(Out_put)
    return Out_put


