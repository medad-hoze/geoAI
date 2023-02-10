# -*- coding: utf-8 -*-
import requests

import os,glob,sys,re
import tempfile
import datetime

from osgeo import ogr
from osgeo import osr
from osgeo import gdal

import arcpy,os,json
import pandas as pd
import tempfile
import operator
from difflib import SequenceMatcher
from operator import itemgetter

import numpy as np
arcpy.env.overwriteOutput = True


def find_number_in_sentance(text):
    number = re.findall(r'\b\d+\b', text)
    if number:
        return number[0]
    else:
        return 5


def find_word_after(text:str,keywords_first:list):
    text        = text.split()
    text        = [''] + text
    for i in range(len(text)):
        if text[i].lower() in keywords_first:
            if text[i-1] not in ['layer','fc','shp','layers','fcs','shps','table','tables']:
                if len(text[i+1]) > 1:
                    if text[i+1] not in['to','too','two']:
                        return text[i+1]
    return ''

def find_field_name(text:str):
    '''
    find field that not exists in any layer, field need to be added
    '''
    keywords_first    = ['name','names']
    keywords_second   = ['field','fields','column','columns']

    a = find_word_after(text,keywords_first)
    if a: return a
    return find_word_after(text,keywords_second)


def find_type_in_text(sentences:list):

    types = {'TEXT':['string','text'],'DOUBLE':['decimal','double','float'],
            'LONG':['long','short','integer'],'DATE':['date','time']}
    flat_list = [item for sublist in [types[key] for key in types] for item in sublist]
    type_     = ''
    score     = 0
    type_pick = ''
    for word in sentences:
        for type_word in flat_list:
            word = word.lower()
            match_ratio = SequenceMatcher(None, word, type_word).ratio()
            if match_ratio > score:
                score = match_ratio
                if match_ratio > 0.7:
                    type_ = type_word
                    score = match_ratio

    for key in types.keys():
        if type_ in types[key]:
            type_pick = key
            return type_pick
    return type_pick


def getLayerOnMap(path_layer):
    if not arcpy.Exists(path_layer):return 
    try:
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.listMaps("Map")[0] 
        lyr = aprxMap.addDataFromPath(path_layer)
        # aprxMap.addLayer(lyr)
        aprx.activeView

        del aprxMap
        del aprx
    except:
        pass


def create_out_put(InputsManager):

    gdb     = os.path.dirname(InputsManager.mainInput.data_source)
    out_put = [input_.layer for input_ in InputsManager.all_inputs if 'out_put' in input_.layer]

    if out_put:
        out_put           = sorted(out_put)[-1]
        old_name_num      = out_put.split('_')[-1]
        old_name_num      = str(find_number_in_sentance(old_name_num))
        new_name_num      = str(int(old_name_num) + 1)
        name_output_layer = gdb + '\\' + out_put.replace(old_name_num,new_name_num)
    else:
        name_output_layer = gdb + '\\' + 'out_put_1'

    if arcpy.Exists(name_output_layer +'\\' + '_Temp'):
        arcpy.Delete_management(name_output_layer +'\\' + '_Temp')

    return name_output_layer


def find_data_source(sentences):
    path_dataSorce = ''
    sentences        = [''] + sentences.split()
    length           = len(sentences)
    for i in range(length):
        full_search = ''
        for j in range(i+1,length):
            words = sentences[j]
            full_search += words + ' '
            if os.path.exists(full_search):
                path_dataSorce = full_search

    path_dataSorce = path_dataSorce.rstrip()
    return path_dataSorce


def find_city(data_SETL,sentance):
    cities = [i[1] for i in data_SETL]
    sentance = sentance.split()
    city_final = ''
    for city in cities:
        similar_field = 0
        for word in sentance:
            word = word.lower()
            city = city.lower()
            match_ratio = SequenceMatcher(None, word, city).ratio()
            if match_ratio > similar_field:
                similar_field =  match_ratio
                if match_ratio > 0.7:
                    city_final = city
    return city_final


def find_type_for_feature_to_point(sentance):
    types_accepted = ["INSIDE","CENTROID"]
    sentance = sentance.split()
    type_ = ''
    score = 0
    for word in sentance:
        for type_word in types_accepted:
            word = word.lower()
            match_ratio = SequenceMatcher(None, word, type_word).ratio()
            if match_ratio > score:
                score = match_ratio
                if match_ratio > 0.7:
                    type_ = type_word
    
    if type_ == '':
        type_ = 'INSIDE'
    
    return type_


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


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


def Split_Line_By_Vertex_tool  (aoi_line,out_put):

    temp = aoi_line + 'Temp'

    arcpy.MultipartToSinglepart_management (aoi_line,temp)


    columns  = [f.name for f in arcpy.ListFields(temp) if 'shape' not in f.name]
    columns  = columns +["SHAPE@"]

    arcpy.Select_analysis(temp, out_put, "\"OBJECTID\" < 0")
    iCursor = arcpy.da.InsertCursor(out_put, columns)
    with arcpy.da.SearchCursor(temp,columns) as sCursor:
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

    if arcpy.Exists(temp):arcpy.Delete_management(temp)
    return out_put


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


def create_output(fc,Out_put):

    if not Out_put == '':
        arcpy.CopyFeatures_management(fc,Out_put)
        return Out_put
    return fc


def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:arcpy.AddField_management (fc, field, Type, "", "", 500)


def Read_Fc(addr,num_rows = 9999999):
    # read fc to pandas dataframe 
    columns = [f.name for f in arcpy.ListFields(addr) if f.name.lower() not in ('shape')]
    df       = pd.DataFrame(data = [row for row in arcpy.da.SearchCursor\
               (addr,columns,"\"OBJECTID\" < {}".format(num_rows))],columns = columns)
    
    return df


def delete_layers(deletelayers):
    for i in deletelayers:arcpy.Delete_management(i)


def convertToCodes(value,groundValue = 1):
    '''
    convertToCodes(324.214,695.223,1)  --->  '324.2_695.2'
    '''
    if type(value) == list:
        return str(round(value[0],groundValue)) + '_' +str(round(value[1],groundValue)) 
    return str(value)


arcpy.env.overwriteOutput = True

def FeatureVerticesToPoints(layer,outPut):

    '''
    get polygon or polyline and return vertics
    '''

    createNewLayer(outPut,layer,'POINT')

    name       = os.path.basename(layer)
    field_name = 'FID_'+ name
    OID        = str(arcpy.Describe(outPut).OIDFieldName)

    add_field(outPut,field_name,'LONG')
    arcpy.CalculateField_management (outPut, field_name,f"!{OID}!", "PYTHON")

    columns    = [f.name for f in arcpy.ListFields(layer) if f.name not in ('SHAPE','Shape_Length','Shape_Area','Shape')] + ["SHAPE@"] + [field_name]
    ins_cursor = arcpy.da.InsertCursor (outPut, columns)
    OID_in     = str(arcpy.Describe(layer).OIDFieldName)
    poly_data  = [list(i[:-1]) + [arcpy.PointGeometry(arcpy.Point(j.X,j.Y))] + [i[columns.index(OID_in)]]
                       for i in arcpy.da.SearchCursor (layer,columns[:-1]) for n in i[-1] for j in n if j]


    for i in poly_data:ins_cursor.insertRow (i)  



def dist(coords):
    x1,y1,x2,y2 = coords
    return np.sqrt(pow(x2-x1,2) + pow(y2-y1,2))
        

def createSpatial_index(layer,line_lyr,buffer_size):

    vertx_poly   = layer      + '_vertx'
    buffer_poly  = vertx_poly + '_buff' 
    vertx_line   = line_lyr   + '_vertic'
    lyr_inter    = layer      + 'inter'

    FeatureVerticesToPoints (layer   ,vertx_poly)

    geom_type = Layer_Management(line_lyr).Geom_type
    if geom_type != 'Point': 
        FeatureVerticesToPoints (line_lyr,vertx_line)
    else: 
        arcpy.Copy_management(line_lyr,vertx_line)


    add_field                (vertx_poly, "X","DOUBLE")
    add_field                (vertx_poly, "Y","DOUBLE")
    arcpy.CalculateGeometryAttributes_management(vertx_poly,[['Y','POINT_Y'],['X','POINT_X']])  


    arcpy.Buffer_analysis    (vertx_poly,buffer_poly,f"{buffer_size} Meters")
    arcpy.Intersect_analysis ([buffer_poly,vertx_line],lyr_inter)


    add_field                (lyr_inter, "X_line","DOUBLE")
    add_field                (lyr_inter, "Y_line","DOUBLE")
    arcpy.CalculateGeometryAttributes_management(lyr_inter,[['Y_line','POINT_Y'],['X_line','POINT_X']])  

    name_layer        = os.path.basename(layer)
    name_lyr_field    =  'FID_'+name_layer

    name_buffer       = os.path.basename(buffer_poly)
    name_buffer_field = 'FID_' + name_buffer

    df = Read_Fc(lyr_inter)
    df = df[['X','Y','Y_line','X_line',name_lyr_field,name_buffer_field]]

    if df.empty: return

    df['distance'] = df[['X','Y','X_line','Y_line']].apply(lambda x: dist(x), axis = 1)

    gb        = df.groupby([name_lyr_field,name_buffer_field])['distance'].min().reset_index()
    merged_df = pd.merge(df, gb, on=[name_lyr_field, name_buffer_field], how='inner')
    df_stay   = merged_df.query("distance_x == distance_y")

    df_stay['key'] = df_stay['X'].round(1).astype(str) + '_' + df_stay['Y'].round(1).astype(str)

    df_stay        = df_stay[['key',name_lyr_field,'X_line','Y_line']]

    grouped_df = df_stay.groupby(name_lyr_field).apply(lambda x: x.to_dict('split')).to_dict()
    output     = {}
    for key, value in grouped_df.items():
        output[key] = {}
        for data_list in value['data']:
            key_name = str(data_list[0])
            if key_name not in output[key]:
                output[key][key_name] = []
            output[key][key_name].append([data_list[2],data_list[3]])


    delete_layers([vertx_line,vertx_poly,buffer_poly,lyr_inter])

    return output



def Snap(layer,snap_to,out_put,distance):

    geom_layer = Layer_Management(layer).Geom_type

    index_dis = createSpatial_index(layer,snap_to,distance)

    arcpy.Copy_management(layer,out_put)
    with arcpy.da.UpdateCursor(out_put,['SHAPE@','OBJECTID']) as Ucursor:
        for i in Ucursor:

            geom = Geom(i[0],geom_layer)

            geoms = geom.GeomJson[geom.strType]
            rings_all = []
            if not index_dis: continue
            if i[1] not in index_dis.keys(): continue
            dict_moveOrder = index_dis[i[1]]
            for part in geoms:
                rings = []
                for pt in part:
                    if type(pt) != dict:  
                        key = convertToCodes([pt[0],pt[1]])
                        if key in dict_moveOrder:
                            rings.append(dict_moveOrder[key][0])
                        else:
                            rings.append([pt[0],pt[1]])
                    else:
                        key1 = convertToCodes(pt['c'][0])
                        key2 = convertToCodes(pt['c'][1])
                        if (key1 in dict_moveOrder) or (key2 in dict_moveOrder):
                            if key1 in dict_moveOrder:
                                pt['c'][0] = dict_moveOrder[key1][0]
                            if key2 in dict_moveOrder:
                                pt['c'][1] = dict_moveOrder[key2][0]
                            rings.append(pt)
                        else:
                            rings.append(pt)

                rings_all.append(rings)

            if i[0].isMultipart is True:
                geom.GeomJson[geom.strType] = rings_all
                polygon    = arcpy.AsShape(geom.GeomJson,True)
            else:
                geom.geojson_polygon[geom.strType] = rings_all
                polygon    = arcpy.AsShape(geom.geojson_polygon,True)
            
            i[0] = polygon
            Ucursor.updateRow(i)

    del Ucursor



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


def set_ISR(filename):
    target_srs = 'EPSG:2039'
    ds = gdal.Open(filename, gdal.GA_Update)
    gdal.Warp(ds, ds, dstSRS=target_srs)
    ds = None

def RasterToPolygon(filename,out_put):


    set_ISR(filename)
    arcpy.AddMessage(filename)
    ds  = gdal.Open( filename )

        # def polygonize(self,shp_path):
    # mapping between gdal type and ogr field type
    type_mapping = {gdal.GDT_Byte: ogr.OFTInteger,
                    gdal.GDT_UInt16: ogr.OFTInteger,
                    gdal.GDT_Int16: ogr.OFTInteger,
                    gdal.GDT_UInt32: ogr.OFTInteger,
                    gdal.GDT_Int32: ogr.OFTInteger,
                    gdal.GDT_Float32: ogr.OFTReal,
                    gdal.GDT_Float64: ogr.OFTReal,
                    gdal.GDT_CInt16: ogr.OFTInteger,
                    gdal.GDT_CInt32: ogr.OFTInteger,
                    gdal.GDT_CFloat32: ogr.OFTReal,
                    gdal.GDT_CFloat64: ogr.OFTReal}

  
    srcband       = ds.GetRasterBand (1)
    dst_layername = "Shape"

    # Create polygon
    shp_path     = os.path.dirname(filename) + '\\' + 'temp.shp'
    drv          = ogr.GetDriverByName      ("ESRI Shapefile")
    dst_ds       = drv.CreateDataSource     (shp_path)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(2039)
    dst_layer    = dst_ds.CreateLayer       (dst_layername, sr,ogr.wkbPolygon)
    raster_field = ogr.FieldDefn            ('id', type_mapping[srcband.DataType]) # get gdal based field type to ogr 

    dst_layer.CreateField     (raster_field)
    gdal.Polygonize           (srcband, srcband, dst_layer, 0,['id'], callback=None)

    dst_ds.Destroy()

    del dst_layer
    del srcband
    
    arcpy.Select_analysis   (shp_path,out_put)
    arcpy.Delete_management (shp_path)




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




def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)

def combine_str(list_):
    #  take list of values and connect by '-'
    list_ = [str(i) for i in list_]
    if len(list_) > 1:
        return '-'.join(list_)
    elif len(list_) == 1:
        return list_[0]
    else:
        print ('error no id field is found')
        sys.exit(1)


def updated_data(list_):
    if len(list_) == 1:
        return list_[0]
    return list_

def extract_data_key_value(path_layer,field1_ids,field1_data):
    fields_all = field1_ids + field1_data
    len_id     = len(field1_ids)
    data       = {combine_str(row[:len_id]): updated_data(row[len_id:]) 
            for row in arcpy.da.SearchCursor(path_layer,fields_all)}
    return data


def update_columns_by_key(update_layer,field2_ids,field2_update,data,field1_data):
    for i in field2_update: add_field(update_layer,i)

    fields_all2 = field2_ids + field2_update
    len_id2     = len(field2_ids)

    if len(field1_data) != len(field2_update):
        print ('updated fields and data source fields must be the same number')
        sys.exit(1)

    with arcpy.da.UpdateCursor(update_layer,fields_all2) as Ucursor:
        for row in Ucursor:
            id = combine_str(row[:len_id2])
            if data.get(id):
                if len(row[len_id2:]) == 1:
                    row[-1] = data[id]
                else:
                    row[len_id2:] = data[id]

                Ucursor.updateRow(row)
    del Ucursor


def get_ID_value(text):
    text= text.split(';')

    id_    = []
    value_ = []
    for i in text:
        split_me = i.split(' ')
        if (split_me[0] != '#'): 
            id_.append(split_me[0])
        if (split_me[1] != '#'):
            value_.append(split_me[1])

    return id_,value_


def join_field(source_layer,field1_ids,field1_data,update_layer,field2_ids,field2_update):
    # extract data from path_layer
    if (field1_ids == None) or (field1_data == None):return None
    data         = extract_data_key_value(source_layer,field1_ids,field1_data)

    if (field2_ids == None):
        return None
    if (field1_data == None):
        return None
    # update data in update_layer by the data extracted 
    update_columns_by_key(update_layer,field2_ids,field2_update,data,field1_data)



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
		

def dpi(raster):
	RowCount = int(str(arcpy.GetRasterProperties_management(str(raster),"ROWCOUNT")))
	if RowCount > 14000 and RowCount < 16200:
		return 1588
	elif RowCount < 13001 and RowCount > 2000:
		return 1270
	elif RowCount > 16201:
		return 2117
	else:
		return 0

	
def convert_bytes(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.lf %s" % (num,x)
        num /= 1024.0

				
def file_size(file_path):
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            return convert_bytes(file_info.st_size)
    else:
        return 'no file found'

				
def GEtTypeFromString(text):
	Types = ['DEM','dem','raster','Raster','Photo','PHOTO','NDSM','DSM','DTM','NDSM','ndsm,dsm','aster']
	for i in Types:
		if i in text:
			return str(i)
		else:
			pass

			
def raster_type(text):
    if text.find('.') > -1:
        return text.split ('.')[-1]
    else:
        return text.split ('\\')[-1]

				
def get_accurancy_dict(dic):
        return {k:list(str(dic.values())).count(i) for k,i in dic.items()}


def modification_date(filename):
    try:
        gt    = os.path.getmtime(filename)
        time  = datetime.datetime.fromtimestamp(gt)
        year_ = time.year
        month_= time.month
        return month_,year_
    except:
        return 0,0


def Get_raster_Min_Max(ras):
    try:
        inRas     = arcpy.Raster             (ras)
        arr       = arcpy.RasterToNumPyArray (inRas, nodata_to_value=0)
        min_,max_ = arr.min(),arr.max()
        return str(min_),str(max_)
    except:
        return "No Data","No Data"


def Get_cell_Size(Ras):
    try:
        cell_size = str(arcpy.GetRasterProperties_management (Ras, "CELLSIZEX"))
        return cell_size
    except:
        return "coudnt find Cell Size"


def Get_bands(Ras):
    try:
        band = str(arcpy.GetRasterProperties_management(str(Ras), "BANDCOUNT"))
        return band
    except:
        return "not Found"



def Create_Csv(outFile,data):
    outFile  = os.path.dirname(outFile)
    output   = os.path.dirname(outFile) +"\\" + "geometry_chack.csv"
    df_csv   = pd.DataFrame(data = [data]    ,columns=["Raster_path","ras_name","ras_date","year","ras_type","min_","max_","size_file","dpi_ras","cell_size","band","TypeRaster","time_","X_Y","Coord"])

    if not os.path.exists(output):
        df_csv.to_csv   (output)
    else:
        df_csv.to_csv   (output,mode = 'a',header = False)

    return output

def Create_Csv_error(outFile,data):
    outFile   = os.path.dirname(outFile)
    output2   = os.path.dirname(outFile) +"\\" + "errors.csv"
    df_error  = pd.DataFrame(data = data,columns=["Raster_path"])

    if not os.path.exists(output2):
        
        df_error.to_csv (output2)
    else:
        df_error.to_csv (output2,mode = 'a',header = False)

    return output2

def fix_str(str1):

    if len(str1) >499:
        num = len(str1)
        while num > 499:
            str1 = os.path.dirname(str1)
            num  = len(str1)
    return str1


def Get_X_Y(Geometry):
    Diff_coord = 'ok'
    if Geometry[0] < 10000 or Geometry[1] < 10000:
        Diff_coord = 'Warning'

    return str(Geometry[0]) + '-' + str(Geometry[1]),Diff_coord


def Envelope_Geom(Xmin, Ymin, Xmax, Ymax,spatial_referance = ''):
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    if spatial_referance == '':
        spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance)
    return polygon


def Get_fcs_shps(folders):
    list_shp = []
    list_fc  = []
    for Folder in folders:
        for root, dirs, files in os.walk(Folder):
            for file in files:
                if file.endswith(".shp"):
                    list_shp.append(root + '\\' +file)
            if root.endswith(".gdb"):
                arcpy.env.workspace = root
                fcs = [root + '\\' + i for i in arcpy.ListFeatureClasses()]
                list_fc.extend(fcs)

    return list_fc,list_shp


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


def gdb_or_shp(name):
    if name.endswith('.shp'):
        return 'shp'
    elif '.gdb' in name:
        return 'gdb'
    else:
        return 'Unknown'

def Find_Rasters(inDir,outFile):

    exists_rasters = []

    if arcpy.Exists(outFile):
        exists_rasters = [str(i[0]) for i in arcpy.da.SearchCursor(outFile,['RasterPath'])]

    feature_classes = [root +'\\' + file for i in inDir for root, dirs, files in os.walk(i) for file in files if (file.endswith('tiff')\
                   or file.endswith('tif')) and root +'\\' + file if str(root) +'\\' + str(file) not in exists_rasters]
                
    if not arcpy.Exists(outFile): arcpy.CreateFeatureclass_management (os.path.dirname (outFile), os.path.basename (outFile), "POLYGON")

    arcpy.AddMessage("Number of Rasters: " + str(len(feature_classes)))

    sr = arcpy.SpatialReference(2039) # (3765)
    arcpy.DefineProjection_management(outFile, sr)

    list_of_fields = [["RasterName","String"] ,["RasterPath","String"]  ,["Bands",'String']   ,["definition","String"],\
                    ["Cell_Size",'String']    ,["Raster_Type","String"] ,["Time",'String']    ,["File_Size",'String' ],\
                    ["dpi",'double']          ,['Date_made',"double"]   ,['min_pix','String'] ,['max_pix','String'   ] ,\
                    ['X_Y','String']          ,["Year",'double']        ,['Coord','String']   ,['crs','String']      ]
                    

    for i in list_of_fields: arcpy.AddField_management (outFile, i[0], i[1], "", "", 500)

    cursor  = arcpy.InsertCursor (outFile)
    point   = arcpy.Point ()
    array   = arcpy.Array ()
    corners = ["lowerLeft", "lowerRight", "upperRight", "upperLeft"]

    error_files  = []
    min_max_key  = {}
    Geometry_key = {}

    count = 1
    for Ras in feature_classes:
        error_files = []
        try:	
            Geometry     = []
            feat = cursor.newRow ()
            r = arcpy.Raster (Ras)
            for corner in corners:
                    point.X = getattr (r.extent, "%s" % corner).X
                    point.Y = getattr (r.extent, "%s" % corner).Y
                    x = getattr (r.extent, "%s" % corner).X
                    y = getattr (r.extent, "%s" % corner).Y
                    Geometry.append(x)
                    Geometry.append(y)
                    array.add (point)
            
            Geometry_key[Ras] = Geometry
                    
            array.add (array.getObject (0))
            polygon    = arcpy.Polygon (array)
            feat.shape = polygon

            ras_path   = fix_str (Ras)
            date_,year = modification_date  (Ras)
            ras_type   = raster_type        (Ras)
            min_,max_  = Get_raster_Min_Max (Ras)
            size_file  = file_size          (Ras)
            dpi_ras    = dpi                (Ras)
            cell_size  = Get_cell_Size      (Ras)
            band       = Get_bands          (Ras)
            TypeRaster = GEtTypeFromString  (Ras)
            time_      = str(datetime.datetime.now()).split(' ')[0]
            ras_name   = Ras.split ('\\')[-1].split('.')[0]
            X_Y,warn   = Get_X_Y(Geometry)
            crs        = Get_crs(Ras)

            feat.setValue ("RasterName" ,ras_name)
            feat.setValue ("RasterPath" ,ras_path)
            feat.setValue ("Raster_Type",ras_type)
            feat.setValue ("Date_made"  ,date_)
            feat.setValue ("Year"       ,year)
            feat.setValue ("min_pix"    ,min_)
            feat.setValue ("max_pix"    ,max_)
            feat.setValue ("Bands"      ,band)
            feat.setValue ("definition" ,str(TypeRaster))
            feat.setValue ("Cell_Size"  ,cell_size)
            feat.setValue ("dpi"        ,dpi_ras)
            feat.setValue ("Time"       ,time_)
            feat.setValue ("File_Size"  ,size_file)
            feat.setValue ("X_Y"        ,X_Y)
            feat.setValue ("Coord"      ,warn)
            feat.setValue ('crs'        ,crs)


            min_max_key[Ras] = min_+'-'+ max_
            cursor.insertRow (feat)
            array.removeAll  ()
            del Geometry

        except:
            arcpy.AddMessage('failes to add raster: '+ Ras)
            error_files.append(Ras)
            # Create_Csv_error   (outFile,data_excel)

        count += 1

    del cursor


def ShapeType(layer):
    desc          = arcpy.Describe(layer)
    if str(desc.shapeType) == 'Point':
        Geom_type = 'POINT'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'POLYLINE'
    else:
        Geom_type = 'POLYGON'
    return Geom_type


def Get_crs(fc):
    return arcpy.Describe(fc).spatialReference.name


def get_name(path):
    name_all = os.path.basename(path)
    if name_all.endswith('.shp'):
        name_all = name_all.split('.')[0]
    return name_all

def Find_layers(Folder,outFile):

    list_fc,list_shp = Get_fcs_shps(Folder)

    exists_path = []
    if arcpy.Exists(outFile):
        exists_path = [i[0] for i in arcpy.da.SearchCursor(outFile,['Path'])]
    else:
        arcpy.CreateFeatureclass_management (os.path.dirname (outFile), os.path.basename (outFile), "POLYGON")

    fields_to_add = [['Path','TEXT'],['Num_features','DOUBLE'],['Year_Created','LONG'],['Month_Created','LONG'],['Type','TEXT'],['File_size','TEXT'],['Geom_type','TEXT'],['crs','TEXT'],['Name','TEXT']]

    for i in fields_to_add: add_field(outFile,i[0],i[1])

    fields   = ['SHAPE@','Path','Num_features','Year_Created','Month_Created','Type','File_size','Geom_type','crs','Name']
    insert   = arcpy.da.InsertCursor(outFile,fields)
    list_all = list_fc + list_shp
    list_all = [i for i in list_all if i not in exists_path]

    count   = 1
    for layer in list_all:
        num_feat   = int(str(arcpy.GetCount_management(layer)))
        if num_feat < 0:
            count += 1
            continue
        s_r        = arcpy.Describe (layer).spatialReference
        extent     = arcpy.Describe(layer).extent

        Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

        month_,year_           = modification_date (layer)
        type_                  = gdb_or_shp        (layer)
        file_size_             = file_size         (layer)
        polygon                = Envelope_Geom     (Xmin, Ymin, Xmax, Ymax,s_r)
        geom_type              = ShapeType         (layer)
        crs                    = Get_crs           (layer)
        name                   = get_name          (layer)


        insert.insertRow ([polygon,layer,num_feat,year_,month_,type_,file_size_,geom_type,crs,name])
        count += 1
    del insert
        

    arcpy.RepairGeometry_management(outFile)


def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"
    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, str(GDB_name), "CURRENT"))
    return fgdb_name

def get_date_as_name():
        time  = datetime.datetime.now()
        return 'Date_' + str(time.year) + '_' + str(time.month) + '_' + str(time.day)



def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def Envelope_Geom_by_Geom(geom,spatial_referance = ''):
    extent = geom.extent
    Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    if spatial_referance == '':
        spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance)
    return polygon


def remove_decimal(input_str):
    output_str = re.sub(r'(\d+\.\d+)', lambda m: str(int(float(m.group(1)))), input_str)
    return output_str


def isHebrew(name_input:str) -> bool:
    '''
    Check if the input string is in Hebrew, if so return True
    '''
    return any("\u0590" <= c <= "\u05EA" for c in name_input)


def get_settlement_to_layer(data_SETL,name_input:str,out_put:str) -> str:

    if arcpy.Exists(out_put):arcpy.Delete_management(out_put)

    ishebrew    = isHebrew(name_input)
    field_check = 'SETL_NAME' if ishebrew else 'SETL_NAME_LTN'

    df            = pd.DataFrame(data_SETL,columns= ['SETL_NAME','SETL_NAME_LTN','SETL_CODE','SHAPE'])
    df['Similar'] = df[field_check].apply(lambda x: similar(x,name_input))
    df            = df[df['Similar'] > 0.5]
    if not df.empty:
        df   = df[df['Similar'] ==  df['Similar'].max()]
        geom = arcpy.FromWKT(df['SHAPE'].values[0])
        arcpy.CopyFeatures_management(geom,out_put)
        return out_put
    else:
        arcpy.AddMessage('No settlement found')

def zoom_in(layer):

    '''
    layer: layer to zoom to
    '''

    extent= arcpy.Describe(layer).extent
    aprx= arcpy.mp.ArcGISProject('CURRENT')
    arcpy.AddMessage(aprx)
    mv  = aprx.activeView
    arcpy.AddMessage(str(mv))
    mv.camera.setExtent(extent)

def create_gdb_temp():
    gdb_temp      = tempfile.gettempdir() + '\\' + 'temp.gdb'
    if arcpy.Exists(gdb_temp): arcpy.Delete_management(gdb_temp)
    arcpy.CreateFileGDB_management(tempfile.gettempdir(),'temp.gdb')
    return gdb_temp

def getRasterOnMap(temp_layer,raster_RGB,intersects,folderName):

    if arcpy.Exists(intersects): arcpy.Delete_management(intersects)

    if not raster_RGB: return
    arcpy.Intersect_analysis([temp_layer,raster_RGB],intersects)

    rasterList = list(set([row[0] for row in arcpy.da.SearchCursor(intersects,[folderName])]))

    try:
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.listMaps("Map")[0] 

        for row in rasterList:
            lyr = aprxMap.addDataFromPath(row)
            # aprxMap.addLayer(lyr)
            aprx.activeView

        del aprxMap
        del aprx

        return intersects
    except:
        print ('run on test mode')


def removeRastersFromMap(mxd_path,removename):
    p = arcpy.mp.ArcGISProject (mxd_path)
    m   = p.listMaps('Map')[0]
    delete_templates = [m.removeLayer(i) for i in m.listLayers() if (removename in i.dataSource)]


def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')


def set_ISR(filename):
    target_srs = 'EPSG:2039'
    ds = gdal.Open(filename, gdal.GA_Update)
    gdal.Warp(ds, ds, dstSRS=target_srs)
    ds = None



def RasterToPolygon(filename,out_put):


    set_ISR(filename)
    ds  = gdal.Open( filename )

        # def polygonize(self,shp_path):
    # mapping between gdal type and ogr field type
    type_mapping = {gdal.GDT_Byte: ogr.OFTInteger,
                    gdal.GDT_UInt16: ogr.OFTInteger,
                    gdal.GDT_Int16: ogr.OFTInteger,
                    gdal.GDT_UInt32: ogr.OFTInteger,
                    gdal.GDT_Int32: ogr.OFTInteger,
                    gdal.GDT_Float32: ogr.OFTReal,
                    gdal.GDT_Float64: ogr.OFTReal,
                    gdal.GDT_CInt16: ogr.OFTInteger,
                    gdal.GDT_CInt32: ogr.OFTInteger,
                    gdal.GDT_CFloat32: ogr.OFTReal,
                    gdal.GDT_CFloat64: ogr.OFTReal}

  
    srcband       = ds.GetRasterBand (1)
    dst_layername = "Shape"

    # Create polygon

    if os.path.exists(out_put): os.remove(out_put)
    drv          = ogr.GetDriverByName      ("ESRI Shapefile")
    dst_ds       = drv.CreateDataSource     (out_put)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(2039)
    dst_layer    = dst_ds.CreateLayer       (dst_layername, sr,ogr.wkbPolygon)
    raster_field = ogr.FieldDefn            ('id', type_mapping[srcband.DataType]) # get gdal based field type to ogr 

    dst_layer.CreateField     (raster_field)
    gdal.Polygonize           (srcband, None, dst_layer, -1,[], callback=None)

    dst_ds.Destroy()

    del dst_layer
    del srcband
    


def isLayer(layer):

    if not arcpy.Exists(layer): return False
    desc       = arcpy.Describe(layer)
    type_layer = desc.dataType
    if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):
        return 'layer'
    elif type_layer == "RasterDataset":
        return 'raster'
    else:
        return 'city'

def delete_if_exist(layers):
    for layer in layers:
        if arcpy.Exists(layer):
            try:
                arcpy.Delete_management(layer)
            except:
                pass



# def removeRastersFromMap(removename):
#     p = arcpy.mp.ArcGISProject ('CURRENT')
#     m   = p.listMaps('Map')[0]
#     delete_templates = [m.removeLayer(i) for i in m.listLayers() if (removename in i.dataSource)]

def find_layers_main(city,Folder):

    temp_gdb  = create_gdb_temp  ()

    out_put   = temp_gdb + '\\' + 'geom'
    fc_raster = temp_gdb + '\\' + 'rasters'
    fc_layer  = temp_gdb + '\\' + 'layers'
    inter_ras = temp_gdb + '\\' + 'intersects'
    inter_vec = temp_gdb + '\\' + 'intersects_vec'

    poly_temp = tempfile.gettempdir() + '\\' + 'temp.shp'

    if isLayer(city) == 'layer':
        arcpy.Dissolve_management(city,out_put)
    elif isLayer(city) == 'raster':
        RasterToPolygon(city,poly_temp)
        arcpy.Dissolve_management (poly_temp,out_put)
    else:
        get_settlement_to_layer  (data_SETL,city,out_put)

    if not arcpy.Exists(out_put): return
    try:
        if out_put      :zoom_in(out_put)
    except:
        pass

    if Folder == '' : sys.exit(1)

    Folder = Folder.strip()
    Find_Rasters ([Folder],fc_raster)
    Find_layers  ([Folder],fc_layer )

    getRasterOnMap(out_put, fc_raster,inter_ras ,'RasterPath')
    getRasterOnMap(out_put, fc_layer ,inter_vec ,'Path'      )


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



def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:arcpy.AddField_management (fc, field, Type, "", "", 500)


def createNewLayer(new_layer,template = "",geomType = "POLYGON"):
    name = os.path.basename(new_layer)
    path = os.path.dirname (new_layer)
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)
    arcpy.CreateFeatureclass_management(path, name, geomType,template)
    return new_layer


def FeatureVerticesToPoints(layer,outPut):

    '''
    get polygon or polyline and return vertics
    '''

    createNewLayer(outPut,layer,'POINT')

    name       = os.path.basename(layer)
    field_name = 'FID_'+ name
    OID        = str(arcpy.Describe(outPut).OIDFieldName)

    add_field(outPut,field_name,'LONG')
    arcpy.CalculateField_management (outPut, field_name,f"!{OID}!", "PYTHON")

    columns    = [f.name for f in arcpy.ListFields(layer) if f.name not in ('SHAPE','Shape_Length','Shape_Area','Shape')] + ["SHAPE@"] + [field_name]
    ins_cursor = arcpy.da.InsertCursor (outPut, columns)
    OID_in     = str(arcpy.Describe(layer).OIDFieldName)
    poly_data  = [list(i[:-1]) + [arcpy.PointGeometry(arcpy.Point(j.X,j.Y))] + [i[columns.index(OID_in)]]
                       for i in arcpy.da.SearchCursor (layer,columns[:-1]) for n in i[-1] for j in n if j]


    for i in poly_data:ins_cursor.insertRow (i)  



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

def createNewLayer(new_layer,template = "",geomType = "POLYGON"):
    name = os.path.basename(new_layer)
    path = os.path.dirname (new_layer)
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)
    arcpy.CreateFeatureclass_management(path, name, geomType,template)
    return new_layer

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

def Split_List_by_value(list1,value,del_value = False):
    '''
    Split_List_by_value([1,3,None,5,7],None,True)  --> [[1, 3], [5, 7]]
    '''
    list_index = [n for n,val in enumerate(list1) if val == value]
    list_index.append(len(list1))

    list_val = []
    num = 0
    for i in list_index:
        list_val.append(list1[num:i])
        num = + i

    if del_value:
        for i in list_val:
            for n in i:
                if n is None:
                        i.remove(value)
    return list_val


def Feature_to_polygon(path_,out_put,lineField='',sortField =''):


    arcpy.RepairGeometry_management(path_)
    
    gdb = os.path.dirname(str(path_))
    dissolve       = gdb +'\\' + 'tempDissolve'
    new_LINE_layer = gdb +'\\' + 'new_LINE_layer'

    createNewLayer  (out_put,path_,'POLYGON')
    geom_type  = Layer_Management(path_).Geom_type

    if geom_type == 'Point':
        path_ = arcpy.PointsToLine_management(path_, new_LINE_layer, lineField, sortField)
        geom_type  = Layer_Management(path_).Geom_type

    ins_cursor = arcpy.da.InsertCursor (out_put, ["SHAPE@"])

    arcpy.Dissolve_management       (path_,dissolve)
    Multi_to_single(dissolve)

    
    with arcpy.da.SearchCursor(dissolve,['SHAPE@','OBJECTID']) as cursor:
        for row in cursor:
            geom       = row[0]
            ClassGeom  = Geom(geom,geom_type)
            if ClassGeom.isSingalePart:
                array_isSingalePart = []
            for i in range(len(ClassGeom.openGeom)):
                array = []

                if geom_type == 'Polygon':
                    for j in range(len(ClassGeom.openGeom[i])):
                        if type(ClassGeom.openGeom[i]) == dict:
                            array_isSingalePart.append(ClassGeom.openGeom[i])
                            ClassGeom.strType = 'curveRings'
                        else:
                            array.append(ClassGeom.openGeom[i][j])

                if geom_type == 'Polyline':
                    array_isSingalePart.append(ClassGeom.openGeom[i])
                    if ClassGeom.isCurve:
                        ClassGeom.strType = 'curveRings'
                    else:
                        ClassGeom.strType = 'rings'

                if not ClassGeom.isSingalePart:
                    array           = Split_List_by_value(array,None,True)  
                    geojson_polygon = {ClassGeom.strType: array, u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                    polygon         = arcpy.AsShape(geojson_polygon,True)
                    ins_cursor.insertRow ([polygon])
                else:
                    array_isSingalePart.append(array)
                    
            if ClassGeom.isSingalePart:
                array_isSingalePart = [i for i in array_isSingalePart if i]
                geojson_polygon = {ClassGeom.strType: [array_isSingalePart], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                polygon         = arcpy.AsShape(geojson_polygon,True)
                ins_cursor.insertRow ([polygon])    
                       
    del ins_cursor
    cursor =None 

    if geom_type == 'Polygon':

        OBJECTID   = str(arcpy.Describe(out_put).OIDFieldName)
        dict_      = {row[0].area:row[1] for row in arcpy.da.SearchCursor(out_put,['SHAPE@',OBJECTID]) if row[0]}
        max_value  = max(dict_.keys())
        obj_delete = dict_[max_value]

        arcpy.MakeFeatureLayer_management (out_put,'newLayer',"\""+OBJECTID+"\" = {}".format(str(obj_delete)))
        arcpy.DeleteFeatures_management   ('newLayer')
        arcpy.Append_management            (path_,out_put,'NO_TEST')

    arcpy.Delete_management            (dissolve)
    arcpy.Delete_management            (new_LINE_layer)

    return out_put



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

arcpy.env.overwriteOutput = True


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

def createNewLayer(new_layer,template = "",geomType = "POLYGON"):
    name = os.path.basename(new_layer)
    path = os.path.dirname (new_layer)
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)
    arcpy.CreateFeatureclass_management(path, name, geomType,template)
    return new_layer

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

def Split_List_by_value(list1,value,del_value = False):
    '''
    Split_List_by_value([1,3,None,5,7],None,True)  --> [[1, 3], [5, 7]]
    '''
    list_index = [n for n,val in enumerate(list1) if val == value]
    list_index.append(len(list1))

    list_val = []
    num = 0
    for i in list_index:
        list_val.append(list1[num:i])
        num = + i

    if del_value:
        for i in list_val:
            for n in i:
                if n is None:
                        i.remove(value)
    return list_val


def Feature_to_polygon(path_,out_put,lineField='',sortField =''):


    arcpy.RepairGeometry_management(path_)
    
    gdb = os.path.dirname(str(path_))
    dissolve       = gdb +'\\' + 'tempDissolve'
    new_LINE_layer = gdb +'\\' + 'new_LINE_layer'

    createNewLayer  (out_put,path_,'POLYGON')
    geom_type  = Layer_Management(path_).Geom_type

    if geom_type == 'Point':
        path_ = arcpy.PointsToLine_management(path_, new_LINE_layer, lineField, sortField)
        geom_type  = Layer_Management(path_).Geom_type

    ins_cursor = arcpy.da.InsertCursor (out_put, ["SHAPE@"])

    arcpy.Dissolve_management       (path_,dissolve)
    Multi_to_single(dissolve)

    
    with arcpy.da.SearchCursor(dissolve,['SHAPE@','OBJECTID']) as cursor:
        for row in cursor:
            geom       = row[0]
            ClassGeom  = Geom(geom,geom_type)
            if ClassGeom.isSingalePart:
                array_isSingalePart = []
            for i in range(len(ClassGeom.openGeom)):
                array = []

                if geom_type == 'Polygon':
                    for j in range(len(ClassGeom.openGeom[i])):
                        if type(ClassGeom.openGeom[i]) == dict:
                            array_isSingalePart.append(ClassGeom.openGeom[i])
                            ClassGeom.strType = 'curveRings'
                        else:
                            array.append(ClassGeom.openGeom[i][j])

                if geom_type == 'Polyline':
                    array_isSingalePart.append(ClassGeom.openGeom[i])
                    if ClassGeom.isCurve:
                        ClassGeom.strType = 'curveRings'
                    else:
                        ClassGeom.strType = 'rings'

                if not ClassGeom.isSingalePart:
                    array           = Split_List_by_value(array,None,True)  
                    geojson_polygon = {ClassGeom.strType: array, u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                    polygon         = arcpy.AsShape(geojson_polygon,True)
                    ins_cursor.insertRow ([polygon])
                else:
                    array_isSingalePart.append(array)
                    
            if ClassGeom.isSingalePart:
                array_isSingalePart = [i for i in array_isSingalePart if i]
                geojson_polygon = {ClassGeom.strType: [array_isSingalePart], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                polygon         = arcpy.AsShape(geojson_polygon,True)
                ins_cursor.insertRow ([polygon])    
                       
    del ins_cursor
    cursor =None 

    if geom_type == 'Polygon':

        OBJECTID   = str(arcpy.Describe(out_put).OIDFieldName)
        dict_      = {row[0].area:row[1] for row in arcpy.da.SearchCursor(out_put,['SHAPE@',OBJECTID]) if row[0]}
        max_value  = max(dict_.keys())
        obj_delete = dict_[max_value]

        arcpy.MakeFeatureLayer_management (out_put,'newLayer',"\""+OBJECTID+"\" = {}".format(str(obj_delete)))
        arcpy.DeleteFeatures_management   ('newLayer')
        arcpy.Append_management            (path_,out_put,'NO_TEST')

    arcpy.Delete_management            (dissolve)
    arcpy.Delete_management            (new_LINE_layer)

    return out_put


def delete_layers(deletelayers):
    for i in deletelayers:arcpy.Delete_management(i)


def Eliminate(parcels,path2):
        
    '''
    [INFO]   -  cover holes by the nearby polygon with the biggiest segment
    [INPUT]  
        1) parcels - the parcel that participants in the process
        2) tazar   - the data from the modad
    [OUTPUT] 
        3) path2   - output
    '''

    GDB = os.path.dirname(parcels)

    in_memory          = r'in_memory' 

    arcpy.CopyFeatures_management(parcels,path2)

    FEATURE_TO_POLYGON = GDB + '\FEATURE_TO_POLYGON'
    slivers            = GDB + '\slivers'
    line               = GDB + '\Line'
    slivers_Intersect  = GDB + '\slivers_Intersect'

    arcpy.AddField_management        (path2, "KEY_parcel", "LONG")
    arcpy.CalculateField_management  (path2, "KEY_parcel", "!OBJECTID!", "PYTHON", "")
        
    Feature_to_polygon                (path2, FEATURE_TO_POLYGON)
    analysis_Erase                    (FEATURE_TO_POLYGON, path2, slivers)
    
        
    number_of_slivers = int(str(arcpy.GetCount_management(slivers)))
    if number_of_slivers > 0:

            arcpy.AddField_management        (slivers, "KEY_sliv", "LONG")
            arcpy.CalculateField_management  (slivers, "KEY_sliv", "!OBJECTID!", "PYTHON", "")

            PolygonToLine    (path2, line)

            arcpy.MakeFeatureLayer_management      (slivers, 'sliver_feature_layer')
            arcpy.SelectLayerByLocation_management ('sliver_feature_layer', 'BOUNDARY_TOUCHES', path2)
            intersect_list = ['sliver_feature_layer',line]

            arcpy.Intersect_analysis    (intersect_list, slivers_Intersect, "ALL", ".001 Meters", "INPUT")

            data       = [[row[0],row[1],row[2]] for row in arcpy.da.SearchCursor(slivers_Intersect,['KEY_sliv','ORIG_FID','SHAPE@LENGTH'])]
            print (data)
            df         = pd.DataFrame(data,columns= ['KEY_sliv','KEY_parcel_1','SHAPE@LENGTH'])
            df         = df.astype(float)
            df["RANK"] = df.groupby('KEY_sliv')['SHAPE@LENGTH'].rank(method='first',ascending=False)
            df         = df[df['RANK'] == 1]

            print (df)

            data_to_gis = [[getattr(row, "KEY_sliv"), getattr(row, "KEY_parcel_1")]for row in df.itertuples(index=True, name='Pandas')]

            print (data_to_gis)
            arcpy.AddField_management (slivers, "ID_KEY_par", "LONG")
            for data in data_to_gis:
                with arcpy.da.UpdateCursor(slivers,['KEY_sliv','ID_KEY_par']) as cursor:
                    for row in cursor:
                        if row[0] == data[0]:
                            row[1] = data[1]
                            cursor.updateRow (row)
                            

            x = [[x[0],x[1]] for x in arcpy.da.SearchCursor(slivers,['ID_KEY_par','SHAPE@'])]
            print (x)
            for i in x:
                with arcpy.da.UpdateCursor(path2,['KEY_parcel','SHAPE@']) as icursor:
                    for row in icursor:
                        if row[0] == i[0]:
                            print ('connected')
                            new    = row[1].union(i[1])
                            row[1] = new
                            icursor.updateRow(row)

                                
            arcpy.Delete_management(line)
            arcpy.Delete_management(slivers_Intersect)

    else:
            print("no holes found".format(str(number_of_slivers)))

    delete_layers([FEATURE_TO_POLYGON,slivers,line,slivers_Intersect])




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


def Split_List_by_value(list1,value,del_value = False):
    '''
    Split_List_by_value([1,3,None,5,7],None,True)  --> [[1, 3], [5, 7]]
    '''
    list_index = [n for n,val in enumerate(list1) if val == value]
    list_index.append(len(list1))

    list_val = []
    num = 0
    for i in list_index:
        list_val.append(list1[num:i])
        num = + i

    if del_value:
        for i in list_val:
            for n in i:
                if n is None:
                        i.remove(value)
    return list_val


def Feature_to_polygon(path_,out_put,lineField='',sortField =''):


    arcpy.RepairGeometry_management(path_)
    
    gdb = os.path.dirname(str(path_))
    dissolve       = gdb +'\\' + 'tempDissolve'
    new_LINE_layer = gdb +'\\' + 'new_LINE_layer'

    createNewLayer  (out_put,path_,'POLYGON')
    geom_type  = Layer_Management(path_).Geom_type

    if geom_type == 'Point':
        path_ = arcpy.PointsToLine_management(path_, new_LINE_layer, lineField, sortField)
        geom_type  = Layer_Management(path_).Geom_type

    ins_cursor = arcpy.da.InsertCursor (out_put, ["SHAPE@"])

    arcpy.Dissolve_management       (path_,dissolve)
    Multi_to_single(dissolve)

    
    with arcpy.da.SearchCursor(dissolve,['SHAPE@','OBJECTID']) as cursor:
        for row in cursor:
            geom       = row[0]
            ClassGeom  = Geom(geom,geom_type)
            if ClassGeom.isSingalePart:
                array_isSingalePart = []
            for i in range(len(ClassGeom.openGeom)):
                array = []

                if geom_type == 'Polygon':
                    for j in range(len(ClassGeom.openGeom[i])):
                        if type(ClassGeom.openGeom[i]) == dict:
                            array_isSingalePart.append(ClassGeom.openGeom[i])
                            ClassGeom.strType = 'curveRings'
                        else:
                            array.append(ClassGeom.openGeom[i][j])

                if geom_type == 'Polyline':
                    array_isSingalePart.append(ClassGeom.openGeom[i])
                    if ClassGeom.isCurve:
                        ClassGeom.strType = 'curveRings'
                    else:
                        ClassGeom.strType = 'rings'

                if not ClassGeom.isSingalePart:
                    array           = Split_List_by_value(array,None,True)  
                    geojson_polygon = {ClassGeom.strType: array, u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                    polygon         = arcpy.AsShape(geojson_polygon,True)
                    ins_cursor.insertRow ([polygon])
                else:
                    array_isSingalePart.append(array)
                    
            if ClassGeom.isSingalePart:
                array_isSingalePart = [i for i in array_isSingalePart if i]
                geojson_polygon = {ClassGeom.strType: [array_isSingalePart], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                polygon         = arcpy.AsShape(geojson_polygon,True)
                ins_cursor.insertRow ([polygon])    
                       
    del ins_cursor
    cursor =None 

    if geom_type == 'Polygon':

        OBJECTID   = str(arcpy.Describe(out_put).OIDFieldName)
        dict_      = {row[0].area:row[1] for row in arcpy.da.SearchCursor(out_put,['SHAPE@',OBJECTID]) if row[0]}
        max_value  = max(dict_.keys())
        obj_delete = dict_[max_value]

        arcpy.MakeFeatureLayer_management (out_put,'newLayer',"\""+OBJECTID+"\" = {}".format(str(obj_delete)))
        arcpy.DeleteFeatures_management   ('newLayer')
        arcpy.Append_management            (path_,out_put,'NO_TEST')

    arcpy.Delete_management            (dissolve)
    arcpy.Delete_management            (new_LINE_layer)

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


def create_output(fc,Out_put):

    if not Out_put == '':
        arcpy.CopyFeatures_management(fc,Out_put)
        return Out_put
    return fc


def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:arcpy.AddField_management (fc, field, Type, "", "", 500)


def Read_Fc(addr,num_rows = 9999999):
    # read fc to pandas dataframe 
    columns = [f.name for f in arcpy.ListFields(addr) if f.name.lower() not in ('shape')]
    df       = pd.DataFrame(data = [row for row in arcpy.da.SearchCursor\
               (addr,columns,"\"OBJECTID\" < {}".format(num_rows))],columns = columns)
    
    return df


def delete_layers(deletelayers):
    for i in deletelayers:arcpy.Delete_management(i)


def convertToCodes(value,groundValue = 1):
    '''
    convertToCodes(324.214,695.223,1)  --->  '324.2_695.2'
    '''
    if type(value) == list:
        return str(round(value[0],groundValue)) + '_' +str(round(value[1],groundValue)) 
    return str(value)




def explode_double_vertix(layer_path):

    new_layer  = layer_path + 'new_layer'
    save_name  = layer_path
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)

    arcpy.Select_analysis(layer_path,new_layer,"\"OBJECTID\" < 0")
    insert = arcpy.da.InsertCursor(new_layer,['SHAPE@'])

    with arcpy.da.SearchCursor(layer_path,['SHAPE@']) as Ucursor:
        for i in Ucursor:

            Geom = i[0]

            GeomJson   = json.loads(Geom.JSON)
            GeomJson   = GeomJson

            if 'curveRings' in GeomJson.keys():
                strType = 'curveRings'
                geojson_polygon = {strType: [], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
            else:
                strType = 'rings'
                geojson_polygon = {strType: [], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}

            geoms    = GeomJson[strType]
            
            listF  = []
            for part in geoms:
                list_temp = []
                for i in range(len(part)):
                    list_temp.append(part[i])
                listF.append(list_temp)

            for list_ in listF:
                geojson_polygon = {strType: [list_], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}
                polygon        = arcpy.AsShape(geojson_polygon,True)
                insert.insertRow  ([polygon])

    del insert

    if int(str(arcpy.GetCount_management(layer_path))) < int(str(arcpy.GetCount_management(new_layer))):
        arcpy.Delete_management (layer_path)
        arcpy.Rename_management (new_layer,save_name)
        return True
    else:
        arcpy.Delete_management(new_layer)
        return False


def CreateTopology(layer,out_put):
    
    gdb                 = os.path.dirname(layer)
    memory              = r'in_memory'
    Dissolve_temp       = gdb + '\\'+ 'dissolve_me'
    Feature_to_poly     = gdb + '\\'+'Feature_to_poly'
    Topolgy_Check_holes = gdb + '\\'+'Topolgy_Check_holes'
    Topolgy__intersect  = gdb + '\\'+'Topolgy_Check_intersect'

    over_lap_count = 0
    holes_count    = 0

    arcpy.Dissolve_management                 (layer,Dissolve_temp)
    Multi_to_single                           (Dissolve_temp)
    Feature_to_polygon                        (Dissolve_temp,Feature_to_poly)
    analysis_Erase                            (Feature_to_poly,Dissolve_temp,Topolgy_Check_holes)

    holes_count = int(str(arcpy.GetCount_management (Topolgy_Check_holes)))
    if holes_count != 0:
        explode_double_vertix(Topolgy_Check_holes)
        holes_count = int(str(arcpy.GetCount_management (Topolgy_Check_holes)))

    over_lap       = arcpy.Intersect_analysis([layer],Topolgy__intersect)
    over_lap_count = int(str(arcpy.GetCount_management (over_lap)))
    if over_lap_count != 0:
        over_lap_count = int(str(arcpy.GetCount_management (Topolgy__intersect))) /2


    add_field(Topolgy_Check_holes,'TYPE','TEXT')
    add_field(Topolgy__intersect ,'TYPE','TEXT')

    arcpy.CalculateField_management (Topolgy_Check_holes, "TYPE","'Hole'"     , "PYTHON_9.3")
    arcpy.CalculateField_management (Topolgy__intersect , "TYPE","'Intersect'", "PYTHON_9.3")

    arcpy.Append_management  ([Topolgy__intersect],Topolgy_Check_holes,'NO_TEST')
    Delete_Identical_Byfield (Topolgy_Check_holes ,['Shape']          ,out_put  )

    arcpy.AddMessage('Total of holes found: {}'     .format(holes_count   ))
    arcpy.AddMessage('Total of Intersects found: {}'.format(over_lap_count))

    delete_layers([Topolgy_Check_holes,Topolgy__intersect,Dissolve_temp,Feature_to_poly])

    return out_put





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


def find_files_by_extension(out_root,ext):

    files =glob.glob(os.path.join(out_root ,"*{}".format(ext)))
    return files

def set_ISR(filename):
    target_srs = 'EPSG:2039'
    ds = gdal.Open(filename, gdal.GA_Update)
    gdal.Warp(ds, ds, dstSRS=target_srs)
    ds = None


def RasterToPolygon(filename,out_put):


    set_ISR(filename)
    ds  = gdal.Open( filename )

        # def polygonize(self,shp_path):
    # mapping between gdal type and ogr field type
    type_mapping = {gdal.GDT_Byte: ogr.OFTInteger,
                    gdal.GDT_UInt16: ogr.OFTInteger,
                    gdal.GDT_Int16: ogr.OFTInteger,
                    gdal.GDT_UInt32: ogr.OFTInteger,
                    gdal.GDT_Int32: ogr.OFTInteger,
                    gdal.GDT_Float32: ogr.OFTReal,
                    gdal.GDT_Float64: ogr.OFTReal,
                    gdal.GDT_CInt16: ogr.OFTInteger,
                    gdal.GDT_CInt32: ogr.OFTInteger,
                    gdal.GDT_CFloat32: ogr.OFTReal,
                    gdal.GDT_CFloat64: ogr.OFTReal}

  
    srcband       = ds.GetRasterBand (1)
    dst_layername = "Shape"

    # Create polygon

    if os.path.exists(out_put): os.remove(out_put)
    drv          = ogr.GetDriverByName      ("ESRI Shapefile")
    dst_ds       = drv.CreateDataSource     (out_put)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(2039)
    dst_layer    = dst_ds.CreateLayer       (dst_layername, sr,ogr.wkbPolygon)
    raster_field = ogr.FieldDefn            ('id', type_mapping[srcband.DataType]) # get gdal based field type to ogr 

    dst_layer.CreateField     (raster_field)
    gdal.Polygonize           (srcband, None, dst_layer, -1,[], callback=None)

    dst_ds.Destroy()

    del dst_layer
    del srcband
    

def Envelope_Geom(geom,buffer = 0):
    extent = geom.extent
    Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance).buffer(buffer)
    return polygon


def updateEnvelope(cliped_layer, buffer=0):
    with arcpy.da.UpdateCursor(cliped_layer, ['SHAPE@']) as cursor:
        for row in cursor:
            geom = row[0]
            polygon = Envelope_Geom(geom,buffer)
            row[0] = polygon
            cursor.updateRow(row)
    del cursor


def Get_fcs_shps_ras(items):
    list_shp,list_fc,list_ras,dwg_list = [],[],[],[]

    for item in items:
        if not arcpy.Exists(item): continue
        if item.endswith(".shp"):
            list_shp.append(item)

        elif item.endswith(".gdb"):
            arcpy.env.workspace = item
            ListDatasets = [i for i in arcpy.ListDatasets()]
            for dataset in ListDatasets:
                arcpy.env.workspace = item + '\\' + dataset
                fcs = [item + '\\' + dataset + '\\' + i for i in arcpy.ListFeatureClasses() if i]
                list_fc.extend(fcs)
            arcpy.env.workspace = item
            fcs = [item + '\\' + i for i in arcpy.ListFeatureClasses() if i]
            list_fc.extend(fcs)

        elif item.endswith(".tif"):
            list_ras.append(item)

        elif item.endswith(".dwg"):
            dwg_list.append(item)

        elif os.path.dirname(item).split('.')[-1] == 'gdb':
            list_fc.append(item)

        elif os.path.isdir(item):
            for root, dirs, files in os.walk(item):
                for file in files:
                    if file.endswith(".shp"):
                        list_shp.append(root + '\\' +file)
                    if file.endswith(".tif"):
                        print (root + '\\' + file)
                        list_ras.append(root + '\\' + file)
                    if file.endswith(".dwg"):
                        print(".dwg")
                        print(root + '\\' + file)
                        dwg_list.append(root + '\\' + file)
                if root.endswith(".gdb"):
                    arcpy.env.workspace = root
                    fcs = [root + '\\' + i for i in arcpy.ListFeatureClasses()]
                    list_fc.extend(fcs)


        else:
            print ('not supported file type: {}'.format(item))

    list_fc  = list(set(list_fc ))
    list_shp = list(set(list_shp))
    list_ras = list(set(list_ras))

    return list_fc,list_shp,list_ras,dwg_list


def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"
    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, str(GDB_name), "CURRENT"))
    return fgdb_name


def createFolder(dic):
    try:
        if not os.path.exists(dic):
            os.makedirs(dic)
        return dic
    except:
        return dic

def create_out_folder_or_gdb(folder_out,feature_name,type_out):
    if type_out == "GDB":
        export_to = folder_out + '\\' + 'Clip_' + str(feature_name) + '.gdb'
        if arcpy.Exists(export_to): arcpy.Delete_management(export_to)
        Create_GDB(folder_out,'Clip_' + str(feature_name) + '.gdb')
    if type_out == "SHP":
        export_to = folder_out + '\\' + 'Clip_' + str(feature_name)
        if os.path.exists(export_to):
            try:
                os.remove(export_to)
            except:
                pass
        createFolder(export_to)
    return export_to

def create_path_out(item,name,type_out,type_layer,out_export):
    if type_out == "GDB": 
        name = name.replace('.shp','')
    if (type_out == "SHP") and (name.endswith('.shp') == False): 
        name = name + '.shp'
    if type_layer == "RasterDataset":
        name = os.path.basename(item)
        if type_out == "GDB":
            name = name.replace('.tif','')

    path_out   = out_export + '\\' + name 
    return path_out


def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')




def create_layers(gdb):
    
    list_fc_type = [['Polygon',"POLYGON"],['Polyline',"POLYLINE"],['Point',"POINT"]]
    exe = [arcpy.CreateFeatureclass_management(gdb,str(value[0]),value[1],has_z = "ENABLED")
           for value in list_fc_type if not arcpy.Exists(gdb +'\\' + str(value[0]))]

    return gdb + '\\' + 'Polygon', gdb + '\\' + 'Polyline', gdb + '\\' + 'Point'

def append_Poly_line_point(list_layers,layer_to_get_the_files):
    if list_layers:
        if layer_to_get_the_files:
            arcpy.Append_management (list_layers , layer_to_get_the_files  ,"NO_TEST")


def convertTo3Layers(dwgs_workspace, gdb_out):

    poly,line,point = '','',''

    for dwg_workspace in dwgs_workspace:
        polygons_fcs = dwg_workspace + '\\' + "Polygon"
        polyline_fcs = dwg_workspace + '\\' + "Polyline"
        points_fcs   = dwg_workspace + '\\' + "Point"

        folder,name  = os.path.split    (gdb_out)
        Create_GDB                      (folder,name)
        poly,line,point = create_layers (gdb_out)

        append_Poly_line_point(polygons_fcs ,poly )
        append_Poly_line_point(polyline_fcs ,line )
        append_Poly_line_point(points_fcs   ,point)

        arcpy.RepairGeometry_management(poly)
        arcpy.RepairGeometry_management(line)
        arcpy.RepairGeometry_management(point)

    

    return poly,line,point




def input_paramater_chack(param,polyon = True, polyline = True, point = True):

    desc = arcpy.Describe(param)
    Geom_type    = desc.shapeType 

    if Geom_type == 'Polygon' and polyon is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be polygon",2)
        sys.exit(1)

    if Geom_type == 'Polyline' and polyline is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be Polyline",2)
        sys.exit(1)

    if Geom_type == 'Point' and point is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be Polyline",2)
        sys.exit(1)

    return Geom_type


def multiClip(cliped_layer,dissolve_fields,layers_in,mask,folder_out,type_out):
    #############################################################################################################

    desc       = arcpy.Describe(cliped_layer)
    coord_sys  = desc.spatialReference
    type_layer = desc.dataType

    ####################################################  cliped_layer ####################################################

    # # # # # # # #    create temp folder and gdb    # # # # # # # #
    gdb_temp      = tempfile.gettempdir() + '\\' + 'temp.gdb'
    cutting_mask  = gdb_temp              + '\\' + 'cutting_maask'
    if arcpy.Exists(gdb_temp): arcpy.Delete_management(gdb_temp)
    arcpy.CreateFileGDB_management(tempfile.gettempdir(),'temp.gdb')
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

    # # # # # # # # # # #    if raster    # # # # # # # # # # # # # #
    if type_layer == "RasterDataset":
        out_put      = tempfile.gettempdir() + '\\' + 'temp.shp'
        cliped_layer = RasterToPolygon(cliped_layer,out_put)
        arcpy.Dissolve_management     (out_put,cutting_mask)
        if mask == "true":  updateEnvelope (cutting_mask, buffer=0)
        os.remove(out_put)

    # # # # # # # # # # #    if fc or shp    # # # # # # # # # # # # # #
    if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):

        input_paramater_chack(cliped_layer,polyon = True, polyline = False, point = False)

        OID_ = str(arcpy.Describe(cliped_layer).OIDFieldName)
        if dissolve_fields == []:
            dissolve_fields = [OID_]
        try:
            arcpy.Dissolve_management     (cliped_layer,cutting_mask,dissolve_fields, multi_part="SINGLE_PART")
        except:
            arcpy.Dissolve_management     (cliped_layer,cutting_mask, multi_part="SINGLE_PART")
        if mask == "true":  updateEnvelope (cutting_mask, buffer=0)
        if OID_ in dissolve_fields:
            dissolve_fields.remove(OID_)
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    ####################################################  layers_in ####################################################

    # can get:  GDB, folder, shp, fc, dwg, raster

    list_fc,list_shp,list_ras,dwg_list = Get_fcs_shps_ras(layers_in)

    gdb_out_dwg     = tempfile.gettempdir() + '\\' + 'dwg.gdb'
    poly,line,point = convertTo3Layers(dwg_list, gdb_out_dwg)

    list_all = list_fc + list_shp + list_ras + [poly,line,point]
    list_all = [i for i in list_all if i != '']

    OID_    = str(arcpy.Describe(cutting_mask).OIDFieldName)
    columns = ['SHAPE@',OID_] + dissolve_fields
    columns = [i for i in columns if i != '']

    with arcpy.da.SearchCursor(cutting_mask,columns) as Cursor:
        for row in Cursor:
            geom       = row[0]
            all_other  = '_'.join([str(i) for i in row[1:]])
            out_export = create_out_folder_or_gdb (folder_out,all_other,type_out)

            for item in list_all:
                if not arcpy.Exists(item): continue
                
                desc       = arcpy.Describe(item)
                type_layer = desc.dataType
                name       = desc.name
                path_out   = create_path_out(item,name,type_out,type_layer,out_export)

                if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):
                    
                    if arcpy.Exists(path_out): continue
                    arcpy.Clip_analysis(item,geom,path_out)
                    if int(str(arcpy.GetCount_management(path_out))) == 0: 
                        arcpy.Delete_management(path_out)

                if type_layer == "RasterDataset":
                    try:
                        arcpy.Clip_management(item, "", path_out,geom , "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
                        arcpy.DefineProjection_management(path_out,coord_sys)
                        if arcpy.GetRasterProperties_management(path_out, "MAXIMUM") == 0:
                            arcpy.Delete_management(path_out)
                    except:
                        if arcpy.Exists(path_out): arcpy.Delete_management(path_out)

            if type_out == 'GDB':
                arcpy.env.workspace = out_export
                feC = list(arcpy.ListFeatureClasses())
                feD = list(arcpy.ListDatasets())
                LeR = list(arcpy.ListRasters())
                if (feC == []) and (feD == []) and (LeR == []):
                    arcpy.Delete_management(out_export)

    try:
        arcpy.Delete_management(gdb_temp)
    except:
        pass
    try:
        arcpy.Delete_management(gdb_out_dwg)
    except:
        pass
                    

def check_lists(list1,list2):
    for i in list1:
        if i in list2:
            return True
    return False


class Tools_manager():
    all_tools = []
    def __init__(self):
        self.len_InputTools    = len(self.all_tools)
        len_all_current_tools = 0
        self.picked_tool      = None
        self.int_picked_tool  = None

    def get_int_picked_tool(self):
        if self.picked_tool:
            self.int_picked_tool = self.picked_tool.num_input
        else:
            self.int_picked_tool = None


    def __repr__(self) -> str:
        print ('####################     Tools_manager     ###################') 
        
        print ('number of tools from source: ' + str(self.len_InputTools))
        print ('current tools: ' + str(self.len_all_current_tools))
        print ('picked tool: ' + str(self.picked_tool.id_))
        print ('number of outputs needed: ' + str(self.int_picked_tool))

    def __str__(self) -> str:
        for tool in self.all_tools:
            tool.__str__()

    def Get_len_tools(self):
        if self.len_InputTools == 0:
            self.len_InputTools         = len(self.all_tools)
        self.len_all_current_tools = len(self.all_tools)

    def insertTools(self,tools):
        for tool in tools:
            class_tool = Tools(tool)
            self.all_tools.append(class_tool)
        self.Get_len_tools()

    def remove_by_input_geom(self,Input_manager):
        print ('remove tools by input geom')
        all_geom = list(set([i[5]for i in Input_manager.all_inputs if i[5]]))
        self.dict_tools = {key: value for key, value in self.dict_tools.items() if check_lists(value[1],all_geom)}


    def keep_chosen_tools(self,chosen_tool):
        if chosen_tool:
            self.all_tools  = [tool for tool in self.all_tools if tool.id_ == chosen_tool.id_]
            self.picked_tool = chosen_tool
            self.Get_len_tools()

    def remove_tools_by_inputLayers(self):
        print ('remove tools if all layers are not match the tool input parameters')
        if InputsManager.allRaster:
            print ('all rasters')
            before_len     = len(self.all_tools)
            self.all_tools = [tool for tool in self.all_tools if 'raster'  in tool.Geotypes]
            after_len      = len(self.all_tools)
            print ('before: ' + str(before_len) + ' after: ' + str(after_len))

            self.Get_len_tools()

        elif InputsManager.allVectors:
            print ('all vectors')
            before_len = len(self.all_tools)
            self.all_tools = [tool for tool in self.all_tools if 'raster' not in tool.Geotypes]
            after_len = len(self.all_tools)
            print ('before: ' + str(before_len) + ' after: ' + str(after_len))
            self.Get_len_tools()
        else:
            # check if raster input have the must score
            max_score = max([input_.score for input_ in InputsManager.all_inputs])
            for input_ in InputsManager.all_inputs:
                if max_score > 0.8:
                    if int(input_.score) == int(max_score):
                        print ('is raster input')
                        if input_.geomType == 'raster':
                            self.all_tools = [tool for tool in self.all_tools if 'raster' in tool.Geotypes]
                            self.Get_len_tools()
            pass


class Tools():

    dict_tools = {}
    
    def __init__(self,tool):

        id,ToolActivate,Geotypes,keywords,num_input,fields,isoutput = tool
        self.id_          = id
        self.ToolActivate = ToolActivate
        self.Geotypes     = Geotypes
        self.keywords     = keywords
        self.num_input    = num_input
        self.fields       = fields
        self.isoutput     = isoutput

    def __str__(self) -> str:
        print ('####################     Tools     ###################')
        print ('id: ' + self.id_ + '\n' + 'Geotypes:' + str(self.Geotypes) + '\n' + 'keywords:' + str(self.keywords) +
               '\n' + 'num_input:' + str(self.num_input) + '\n' + 'fields:' + str(self.fields) + '\n' + 'isoutput:' + str(self.isoutput))


class InputManager():
    all_inputs = []
    def __init__(self):
        print ('InputManager')

        self.mainInput       = None
        self.seconfInputs    = None
        self.allRaster       = False
        self.allVectors      = False
        self.countInputs     = 0

        self.main_a_field    = None
        self.main_b_field    = None

        self.secoend_a_field = None
        self.secoend_b_field = None


    def Get_main_and_seconed_fields(self):
        
        main_a_field_exists = False
        main_b_field_exists = False
        for input_ in self.all_inputs:
            if not input_: continue
            sorted_list = sorted(input_.fields_match, key=itemgetter(3))
            for field in sorted_list:
                if not self.mainInput: continue
                if input_.layer == self.mainInput.layer:
                    if not main_a_field_exists:
                        self.main_a_field = field
                        input_.main_field = field
                        main_a_field_exists = True
                    else:
                        self.main_b_field = field
                        input_.second_field = field
                            
                else:
                    if not main_b_field_exists:
                        self.secoend_a_field = field
                    else:
                        self.secoend_b_field = field

    def add_input(self,InputAprx):
        self.all_inputs.append(InputAprx)

    def __repr__(self) -> str:
        print ("####################   InputManager   ########################")
        main_layer   = self.mainInput.layer if self.mainInput else None
        second_layer = self.seconfInputs.layer if self.seconfInputs else None
        print ('main Input: ' + str(main_layer) + '\n' + 'secon fInputs: ' + str(second_layer) + '\n'
                 + 'all Raster: ' + str(self.allRaster) + '\n' + 'all Vectors: ' + str(self.allVectors) 
                 + '\n' + 'count Inputs: ' + str(self.countInputs), '\n' + 'main_a_field: ' + str(self.main_a_field) + 
                 '\n' + 'main_b_field: ' + str(self.main_b_field) + '\n' + 'secoend_a_field: ' + str(self.secoend_a_field) +
                  '\n' + 'secoend_b_field: ' + str(self.secoend_b_field))

    def __str__(self) -> str:
        for input_ in self.all_inputs:
            input_.__str__()

        print ('number of inputs: ' + str(self.countInputs))

    def Update(self):
        self.Count_inputs()
        self.All_rasters()
        self.All_features()

    def All_rasters(self):

        all_rasters_ = len([i.type for i in self.all_inputs if (i.type == 'raster') or  (i.type == 'TIF')])
        if all_rasters_ == self.countInputs:
            self.allRaster = True

    def All_features(self):
        all_features = len([i.type for i in self.all_inputs if (i.type == 'FC') or(i.type == 'SHP')])
        if all_features == self.countInputs:
            self.allVectors   = True

    def Count_inputs(self):
        self.countInputs = len(self.all_inputs)

    def check_if_first_input(self):
        for input_ in self.all_inputs:
            if not self.mainInput:
                print ('no main input')
                return 
            if input_.geomType not in Tools_store.picked_tool.Geotypes:
                input_.Can_be_first_input =False


    def Get_main_and_seconed_inputs(self):
        '''
        check if smallest index and if can be first input by geomtype
        ''' 
        self.all_inputs.sort(key=operator.attrgetter('index'))
        input_main_already_set = False
        for input_ in self.all_inputs:
            if input_.Can_be_first_input:
                if input_.score > 0.8: 
                    if not input_main_already_set:
                        self.mainInput = input_
                        input_main_already_set = True

        for input_ in self.all_inputs:
            if input_:
                if self.mainInput:
                    if input_.layer != self.mainInput.layer:
                        self.seconfInputs = input_


class InputAprx():

    all_inputs              = []
    dict_all_inputs_archive = {}

    def __init__(self,layer,type_,data_source,isOutput = False, geomType = None):
        self.layer              = layer
        self.type               = type_
        self.data_source        = data_source
        self.isOutput           = isOutput
        self.geomType           = geomType
        self.empty              = False
        self.score              = 0
        self.index              = 0
        self.Can_be_first_input = True
        self.fields_found       = []
        self.fields_match       = []
        self.main_field         = None
        self.second_field       = None

        self.is_empty()
        self.add_fields()

    def __str__(self) -> str:
            print(' #################  InputAprx   ###############')
            print ('layer name:   ' + self.layer + '\n', 'type:        ' + self.type + '\n', 'data source: ' + 
            self.data_source + '\n', 'is output:   ' + str(self.isOutput) + '\n', 'empty:       ' + str(self.empty)
            + '\n', 'geom type:   ' + self.geomType + '\n' + 'index:       ' + str(self.index) 
            + '\n' + 'score:       ' + str(self.score) +'\n' + 'Can be first input: ' + str(self.Can_be_first_input)
            + '\n' + 'fields match: ' + str(self.fields_match) + '\n' + 'fields found: ' + str(self.main_field) + '\n' + str(self.second_field))

    def is_empty(self):
        if self.type == 'FC' or self.type == 'SHP':
            if arcpy.GetCount_management(self.data_source).getOutput(0) == '0':
                self.empty = True

    def add_fields(self):

        if self.type == 'FC' or self.type == 'SHP':
            self.fields_found = [[i.name,i.type,self.check_all_nulls(self.data_source,i.name)] for i in arcpy.ListFields(self.data_source)]

    @staticmethod
    def check_all_nulls(fc,field_name):
        with arcpy.da.SearchCursor(fc, field_name) as cursor:
            for row in cursor:
                if row[0] != None:
                    del cursor
                    return False
        del cursor
        return True

    

def get_all_layers_from_content(aprx_path = 'CURRENT'):
    '''
    Get all layers from the content of the project
    '''

    aprx            = arcpy.mp.ArcGISProject(aprx_path)
    list_map        = aprx.listMaps('*')
    for map_ in list_map:
        list_layers = map_.listLayers('*')
        for layer in list_layers:
            is_output = False
            if 'out_put' in layer.name.lower():
                is_output = True
            
            if layer.isFeatureLayer:
                type_geom     = str(arcpy.Describe(layer).shapeType)
                InputsManager.add_input(InputAprx(layer.name,'FC',layer.dataSource,is_output,type_geom))
            elif layer.isRasterLayer:
                if layer.dataSource.endswith('tif'):
                    InputsManager.add_input(InputAprx(layer.name,'TIF',layer.dataSource,is_output,'raster'))
                else:
                    InputsManager.add_input(InputAprx(layer.name,'raster',layer.dataSource,is_output,'gdb_RASTER'))
            else:
                continue   

    InputsManager.Update()


class Responed():
    def __init__(self):

        self.error_Not_Enough_inputs = False
        self.error_Not_Enough_fields = False

        # check if not enough inputs
        self.num_input_needed_from_tool = None
        self.num_main_and_second_inputs = None

        # check if there is enough fields
        self.len_fields_needed          = None
        self.len_fields_found           = None


    def update(self):

        self.len_fields_needed = Tools_store.picked_tool.fields
        self.len_fields_found  = InputsManager.countInputs

        self.num_input_needed_from_tool = Tools_store.picked_tool.num_input
        if InputsManager.mainInput is not None:
            self.num_main_and_second_inputs = 1
        if InputsManager.seconfInputs is not None:
            self.num_main_and_second_inputs = 2

        if Tools_store.int_picked_tool > InputsManager.countInputs:
            self.error_Not_Enough_inputs = True
            print ('!!!!!!!error: count Inputs' + str(InputsManager.countInputs) + ', num input needed from tool: ' + str(Tools_store.int_picked_tool))
            sys.exit(1)
        

        self.check_for_errors()

    def check_for_errors(self):
        if  not self.num_input_needed_from_tool: return 
        if  not self.num_main_and_second_inputs: return 
        if self.num_input_needed_from_tool > self.num_main_and_second_inputs:
            self.error_Not_Enough_inputs = True

        if self.len_fields_needed > self.len_fields_found:
            self.error_Not_Enough_fields = True


    def __repr__(self) -> str:
        if self.error_Not_Enough_inputs:
            print ('!!!!!!!error: ' + str(self.error_Not_Enough_inputs) + ', num_input_needed_from_tool: ' + str(self.num_input_needed_from_tool))
        if self.error_Not_Enough_fields:
            print ('!!!!!!!error: ' + str(self.error_Not_Enough_fields) + ', len_fields_found: ' + str(self.len_fields_found) + ', len_fields_needed: ' + str(self.len_fields_needed))


    def __str__(self) -> str:
        print(' #################  Responed   ###############')
        print ('error: ' + str(self.error_Not_Enough_inputs) + '\n', 'num_input_needed_from_tool: ' + str(self.num_input_needed_from_tool),
        '\n', 'num of main and second inputs: ' + str(self.num_main_and_second_inputs),
        '\n', 'len_fields_found: ' + str(self.len_fields_found), '\n', 'len_fields_needed: ' + str(self.len_fields_needed))


class Sentance():
    list_sentance = []
    def __init__(self,sentance):
        self.sentance            = sentance
        self.sentance_full  = sentance
        self.get_list_sentance()
        self.list_sentance_full  = self.list_sentance[:]


    def __str__(self) -> str:
        print ('#####################  Sentenace ########################')
        print ('sentance: ' + self.sentance)
        print ('sentance: ' + str(self.list_sentance))
        print ('Full sentance: ' + str(self.sentance_full))

    def Count_sentance(self):
        return len(self.list_sentance)

    def Remove_from_sentance(self,remove_word): 
        print ('remove words input layer from sentance')
        if not remove_word: return
        if type(remove_word) == list:
            self.list_sentance = [word for word in self.list_sentance if word not in remove_word]
        elif type(remove_word) == str:
            self.list_sentance = [word for word in self.list_sentance if word != remove_word]
        else:
            pass

        self.recreate_sentance()

    def remove_str_sentance(self,old):
        print ('remove str from sentance after find tool')
        self.sentance = self.sentance.replace(old,'')
        self.get_list_sentance()

    def recreate_sentance(self):
        self.sentance = ' '.join(self.list_sentance)

    def get_list_sentance(self):
        self.list_sentance = [i for i in self.sentance.split(' ') if i != '']


def FindInputs():

    words_pick    = []
    for layer in InputsManager.all_inputs:
        index_in_text = 1
        for word in Mysentance.list_sentance:
            layer_low   = layer.layer.lower()
            if len(layer_low.split('.')) > 1:
                layer_low = layer_low.split('.')[0]
            word_lower  = word.lower()
            match_ratio = SequenceMatcher(None, layer_low, word_lower).ratio()
            if match_ratio > 0.8:
                layer.score = match_ratio
                layer.index = index_in_text
                words_pick.append(word)
            index_in_text += 1

    Mysentance.Remove_from_sentance (words_pick)

def find_tool():

    similar_sentence = 0
    tool_pick        = ''
    sentences        = [''] + Mysentance.list_sentance
    length           = len(sentences)
    sentace_pick     = ''
    for i in range(length):
        full_search = ''
        for j in range(i+1,length):
            words = sentences[j]
            full_search += words + ' '
            for tool in Tools_store.all_tools:
                for tool_kyewards in tool.keywords:
                    full_search = full_search.lower()
                    match_ratio = SequenceMatcher(None, full_search, tool_kyewards).ratio()
                    if match_ratio > similar_sentence:
                        if match_ratio > 0.8:
                            print (full_search,tool_kyewards,match_ratio)
                            similar_sentence = match_ratio
                            sentace_pick     = full_search
                            tool_pick        = tool

    Tools_store.picked_tool = tool_pick
    Mysentance.remove_str_sentance(sentace_pick)
    Tools_store.keep_chosen_tools(tool_pick)
    Tools_store.get_int_picked_tool()



def match_fields_from_input_to_layer():
    for input_ in InputsManager.all_inputs:
        for field in input_.fields_found:
            index_in_text = 1
            for word in Mysentance.list_sentance:
                field_name = field[0].lower()
                word       = word.lower()
                match_ratio = SequenceMatcher(None, field_name, word).ratio()
                if match_ratio > 0.8:
                    input_.fields_match.append(field + [index_in_text])
                index_in_text += 1


def get_function_Join_Fields_params(field_name):
    input_layer  = InputsManager.mainInput.data_source
    seconfInputs = InputsManager.seconfInputs.data_source

    main_a_field  = InputsManager.main_a_field[0]
    if not InputsManager.main_b_field:
        print ('no field to join with')
        sys.exit(1)
    main_b_field  = InputsManager.main_b_field[0]

    secoend_a_field = InputsManager.secoend_a_field[0]
    
    if not InputsManager.secoend_b_field:
        secoend_b_field = field_name
    else:
        secoend_b_field = InputsManager.secoend_b_field[0]

    return [input_layer,[main_a_field],[main_b_field],seconfInputs,[secoend_a_field],[secoend_b_field]]



def get_out_put_as_Input():
    '''
        if the hightest score is less than 0.8
        and there is output in the inputs
        then the output is the input
    '''

    hightest_socre = [input_.score for input_ in InputsManager.all_inputs]
    if hightest_socre:
        hightest_socre = max(hightest_socre)
    
    if hightest_socre < 0.8:
        all_out_puts = [input_ for input_ in InputsManager.all_inputs if input_.isOutput]
        all_out_puts = sorted(all_out_puts, key=lambda x: x.layer, reverse=True)
        if all_out_puts:
            new_input = all_out_puts[0]
            new_input.score = 1
            new_input.isOutput = False


tools_archive = [
    # '''
    # id tool             ,activation tool                   ,type of tool input          ,        keywards       ,number of inputs\fields          have output
                                                                                                                                                                        
    # '''

    ['delete identical'     ,Delete_Identical_Byfield        ,['Polygon','Polyline','Point'] ,['delete identical']                 ,1,1,True],
    ['polygon to line'      ,PolygonToLine                   ,['Polygon']                    ,['to line','polygon to line',
                                                                                               'to polyline']                      ,1,0,True],
    ['erase'                ,analysis_Erase                  ,['Polygon','Polyline','Point'] ,['delete','erase']                   ,2,0,True],
    ['topology'             ,CreateTopology                  ,['Polygon']                    ,['topology','create topology']       ,2,0,True],
    ['vertiex to point'     ,FeatureVerticesToPoints         ,['Polygon','Polyline']         ,['vertiex to point',      
                                                                                               'vertices to point','get vertices'] ,1,0,True],
    ['snap'                 ,Snap                            ,['Polygon','Polyline']         ,['snap']                             ,2,0,True],
    ['eliminate'            ,Eliminate                       ,['Polygon']                    ,['slivers','eliminate']              ,1,0,True],
    ['find identical'       ,Find_Identical_Byfield          ,['Polygon','Polyline','Point'] ,['find identical']                   ,1,1,False],
    ['simplify'             ,Simplify_Polygons               ,['Polygon','Polyline']         ,['remove vertices','simplify']       ,1,0,True],
    ['split line by vertex' ,Split_Line_By_Vertex_tool       ,['Polyline']                   ,['split line by vertex',
                                                                                               'by vertex','by vertices']          ,1,0,True],
    ['intersect'            ,arcpy.Intersect_analysis        ,['Polygon','Polyline','Point'] ,['intersect','intersects']           ,2,0,True],
    ['buffer'               ,arcpy.Buffer_analysis           ,['Polygon','Polyline','Point'] ,['buffer']                           ,1,0,True],
    ['join fields'          ,join_field                      ,['Polygon','Polyline','Point'] ,['join fields','join field', 
                                                                                               'connect field']                    ,2,2,False],
    ['Spatial Join'         ,arcpy.SpatialJoin_analysis      ,['Polygon','Polyline','Point'] ,['spatial join','by location']       ,2,0,False],
    ['Feature_to_polygon'   ,Feature_to_polygon              ,['Polygon','Polyline','Point'] ,['to polygon','feature to polygon']  ,1,0,False],
    ['find layers'          ,find_layers_main                ,['Polygon','Polyline','Point'] ,['find Layers','locate layers',
                                                                                                'map layers', 'find all layers',
                                                                                                'find raster','go to','zoom to']   ,0,0,False],
    ['create field'         ,add_field                       ,['Polygon','Polyline','Point'] ,['add field','create field',
                                                                                                'create new field']                ,0,1,False],
    ['multiClip'            ,multiClip                       ,['Polygon']                    ,['multiClip','multi clip', 'clip all',
                                                                                                'clip all layers','clip']          ,1,0,True],
    ['feature to point'     ,arcpy.FeatureToPoint_management ,['Polygon','Polyline']         ,['feature to point','create point',
                                                                                                'to point','to points']             ,1,0,True],
    ['raster to polygon'    ,RasterToPolygon                 ,['raster']                     ,['raster to polygon','to polygon',
                                                                                                'as raster','to shp',
                                                                                                'to shapefile','to layer']          ,1,0,True]                                                                      
]

data_SETL = [['סעווה', "Sa'wa", 1360, 'MULTIPOLYGON (((194708 571757, 200534 571757, 200534 575345, 194708 575345, 194708 571757)))'],
['רמלה', 'Ramla', 8500, 'MULTIPOLYGON (((185161 646485, 191358 646485, 191358 649951, 185161 649951, 185161 646485)))'],
['תל שבע', "Tel Sheva'", 1054, 'MULTIPOLYGON (((185149 571700, 188650 571700, 188650 574363, 185149 574363, 185149 571700)))'],
['אבו קורינאת ', 'Abu Kuraynat', 1342, 'MULTIPOLYGON (((194218 558549, 198827 558549, 198827 562814, 194218 562814, 194218 558549)))'],
['אשקלון', 'Ashkelon', 7100, 'MULTIPOLYGON (((154951 614806, 164154 614806, 164154 624324, 154951 624324, 154951 614806)))'],
['ראשון לציון', 'Rishon LeTsiyon', 8300, 'MULTIPOLYGON (((174661 649688, 184348 649688, 184348 656799, 174661 656799, 174661 649688)))'],
["ס'וריף", 'Surif', 3771, 'MULTIPOLYGON (((204590 614997, 208159 614997, 208159 619118, 204590 619118, 204590 614997)))'],
['קריית ביאליק', 'Kiryat Bialik', 9500, 'MULTIPOLYGON (((207084 746249, 210603 746249, 210603 753359, 207084 753359, 207084 746249)))'],
["באקה אל-ר'רבייה", 'Baka al-Gharbiya', 6000, 'MULTIPOLYGON (((202340 700889, 205643 700889, 205643 704439, 202340 704439, 202340 700889)))'],
['קלנסווה', 'Kalansawa', 638, 'MULTIPOLYGON (((196399 686966, 199561 686966, 199561 690184, 196399 690184, 196399 686966)))'],
['ראש העין', "Rosh Ha'Ayin", 2640, 'MULTIPOLYGON (((194076 664555, 199329 664555, 199329 669174, 194076 669174, 194076 664555)))'],
['כפר קאסם', 'Kafr Kasem', 634, 'MULTIPOLYGON (((194812 667875, 199300 667875, 199300 670775, 194812 670775, 194812 667875)))'],
['בני נעים', "Bani Na'im", 3093, 'MULTIPOLYGON (((212708 601163, 216964 601163, 216964 604923, 212708 604923, 212708 601163)))'],
['נהרייה', 'Nahariya', 9100, 'MULTIPOLYGON (((208030 765795, 211556 765795, 211556 772048, 208030 772048, 208030 765795)))'],
['נאות חובב', "Ne'ot Hovav", 1770, 'MULTIPOLYGON (((178682 559064, 181382 559064, 181382 562446, 178682 562446, 178682 559064)))'],
['מעלה אדומים', "Ma'ale Adummim", 3616, 'MULTIPOLYGON (((227376 629992, 232961 629992, 232961 634762, 227376 634762, 227376 629992)))'],
['עארה-ערערה', "Ara-Ar'ara", 637, 'MULTIPOLYGON (((206311 710297, 211970 710297, 211970 713260, 206311 713260, 206311 710297)))'],
['קריית אתא', 'Kiryat Ata', 6800, 'MULTIPOLYGON (((205559 743505, 214070 743505, 214070 747443, 205559 747443, 205559 743505)))'],
['כפר מנדא', 'Kafr Manda', 510, 'MULTIPOLYGON (((222879 744638, 227100 744638, 227100 747019, 222879 747019, 222879 744638)))'],
['טובאס', 'Tubas', 3412, 'MULTIPOLYGON (((233398 690117, 237061 690117, 237061 694127, 233398 694127, 233398 690117)))'],
["מוח'יים פארעה", "Mukhayyam Fari'a", 3540, 'MULTIPOLYGON (((229872 685976, 233469 685976, 233469 690035, 229872 690035, 229872 685976)))'],
['דימונה', 'Dimona', 2200, 'MULTIPOLYGON (((199797 551176, 205196 551176, 205196 555188, 199797 555188, 199797 551176)))'],
['אופקים', 'Ofakim', 31, 'MULTIPOLYGON (((162430 577900, 166197 577900, 166197 581563, 162430 581563, 162430 577900)))'],
['ערערה-בנגב', "Ar'ara BaNegev", 1192, 'MULTIPOLYGON (((200097 561116, 204501 561116, 204501 564058, 200097 564058, 200097 561116)))'],
['לוד', 'Lod', 7000, 'MULTIPOLYGON (((187745 648864, 191461 648864, 191461 653126, 187745 653126, 187745 648864)))'],
['אבן יהודה', 'Even Yehuda', 182, 'MULTIPOLYGON (((188304 684684, 190452 684684, 190452 688421, 188304 688421, 188304 684684)))'],
['פרדס חנה-כרכור', 'Pardes Hanna-Karkur', 7800, 'MULTIPOLYGON (((195129 706444, 200555 706444, 200555 711677, 195129 711677, 195129 706444)))'],
['קבאטיה', 'Kabatiya', 3801, 'MULTIPOLYGON (((224919 700497, 228869 700497, 228869 703383, 224919 703383, 224919 700497)))'],
['א-טירה', 'At-Tira', 2720, 'MULTIPOLYGON (((194199 680557, 198258 680557, 198258 683812, 194199 683812, 194199 680557)))'],
['מעלות-תרשיחא', "Ma'alot-Tarshiha", 1063, 'MULTIPOLYGON (((224636 767172, 227779 767172, 227779 770457, 224636 770457, 224636 767172)))'],
['צפת', 'Tsfat', 8000, 'MULTIPOLYGON (((245138 760210, 250446 760210, 250446 765853, 245138 765853, 245138 760210)))'],
['זיכרון יעקב', "Zikhron Ya'akov", 9300, 'MULTIPOLYGON (((194446 718098, 197217 718098, 197217 721825, 194446 721825, 194446 718098)))'],
['קיסריה', 'Kesarya', 1167, 'MULTIPOLYGON (((190731 709730, 192528 709730, 192528 715180, 190731 715180, 190731 709730)))'],
['ירכא', 'Yirka', 502, 'MULTIPOLYGON (((215819 760796, 222870 760796, 222870 763499, 215819 763499, 215819 760796)))'],
['בית שאן', "Bet She'an", 9200, 'MULTIPOLYGON (((245884 710017, 248675 710017, 248675 713900, 245884 713900, 245884 710017)))'],
['עכו', 'Akko', 7600, 'MULTIPOLYGON (((206482 754601, 209453 754601, 209453 761546, 206482 761546, 206482 754601)))'],
['כרמיאל', "Karmi'el", 1139, 'MULTIPOLYGON (((224765 755745, 233045 755745, 233045 759404, 224765 759404, 224765 755745)))'],
['נמל תעופה בן-גוריון', 'Ben-Gurion Airport', 1748, 'MULTIPOLYGON (((186099 654685, 191288 654685, 191288 658792, 186099 658792, 186099 654685)))'],
['כפר קרע', "Kafr Kar'", 654, 'MULTIPOLYGON (((202732 710536, 206722 710536, 206722 713741, 202732 713741, 202732 710536)))'],
['קריית טבעון', "Kiryat Tiv'on", 2300, 'MULTIPOLYGON (((209848 732689, 214396 732689, 214396 738131, 209848 738131, 209848 732689)))'],
['קריית שמונה', 'Kiryat Shmona', 2800, 'MULTIPOLYGON (((252723 788136, 255817 788136, 255817 792792, 252723 792792, 252723 788136)))'],
['יריחו', 'Yeriho', 3600, 'MULTIPOLYGON (((240894 639139, 245990 639139, 245990 643159, 240894 643159, 240894 639139)))'],
['טבריה', 'Tverya (Tiberias)', 6700, 'MULTIPOLYGON (((246819 740758, 252598 740758, 252598 746349, 246819 746349, 246819 740758)))'],
["איד'נא", 'Idhna', 3005, 'MULTIPOLYGON (((195936 606179, 198937 606179, 198937 609489, 195936 609489, 195936 606179)))'],
['גן יבנה', 'Gan Yavne', 166, 'MULTIPOLYGON (((170235 631170, 174068 631170, 174068 634173, 170235 634173, 170235 631170)))'],
['עפולה', 'Afula', 7700, 'MULTIPOLYGON (((225960 720847, 232023 720847, 232023 727392, 225960 727392, 225960 720847)))'],
['יטא', 'Yatta', 3441, 'MULTIPOLYGON (((206282 592287, 213231 592287, 213231 598368, 206282 598368, 206282 592287)))'],
['בית לחם', 'Bet Lehem', 3200, 'MULTIPOLYGON (((216360 619275, 220436 619275, 220436 625741, 216360 625741, 216360 619275)))'],
['נתיבות', 'Netivot', 246, 'MULTIPOLYGON (((158337 590747, 162473 590747, 162473 594777, 158337 594777, 158337 590747)))'],
['רעננה', "Ra'anana", 8700, 'MULTIPOLYGON (((185475 675376, 189913 675376, 189913 679352, 185475 679352, 185475 675376)))'],
['חברון', 'Hevron', 3400, 'MULTIPOLYGON (((205396 600558, 212281 600558, 212281 607912, 205396 607912, 205396 600558)))'],
['הרצלייה', 'Herzliya', 6400, 'MULTIPOLYGON (((180453 672936, 187392 672936, 187392 677697, 180453 677697, 180453 672936)))'],
['סמוע', "Sammu'", 3631, 'MULTIPOLYGON (((204645 587780, 208143 587780, 208143 591149, 204645 591149, 204645 587780)))'],
['אל-יאמון', 'Al-Yamun', 3442, 'MULTIPOLYGON (((220319 708576, 223425 708576, 223425 712550, 220319 712550, 220319 708576)))'],
["ג'ינין", 'Jenin', 3300, 'MULTIPOLYGON (((225200 704160, 231063 704160, 231063 709332, 225200 709332, 225200 704160)))'],
['מגדל העמק', "Migdal Ha'Emek", 874, 'MULTIPOLYGON (((221321 729692, 224646 729692, 224646 733380, 221321 733380, 221321 729692)))'],
['בלאטה', 'Balata', 3090, 'MULTIPOLYGON (((226054 678080, 230215 678080, 230215 680575, 226054 680575, 226054 678080)))'],
['חלחול', 'Halhul', 3305, 'MULTIPOLYGON (((208111 607906, 211709 607906, 211709 611973, 208111 611973, 208111 607906)))'],
['יבנה', 'Yavne', 2660, 'MULTIPOLYGON (((173510 640426, 176783 640426, 176783 645623, 173510 645623, 173510 640426)))'],
["ביר הדאג'", 'Bir Hadaj', 1348, 'MULTIPOLYGON (((169064 546162, 176466 546162, 176466 551100, 169064 551100, 169064 546162)))'],
['שכם', 'Shkhem', 3900, 'MULTIPOLYGON (((220698 678309, 226581 678309, 226581 683406, 220698 683406, 220698 678309)))'],
["ד'ינאבה", 'Dhinnaba', 3211, 'MULTIPOLYGON (((202384 688708, 207453 688708, 207453 692012, 202384 692012, 202384 688708)))'],
['ראמאללה', 'Ramallah', 3800, 'MULTIPOLYGON (((215003 642911, 222047 642911, 222047 648905, 215003 648905, 215003 642911)))'],
['דורא', 'Dura', 3186, 'MULTIPOLYGON (((200836 599594, 205560 599594, 205560 604747, 200836 604747, 200836 599594)))'],
["א-שויוח'", 'Ash-Shuyukh', 3884, 'MULTIPOLYGON (((211603 607519, 215887 607519, 215887 610835, 211603 610835, 211603 607519)))'],
['בית סאחור', 'Bayt Sahur', 3073, 'MULTIPOLYGON (((219903 621216, 223596 621216, 223596 624201, 219903 624201, 219903 621216)))'],
['א-טייבה (בשרון)', 'At-Tayyiba (BaSharon)', 2730, 'MULTIPOLYGON (((198915 683331, 202459 683331, 202459 687709, 198915 687709, 198915 683331)))'],
['טמון', 'Tammun', 3418, 'MULTIPOLYGON (((234346 685648, 240300 685648, 240300 689587, 234346 689587, 234346 685648)))'],
["סח'נין", 'Sakhnin', 7500, 'MULTIPOLYGON (((226581 751046, 230293 751046, 230293 753390, 226581 753390, 226581 751046)))'],
['קריית גת', 'Kiryat Gat', 2630, 'MULTIPOLYGON (((176319 609302, 181445 609302, 181445 616345, 176319 616345, 176319 609302)))'],
['ירוחם', 'Yeroham', 831, 'MULTIPOLYGON (((190569 542784, 195598 542784, 195598 545387, 190569 545387, 190569 542784)))'],
['שדרות', 'Sderot', 1031, 'MULTIPOLYGON (((160154 602750, 163448 602750, 163448 605872, 160154 605872, 160154 602750)))'],
['ערד', 'Arad', 2560, 'MULTIPOLYGON (((217226 570662, 222916 570662, 222916 576043, 217226 576043, 217226 570662)))'],
["מר'אר", 'Mughar', 481, 'MULTIPOLYGON (((237009 753074, 241029 753074, 241029 756159, 237009 756159, 237009 753074)))'],
['נתניה', 'Netanya', 7400, 'MULTIPOLYGON (((184043 684643, 189969 684643, 189969 695559, 184043 695559, 184043 684643)))'],
['חדרה', 'Hadera', 6500, 'MULTIPOLYGON (((188490 702060, 196342 702060, 196342 708276, 188490 708276, 188490 702060)))'],
['ירושלים', 'Jerusalem', 3000, 'MULTIPOLYGON (((213321 624425, 224973 624425, 224973 643358, 213321 643358, 213321 624425)))'],
['נצרת', 'Natsrat', 7300, 'MULTIPOLYGON (((225830 731346, 229805 731346, 229805 737232, 225830 737232, 225830 731346)))'],
['חורה', 'Hura', 1303, 'MULTIPOLYGON (((191945 576261, 196612 576261, 196612 580313, 191945 580313, 191945 576261)))'],
['לקייה', 'Likiya', 1060, 'MULTIPOLYGON (((185406 579477, 189411 579477, 189411 583233, 185406 583233, 185406 579477)))'],
['קלקיליה', 'Kalkilya', 3700, 'MULTIPOLYGON (((196178 675552, 200046 675552, 200046 678754, 196178 678754, 196178 675552)))'],
['נס ציונה', 'Nes Tsiyona', 7200, 'MULTIPOLYGON (((178658 645734, 182531 645734, 182531 649881, 178658 649881, 178658 645734)))'],
['רחובות', 'Rehovot', 8400, 'MULTIPOLYGON (((178113 641566, 184629 641566, 184629 647261, 178113 647261, 178113 641566)))'],
['שפרעם', "Shefar'am", 8800, 'MULTIPOLYGON (((214177 743705, 218864 743705, 218864 747848, 214177 747848, 214177 743705)))'],
['עראבה', 'Arraba', 531, 'MULTIPOLYGON (((230571 749271, 233454 749271, 233454 751981, 230571 751981, 230571 749271)))'],
['עיספייא', 'Isfiya', 534, 'MULTIPOLYGON (((204372 733981, 208340 733981, 208340 738176, 204372 738176, 204372 733981)))'],
['טמרה', 'Tamra', 8900, 'MULTIPOLYGON (((215648 749732, 220495 749732, 220495 752402, 215648 752402, 215648 749732)))'],
['אום אל-פחם', 'Umm al-Fahm', 2710, 'MULTIPOLYGON (((210315 711051, 217923 711051, 217923 716580, 210315 716580, 210315 711051)))'],
['כפר סבא', 'Kfar Sava', 6900, 'MULTIPOLYGON (((189319 673933, 196120 673933, 196120 678661, 189319 678661, 189319 673933)))'],
['חיפה', 'haifa', 4000, 'MULTIPOLYGON (((196006 740322, 207779 740322, 207779 749776, 196006 749776, 196006 740322)))'],
['אילת', 'Elat', 2600, 'MULTIPOLYGON (((190347 378314, 197589 378314, 197589 388216, 190347 388216, 190347 378314)))'],
['באר שבע', "Be'er Sheva", 9000, 'MULTIPOLYGON (((175276 568630, 183985 568630, 183985 577914, 175276 577914, 175276 568630)))'],
['כוסיפה', 'Kusayfa', 1059, 'MULTIPOLYGON (((205417 570325, 210286 570325, 210286 573875, 205417 573875, 205417 570325)))'],
['דאלית אל-כרמל', 'Daliyat al-Karmil', 494, 'MULTIPOLYGON (((203133 731720, 207637 731720, 207637 735205, 203133 735205, 203133 731720)))'],
['נוף הגליל', 'Nof HaGalil', 1061, 'MULTIPOLYGON (((228635 732398, 233273 732398, 233273 737593, 228635 737593, 228635 732398)))'],
['אשדוד', 'Ashdod', 70, 'MULTIPOLYGON (((163743 630402, 171927 630402, 171927 641077, 163743 641077, 163743 630402)))'],
['פתח תקווה', 'Petah Tikva', 7900, 'MULTIPOLYGON (((185612 663776, 193397 663776, 193397 669727, 185612 669727, 185612 663776)))'],
['רמת השרון', 'Ramat HaSharon', 2650, 'MULTIPOLYGON (((181321 669206, 187460 669206, 187460 673977, 181321 673977, 181321 669206)))'],
['רמת גן', 'Ramat Gan', 8600, 'MULTIPOLYGON (((181131 660376, 186333 660376, 186333 668022, 181131 668022, 181131 660376)))'],
['תל אביב-יפו', 'Tel Aviv', 5000, 'MULTIPOLYGON (((175709 659665, 185814 659665, 185814 672651, 175709 672651, 175709 659665)))'],
['תל אביב', 'Yafo', 5000, 'MULTIPOLYGON (((175709 659665, 185814 659665, 185814 672651, 175709 672651, 175709 659665)))'],
['בני ברק', 'Bne Brak', 6100, 'MULTIPOLYGON (((183303 664022, 185713 664022, 185713 668278, 183303 668278, 183303 664022)))'],
['מכחול', "Mak'hul", 1343, 'MULTIPOLYGON (((205230 575713, 208455 575713, 208455 579145, 205230 579145, 205230 575713)))'],
['א-סייד', 'As-Sayid', 1359, 'MULTIPOLYGON (((189331 574886, 195477 574886, 195477 579738, 189331 579738, 189331 574886)))'],
['הוד השרון', 'Hod HaSharon', 9700, 'MULTIPOLYGON (((187825 670558, 193202 670558, 193202 675384, 187825 675384, 187825 670558)))'],
['חולון', 'Holon', 6600, 'MULTIPOLYGON (((176994 655659, 182653 655659, 182653 660622, 176994 660622, 176994 655659)))'],
['בת ים', 'Bat Yam', 6200, 'MULTIPOLYGON (((174936 655606, 177627 655606, 177627 660120, 174936 660120, 174936 655606)))'],
['מודיעין-מכבים-רעות', "Modi'in-Makkabbim-Re'ut", 1200, 'MULTIPOLYGON (((196308 642666, 203813 642666, 203813 648128, 196308 648128, 196308 642666)))'],
['בית שמש', 'Bet Shemesh', 2610, 'MULTIPOLYGON (((195850 622335, 202041 622335, 202041 631700, 195850 631700, 195850 622335)))'],
['רהט', 'Rahat', 1161, 'MULTIPOLYGON (((173567 586694, 179491 586694, 179491 590638, 173567 590638, 173567 586694)))']]


def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')

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

if __name__ == '__main__':

    copyRights(version = '0.0.2')
    license_key()

    sentences = arcpy.GetParameterAsText(0)

    aprx_path  = r"CURRENT"

    if not sentences:
        print ('i have no sentance to work with') 
        sys.exit(1)

    InputsManager = InputManager  ()
    Tools_store   = Tools_manager ()
    Mysentance    = Sentance      (sentences)
    # get_Responed  = Responed      ()

    Tools_store.insertTools(tools_archive)


    get_all_layers_from_content(aprx_path)

    # InputsManager.__str__()

    Mysentance    = Sentance(sentences)


    InputsManager.Count_inputs()

    FindInputs()
    Tools_store.remove_tools_by_inputLayers()
    get_out_put_as_Input       ()
    find_tool()

    InputsManager.check_if_first_input()

    number     = find_number_in_sentance  (Mysentance.sentance)
    type_      = find_type_in_text        (Mysentance.list_sentance)
    field_name = find_field_name          (Mysentance.sentance_full)

    match_fields_from_input_to_layer()

    InputsManager.Get_main_and_seconed_inputs()
    InputsManager.Get_main_and_seconed_fields()


    # get_Responed.update()

    out_put         = create_out_put(InputsManager)
    input_layer     = InputsManager.mainInput.data_source

    print (Tools_store.picked_tool.ToolActivate)
    tool_activation = Tools_store.picked_tool.ToolActivate
    if InputsManager.seconfInputs:
        seconfInputs    = InputsManager.seconfInputs.data_source 
        print (seconfInputs)

    # get_Responed  .__str__ ()
    # get_Responed  .__repr__()
    # InputsManager .__str__ ()
    # InputsManager .__repr__()
    # Mysentance    .__str__ ()
    # Tools_store   .__repr__()


    arcpy.AddMessage (f'hello human, i find that ur input name: {input_layer}')
    arcpy.AddMessage (f'Tool picked: {Tools_store.picked_tool.id_}')
    # if out_put:arcpy.AddMessage (f'i will send the result to: {out_put}')


    #############################  TOOLS  ##############################

    if Tools_store.picked_tool.id_  == 'join fields':
        params     = get_function_Join_Fields_params(field_name)
        activation = Tools_store.picked_tool.ToolActivate
        activation(*params)

    if Tools_store.picked_tool.id_  == 'create field':
        tool_activation(input_layer,field_name,type_)

    if Tools_store.picked_tool.id_ == 'feature to point':
        type_Geom   = find_type_for_feature_to_point(sentences)
        tool_activation   (input_layer,out_put,type_Geom)
        getLayerOnMap     (out_put)

    if Tools_store.picked_tool.id_ == 'snap':
        input_second    = InputsManager.seconfInputs.data_source
        tool_activation   (input_layer,input_second,out_put,number)


    if Tools_store.picked_tool.id_ == 'erase':

        if (InputsManager.seconfInputs.geomType in ['Point','Polyline']) and (InputsManager.mainInput.geomType == 'Polygon'):
            print ('swiching inputs, becuase only polygon can delete other layers')

            input_layer = InputsManager.seconfInputs.data_source
            seconfInputs = InputsManager.mainInput.data_source
            # change the seconfInputs so the IF statment after will work
            InputsManager.seconfInputs = InputsManager.mainInput

        if (InputsManager.seconfInputs.geomType != 'Polygon'):
            print ('deleted layer must be polygon')
            sys.exit(1)
            
        tool_activation   (input_layer,seconfInputs,out_put)
        # id no features left in the output layer, delete it and run the tool again with the inputs swiched
        if int(str(arcpy.GetCount_management(out_put))) == 0:
            arcpy.Delete_management(out_put)
            tool_activation(seconfInputs,input_layer,out_put)
            getLayerOnMap(out_put)


    if Tools_store.picked_tool.id_ == 'delete identical':
        main_a_field  = [i[0] for i in InputsManager.mainInput.fields_match]
        print (main_a_field)
        tool_activation(input_layer,main_a_field,out_put)
        getLayerOnMap(out_put)


    if Tools_store.picked_tool.id_ =='find identical':
        main_a_field  = [i[0] for i in InputsManager.mainInput.fields_match]
        print (main_a_field)
        tool_activation(input_layer,main_a_field)

    if Tools_store.picked_tool.id_ in ('vertiex to point','topology','polygon to line','eliminate','split line by vertex','Feature_to_polygon'):
        tool_activation(input_layer,out_put)
        getLayerOnMap(out_put)


    if (Tools_store.picked_tool.id_ == 'Spatial Join'):
        tool_activation(input_layer,seconfInputs,out_put)
        getLayerOnMap(out_put)
    

    if Tools_store.picked_tool.id_ in ('Simplify','buffer'):
        tool_activation(input_layer,out_put,number)
        getLayerOnMap(out_put)


    if Tools_store.picked_tool.id_ == 'intersect':
        tool_activation([input_layer,seconfInputs],out_put)
        getLayerOnMap(out_put)


    if Tools_store.picked_tool.id_ == 'find layers':
        layer_input_path            = find_city(data_SETL,sentences)
        if not layer_input_path:
            layer_input_path        = input_layer
        data_source = find_data_source(sentences)
        tool_activation(layer_input_path,data_source)


    if Tools_store.picked_tool.id_ == 'multiClip':

        main_a_fields  = [i[0] for i in InputsManager.mainInput.fields_match]
        data_source = find_data_source(sentences)

        if data_source == '':
            data_source = seconfInputs

        folder_out = os.path.dirname(input_layer)
        if folder_out.endswith('gdb'):
            folder_out = os.path.dirname(folder_out)


        tool_activation (input_layer,main_a_fields ,[data_source],'false',folder_out,'GDB')


    if Tools_store.picked_tool.id_ == 'raster to polygon':
    
        folder = os.path.dirname(input_layer) 
        if folder.endswith('gdb'):
            folder = os.path.dirname(folder)
        
        out_put = folder + '\\' + 'raster.shp'

        tool_activation(input_layer,out_put)
        getLayerOnMap(out_put)


    

    