


import arcpy
import os,json,sys
import numpy as np
import pandas as pd

arcpy.env.overwriteOutput = True

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