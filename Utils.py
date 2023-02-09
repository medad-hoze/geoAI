


import re,os
import arcpy
from difflib import SequenceMatcher


def find_number_in_sentance(text):
    number = re.findall(r'\b\d+\b', text)
    if number:
        return number[0]
    else:
        return 5


def find_word_after(text:str,keywords_first:list):
    text        = text.split()
    text        = [''] + text
    for i in range(len(text)):
        if text[i].lower() in keywords_first:
            if text[i-1] not in ['layer','fc','shp','layers','fcs','shps','table','tables']:
                if len(text[i+1]) > 1:
                    if text[i+1] not in['to','too','two']:
                        return text[i+1]
    return ''

def find_field_name(text:str):
    '''
    find field that not exists in any layer, field need to be added
    '''
    keywords_first    = ['name','names']
    keywords_second   = ['field','fields','column','columns']

    a = find_word_after(text,keywords_first)
    if a: return a
    return find_word_after(text,keywords_second)


def find_type_in_text(sentences:list):

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
                    score = match_ratio

    for key in types.keys():
        if type_ in types[key]:
            type_pick = key
            return type_pick
    return type_pick



def getLayerOnMap(path_layer,aprxMap = 'CURRENT'):
    if not arcpy.Exists(path_layer):return 

    aprx = arcpy.mp.ArcGISProject(aprxMap)
    aprxMap = aprx.listMaps("Map")[0] 
    lyr = aprxMap.addDataFromPath(path_layer)
    # aprxMap.addLayer(lyr)
    aprx.activeView

    del aprxMap
    del aprx



def create_out_put(InputsManager):

    gdb     = os.path.dirname(InputsManager.mainInput.data_source)
    out_put = [input_.layer for input_ in InputsManager.all_inputs if 'out_put' in input_.layer]

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


def find_data_source(sentences):
    path_dataSorce = ''
    sentences        = [''] + sentences.split()
    length           = len(sentences)
    for i in range(length):
        full_search = ''
        for j in range(i+1,length):
            words = sentences[j]
            full_search += words + ' '
            if os.path.exists(full_search):
                path_dataSorce = full_search
    return path_dataSorce


def find_city(data_SETL,sentance):
    cities = [i[1] for i in data_SETL]
    sentance = sentance.split()
    city_final = ''
    for city in cities:
        similar_field = 0
        for word in sentance:
            word = word.lower()
            city = city.lower()
            match_ratio = SequenceMatcher(None, word, city).ratio()
            if match_ratio > similar_field:
                similar_field =  match_ratio
                if match_ratio > 0.7:
                    city_final = city
    return city_final


def find_type_for_feature_to_point(sentance):
    types_accepted = ["INSIDE","CENTROID"]
    sentance = sentance.split()
    type_ = ''
    score = 0
    for word in sentance:
        for type_word in types_accepted:
            word = word.lower()
            match_ratio = SequenceMatcher(None, word, type_word).ratio()
            if match_ratio > score:
                score = match_ratio
                if match_ratio > 0.7:
                    type_ = type_word
    
    if type_ == '':
        type_ = 'INSIDE'
    
    return type_