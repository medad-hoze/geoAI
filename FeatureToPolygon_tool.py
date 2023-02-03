


# -*- coding: utf-8 -*-

import arcpy,os,json,sys

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

