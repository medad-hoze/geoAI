



import os



sentences = r'map all layers on  C:\Users\Administrator\Desktop\GeoML\data\New File Geodatabase.gdb'

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


