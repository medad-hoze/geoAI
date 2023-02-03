


from osgeo import ogr
from osgeo import osr

from osgeo import gdal
import arcpy,os


def set_ISR(filename):
    target_srs = 'EPSG:2039'
    ds = gdal.Open(filename, gdal.GA_Update)
    gdal.Warp(ds, ds, dstSRS=target_srs)
    ds = None

def RasterToPolygon(filename,out_put):


    set_ISR(filename)
    arcpy.AddMessage(filename)
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
    shp_path     = os.path.dirname(filename) + '\\' + 'temp.shp'
    drv          = ogr.GetDriverByName      ("ESRI Shapefile")
    dst_ds       = drv.CreateDataSource     (shp_path)
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(2039)
    dst_layer    = dst_ds.CreateLayer       (dst_layername, sr,ogr.wkbPolygon)
    raster_field = ogr.FieldDefn            ('id', type_mapping[srcband.DataType]) # get gdal based field type to ogr 

    dst_layer.CreateField     (raster_field)
    gdal.Polygonize           (srcband, srcband, dst_layer, 0,['id'], callback=None)

    dst_ds.Destroy()

    del dst_layer
    del srcband
    
    arcpy.Select_analysis   (shp_path,out_put)
    arcpy.Delete_management (shp_path)

