# -*- coding: utf-8 -*-

import os
import arcpy
import sys


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)

def combine_str(list_):
    #  take list of values and connect by '-'
    list_ = [str(i) for i in list_]
    if len(list_) > 1:
        return '-'.join(list_)
    elif len(list_) == 1:
        return list_[0]
    else:
        print ('error no id field is found')
        sys.exit(1)


def updated_data(list_):
    if len(list_) == 1:
        return list_[0]
    return list_

def extract_data_key_value(path_layer,field1_ids,field1_data):
    fields_all = field1_ids + field1_data
    len_id     = len(field1_ids)
    data       = {combine_str(row[:len_id]): updated_data(row[len_id:]) 
            for row in arcpy.da.SearchCursor(path_layer,fields_all)}
    return data


def update_columns_by_key(update_layer,field2_ids,field2_update,data,field1_data):
    for i in field2_update: add_field(update_layer,i)

    fields_all2 = field2_ids + field2_update
    len_id2     = len(field2_ids)

    if len(field1_data) != len(field2_update):
        print ('updated fields and data source fields must be the same number')
        sys.exit(1)

    with arcpy.da.UpdateCursor(update_layer,fields_all2) as Ucursor:
        for row in Ucursor:
            id = combine_str(row[:len_id2])
            if data.get(id):
                if len(row[len_id2:]) == 1:
                    row[-1] = data[id]
                else:
                    row[len_id2:] = data[id]

                Ucursor.updateRow(row)
    del Ucursor


def get_ID_value(text):
    text= text.split(';')

    id_    = []
    value_ = []
    for i in text:
        split_me = i.split(' ')
        if (split_me[0] != '#'): 
            id_.append(split_me[0])
        if (split_me[1] != '#'):
            value_.append(split_me[1])

    return id_,value_


def join_field(source_layer,field1_ids,field1_data,update_layer,field2_ids,field2_update):
    # extract data from path_layer
    if (field1_ids == None) or (field1_data == None):return None
    data         = extract_data_key_value(source_layer,field1_ids,field1_data)

    if (field2_ids == None):
        return None
    if (field1_data == None):
        return None
    # update data in update_layer by the data extracted 
    update_columns_by_key(update_layer,field2_ids,field2_update,data,field1_data)


