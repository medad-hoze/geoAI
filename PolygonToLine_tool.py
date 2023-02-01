# -*- coding: utf-8 -*-

import os ,json,sys
import arcpy

# overwrite output files if they already exist
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



class Geom():
    def __init__(self,Geom,type_ = 'Polygon',roundValue=1):
        self.GeomJson   = json.loads(Geom.JSON)
        self.GeomJson   = self.GeomJson
        self.curveStart = []

        if type_ ==  'Polygon':
            if 'curveRings' in self.GeomJson.keys():
                self.isCurve = True
                self.strType = 'curveRings'
            else:
                self.isCurve = False
                self.strType = 'rings'
            self.geojson_polygon = {self.strType: [], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
        elif type_ ==  'Polyline':
            if 'curvePaths' in self.GeomJson.keys():
                self.strType = 'curvePaths'
                self.isCurve = True
            else:
                self.isCurve = False
                self.strType = 'paths'
            self.geojson_polygon = {self.strType: [], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
        else: 
            self.strType =  'Point'
            self.isCurve = False

        if type_ ==  'Polygon' or type_ ==  'Polyline':
            self.openGeom   = self.GeomJson[self.strType]
            self.roundValue = roundValue
            if len(self.openGeom) == 1:
                self.isSingalePart = True
                self.openGeom      = self.GeomJson[self.strType][0]
            else:
                self.isSingalePart = False
                self.openGeom      = self.GeomJson[self.strType]
        else:
            self.openGeom      = self.GeomJson
            self.isSingalePart = False


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


def createNewLayer(new_layer,template = "",geomType = "POLYGON"):
    name = os.path.basename(new_layer)
    path = os.path.dirname (new_layer)
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)
    arcpy.CreateFeatureclass_management(path, name, geomType,template)
    return new_layer

def Split_Line_By_Vertex  (aoi_line):

    Multi_to_single(aoi_line)
    New_Line  = aoi_line + '_Temp'
    save_name = aoi_line

    columns  = [f.name for f in arcpy.ListFields(aoi_line) if 'shape' not in f.name]
    columns  = columns +["SHAPE@"]

    arcpy.Select_analysis(aoi_line, New_Line, "\"OBJECTID\" < 0")
    iCursor = arcpy.da.InsertCursor(New_Line, columns)
    with arcpy.da.SearchCursor(aoi_line,columns) as sCursor:
        for row in sCursor:
            geom     = row[-1]
            GeomJson = json.loads(geom.JSON)
            typeStr = 'paths'
            if 'curvePaths' in GeomJson.keys():
                typeStr = 'curvePaths'
            for part in GeomJson[typeStr]:
                prevX = None
                prevY = None
                for pnt in part:
                    if prevX:
                        if type(pnt) == dict:
                            array = [[prevX, prevY],pnt]
                        else:
                            array = [[prevX, prevY],[pnt[0], pnt[1]]]
                        
                        line      = {typeStr: [array], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                        polyline  = arcpy.AsShape(line,True)
                        iCursor.insertRow(list(row)[:-1] + [polyline])

                    if type(pnt) == dict:
                        prevX = pnt['c'][0][0]
                        prevY = pnt['c'][0][1]
                    else:
                        prevX = pnt[0]
                        prevY = pnt[1]
                else:
                    pass

    arcpy.Delete_management                (aoi_line)
    arcpy.Rename_management                (New_Line,save_name)

    return save_name

def PolygonToLine(polygon,line_output):

    """
    convert polygon geometry to lines
    
    Parameters:
        polygon (str)    : Path to the polygon feature class.
        line_output (str): Path to the polyline output .
    """

    input_paramater_chack (polygon,polyon = True)

    createNewLayer        (line_output,polygon,'POLYLINE')

    columns  = [f.name for f in arcpy.ListFields(line_output) if 'shape' not in f.name]
    columns  = columns +["SHAPE@"]
    insert   = arcpy.da.InsertCursor(line_output,columns)

    with arcpy.da.SearchCursor(polygon,columns) as cursor:
        for row in cursor:
            ClassGeom = Geom(row[-1])
            if ClassGeom.isCurve:
                lineStrType = 'curvePaths'
            else:
                lineStrType = 'paths'

            if not ClassGeom.isSingalePart:
                for i in ClassGeom.GeomJson[ClassGeom.strType]:
                    geojson_polyline = {lineStrType: [i], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                    polyline         = arcpy.AsShape(geojson_polyline,True)
                    insert_data      = list(row)[:-1] + [polyline]
                    
                    insert.insertRow(insert_data)
            
            else:
                geojson_polyline = {lineStrType: ClassGeom.GeomJson[ClassGeom.strType], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                polyline         = arcpy.AsShape(geojson_polyline,True)
                insert_data      = list(row)[:-1] + [polyline]
                insert.insertRow(insert_data)

    insert = cursor = None

    Split_Line_By_Vertex  (line_output)

