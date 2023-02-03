# -*- coding: utf-8 -*-

import arcpy,os
import pandas  as pd

import arcpy,os,json,sys

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

