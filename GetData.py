# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import sys
from difflib import SequenceMatcher

from DeleteIdentical_tool import Delete_Identical_Byfield
from PolygonToLine_tool   import PolygonToLine
from Erase_tool           import analysis_Erase

class Layer_Management():

    '''
    This class is used to manage the layer in the project
    '''

    def __init__(self,Layer):
        if arcpy.Exists(Layer):
            self.gdb          = os.path.dirname  (Layer)
            self.name         = os.path.basename (Layer)
            self.layer        = Layer
            self.oid          = str(arcpy.Describe(Layer).OIDFieldName)

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
            pass



def get_all_layers_from_content(aprx_path = 'CURRENT'):
    '''
    Get all layers from the content of the project
    '''
    dict_all_layers = {}
    aprx            = arcpy.mp.ArcGISProject(aprx_path)
    list_map        = aprx.listMaps('*')
    for map in list_map:
        list_layers = map.listLayers('*')
        for layer in list_layers:
            if layer.isFeatureLayer:
                dict_all_layers[layer.name] = layer.dataSource

    return dict_all_layers


def find_tool_to_use(sentences,tools_dict):
    '''
    Find the tool to use based on the sentences input by user and the tools_dict that contains all tools
    '''
    tools_list       = list(tools_dict.keys())
    similar_sentence = 0
    tool_pick        = ''
    sentences        = sentences.split()
    length           = len(sentences)
    for i in range(length):
        full_search = ''
        for j in range(i+1,length):
            words = sentences[j]
            full_search += words + ' '
            for tool in tools_list:
                tool        = tool.lower()
                full_search = full_search.lower()
                match_ratio = SequenceMatcher(None, full_search, tool).ratio()
                if match_ratio > similar_sentence:
                    similar_sentence = match_ratio
                    tool_pick        = tool

    return tool_pick, similar_sentence


def find_Layer_to_use(dict_all_layers,sentences,tool_geom_check):
    '''
    Find the layer to use based on the sentences input by user and layers in content of the project
    '''
    list_layers     = list(dict_all_layers.keys())

    # delete the layer that is not in the same geometry as accepted in the tool
    layer_to_run_on = [layer for layer in list_layers if arcpy.Describe(dict_all_layers[layer]).shapeType in tool_geom_check]

    similar_word = 0
    layer_pick   = ''
    for layer in layer_to_run_on:
        for word in sentences:
            layer_low = layer.lower()
            word      = word.lower()
            match_ratio = SequenceMatcher(None, layer_low, word).ratio()
            if match_ratio > similar_word:
                similar_word = match_ratio
                layer_pick   = layer
    return layer_pick, similar_word


tools_dict = {
    'delete identical': [Delete_Identical_Byfield,['Polygon','Polyline','Point']],
    'polygon to line' : [PolygonToLine,['Polygon']],
    'erase'           : [analysis_Erase,['Polygon','Polyline','Point']],
    'delete'          : [analysis_Erase,['Polygon','Polyline','Point']],
}



if __name__ == '__main__':

    # sentences       = 'take layer sett and delete identical' 

    sentences = arcpy.GetParameterAsText(0)

    # get all layers from the content of the project
    aprx_path       = "CURRENT"     #C:\Users\Administrator\Desktop\GeoML\Geom_.aprx"
    dict_all_layers = get_all_layers_from_content(aprx_path)

    # return the tool that the user want to use
    tool_pick,match_ratio   = find_tool_to_use(sentences,tools_dict)

    # return the the geometry that the tool can work on : ['Polygon','Polyline','Point']
    tool_geom_check  = tools_dict[tool_pick][1]

    # return the layer that the user put as input
    layer_pick,similar_word = find_Layer_to_use(dict_all_layers,sentences,tool_geom_check)

    # get the path of the input layer
    layer_input_path   = dict_all_layers[layer_pick]

    # get the path of the output layer
    gdb_output_layer = os.path.dirname(layer_input_path)
    name_output_layer  = 'out_put' #tool_pick.replace(' ','_')
    out_put            = os.path.join(gdb_output_layer,name_output_layer)

    # get the activation function of the tool
    tool_activate  = tools_dict[tool_pick][0]

    # run the tool
    arcpy.AddMessage(f"Run {tool_pick} on {layer_pick} to get {name_output_layer}")
    
    try:
        tool_activate(layer_input_path,['Shape'],out_put)
    except:
        tool_activate(layer_input_path,out_put)

