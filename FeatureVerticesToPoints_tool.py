


import arcpy,os

arcpy.env.overwriteOutput = True


def add_field(fc,field,Type = 'TEXT'):

    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:arcpy.AddField_management (fc, field, Type, "", "", 500)


def createNewLayer(new_layer,template = "",geomType = "POLYGON"):
    name = os.path.basename(new_layer)
    path = os.path.dirname (new_layer)
    if arcpy.Exists(new_layer):
        arcpy.Delete_management(new_layer)
    arcpy.CreateFeatureclass_management(path, name, geomType,template)
    return new_layer


def FeatureVerticesToPoints(layer,outPut):

    '''
    get polygon or polyline and return vertics
    '''

    createNewLayer(outPut,layer,'POINT')

    name       = os.path.basename(layer)
    field_name = 'FID_'+ name
    OID        = str(arcpy.Describe(outPut).OIDFieldName)

    add_field(outPut,field_name,'LONG')
    arcpy.CalculateField_management (outPut, field_name,f"!{OID}!", "PYTHON")

    columns    = [f.name for f in arcpy.ListFields(layer) if f.name not in ('SHAPE','Shape_Length','Shape_Area','Shape')] + ["SHAPE@"] + [field_name]
    ins_cursor = arcpy.da.InsertCursor (outPut, columns)
    OID_in     = str(arcpy.Describe(layer).OIDFieldName)
    poly_data  = [list(i[:-1]) + [arcpy.PointGeometry(arcpy.Point(j.X,j.Y))] + [i[columns.index(OID_in)]]
                       for i in arcpy.da.SearchCursor (layer,columns[:-1]) for n in i[-1] for j in n if j]


    for i in poly_data:ins_cursor.insertRow (i)  



