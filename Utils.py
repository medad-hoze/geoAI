


import re
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

    for key in types.keys():
        if type_ in types[key]:
            type_pick = key
            break
        
    return type_pick


# def create_out_put(gdb,all_inputss):

#     data_tool = Tools_store.dict_tools[Tools_store.chosen_tool]

#     if data_tool[3] == 0: return ''
#     out_put = [i[0] for i in all_inputss if 'out_put' in i[0].lower()]
#     if out_put:
#         out_put           = sorted(out_put)[-1]
#         old_name_num      = out_put.split('_')[-1]
#         old_name_num      = str(find_number_in_sentance(old_name_num))
#         new_name_num      = str(int(old_name_num) + 1)
#         name_output_layer = gdb + '\\' + out_put.replace(old_name_num,new_name_num)
#     else:
#         name_output_layer = gdb + '\\' + 'out_put_1'

#     if arcpy.Exists(name_output_layer +'\\' + '_Temp'):
#         arcpy.Delete_management(name_output_layer +'\\' + '_Temp')

#     return name_output_layer