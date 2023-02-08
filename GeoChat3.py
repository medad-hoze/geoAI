# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import re,sys
from difflib import SequenceMatcher
import tempfile
import operator

from ToolsSafe import tools_archive
from Utils import *


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

    def __repr__(self) -> str:
        print ('####################     Tools_manager     ###################') 
        
        print ('number of tools from source: ' + str(self.len_InputTools))
        print ('current tools: ' + str(self.len_all_current_tools))
        print ('picked tool: ' + str(self.picked_tool.id_))

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
            before_len = len(self.all_tools)
            self.all_tools = [tool for tool in self.all_tools if 'raster'  in tool.Geotypes]
            after_len = len(self.all_tools)
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

        self.mainInput          = None
        self.seconfInputs       = None
        self.allRaster          = False
        self.allVectors         = False
        self.countInputs        = 0

    def add_input(self,InputAprx):
        self.all_inputs.append(InputAprx)

    def __repr__(self) -> str:
        print ("####################   InputManager   ########################")
        main_layer   = self.mainInput.layer if self.mainInput else None
        second_layer = self.seconfInputs.layer if self.seconfInputs else None
        print ('main Input: ' + str(main_layer) + '\n' + 'secon fInputs: ' + str(second_layer) + '\n'
                 + 'all Raster: ' + str(self.allRaster) + '\n' + 'all Vectors: ' + str(self.allVectors) 
                 + '\n' + 'count Inputs: ' + str(self.countInputs))

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
            if input_.geomType not in Tools_store.picked_tool.Geotypes:
                input_.Can_be_first_input =False


    def Get_main_and_seconed_inputs(self):
        '''
        check if smallest index and if can be first input by geomtype
        '''
        self.all_inputs.sort(key=operator.attrgetter('index'))
        for input_ in self.all_inputs:
            if input_.Can_be_first_input:
                self.mainInput = input_

        for input_ in self.all_inputs:
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

        self.is_empty()
        self.add_fields()

    def __str__(self) -> str:
            print(' #################  InputAprx   ###############')
            print ('layer name:   ' + self.layer + '\n', 'type:        ' + self.type + '\n', 'data source: ' + 
            self.data_source + '\n', 'is output:   ' + str(self.isOutput) + '\n', 'empty:       ' + str(self.empty)
            + '\n', 'geom type:   ' + self.geomType + '\n' + 'index:       ' + str(self.index) 
            + '\n' + 'score:       ' + str(self.score) +'\n' + 'Can be first input: ' + str(self.Can_be_first_input)
            + '\n' + 'fields match: ' + str(self.fields_match))

    def is_empty(self):
        if self.type == 'FC' or self.type == 'SHP':
            if arcpy.GetCount_management(self.data_source).getOutput(0) == '0':
                self.empty = True

    def add_fields(self):

        if self.type == 'FC' or self.type == 'SHP':
            self.fields_found = [i.name for i in arcpy.ListFields(self.data_source)]


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
                    InputsManager.add_input(InputAprx(layer.name,'TIF',layer.dataSource,is_output,'RASTER'))
                else:
                    InputsManager.add_input(InputAprx(layer.name,'raster',layer.dataSource,is_output,'gdb_RASTER'))
            else:
                continue   

    InputsManager.Update()


class Responed():
    def __init__(self):
        self.error = False
        self.num_input_needed_from_tool = None
        self.num_main_and_second_inputs = None

        self.fields_needed              = None
        self.len_fields_found           = None

        self.fields_needed_tool         = None
        self.fields_found_input         = None

    def update(self):
        self.len_fields_found = InputsManager.countInputs
        self.fields_needed    = Tools_store.picked_tool.fields

        self.num_input_needed_from_tool = Tools_store.picked_tool.num_input
        if InputsManager.mainInput is not None:
            self.num_main_and_second_inputs = 1
        if InputsManager.seconfInputs is not None:
            self.num_main_and_second_inputs = 2

        self.fields_needed_tool = Tools_store.picked_tool.fields
        if InputsManager.mainInput is not None:
            self.fields_found_input = len(InputsManager.mainInput.fields_found)


    def check_for_errors(self):
        pass

    def __str__(self) -> str:
        print(' #################  Responed   ###############')
        print ('error: ' + str(self.error) + '\n', 'num_input_needed_from_tool: ' + str(self.num_input_needed_from_tool),
        '\n', 'num of main and second inputs: ' + str(self.num_main_and_second_inputs), '\n', 'fields_needed: ' + str(self.fields_needed),
        '\n', 'len_fields_found: ' + str(self.len_fields_found), '\n', 'fields_needed_tool: ' + str(self.fields_needed_tool))


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
            layer_low  = layer.layer.lower()
            word_lower = word.lower()
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
                        if match_ratio > 0.7:
                            similar_sentence = match_ratio
                            sentace_pick     = full_search
                            tool_pick        = tool

    Tools_store.picked_tool = tool_pick
    Mysentance.remove_str_sentance(sentace_pick)
    Tools_store.keep_chosen_tools(tool_pick)


def match_fields_from_input_to_layer():
    for input_ in InputsManager.all_inputs:
        for field in input_.fields_found:
            for word in Mysentance.list_sentance:
                field_name = field.lower()
                word       = word.lower()
                match_ratio = SequenceMatcher(None, field_name, word).ratio()
                if match_ratio > 0.8:
                    input_.fields_match.append(field)


if __name__ == '__main__':

    # sentences = arcpy.GetParameterAsText(0)

    sentences  = r' to snap yest 1000 sett test1 name mama2'
    aprx_path  = r"CURRENT"
    aprx_path  = r"C:\Users\Administrator\Desktop\GeoML\Geom_.aprx"

    InputsManager = InputManager  ()
    Tools_store   = Tools_manager ()
    get_Responed  = Responed      ()
    Mysentance    = Sentance      (sentences)

    Tools_store.insertTools(tools_archive)

    get_all_layers_from_content(aprx_path)

    Mysentance    = Sentance(sentences)

    InputsManager.Count_inputs()
    Tools_store.remove_tools_by_inputLayers()

    FindInputs()
    find_tool()

    InputsManager.check_if_first_input()

    number     = find_number_in_sentance  (Mysentance.sentance)
    type_      = find_type_in_text        (Mysentance.list_sentance)
    field_name = find_field_name          (Mysentance.sentance_full)

    InputsManager.Get_main_and_seconed_inputs()

    match_fields_from_input_to_layer()


    get_Responed.update()

    get_Responed.__str__()

    # InputsManager.__str__()
    # InputsManager.__repr__()
    # Mysentance.__str__()
    # Tools_store.__repr__()
    


    # out_put = create_out_put()

    # run_over_fields_for_input()

    # print (Input_manager.mainInput)
    # print (Tools_store.chosen_tool)
    # if out_put:
    #     print (out_put)

    # if Input_manager.seconfInputs:
    #     print (Input_manager.seconfInputs)

    # if Tools_store.chosen_tool  == 'create field':
    #     field_name = find_word_after_main  (sentences)
    #     field_type = find_type_in_text     (sentences)

    #     input_    = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation(input_,field_name,field_type)


    # if Tools_store.chosen_tool == 'feature to point':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)


    # if Tools_store.chosen_tool == 'delete identical':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     fields_input    = Input_manager.fieldsInput
    #     tool_activation   (input_,fields_input,out_put)
    

    # if Tools_store.chosen_tool == 'polygon to line':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)

    # if Tools_store.chosen_tool == 'erase':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     input_second    = Input_manager.dict_all_inputs_archive[Input_manager.seconfInputs][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,input_second,out_put)
    #     try:
    #         if int(str(arcpy.GetCount_management(out_put))) == 0:
    #             tool_activation   (input_second,input_,out_put)
    #     except:
    #         pass

    # if Tools_store.chosen_tool == 'topology':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)

    # if Tools_store.chosen_tool == 'vertiex to point':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)

    # if Tools_store.chosen_tool == 'snap':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     input_second    = Input_manager.dict_all_inputs_archive[Input_manager.seconfInputs][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     distance        = find_number_in_sentance(Mysentance.sentance)
    #     tool_activation   (input_,input_second,out_put,distance)

    # if Tools_store.chosen_tool == 'erase':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)