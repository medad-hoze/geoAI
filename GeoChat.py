# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import re
from difflib import SequenceMatcher
# import openai

from DeleteIdentical_tool         import Delete_Identical_Byfield
from PolygonToLine_tool           import PolygonToLine
from Erase_tool                   import analysis_Erase
from CreateTopology_tool          import CreateTopology
from FeatureVerticesToPoints_tool import FeatureVerticesToPoints
from Snap_tool                    import Snap
from Eliminate_tool               import Eliminate
from FindIdentical_tool           import Find_Identical_Byfield
from Simplify_Polygon             import Simplify_Polygons
from SplitLineAtVertices          import Split_Line_By_Vertex_tool  
from FeatureToPolygon_tool        import Feature_to_polygon

def find_number_in_sentance(text):
    number = re.findall(r'\b\d+\b', text)
    if number:
        return number[0]
    else:
        return 5


def get_all_layers_from_content(aprx_path = 'CURRENT'):
    '''
    Get all layers from the content of the project
    '''
    dict_all_layers = {}
    outputs         = []
    aprx            = arcpy.mp.ArcGISProject(aprx_path)
    list_map        = aprx.listMaps('*')
    for map in list_map:
        list_layers = map.listLayers('*')
        for layer in list_layers:
            if layer.isFeatureLayer:
                dict_all_layers[layer.name] = layer.dataSource
                if 'out_put' in layer.name.lower():
                    outputs.append(layer.name)
    
    return dict_all_layers,outputs


def find_tool_to_use(sentences,tools_dict):
    '''
    Find the tool to use based on the sentences input by user 
    '''
    tools_list       = []
    for key in tools_dict.keys():
        tools_list += tools_dict[key][2]

    similar_sentence = 0
    tool_pick        = ''
    sentences        = [''] + sentences.split()
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

    for key in tools_dict.keys():
        if tool_pick in tools_dict[key][2]:
            tool_pick = key
            break

    return tool_pick, similar_sentence


def find_Layer_to_use(dict_all_layers,sentences,tool_geom_check,out_puts,is_seconed_input = ''):
    '''
    [INFO] - Find the layer to use based on the sentences input by user and layers in content of the project,
    if there is no layer in the content of the project that match the input by user, 
    the function will return the layer that is highest out_put layer from prior tools

    [INPUT] - 
        1) dict_all_layers : dictionary of all layers in the content of the project
        2) sentences       : sentences input by user
        3) tool_geom_check : geometry that the tool can work on ['Polygon','Polyline','Point']
        4) out_puts        : list of all layers that are out_put layers from prior tools
    [OUTPUT] -
        1) layer_pick      : layer that is picked to use
        2) similar_word    : the similarity between the layer and the input by user
    '''

    list_layers     = list(dict_all_layers.keys())

    # delete the layer that is not in the same geometry as accepted in the tool
    layer_to_run_on = [layer for layer in list_layers if arcpy.Describe(dict_all_layers[layer]).shapeType in tool_geom_check]

    sentences       = sentences.split()

    similar_word = 0
    layer_pick   = ''
    for layer in layer_to_run_on:
        for word in sentences:
            layer_low = layer.lower()
            word      = word.lower()
            match_ratio = SequenceMatcher(None, layer_low, word).ratio()
            if is_seconed_input == layer: 
                continue

            if match_ratio > similar_word:
                similar_word = match_ratio
                layer_pick   = layer

    # if there is no layer in the content of the project that match the input by user,
    # the function will return the layer that is highest out_put layer from prior tools
    if out_puts:
        if similar_word < 0.5:
            if len(out_puts) > 1:
                layer_pick = sorted(layer_pick)
                layer_pick = layer_pick[-1]
            else:
                layer_pick = out_puts[0]
            similar_word = 1

    return layer_pick, similar_word


def run_over_fields_for_matching_layers(layers,sentences):
    '''
    [INFO] - 
        Run over all fields in the layer that is picked to use and find the field that is most similar to the input by user
    [INPUT] - 
        get the closest field to the input layer 
    [OUTPUT] -
        return a dict with the most similar field name to the input by user - {../sett : muni_heb}
    '''
    fields_input = sentences.split()
    
    field_pick    = {}

    for layer in layers:
        fields_layer = [i.name for i in arcpy.ListFields(layer)]
        similar_field = 0
        for field in fields_input:
            for field_layer in fields_layer:
                field_low       = field.lower()
                field_layer_low = field_layer.lower()
                match_ratio = SequenceMatcher(None, field_low, field_layer_low).ratio()
                if match_ratio > similar_field:
                    if match_ratio > 0.7:
                        similar_field     = match_ratio
                        field_pick[layer] = field_layer_low

    if len(field_pick) == 0:
        field_pick[layer] = 'Shape'

    return field_pick



def run_over_2layers_for_maching_fields(layer1,layer2,sentences = ''):

    fields_input = sentences.split()
    
    layer_1_fields = set([i.name for i in arcpy.ListFields(layer1)])
    layer_2_fields = set([i.name for i in arcpy.ListFields(layer2)])

    same_fields = list(layer_1_fields.intersection(layer_2_fields))

    layers = [layer1,layer2]
    field_pick = {layer1:'',layer2:''}

    for layer in layers:
        similar_field = 0
        for field in fields_input:
            for field_layer in same_fields:
                field_low       = field.lower()
                field_layer_low = field_layer.lower()
                match_ratio = SequenceMatcher(None, field_low, field_layer_low).ratio()
                if match_ratio > similar_field:
                    if match_ratio > 0.7:
                        similar_field     = match_ratio
                        field_pick[layer] = field_layer_low
    

    return field_pick



def create_name_output_layer(layer_input_path):
    '''
        [INFO] - 
            create name for the output layer, if out_put_1 exist, the function will create out_put_2 and so on
        [INPUT] - 
            layer_input_path : path of the input layer
        [OUTPUT] -
            out_put          : path of the output layer
    '''
    gdb_output_layer   = os.path.dirname (layer_input_path)
    name_input         = os.path.basename(layer_input_path)
    name_output_layer  = 'out_put_1'
    if 'out_put' in name_input:
        old_name_num      = name_input.split('_')[-1]
        old_name_num      = str(find_number_in_sentance(old_name_num))
        new_name_num      = str(int(old_name_num) + 1)
        name_output_layer = name_input.replace(old_name_num,new_name_num)
        
    name_output_layer  = name_output_layer 
    out_put            = os.path.join(gdb_output_layer,name_output_layer)
    return out_put

tools_dict = {

    'delete identical'     : [Delete_Identical_Byfield  ,['Polygon','Polyline','Point'] ,['delete identical']],
    'polygon to line'      : [PolygonToLine             ,['Polygon']                    ,['to line','polygon to line']],
    'erase'                : [analysis_Erase            ,['Polygon']                    ,['delete','erase']],
    'topology'             : [CreateTopology            ,['Polygon']                    ,['topology','create topology']],
    'vertiex to point'     : [FeatureVerticesToPoints   ,['Polygon','Polyline']         ,['vertiex to point','Vertices to point']],
    'snap'                 : [Snap                      ,['Polygon','Polyline']         ,['snap']],
    'eliminate'            : [Eliminate                 ,['Polygon']                    ,['slivers','eliminate']],
    'find identical'       : [Find_Identical_Byfield    ,['Polygon','Polyline','Point'] ,['find identical']],
    'simplify'             : [Simplify_Polygons         ,['Polygon','Polyline']         ,['remove vertices','simplify']],
    'split line by vertex' : [Split_Line_By_Vertex_tool ,['Polyline']                   ,['split line by vertex','by vertex','by vertices']],
    'intersect'            : [arcpy.Intersect_analysis  ,['Polygon','Polyline','Point'] ,['intersect','intersects']],
    'buffer'               : [arcpy.Buffer_analysis     ,['Polygon','Polyline','Point'] ,['buffer']],
    'join fields'          : [arcpy.JoinField_management,['Polygon','Polyline','Point'] ,['join fields','join field', 'connect field']],
    'Spatial Join'         : [arcpy.SpatialJoin_analysis,['Polygon','Polyline','Point'] ,['spatial join','by location']],
    'Feature_to_polygon'   : [Feature_to_polygon        ,['Polygon','Polyline','Point'] ,['to polygon','feature to polygon']],
}


def if_name_close_to_list_names(name,list_names):
    ans = [i for i in list_names if SequenceMatcher(None, name.lower(), i.lower()).ratio() > 0.7]
    if ans != []:
        return True
    else:
        return False


def get_all_fields_in_layer(layer,sentance,fields_out:list):

    new_fields = []
    sentance   = sentance.split()
    fields_layer = [i.name for i in arcpy.ListFields(layer)]
    for field in fields_layer:
        field = field.lower()
        for word in sentance:
            if if_name_close_to_list_names(field,fields_out): continue
            word = word.lower()
            match_ratio = SequenceMatcher(None, word, field).ratio()
            if match_ratio > 0.7:
                new_fields.append(field)

    return new_fields



if __name__ == '__main__':
    # sentences       = 'take layer sett and delete identical' 
    sentences = arcpy.GetParameterAsText(0)

    # get all layers from the content of the project
    aprx_path                = "CURRENT"     #C:\Users\Administrator\Desktop\GeoML\Geom_.aprx"
    dict_all_layers,out_puts = get_all_layers_from_content(aprx_path)

    # return the tool that the user want to use
    tool_pick,match_ratio   = find_tool_to_use(sentences,tools_dict)

    # return the the geometry that the tool can work on : ['Polygon','Polyline','Point']
    tool_geom_check  = tools_dict[tool_pick][1]

    # return the layer that the user put as input
    layer_pick,similar_word = find_Layer_to_use(dict_all_layers,sentences,tool_geom_check,out_puts)

    # get the path of the input layer
    layer_input_path   = dict_all_layers[layer_pick]

    # get the path of the output layer
    out_put = create_name_output_layer(layer_input_path)

    # get the activation function of the tool
    tool_activate  = tools_dict[tool_pick][0]

    # run the tool
    arcpy.AddMessage(f"INPUT : {layer_input_path}")
    arcpy.AddMessage(f"TOOL  : {tool_pick}")
    arcpy.AddMessage(f"OUTPUT: {out_put}")
    
    # One input layer, one field, one output layer
    if tool_pick == 'delete identical':
        layer_field = run_over_fields_for_matching_layers([layer_input_path],sentences)
        field_to_use = layer_field[layer_input_path]
        tool_activate(layer_input_path,field_to_use,out_put)

    # One input layer, one field
    if tool_pick == 'find identical':
        layer_field = run_over_fields_for_matching_layers([layer_input_path],sentences)
        field_to_use = layer_field[layer_input_path]
        tool_activate(layer_input_path,field_to_use)

    # One input layer, one output layer
    if tool_pick in ('vertiex to point','topology','polygon to line','eliminate','split line by vertex','Feature_to_polygon'):
        tool_activate(layer_input_path,out_put)

    # Two input layer, one output layer, Swich if empty
    if (tool_pick == 'erase'):
        layer_pick2,similar_word2 = find_Layer_to_use(dict_all_layers,sentences,
                                    ['Polygon','Polyline','Point'],out_puts,layer_pick)
        layer_input_path2   = dict_all_layers[layer_pick2]

        tool_activate(layer_input_path,layer_input_path2,out_put)
        if int(str(arcpy.GetCount_management(out_put))) == 0:
            arcpy.Delete_management(out_put)
            tool_activate(layer_input_path2,layer_input_path,out_put)

    # Two input layer, one output layer
    if (tool_pick == 'Spatial Join'):
        layer_pick2,similar_word2 = find_Layer_to_use(dict_all_layers,sentences,
                            ['Polygon','Polyline','Point'],out_puts,layer_pick)
        layer_input_path2   = dict_all_layers[layer_pick2]

        tool_activate(layer_input_path,layer_input_path2,out_put)

    # Two input layer, one output layer, one number
    if tool_pick == 'snap':
        distance = find_number_in_sentance(sentences)
        layer_pick2,similar_word2 = find_Layer_to_use(dict_all_layers,sentences,
                                    ['Polygon','Polyline','Point'],out_puts,layer_pick)

        layer_input_path2   = dict_all_layers[layer_pick2]
        tool_activate(layer_input_path,layer_input_path2,out_put,distance)

    # One input layer, one output layer, one number
    if tool_pick in ('Simplify','buffer'):
        num = find_number_in_sentance(sentences)
        tool_activate(layer_input_path,out_put,num)

    # Many input layer, one output layer
    if tool_pick == 'intersect':
        layer_pick2,similar_word2 = find_Layer_to_use(dict_all_layers,sentences,
                                    ['Polygon','Polyline','Point'],out_puts,layer_pick)
        layer_input_path2   = dict_all_layers[layer_pick2]
        tool_activate([layer_input_path,layer_input_path2],out_put)


    if tool_pick == 'join fields':
        layer_pick2,similar_word2 = find_Layer_to_use(dict_all_layers,sentences,
                                    ['Polygon','Polyline','Point'],out_puts,layer_pick)
        layer_input_path2   = dict_all_layers[layer_pick2]
        layer_field = run_over_2layers_for_maching_fields(layer_input_path,layer_input_path2,sentences)

        field_to_use   = layer_field[layer_input_path]
        field_to_use2  = layer_field[layer_input_path2]

        connect_fields = get_all_fields_in_layer(layer_input_path2,sentences,[field_to_use2])
        if connect_fields == []:
            connect_fields = get_all_fields_in_layer(layer_input_path,sentences,[field_to_use])
            layer_input_path  = dict_all_layers[layer_pick2]
            layer_input_path2 = dict_all_layers[layer_pick]
        
        arcpy.AddMessage(connect_fields)
        tool_activate(layer_input_path,field_to_use,layer_input_path2,field_to_use2,connect_fields)


# openai.api_key = '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'

# # Generate text with the GPT-3 model
# model_engine = "text-davinci-002"
# prompt = "Once upon a time, there was a"

# completions = openai.Completion.create(
#     engine=model_engine,
#     prompt=prompt,
#     max_tokens=1024,
#     n=1,
#     stop=None,
#     temperature=0.5,
# )

# message = completions.choices[0].text
# print(message)
