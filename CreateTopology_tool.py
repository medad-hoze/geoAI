# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import sys

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


