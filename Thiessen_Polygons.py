# -*- coding: utf-8 -*-

import arcpy
import numpy as np
from scipy.spatial.distance import cdist
import os
import requests,re,sys

arcpy.env.overwriteOutput = True

def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


def create_box_with_size(centroid_x,centroid_y,x_size,y_size):

    xmin = centroid_x - x_size/2
    xmax = centroid_x + x_size/2
    ymin = centroid_y - y_size/2
    ymax = centroid_y + y_size/2

    array = arcpy.Array([arcpy.Point(xmin, ymin),
                        arcpy.Point(xmin, ymax),
                        arcpy.Point(xmax, ymax),
                        arcpy.Point(xmax, ymin)])

    polygon = arcpy.Polygon(array)
    return polygon


def create_thiessen_arrey(in_points,num_array = 100):

    fields      = ['SHAPE@XY']
    point_array = arcpy.da.FeatureClassToNumPyArray(in_points, fields)

    xmin, ymin = np.min(point_array['SHAPE@XY'], axis=0)
    xmax, ymax = np.max(point_array['SHAPE@XY'], axis=0)

    x, y                  = np.meshgrid(np.linspace(xmin, xmax, num=num_array), np.linspace(ymin, ymax, num=num_array))
    grid_points           = np.column_stack((x.flatten(), y.flatten()))
    distances             = cdist(grid_points, point_array['SHAPE@XY'])
    closest_point_indices = np.argmin(distances, axis=1)

    polygon_array            = np.empty((len(grid_points),), dtype=[('SHAPE@X', 'f8'), ('SHAPE@Y', 'f8'), ('ID', 'i4')])
    polygon_array['SHAPE@X'] = grid_points[:, 0]
    polygon_array['SHAPE@Y'] = grid_points[:, 1]
    polygon_array['ID']      = closest_point_indices

    x_size = abs(x[0][0] - x[0][1])
    y_size = abs(y[0][0] - y[1][0])
        
    return polygon_array,x_size,y_size


def create_thiessen_polygon(in_points,out_polygons,accuracy = 100):

    polygon_array,x_size,y_size = create_thiessen_arrey(in_points,accuracy)

    if arcpy.Exists(out_polygons):
        arcpy.Delete_management(out_polygons)

    spatial_reference = arcpy.Describe(in_points).spatialReference
    path_,name_       = os.path.split(out_polygons)
    temp_polygons     = r'in_memory' + os.sep + name_

    arcpy.CreateFeatureclass_management(r'in_memory', name_, "POLYGON", spatial_reference=spatial_reference)

    add_field(temp_polygons,'ID'  ,Type = 'DOUBLE')

    cursor = arcpy.da.InsertCursor(temp_polygons, ['SHAPE@', 'ID'])
    for row in polygon_array:
        polygon = create_box_with_size(row['SHAPE@X'],row['SHAPE@Y'],x_size,y_size)
        cursor.insertRow([polygon, row['ID']])
    del cursor

    arcpy.Dissolve_management(temp_polygons, out_polygons, "ID", "", "MULTI_PART")
