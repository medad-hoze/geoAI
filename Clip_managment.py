# -*- coding: utf-8 -*-


import requests

import os,glob,sys,re
import tempfile
import arcpy
import datetime

from osgeo import ogr
from osgeo import osr
from osgeo import gdal

arcpy.env.overwriteOutput = True

def print_arcpy_message(msg,status = 1):
	'''
	return a message :
	
	print_arcpy_message('sample ... text',status = 1)
	>>> [info][08:59] sample...text
	'''
	msg = str(msg)
	
	if status == 1:
		prefix = '[info]'
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddMessage(msg)
		
	if status == 2 :
		prefix = '[!warning!]'
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
			
	if status == 0 :
		prefix = '[!!!err!!!]'
		
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
		msg = prefix + str(datetime.datetime.now()) +"  "+ msg
		print (msg)
		arcpy.AddWarning(msg)
			
		warning = arcpy.GetMessages(1)
		error   = arcpy.GetMessages(2)
		arcpy.AddWarning(warning)
		arcpy.AddWarning(error)
			
	if status == 3 :
		prefix = '[!FINISH!]'
		msg = prefix + str(datetime.datetime.now()) + " " + msg
		print (msg)
		arcpy.AddWarning(msg)


def find_files_by_extension(out_root,ext):

    files =glob.glob(os.path.join(out_root ,"*{}".format(ext)))
    return files

def set_ISR(filename):
    target_srs = 'EPSG:2039'
    ds = gdal.Open(filename, gdal.GA_Update)
    gdal.Warp(ds, ds, dstSRS=target_srs)
    ds = None


def RasterToPolygon(filename,out_put):


    set_ISR(filename)
    ds  = gdal.Open( filename )

        # def polygonize(self,shp_path):
    # mapping between gdal type and ogr field type
    type_mapping = {gdal.GDT_Byte: ogr.OFTInteger,
                    gdal.GDT_UInt16: ogr.OFTInteger,
                    gdal.GDT_Int16: ogr.OFTInteger,
                    gdal.GDT_UInt32: ogr.OFTInteger,
                    gdal.GDT_Int32: ogr.OFTInteger,
                    gdal.GDT_Float32: ogr.OFTReal,
                    gdal.GDT_Float64: ogr.OFTReal,
                    gdal.GDT_CInt16: ogr.OFTInteger,
                    gdal.GDT_CInt32: ogr.OFTInteger,
                    gdal.GDT_CFloat32: ogr.OFTReal,
                    gdal.GDT_CFloat64: ogr.OFTReal}

  
    srcband       = ds.GetRasterBand (1)
    dst_layername = "Shape"

    # Create polygon

    if os.path.exists(out_put): os.remove(out_put)
    drv          = ogr.GetDriverByName      ("ESRI Shapefile")
    dst_ds       = drv.CreateDataSource     (out_put)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(2039)
    dst_layer    = dst_ds.CreateLayer       (dst_layername, sr,ogr.wkbPolygon)
    raster_field = ogr.FieldDefn            ('id', type_mapping[srcband.DataType]) # get gdal based field type to ogr 

    dst_layer.CreateField     (raster_field)
    gdal.Polygonize           (srcband, None, dst_layer, -1,[], callback=None)

    dst_ds.Destroy()

    del dst_layer
    del srcband
    

def Envelope_Geom(geom,buffer = 0):
    extent = geom.extent
    Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance).buffer(buffer)
    return polygon


def updateEnvelope(cliped_layer, buffer=0):
    with arcpy.da.UpdateCursor(cliped_layer, ['SHAPE@']) as cursor:
        for row in cursor:
            geom = row[0]
            polygon = Envelope_Geom(geom,buffer)
            row[0] = polygon
            cursor.updateRow(row)
    del cursor


def Get_fcs_shps_ras(items):
    list_shp,list_fc,list_ras,dwg_list = [],[],[],[]

    for item in items:
        if not arcpy.Exists(item): continue
        if item.endswith(".shp"):
            list_shp.append(item)

        elif item.endswith(".gdb"):
            arcpy.env.workspace = item
            ListDatasets = [i for i in arcpy.ListDatasets()]
            for dataset in ListDatasets:
                arcpy.env.workspace = item + '\\' + dataset
                fcs = [item + '\\' + dataset + '\\' + i for i in arcpy.ListFeatureClasses() if i]
                list_fc.extend(fcs)
            arcpy.env.workspace = item
            fcs = [item + '\\' + i for i in arcpy.ListFeatureClasses() if i]
            list_fc.extend(fcs)

        elif item.endswith(".tif"):
            list_ras.append(item)

        elif item.endswith(".dwg"):
            dwg_list.append(item)

        elif os.path.dirname(item).split('.')[-1] == 'gdb':
            list_fc.append(item)

        elif os.path.isdir(item):
            for root, dirs, files in os.walk(item):
                for file in files:
                    if file.endswith(".shp"):
                        list_shp.append(root + '\\' +file)
                    if file.endswith(".tif"):
                        print (root + '\\' + file)
                        list_ras.append(root + '\\' + file)
                    if file.endswith(".dwg"):
                        print(".dwg")
                        print(root + '\\' + file)
                        dwg_list.append(root + '\\' + file)
                if root.endswith(".gdb"):
                    arcpy.env.workspace = root
                    fcs = [root + '\\' + i for i in arcpy.ListFeatureClasses()]
                    list_fc.extend(fcs)


        else:
            print ('not supported file type: {}'.format(item))

    list_fc  = list(set(list_fc ))
    list_shp = list(set(list_shp))
    list_ras = list(set(list_ras))

    return list_fc,list_shp,list_ras,dwg_list


def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"
    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, str(GDB_name), "CURRENT"))
    return fgdb_name


def createFolder(dic):
    try:
        if not os.path.exists(dic):
            os.makedirs(dic)
        return dic
    except:
        return dic

def create_out_folder_or_gdb(folder_out,feature_name,type_out):
    if type_out == "GDB":
        export_to = folder_out + '\\' + 'Clip_' + str(feature_name) + '.gdb'
        if arcpy.Exists(export_to): arcpy.Delete_management(export_to)
        Create_GDB(folder_out,'Clip_' + str(feature_name) + '.gdb')
    if type_out == "SHP":
        export_to = folder_out + '\\' + 'Clip_' + str(feature_name)
        if os.path.exists(export_to):
            try:
                os.remove(export_to)
            except:
                pass
        createFolder(export_to)
    return export_to

def create_path_out(item,name,type_out,type_layer,out_export):
    if type_out == "GDB": 
        name = name.replace('.shp','')
    if (type_out == "SHP") and (name.endswith('.shp') == False): 
        name = name + '.shp'
    if type_layer == "RasterDataset":
        name = os.path.basename(item)
        if type_out == "GDB":
            name = name.replace('.tif','')

    path_out   = out_export + '\\' + name 
    return path_out


def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')




def create_layers(gdb):
    
    list_fc_type = [['Polygon',"POLYGON"],['Polyline',"POLYLINE"],['Point',"POINT"]]
    exe = [arcpy.CreateFeatureclass_management(gdb,str(value[0]),value[1],has_z = "ENABLED")
           for value in list_fc_type if not arcpy.Exists(gdb +'\\' + str(value[0]))]

    return gdb + '\\' + 'Polygon', gdb + '\\' + 'Polyline', gdb + '\\' + 'Point'

def append_Poly_line_point(list_layers,layer_to_get_the_files):
    if list_layers:
        if layer_to_get_the_files:
            arcpy.Append_management (list_layers , layer_to_get_the_files  ,"NO_TEST")


def convertTo3Layers(dwgs_workspace, gdb_out):

    poly,line,point = '','',''

    for dwg_workspace in dwgs_workspace:
        polygons_fcs = dwg_workspace + '\\' + "Polygon"
        polyline_fcs = dwg_workspace + '\\' + "Polyline"
        points_fcs   = dwg_workspace + '\\' + "Point"

        folder,name  = os.path.split    (gdb_out)
        Create_GDB                      (folder,name)
        poly,line,point = create_layers (gdb_out)

        append_Poly_line_point(polygons_fcs ,poly )
        append_Poly_line_point(polyline_fcs ,line )
        append_Poly_line_point(points_fcs   ,point)

        arcpy.RepairGeometry_management(poly)
        arcpy.RepairGeometry_management(line)
        arcpy.RepairGeometry_management(point)

    

    return poly,line,point




def input_paramater_chack(param,polyon = True, polyline = True, point = True):

    desc = arcpy.Describe(param)
    Geom_type    = desc.shapeType 

    if Geom_type == 'Polygon' and polyon is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be polygon",2)
        sys.exit(1)

    if Geom_type == 'Polyline' and polyline is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be Polyline",2)
        sys.exit(1)

    if Geom_type == 'Point' and point is False:
        print_arcpy_message (f"INPUT: {os.path.basename(param)}, cant be Polyline",2)
        sys.exit(1)

    return Geom_type


def multiClip(cliped_layer,dissolve_fields,layers_in,mask,folder_out,type_out):
    #############################################################################################################

    desc       = arcpy.Describe(cliped_layer)
    coord_sys  = desc.spatialReference
    type_layer = desc.dataType

    ####################################################  cliped_layer ####################################################

    # # # # # # # #    create temp folder and gdb    # # # # # # # #
    gdb_temp      = tempfile.gettempdir() + '\\' + 'temp.gdb'
    cutting_mask  = gdb_temp              + '\\' + 'cutting_maask'
    if arcpy.Exists(gdb_temp): arcpy.Delete_management(gdb_temp)
    arcpy.CreateFileGDB_management(tempfile.gettempdir(),'temp.gdb')
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

    # # # # # # # # # # #    if raster    # # # # # # # # # # # # # #
    if type_layer == "RasterDataset":
        out_put      = tempfile.gettempdir() + '\\' + 'temp.shp'
        cliped_layer = RasterToPolygon(cliped_layer,out_put)
        arcpy.Dissolve_management     (out_put,cutting_mask)
        if mask == "true":  updateEnvelope (cutting_mask, buffer=0)
        os.remove(out_put)

    # # # # # # # # # # #    if fc or shp    # # # # # # # # # # # # # #
    if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):

        input_paramater_chack(cliped_layer,polyon = True, polyline = False, point = False)

        OID_ = str(arcpy.Describe(cliped_layer).OIDFieldName)
        if dissolve_fields == []:
            dissolve_fields = [OID_]
        try:
            arcpy.Dissolve_management     (cliped_layer,cutting_mask,dissolve_fields, multi_part="SINGLE_PART")
        except:
            arcpy.Dissolve_management     (cliped_layer,cutting_mask, multi_part="SINGLE_PART")
        if mask == "true":  updateEnvelope (cutting_mask, buffer=0)
        if OID_ in dissolve_fields:
            dissolve_fields.remove(OID_)
    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

    ####################################################  layers_in ####################################################

    # can get:  GDB, folder, shp, fc, dwg, raster

    list_fc,list_shp,list_ras,dwg_list = Get_fcs_shps_ras(layers_in)

    gdb_out_dwg     = tempfile.gettempdir() + '\\' + 'dwg.gdb'
    poly,line,point = convertTo3Layers(dwg_list, gdb_out_dwg)

    list_all = list_fc + list_shp + list_ras + [poly,line,point]
    list_all = [i for i in list_all if i != '']

    OID_    = str(arcpy.Describe(cutting_mask).OIDFieldName)
    columns = ['SHAPE@',OID_] + dissolve_fields
    columns = [i for i in columns if i != '']

    with arcpy.da.SearchCursor(cutting_mask,columns) as Cursor:
        for row in Cursor:
            geom       = row[0]
            all_other  = '_'.join([str(i) for i in row[1:]])
            out_export = create_out_folder_or_gdb (folder_out,all_other,type_out)

            for item in list_all:
                if not arcpy.Exists(item): continue
                
                desc       = arcpy.Describe(item)
                type_layer = desc.dataType
                name       = desc.name
                path_out   = create_path_out(item,name,type_out,type_layer,out_export)

                if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):
                    
                    if arcpy.Exists(path_out): continue
                    arcpy.Clip_analysis(item,geom,path_out)
                    if int(str(arcpy.GetCount_management(path_out))) == 0: 
                        arcpy.Delete_management(path_out)

                if type_layer == "RasterDataset":
                    try:
                        arcpy.Clip_management(item, "", path_out,geom , "", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
                        arcpy.DefineProjection_management(path_out,coord_sys)
                        if arcpy.GetRasterProperties_management(path_out, "MAXIMUM") == 0:
                            arcpy.Delete_management(path_out)
                    except:
                        if arcpy.Exists(path_out): arcpy.Delete_management(path_out)

            if type_out == 'GDB':
                arcpy.env.workspace = out_export
                feC = list(arcpy.ListFeatureClasses())
                feD = list(arcpy.ListDatasets())
                LeR = list(arcpy.ListRasters())
                if (feC == []) and (feD == []) and (LeR == []):
                    arcpy.Delete_management(out_export)

    try:
        arcpy.Delete_management(gdb_temp)
    except:
        pass
    try:
        arcpy.Delete_management(gdb_out_dwg)
    except:
        pass
                    



