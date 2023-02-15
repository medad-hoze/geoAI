# -*- coding: utf-8 -*-

import arcpy,os,json
import pandas as pd
import re,sys
from difflib import SequenceMatcher
import tempfile
import operator
from operator import itemgetter
from ToolsSafe import tools_archive
from Utils import *
import os,requests
from FindLayers import data_SETL


def check_lists(list1,list2):
    for i in list1:
        if i in list2:
            return True
    return False


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


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
        if self.picked_tool:
            print ('picked tool: ' + str(self.picked_tool.id_))
            print ('number of outputs needed: ' + str(self.int_picked_tool))
        else:
            print ('no tool find')
        

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

            # check if tool geom fit with input

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
                if Tools_store.picked_tool:
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
            if arcpy.Exists(self.data_source):
                if arcpy.GetCount_management(self.data_source).getOutput(0) == '0':
                    self.empty = True
            else:
                self.empty = True

    def add_fields(self):
        if arcpy.Exists(self.data_source):
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
 

        if Tools_store.picked_tool == '':
            print ('error: no main tool found')
            arcpy.AddMessage('No main tool found, improve your query')
            sys.exit(1)
        else:
            print ('error: no main input found')
            if Tools_store.picked_tool == '':
                print ('error: no main tool found')
                arcpy.AddMessage('No main input or tool found, plz save aprex, and improve your query')
                sys.exit(1)


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


def is_1_input_and_fit_geometry(tool):
    '''
    if tool can have 1 input and the must score input is not in his
    geometry type then return False, for example: will know if: to line, is from polygon or point 
    with the user input
    '''
    if tool.num_input == 1:
        geometry_  = None
        save_score = 0
        for input_ in InputsManager.all_inputs:
            score = input_.score
            if score > 0.8:
                if score > save_score:
                    save_score = score
                    geometry_ = input_.geomType
        if geometry_:
            if geometry_ not in tool.Geotypes:
                return False
    return True


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
                    if not is_1_input_and_fit_geometry(tool):continue
                    full_search = full_search.lower()
                    match_ratio = SequenceMatcher(None, full_search, tool_kyewards).ratio()
                    if match_ratio > similar_sentence:
                        if match_ratio > 0.78:
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
        arcpy.AddMessage('####################################################',2)
        arcpy.AddMessage('#########  internet connection is needed ###########',2)
        arcpy.AddMessage('####################################################',2)
        sys.exit(1)



def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |       Made by: MYYGeoAi , all rights reserved      |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')


def check_geom_match(input_1,input_2):

    shape_type1 = arcpy.Describe(input_1).shapeType
    shape_type2 = arcpy.Describe(input_2).shapeType
    if shape_type1 != shape_type2:
        arcpy.AddMessage ('Geom of inputs are not match')
        sys.exit(1)

def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


def get_field_if_not_exists_create_field(input_layer):
        main_a_field  = [i[0] for i in InputsManager.mainInput.fields_match if i[0] != 'to']
        if main_a_field:
            main_a_field = main_a_field[0]
        if not main_a_field:
            add_field(input_layer,'TempField','LONG')
            arcpy.CalculateField_management(input_layer,'TempField',1)
            main_a_field = 'TempField'
            return main_a_field,True
        return main_a_field,False


def found_claculation_methos():

    values_calculate = {'min':['min','minimum'],
                        'max':['max','maximum'],
                        'sum':['sum'],
                        'sub':['sub','subtract','reduce'],
                        'mul':['mul','multiply'],
                        'div':['div','divide'],
                        'pow':['pow','power']}

    best_score = 0
    calc_method = None
    for key,value in values_calculate.items():
        for v in value:
            for word in Mysentance.list_sentance:
                word = word.lower()
                match_ratio = SequenceMatcher(None, v, word).ratio()
                if match_ratio > 0.7:
                    if match_ratio > best_score:
                        calc_method = key
                        best_score = match_ratio
    return calc_method


def get_layer_and_field_from_city(data_SETL,input_layer,sentences):

    city          = find_city(data_SETL,sentences)
    gdb_temp      = tempfile.gettempdir() + '\\' + 'temp.gdb'
    if arcpy.Exists(gdb_temp): arcpy.Delete_management(gdb_temp)
    arcpy.CreateFileGDB_management(tempfile.gettempdir(),'temp.gdb')
    
    input_layer        = gdb_temp + '\\' + 'temp_city'
    get_settlement_to_layer(data_SETL,city,input_layer)
    main_a_fields   = ['OBJECTID']
    if field_name:
        main_a_fields  = [field_name]

    return input_layer,main_a_fields

if __name__ == '__main__':

    copyRights(version = '0.0.3')
    license_key()

    sentences = arcpy.GetParameterAsText(0)

    # sentences  = r'join field mama from layer sett with field id in layer test1 and transfer field pizza'
    # sentences  = r'create field blabla type long in sett'
    # sentences  = r'feature to point sett'
    # sentences  = r'delete test1 from layer sett'
    # sentences  = r'delete identical from layer sett on field mama2'
    # sentences  = r'find identical from layer sett on field mama2'
    # sentences  = r'convert DEM_haifa to polygon'
    # sentences  = r'go to haifa'
    # sentences =  r'fdwseef to polyline'
    # sentences =  r'fdwseefefcewf'
    # sentences = r'out_put_1 to raster'
    # sentences = r'out_put_2 to line'
    # sentences = r'calculate rdsfsdfer and Point_to_raster find the maximum value'
    # sentences = r'clip all layers from haifa in folder: C:\Users\Administrator\Desktop\ArcpyToolsBox\test'

    # sentences  = r'clip fdwseef from C:\Users\Administrator\Desktop\ArcpyToolsBox\test'

    aprx_path  = r"CURRENT"
    # aprx_path  = r"C:\Users\Administrator\Desktop\GeoML\Geom_.aprx"

    if not sentences:
        print ('i have no sentance to work with') 
        sys.exit(1)

    arcpy.AddMessage('Your sentance is: ' + sentences)

    InputsManager = InputManager  ()
    Tools_store   = Tools_manager ()
    Mysentance    = Sentance      (sentences)
    get_Responed  = Responed      ()

    Tools_store.insertTools(tools_archive)

    get_all_layers_from_content(aprx_path)

    Mysentance    = Sentance(sentences)


    InputsManager.Count_inputs()

    FindInputs()
    Tools_store.remove_tools_by_inputLayers()
    get_out_put_as_Input       ()
    find_tool()

    InputsManager.check_if_first_input()


    number      = find_number_in_sentance  (Mysentance.sentance)
    type_       = find_type_in_text        (Mysentance.list_sentance)
    field_name  = find_field_name          (Mysentance.sentance_full)
    calc_method = found_claculation_methos()

    match_fields_from_input_to_layer()

    InputsManager.Get_main_and_seconed_inputs()
    InputsManager.Get_main_and_seconed_fields()


    get_Responed.update()

    out_put         = create_out_put(InputsManager)
    input_layer = ''
    if InputsManager.mainInput:
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

    if input_layer:
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

    layer_1_input_1_out = ('point to line','vertiex to point','topology','polygon to line',
                            'eliminate','split line by vertex','Feature_to_polygon')
    if Tools_store.picked_tool.id_ in layer_1_input_1_out:
        tool_activation(input_layer,out_put)
        getLayerOnMap(out_put)


    if (Tools_store.picked_tool.id_ == 'Spatial Join'):
        tool_activation(input_layer,seconfInputs,out_put)
        getLayerOnMap(out_put)

    if (Tools_store.picked_tool.id_ == 'near'):
        tool_activation(input_layer,seconfInputs,number)
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

        if InputsManager.mainInput:
            main_a_fields  = [i[0] for i in InputsManager.mainInput.fields_match]
        else:
            input_layer,main_a_fields =  get_layer_and_field_from_city(data_SETL,input_layer,sentences)

        data_source = find_data_source(sentences)

        if data_source == '':
            data_source = seconfInputs

        folder_out = os.path.dirname(input_layer)
        if folder_out.endswith('gdb'):
            folder_out = os.path.dirname(folder_out)

        tool_activation (input_layer,main_a_fields ,[data_source],'false',folder_out,'GDB',False)


    if Tools_store.picked_tool.id_ == 'raster to polygon':
    
        folder = os.path.dirname(input_layer) 
        if folder.endswith('gdb'):
            folder = os.path.dirname(folder)
        
        out_put = folder + '\\' + 'raster.shp'

        tool_activation(input_layer,out_put)
        getLayerOnMap(out_put)


    if Tools_store.picked_tool.id_ == 'append':
        check_geom_match(input_layer,seconfInputs)
        tool_activation([seconfInputs],input_layer,'NO_TEST')
        getLayerOnMap(out_put)
    

    if Tools_store.picked_tool.id_ == 'point to raster':
        out_put = os.path.dirname(os.path.dirname(input_layer)) + '\\' + 'Point_to_raster.tif'
        main_a_field,is_changed = get_field_if_not_exists_create_field(input_layer)

        arcpy.AddMessage (f'will use {main_a_field} as value field')
        arcpy.AddMessage (f'you will found out put at: {out_put}')
        arcpy.AddMessage (f'field of Z values        : {main_a_field}')
        if number:
            arcpy.AddMessage (f'cell size: {number}') 
        else:
            arcpy.AddMessage (f'cell size defualt is: 1 meters')

        if arcpy.Exists(out_put):arcpy.Delete_management(out_put)
        tool_activation(input_layer,main_a_field,out_put,number)
        getLayerOnMap(out_put)
        if is_changed:arcpy.DeleteField_management(input_layer,main_a_field)


    if Tools_store.picked_tool.id_ == 'raster Calculator':
        out_put = os.path.dirname(input_layer) + '\\' + 'Raster_Calculator.tif'
        arcpy.AddMessage (f'you will found out put at: {out_put}')
        arcpy.AddMessage (f'calc_method: {calc_method}')
        arcpy.AddMessage (f'seconed raster: {seconfInputs}')
        tool_activation([input_layer,seconfInputs],calc_method,out_put)