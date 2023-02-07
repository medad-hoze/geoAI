# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import re,sys
from difflib import SequenceMatcher
import tempfile


from ToolsSafe import tools_archive


def check_lists(list1,list2):
    for i in list1:
        if i in list2:
            return True
    return False


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
        self.chosen_tool  = ''

        self.insertTools()
        self.isRasterinput()
        
    
    def insertTools(self):
        self.dict_tools[self.id_] = [self.ToolActivate,self.Geotypes,self.keywords,self.num_input,self.fields,self.isoutput]

    def isRasterinput(self):
        self.isRaster =  False
        for tool in self.dict_tools:
            if self.dict_tools[tool][2] == 'raster':
                self.isRaster =  True

    def remove_tools(self,Input_manager):
        
        if Input_manager.allRaster:
            self.dict_tools = {key: value for key, value in self.dict_tools.items() if 'raster' in value[1]}
        elif Input_manager.allVectors:
            self.dict_tools = {key: value for key, value in self.dict_tools.items() if 'raster' not in value[1]}
        else:
            pass

    def remove_by_input_geom(self,Input_manager):
        print ('remove tools by input geom')
        all_geom = list(set([i[5]for i in Input_manager.all_inputs if i[5]]))
        self.dict_tools = {key: value for key, value in self.dict_tools.items() if check_lists(value[1],all_geom)}
        

    def keep_chosen_tools(self,chosen_tool):
        if chosen_tool:
            self.dict_tools  = {key: value for key, value in self.dict_tools.items() if key == chosen_tool}
            self.chosen_tool = chosen_tool

class InputAprx():

    all_inputs              = []
    dict_all_inputs_archive = {}

    def __init__(self,layer,type_,data_source,isOutput = False, geomType = None):
        self.layer        = layer
        self.type         = type_
        self.data_source  = data_source
        self.isOutput     = isOutput
        self.geomType     = geomType
        self.empty        = False
        self.allRaster    = False
        self.allVectors   = False
        self.mainInput    = ''
        self.seconfInputs = ''
        self.fieldsInput  = []

        self.insert_inputs()
        self.is_empty()
        self.all_rasters()
        self.all_features()



    def is_empty(self):
        if self.type == 'FC' or self.type == 'SHP':
            if arcpy.GetCount_management(self.data_source).getOutput(0) == '0':
                self.empty = True

    def insert_inputs(self):
        self.all_inputs.append([self.layer,self.type,self.data_source,self.isOutput,self.empty,self.geomType])
        self.dict_all_inputs_archive = {i[0]:i[1:] for i in self.all_inputs}
    
    def count_inputs(self):
        return len(self.all_inputs)

    def all_rasters(self):

        all_rasters_ = len([i[1] for i in self.all_inputs if (i[1] == 'raster') or  (i[1] == 'TIF')])
        if all_rasters_ == self.count_inputs():
            self.allRaster = True

    def all_features(self):
        all_features = len([i[1] for i in self.all_inputs if (i[1] == 'FC') or(i[1] == 'SHP')])
        if all_features == self.count_inputs():
            self.allVectors   = True

    def remove_inputs(self,input_):
        self.all_inputs = [i for i in self.all_inputs if i[0] != input_]


    def add_fields_to_main_input(self):
        layer        = self.dict_all_inputs_archive[self.mainInput][1]
        self.fields  = [i.name for i in arcpy.ListFields(layer)]

    def add_fields_to_second_input(self):
        layer            = self.dict_all_inputs_archive[self.seconfInputs]
        self.sec_fields  = [i.name for i in arcpy.ListFields(layer)]


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
                Input_manager = InputAprx(layer.name,'FC',layer.dataSource,is_output,type_geom)
            elif layer.isRasterLayer:
                if layer.dataSource.endswith('tif'):
                    Input_manager = InputAprx(layer.name,'TIF',layer.dataSource,is_output,'RASTER')
                else:
                    Input_manager = InputAprx(layer.name,'raster',layer.dataSource,is_output,'gdb_RASTER')
            else:
                continue   

    return Input_manager
    


class Responed():
    def __init__(self,message = '',type_ = 'text',data = None):
        self.message = message



class Sentance():
    list_sentance = []
    def __init__(self,sentance):
        self.sentance      = sentance
        self.get_list_sentance()

    def count_sentance(self):
        return len(self.list_sentance)

    def remove_from_sentance(self,remove_word): 
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

    similar_word = 0
    mainInput     = ''
    words_pick    = []
    for layer in Input_manager.all_inputs:
        lay  = layer[0]
        for word in Mysentance.list_sentance:
            layer_low  = lay.lower()
            word_lower = word.lower()
            match_ratio = SequenceMatcher(None, layer_low, word_lower).ratio()
            if match_ratio > similar_word:
                if match_ratio > 0.8:
                    similar_word = match_ratio
                    mainInput = lay
                    words_pick.append(word)
                    if match_ratio > 9.5:
                        break

    if mainInput == '': return 

    if not Input_manager.mainInput:
        Input_manager.mainInput = mainInput
        Input_manager.add_fields_to_main_input()
        Mysentance.remove_from_sentance (words_pick)
    else:
        if list(Tools_store.dict_tools.values())[0][3] > 1:
            Input_manager.seconfInputs = mainInput
            Mysentance.remove_from_sentance (words_pick)



def move_to_seconed_input_if_geom_not_match_tool():
    print ('check if input is in tool accepted inpy')
    if Input_manager.dict_all_inputs_archive[Input_manager.mainInput][4] not in Tools_store.dict_tools[Tools_store.chosen_tool][1]:
        print ('geom is not much, moving layer to second input')
        print (Input_manager.dict_all_inputs_archive[Input_manager.mainInput][4])
        print (Tools_store.dict_tools[Tools_store.chosen_tool][1])
        Input_manager.mainInput, Input_manager.seconfInputs = Input_manager.seconfInputs, Input_manager.mainInput
        Input_manager.mainInput = ''


def find_tool():

    Tools_store.remove_by_input_geom(Input_manager)
    
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
            for tool in Tools_store.dict_tools:
                for tool_kyewards in Tools_store.dict_tools[tool][2]:
                    full_search = full_search.lower()
                    match_ratio = SequenceMatcher(None, full_search, tool_kyewards).ratio()
                    if match_ratio > similar_sentence:
                        if match_ratio > 0.7:
                            similar_sentence = match_ratio
                            tool_pick        = tool
                            sentace_pick     = full_search

    Mysentance.remove_str_sentance(sentace_pick)
    Tools_store.keep_chosen_tools(tool_pick)

    move_to_seconed_input_if_geom_not_match_tool()



def find_number_in_sentance(text):
    number = re.findall(r'\b\d+\b', text)
    if number:
        return number[0]
    else:
        return 5


def create_out_put():

    gdb = os.path.dirname(Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1])

    data_tool = Tools_store.dict_tools[Tools_store.chosen_tool]

    if data_tool[3] == 0: return ''
    out_put = [i[0] for i in Input_manager.all_inputs if 'out_put' in i[0].lower()]
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

def find_word_after(text,keywords_first):
    text        = text.split()
    text        = [''] + text
    for i in range(len(text)):
        if text[i] in keywords_first:
            if text[i-1] not in ['layer','fc','shp','layers','fcs','shps','table','tables']:
                if len(text[i+1]) > 1:
                    if text[i+1] not in['to','too','two']:
                        return text[i+1]

def find_word_after_main(text):
    keywords_first    = ['name','names']
    keywords_second   = ['field','fields','column','columns']

    a = find_word_after(text,keywords_first)
    if a: return a
    return find_word_after(text,keywords_second)


def find_type_in_text(sentences):

    sentences = sentences.split()
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

    for key in types.keys():
        if type_ in types[key]:
            type_pick = key
            break
        
    return type_pick


def run_over_fields_for_input():
    '''
    [INFO]   - Run over all fields in the layer that is picked to use and find the field that is most similar to the input by user
    [INPUT]  - get the closest field to the input layer 
    [OUTPUT] - return a dict with the most similar field name to the input by user - {../sett : muni_heb}
    '''
    if Input_manager.mainInput == '': return

    field_pick    = []
    similar_field = 0
    for field in Mysentance.list_sentance:
        for field_layer in Input_manager.fields:
            field_low       = field.lower()
            field_layer_low = field_layer.lower()
            match_ratio = SequenceMatcher(None, field_low, field_layer_low).ratio()
            if match_ratio > similar_field:
                if match_ratio > 0.7:
                    similar_field     = match_ratio
                    field_pick.append(field_layer)

    if len(field_pick) == 0:
        field_pick.append('Shape')

    Input_manager.fieldsInput = field_pick




if __name__ == '__main__':

    # sentences = arcpy.GetParameterAsText(0)

    sentences  = r' to snap yest 1000 sett'
    aprx_path  = r"CURRENT"
    aprx_path  = r"C:\Users\Administrator\Desktop\GeoML\Geom_.aprx"

    for tool in tools_archive:
        Tools_store = Tools(tool)

    Input_manager = get_all_layers_from_content(aprx_path)
    Mysentance    = Sentance(sentences)
    Tools_store.remove_tools(Input_manager)

    FindInputs()
    find_tool()
    FindInputs()

    out_put = create_out_put()

    run_over_fields_for_input()

    print (Input_manager.mainInput)
    print (Tools_store.chosen_tool)
    if out_put:
        print (out_put)

    if Input_manager.seconfInputs:
        print (Input_manager.seconfInputs)

    if Tools_store.chosen_tool  == 'create field':
        field_name = find_word_after_main  (sentences)
        field_type = find_type_in_text     (sentences)

        input_    = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation(input_,field_name,field_type)


    if Tools_store.chosen_tool == 'feature to point':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation   (input_,out_put)


    if Tools_store.chosen_tool == 'delete identical':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        fields_input    = Input_manager.fieldsInput
        tool_activation   (input_,fields_input,out_put)
    

    if Tools_store.chosen_tool == 'polygon to line':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation   (input_,out_put)

    if Tools_store.chosen_tool == 'erase':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        input_second    = Input_manager.dict_all_inputs_archive[Input_manager.seconfInputs][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation   (input_,input_second,out_put)
        try:
            if int(str(arcpy.GetCount_management(out_put))) == 0:
                tool_activation   (input_second,input_,out_put)
        except:
            pass

    if Tools_store.chosen_tool == 'topology':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation   (input_,out_put)

    if Tools_store.chosen_tool == 'vertiex to point':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        tool_activation   (input_,out_put)

    if Tools_store.chosen_tool == 'snap':
        input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
        input_second    = Input_manager.dict_all_inputs_archive[Input_manager.seconfInputs][1]
        tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
        distance        = find_number_in_sentance(Mysentance.sentance)
        tool_activation   (input_,input_second,out_put,distance)

    # if Tools_store.chosen_tool == 'erase':
    #     input_          = Input_manager.dict_all_inputs_archive[Input_manager.mainInput][1]
    #     tool_activation = Tools_store.dict_tools[Tools_store.chosen_tool][0]
    #     tool_activation   (input_,out_put)