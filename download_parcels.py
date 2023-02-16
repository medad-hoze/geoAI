
# pyodbc

import  requests,os, zipfile
import tempfile
import arcpy

def unzip_files(datafolder,targetFile):
    '''
    Unzip the parcels data
    '''

    try:
        zipToFolder = datafolder + "\\" + "unzipFiles"
        if not os.path.exists(zipToFolder):
            os.mkdir(zipToFolder)
        with zipfile.ZipFile(targetFile, 'r') as zip_ref:
            zip_ref.extractall(zipToFolder)
    except:
        print("Error")
        raise


def download_parcels_data(out_put = ''):
    '''
    Download the parcels data from data.gov.il
    '''

    datafolder = tempfile.gettempdir() 

    if not os.path.exists(out_put):
        out_put = datafolder
        arcpy.AddMessage('out_put not found, using temp folder')

    
    zipURL = 'https://data.gov.il/dataset/shape/resource/c68b4df6-c809-4bb5-a546-61fa1528fed5/download/parcel_all.zip'
    targetFile = datafolder + '\parcel_all.zip'

    try:
        headers = {'User-Agent': 'datagov-external-client'}
        req = requests.get(zipURL, stream = True, headers = headers, verify=False)
        with open(targetFile, "wb") as f:
            for chunk in req.iter_content(chunk_size = 1024):
                if chunk:
                    f.write(chunk)
    except:
        print("Error")
        raise

    unzip_files(out_put,targetFile)

    return out_put + '\\' + 'unzipFiles' + '\\' + 'PARCEL_ALL.shp'


