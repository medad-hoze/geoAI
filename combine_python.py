# combine.py




def read_file(filename):
    with open(filename, 'r') as f:
        return f.read()

def combine_files(filenames):
    combined_code = ''
    for filename in filenames:
        combined_code += read_file(filename)
    return combined_code

if __name__ == '__main__':

    path = r'C:\Users\Administrator\Desktop\GeoML2'

    filenames = [path + '\\' + 'Clip_managment.py', path + '\\''CreateTopology_tool.py',path + '\\''DeleteIdentical_tool.py',
                 path + '\\'+'Utils.py', path + '\\' + 'SplitLineAtVertices.py',path + '\\' + 'FindLayers.py',
                 path + '\\'+'Snap_tool.py', path + '\\'+'Simplify_Polygon.py', path + '\\'+'Raster_to_Polygon_tool.py',
                 path + '\\'+'PolygonToLine_tool.py', path + '\\'+'FeatureToPolygon_tool.py',path + '\\'+'Erase_tool.py',
                 path + '\\'+'FindIdentical_tool.py',path + '\\'+'FeatureVerticesToPoints_tool.py',path + '\\'+'Multi_FieldJoin_tool.py',
                 path + '\\'+'Eliminate_tool.py',path + '\\' +'ToolsSafe.py',path + '\\'+'GeoChat3.py']
    combined_code = combine_files(filenames)
    with open(path + '\\' +'combined.py', 'w') as f:
        f.write(combined_code)