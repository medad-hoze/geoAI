# -*- coding: utf-8 -*-

# import matplotlib.pyplot as plt
import pandas as pd
import arcpy,re
import json,datetime
import math,sys,os
import random

def find_number_in_sentance(text):
    number = re.findall(r'\b\d+\b', text)
    if number:
        number = sorted([float(i) for i in number])
        return number
    else:
        return [1, 1000]


def get_random_number(range_nums):
    if (len(range_nums) == 2) and (range_nums[1] > 1):
        random_number = random.randint(range_nums[0], range_nums[1])
    else:
        random_number = random.random()

    return random_number


def insert_random_number_to_layer(layer, sentence,field_name):
    range_nums = find_number_in_sentance(sentence)


    with arcpy.da.UpdateCursor(layer, [field_name]) as cursor:
        for row in cursor:
            random_number = get_random_number(range_nums)
            row[0] = random_number
            cursor.updateRow(row)

    del cursor