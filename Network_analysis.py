# -*- coding: utf-8 -*-

import networkx as nx
# import matplotlib.pyplot as plt
import pandas as pd
import arcpy,re
import json,datetime
import math,sys,os

import requests

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

class Geom_line():
    def __init__(self,Geom,roundValue=1):
        self.GeomJson   = json.loads(Geom.JSON)
        self.GeomJson   = self.GeomJson
        self.curveStart = []

        if 'curvePaths' in self.GeomJson.keys():
            self.strType = 'curvePaths'
            self.isCurve = True
        else:
            self.isCurve = False
            self.strType = 'paths'
        self.geojson_polygon = {self.strType: [], u'spatialReference': {u'wkid': 2039, u'latestWkid': 2039}}

        self.openGeom   = self.GeomJson[self.strType]
        self.roundValue = roundValue
        if len(self.openGeom) == 1:
            self.isSingalePart = True
            self.openGeom      = self.GeomJson[self.strType][0]
            self.lenGeom       = len(self.openGeom)
        else:
            self.isSingalePart = False
            self.openGeom      = self.GeomJson[self.strType]
            self.lenGeom       = len(self.openGeom)

def dis(point1,point2):
    if len(point1) == 3:
        x1,y1,z1 = point1
        x2,y2,z1 = point2
    else:
        x1,y1 = point1
        x2,y2 = point2  
    dist = round(math.sqrt(((x1-x2)**2) + ((y1-y2)**2)),1)
    return dist

def get_node_edges(path,wightField):
    '''
    path       = network path
    wightField = field name of the wight

    return:
        pair_list  = list of all the edges in the network and attributes
    
    '''
    if wightField == '':
        wightField       = str(arcpy.Describe(path).OIDFieldName)  
    pair_list = []
    for row in arcpy.da.SearchCursor(path,['SHAPE@',wightField]):
        geom       = Geom_line(row[0])
        list_geoms = geom.openGeom
        if geom.lenGeom == 2:
            key_1 = str(round(list_geoms[0][0],1)) +'-'+str(round(list_geoms[0][1],1))
            key_2 = str(round(list_geoms[1][0],1)) +'-'+str(round(list_geoms[1][1],1))
            distance  = round(dis(list_geoms[0],list_geoms[1]),1)
            pair_list.append([key_1,key_2,distance,row[1]])
        if geom.lenGeom > 2:
            for i in range(geom.lenGeom):
                next = i + 1
                if next < geom.lenGeom:
                    key_1 = str(round(list_geoms[i][0],1)) +'-'+str(round(list_geoms[i][1],1))
                    key_2 = str(round(list_geoms[next][0],1)) +'-'+str(round(list_geoms[next][1],1))
                    distance  = round(dis(list_geoms[0],list_geoms[1]),1)
                    pair_list.append([key_1,key_2,distance,row[1]])
    return pair_list

def get_first_end_nodes(first_end,nodes):
    arcpy.analysis.Near(first_end, nodes)
    ids_start_end  = [i[0] for i in arcpy.da.SearchCursor(first_end,['NEAR_FID','NEAR_DIST'])]

    if len(ids_start_end) < 2:
        arcpy.AddMessage('The number of start and end nodes must be at least 2')
        sys.exit(1)
    elif len(ids_start_end) > 2:
        arcpy.AddMessage('The number of start and end nodes need to be 2, taking the  first and last nodes')
        ids_start_end = [ids_start_end[0],ids_start_end[-1]]
    else:
        pass

    id_field       = str(arcpy.Describe(nodes).OIDFieldName)  
    node_start_end = [str(round(i[1][0],1)) +'-'+str(round(i[1][1],1)) 
                    for i in arcpy.da.SearchCursor(nodes,[id_field,'SHAPE@XY'])
                    if i[0] in ids_start_end]

    arcpy.AddMessage(ids_start_end)      


    return node_start_end

def get_shortast_path_to_layer(pair_list,node_start_end,path_finish,wieghtField):

    if wieghtField == '':
        wieghtField = 'distance'

    G         = nx.Graph                ()
    df        = pd.DataFrame            (pair_list, columns = ['from', 'to', 'distance','weight'])
    G         = nx.from_pandas_edgelist (df, 'from', 'to', edge_attr= ['distance','weight'])

    print (nx.info(G))

    arcpy.AddMessage(node_start_end)
    paths_list = nx.shortest_path(G,source=node_start_end[0], target=node_start_end[1],weight = wieghtField)
    arcpy.CopyFeatures_management(arcpy.Polyline(arcpy.Array([arcpy.Point(float(j.split('-')[0]),j.split('-')[1])
                                    for j in paths_list])),path_finish)

def prepreate_data(path,border,path_finish):

    # gdb    = os.path.dirname(path)
    gdb = r'in_memory' 

    network      = gdb +'\\'+'network'
    nodes        = gdb +'\\'+'nodes'
    border_temp  = gdb +'\\'+'border_temp'
    border_temp2 = gdb +'\\'+'border_temp2'

    del_if_exists = [border_temp,border_temp2,network,nodes,path_finish]
    exe           = [arcpy.Delete_management(i) for i in del_if_exists if arcpy.Exists(i)]

    if arcpy.Exists(border):
        arcpy.Buffer_analysis(border,border_temp,'0.001 Meters')
        analysis_Erase(path,border,border_temp2)
        arcpy.MultipartToSinglepart_management(border_temp2,network)
    else:
        arcpy.CopyFeatures_management(path,network)

    arcpy.CopyFeatures_management([arcpy.PointGeometry(arcpy.Point(j.X,j.Y))
                                    for i in arcpy.SearchCursor (network) for n 
                                    in i.shape for j in n if j],nodes)
                                    
    return nodes,network



def find_shortest_path(path,first_end,path_finish,wieghtField = '',border = ''):
    # # # Input

    if wieghtField == '':
        arcpy.AddMessage('No weight field selected, using distance')
     
    # # # main
    nodes,network  = prepreate_data      (path,border,path_finish)
    node_start_end = get_first_end_nodes (first_end,nodes)
    pair_list      = get_node_edges      (network,wieghtField)

    # # # create layer from the network parilist and start and end nodes
    get_shortast_path_to_layer(pair_list,node_start_end,path_finish,wieghtField)


