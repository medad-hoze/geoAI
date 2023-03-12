import arcpy
import requests,os,re,sys
import numpy as np

arcpy.env.overwriteOutput = True

def dist(coords):
    x1,y1,x2,y2 = coords
    return np.sqrt(pow(x2-x1,2) + pow(y2-y1,2))

def create_cutting_line(geometry, densify_distance):

    array = arcpy.Array()

    x1 = geometry.positionAlongLine (densify_distance).firstPoint.X-1
    y1 = geometry.positionAlongLine (densify_distance).firstPoint.Y-1
    x2 = geometry.positionAlongLine (densify_distance).firstPoint.X+1
    y2 = geometry.positionAlongLine (densify_distance).firstPoint.Y+1
    
    array.add(arcpy.Point(x1,y1))
    array.add(arcpy.Point(x2,y2))
    line_cut = arcpy.Polyline(array)
    return line_cut

def find_closest_dis(items,ref):
    items_ = {i.length: i for i in items}
    min_key = min(items_.keys(), key=lambda x:abs(x-ref))
    max_key = max(items_.keys(), key=lambda x:abs(x-ref))
    return items_[min_key],items_[max_key]

def create_line(output_polyline):
    arcpy.CreateFeatureclass_management(
        out_path=os.path.dirname(output_polyline),
        out_name=os.path.basename(output_polyline),
        geometry_type="POLYLINE",
    )
    arcpy.AddField_management(output_polyline, "LENGTH", "DOUBLE")
    return output_polyline



def split_line_by_distance(layer,out_put,distance_):


    create_line(out_put)
    distance_ = float(distance_)

    insert_fields = ["SHAPE@","LENGTH"]
    insert_cursor = arcpy.da.InsertCursor(out_put, insert_fields)
    fields        = ["SHAPE@LENGTH", "SHAPE@XY",'SHAPE@']

    with arcpy.da.SearchCursor(layer, fields) as cursor:
        for row in cursor:
            geom                = row[2]
            current_line_length = row[2].length

            while current_line_length + 0.1 > distance_:
                line_cut    = create_cutting_line (geom, distance_)
                min_,max_   = find_closest_dis    (geom.cut(line_cut),distance_)
                geom = max_
                insert_cursor.insertRow([min_,distance_])
                current_line_length = min_.length
    del cursor
    del insert_cursor


