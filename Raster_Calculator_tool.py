



from osgeo import gdal
import numpy as np
import arcpy

arcpy.env.overwriteOutput = True

def wrapper1(func, args): # with star
    return func(*args)


def getArrayCalc(list_of_arrays,actions):
    if actions in ['min','minimum'] : 
        result = wrapper1(np.minimum, list_of_arrays)
    if actions in ['max','maximum']: 
        result = wrapper1(np.maximum, list_of_arrays)
    if actions == 'sum': 
        result = wrapper1(np.add, list_of_arrays)
    if actions in ['sub','-']: 
        result = wrapper1(np.subtract, list_of_arrays)
    if actions in ['mul','*']: 
        result = wrapper1(np.multiply, list_of_arrays)
    if actions in ['div','/']: 
        result = wrapper1(np.divide, list_of_arrays)
    if actions in ['pow','**']: 
        result = wrapper1(np.power, list_of_arrays)
    return result

def outRaster(out_put,array,template):
    template = gdal.Open(template)
    driver   = gdal.GetDriverByName("GTiff")
    out_ds   = driver.Create(out_put, template.RasterXSize, template.RasterYSize, 1, gdal.GDT_Float32)
    out_ds.GetRasterBand(1).WriteArray(array)
    out_ds.SetProjection(template.GetProjection())
    out_ds.SetGeoTransform(template.GetGeoTransform())

def packArraysOfRasters(rasters):
    list_of_arrays = []
    for i in rasters:
        raster = gdal.Open(i)
        band   = raster.GetRasterBand(1)
        data   = band.ReadAsArray()
        list_of_arrays.append(data)
    return list_of_arrays



def Raster_Calculator_tool(rasters,actions,out_put):
    list_of_arrays = packArraysOfRasters(rasters)
    result         = getArrayCalc(list_of_arrays,actions)
    outRaster(out_put,result,rasters[0])

