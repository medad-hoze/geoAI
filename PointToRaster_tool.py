# -*- coding: utf-8 -*-

import arcpy ,os,sys
from osgeo import gdal,ogr


arcpy.env.overwriteOutput = True


class Layer_Management():
    def __init__(self,Layer):
        if arcpy.Exists(Layer):
            self.layer        = Layer
            desc = arcpy.Describe(Layer)
            if str(desc.shapeType) == 'Point':
                self.Geom_type = 'Point'
                self.geom_field = 'SHAPE@XY'
            elif str(desc.shapeType) == 'Polyline':
                self.Geom_type = 'Polyline'
                self.geom_field = 'SHAPE@LENGTH'
            else:
                self.Geom_type = 'Polygon'
                self.geom_field = 'SHAPE@AREA'
        else:
            arcpy.AddMessage (f"{Layer}, is not exist")
            print (f"{Layer}, is not exist")
            sys.exit(1)


def input_paramater_chack(param,polyon = True, polyline = True, point = True):

    layerMan  = Layer_Management(param)

    if layerMan.Geom_type == 'Polygon' and polyon is False:
        arcpy.AddMessage (f"{param}, cant be polygon")
        sys.exit(1)

    if layerMan.Geom_type == 'Polyline' and polyline is False:
        arcpy.AddMessage (f"{param}, cant be Polyline")
        sys.exit(1)

    if layerMan.Geom_type == 'Point' and point is False:
        arcpy.AddMessage (f"{param}, cant be Polyline")
        sys.exit(1)

    return layerMan.Geom_type


def Rasrize_point(input_path,field,output_raster_path,pixel_width = 1):

    input_paramater_chack(input_path,polyon = False, polyline = False, point = True)

    folder = os.path.dirname (os.path.dirname(input_path))
    name   = os.path.basename(input_path) + '.shp'
    shapefile_path = folder + '\\' + name

    if arcpy.Exists(shapefile_path): arcpy.Delete_management(shapefile_path)

    arcpy.Select_analysis(input_path,shapefile_path)

    shapefile   = ogr.Open(shapefile_path,0)
    layer       = shapefile.GetLayer()

    Xmin, Xmax, Ymin, Ymax = layer.GetExtent()

    div  = pixel_width/2
    col  = int((Xmax - Xmin)/div) 
    row  = int((Ymax - Ymin)/div) 
    Xmin = Xmin - 20
    Xmax = Xmax - 20


    # Create the output raster
    driver = gdal.GetDriverByName("GTiff")
    raster = driver.Create(output_raster_path, col, row, 1, gdal.GDT_Float32)

    raster.SetGeoTransform((int(Xmin), pixel_width, 0, int(Ymin), 0, pixel_width))
    gdal.RasterizeLayer(raster,[1], layer, burn_values=[1], options=[f"ATTRIBUTE={field}"])

    raster         = None
    shapefile_path = None




    
