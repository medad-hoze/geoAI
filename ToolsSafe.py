


import arcpy


from DeleteIdentical_tool         import Delete_Identical_Byfield
from PolygonToLine_tool           import PolygonToLine
from Erase_tool                   import analysis_Erase
from CreateTopology_tool          import CreateTopology
from FeatureVerticesToPoints_tool import FeatureVerticesToPoints
from Snap_tool                    import Snap
from Eliminate_tool               import Eliminate
from FindIdentical_tool           import Find_Identical_Byfield
from Simplify_Polygon             import Simplify_Polygons
from SplitLineAtVertices          import Split_Line_By_Vertex_tool  
from FeatureToPolygon_tool        import Feature_to_polygon
from FindLayers                   import find_layers_main,data_SETL
from Clip_managment               import multiClip
from Raster_to_Polygon_tool       import RasterToPolygon
from Multi_FieldJoin_tool         import join_field
from PointToRaster_tool           import Rasrize_point
from Raster_Calculator_tool       import Raster_Calculator_tool
from Create_a_continuous_layer    import create_compilation
from download_parcels             import download_parcels_data
from Network_analysis             import find_shortest_path
from Small_tools                  import insert_random_number_to_layer

def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


tools_archive = [
    # '''
    # id tool             ,activation tool                   ,type of tool input          ,        keywards       ,number of inputs\fields          have output
                                                                                                                                                                        
    # '''

    ['delete identical'     ,Delete_Identical_Byfield        ,['Polygon','Polyline','Point'] ,['delete identical']                 ,1,1,True],
    ['polygon to line'      ,PolygonToLine                   ,['Polygon']                    ,['to line','polygon to line',
                                                                                               'to polyline']                      ,1,0,True],
    ['erase'                ,analysis_Erase                  ,['Polygon','Polyline','Point'] ,['delete','erase']                   ,2,0,True],
    ['topology'             ,CreateTopology                  ,['Polygon']                    ,['topology','create topology']       ,1,0,True],
    ['vertiex to point'     ,FeatureVerticesToPoints         ,['Polygon','Polyline']         ,['vertiex to point',      
                                                                                               'vertices to point','get vertices'] ,1,0,True],
    ['snap'                 ,Snap                            ,['Polygon','Polyline']         ,['snap']                             ,2,0,True],
    ['eliminate'            ,Eliminate                       ,['Polygon']                    ,['slivers','eliminate']              ,1,0,True],
    ['find identical'       ,Find_Identical_Byfield          ,['Polygon','Polyline','Point'] ,['find identical']                   ,1,1,False],
    ['simplify'             ,Simplify_Polygons               ,['Polygon','Polyline']         ,['remove vertices','simplify']       ,1,0,True],
    ['split line by vertex' ,Split_Line_By_Vertex_tool       ,['Polyline']                   ,['split line by vertex',
                                                                                               'by vertex','by vertices']          ,1,0,True],
    ['intersect'            ,arcpy.Intersect_analysis        ,['Polygon','Polyline','Point'] ,['intersect','intersects']           ,2,0,True],
    ['buffer'               ,arcpy.Buffer_analysis           ,['Polygon','Polyline','Point'] ,['buffer']                           ,1,0,True],
    ['join fields'          ,join_field                      ,['Polygon','Polyline','Point'] ,['join fields','join field', 
                                                                                               'connect field']                    ,2,2,False],
    ['Spatial Join'         ,arcpy.SpatialJoin_analysis      ,['Polygon','Polyline','Point'] ,['spatial join','by location']       ,2,0,False],
    ['Feature_to_polygon'   ,Feature_to_polygon              ,['Polygon','Polyline','Point'] ,['to polygon','feature to polygon']  ,1,0,False],
    ['find layers'          ,find_layers_main                ,['Polygon','Polyline','Point'] ,['find Layers','locate layers',
                                                                                                'map layers', 'find all layers',
                                                                                                'find raster','go to','zoom to']   ,0,0,False],
    ['create field'         ,add_field                       ,['Polygon','Polyline','Point'] ,['add field','create field',
                                                                                                'create new field']                ,0,1,False],
    ['multiClip'            ,multiClip                       ,['Polygon']                    ,['multiClip','multi clip', 'clip all',
                                                                                                'clip all layers','clip']          ,1,0,True],
    ['feature to point'     ,arcpy.FeatureToPoint_management ,['Polygon','Polyline']         ,['feature to point','create point',
                                                                                                'to point','to points']             ,1,0,True],
    ['raster to polygon'    ,RasterToPolygon                 ,['raster']                     ,['raster to polygon','to polygon',
                                                                                                'as raster','to shp',
                                                                                                'to shapefile','to layer']          ,1,0,True],
    ['point to line'        ,arcpy.PointsToLine_management    ,['Point']                        ,['point to line','to line']        ,1,0,True],
    ['near'                 ,arcpy.Near_analysis              ,['Polygon','Polyline','Point']   ,['near','close to', 'close']       ,2,0,False],

    ['append'               ,arcpy.Append_management          ,['Polygon','Polyline','Point']   ,['append','append layers','add to'
                                                                                                ,'add layer']                       ,2,0,False], 
    ['point to raster'      ,Rasrize_point                    ,['Point']                       ,['point to raster','to raster']     ,1,1,False],
    ['raster Calculator'    ,Raster_Calculator_tool           ,['raster']                      ,['raster calculator','calculator',
                                                                                                'get max','get min','get max',
                                                                                                'get mean','get avareage',
                                                                                                'calculate raster']                 ,2,0,True],
    ['create compilation'   ,create_compilation               ,['Polygon']                     ,['create compilation','overlay',
                                                                                                'compilation','continuous',
                                                                                                 'overlap','rank','by date']         ,1,1,True],
    ['download parcels',    download_parcels_data             ,['Polygon','Polyline','Point']    ,['download parcels','download',
                                                                                                 'cadaster']                         ,0,0,False],
    ['remove field' ,       arcpy.DeleteField_management      ,['Polygon','Polyline','Point']    ,['remove field','delete field']    ,1,1,False],
    ['find shortest path',  find_shortest_path                ,['Polyline']                    ,['shortest path','network',
                                                                                                   'shortest']                       ,2,0,True ],
    ['insert random num',  insert_random_number_to_layer      ,['Polygon','Polyline','Point']  ,['random number','insert random',
                                                                                                 'random']                           ,1,1,True ]                                                                                                                                        
]



# aprx            = arcpy.mp.ArcGISProject(aprx_path)
# list_map        = aprx.listMaps('*')
# for map_ in list_map:
#     # for layer in map_.listTables():
#     print (map_.name)
#     for m in map_.listTables():
#         print (m.name)
#         is_output = False
#         if 'out_put' in m.name.lower():
#             is_output = True
#         Input_manager = InputAprx(layer.name,'table',layer.dataSource,is_output) 


