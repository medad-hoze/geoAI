# -*- coding: utf-8 -*-


import arcpy,os
import requests
import re
import sys
import datetime
from difflib import SequenceMatcher
import pandas as pd
import re
import tempfile

from osgeo import ogr
from osgeo import osr
from osgeo import gdal

arcpy.env.overwriteOutput = True

# def create_data_():
# layer = r'C:\Users\Administrator\Desktop\ML_main_Tools\4_Process_Shade\Layers\Data\Bantal.GDB\BUILDINGS\SETL_AREA'
#     columns       = ['SETL_NAME','SETL_NAME_LTN','SETL_CODE'] + ['SHAPE@']
#     list_data     = [list(row[:-1]) + [remove_decimal(Envelope_Geom_by_Geom(row[-1]).WKT)] for row in
#                     arcpy.da.SearchCursor(layer,columns) if (row[columns.index('SETL_NAME')] is not None) 
#                     and (row[columns.index('SETL_NAME')] != -98) if row[columns.index('SHAPE@')].area > 5000000]
#     print (len(list_data))
#     for i in list_data:
#         print (i+ [','])

data_SETL = [['סעווה', "Sa'wa", 1360, 'MULTIPOLYGON (((194708 571757, 200534 571757, 200534 575345, 194708 575345, 194708 571757)))'],
['רמלה', 'Ramla', 8500, 'MULTIPOLYGON (((185161 646485, 191358 646485, 191358 649951, 185161 649951, 185161 646485)))'],
['תל שבע', "Tel Sheva'", 1054, 'MULTIPOLYGON (((185149 571700, 188650 571700, 188650 574363, 185149 574363, 185149 571700)))'],
['אבו קורינאת ', 'Abu Kuraynat', 1342, 'MULTIPOLYGON (((194218 558549, 198827 558549, 198827 562814, 194218 562814, 194218 558549)))'],
['אשקלון', 'Ashkelon', 7100, 'MULTIPOLYGON (((154951 614806, 164154 614806, 164154 624324, 154951 624324, 154951 614806)))'],
['ראשון לציון', 'Rishon LeTsiyon', 8300, 'MULTIPOLYGON (((174661 649688, 184348 649688, 184348 656799, 174661 656799, 174661 649688)))'],
["ס'וריף", 'Surif', 3771, 'MULTIPOLYGON (((204590 614997, 208159 614997, 208159 619118, 204590 619118, 204590 614997)))'],
['קריית ביאליק', 'Kiryat Bialik', 9500, 'MULTIPOLYGON (((207084 746249, 210603 746249, 210603 753359, 207084 753359, 207084 746249)))'],
["באקה אל-ר'רבייה", 'Baka al-Gharbiya', 6000, 'MULTIPOLYGON (((202340 700889, 205643 700889, 205643 704439, 202340 704439, 202340 700889)))'],
['קלנסווה', 'Kalansawa', 638, 'MULTIPOLYGON (((196399 686966, 199561 686966, 199561 690184, 196399 690184, 196399 686966)))'],
['ראש העין', "Rosh Ha'Ayin", 2640, 'MULTIPOLYGON (((194076 664555, 199329 664555, 199329 669174, 194076 669174, 194076 664555)))'],
['כפר קאסם', 'Kafr Kasem', 634, 'MULTIPOLYGON (((194812 667875, 199300 667875, 199300 670775, 194812 670775, 194812 667875)))'],
['בני נעים', "Bani Na'im", 3093, 'MULTIPOLYGON (((212708 601163, 216964 601163, 216964 604923, 212708 604923, 212708 601163)))'],
['נהרייה', 'Nahariya', 9100, 'MULTIPOLYGON (((208030 765795, 211556 765795, 211556 772048, 208030 772048, 208030 765795)))'],
['נאות חובב', "Ne'ot Hovav", 1770, 'MULTIPOLYGON (((178682 559064, 181382 559064, 181382 562446, 178682 562446, 178682 559064)))'],
['מעלה אדומים', "Ma'ale Adummim", 3616, 'MULTIPOLYGON (((227376 629992, 232961 629992, 232961 634762, 227376 634762, 227376 629992)))'],
['עארה-ערערה', "Ara-Ar'ara", 637, 'MULTIPOLYGON (((206311 710297, 211970 710297, 211970 713260, 206311 713260, 206311 710297)))'],
['קריית אתא', 'Kiryat Ata', 6800, 'MULTIPOLYGON (((205559 743505, 214070 743505, 214070 747443, 205559 747443, 205559 743505)))'],
['כפר מנדא', 'Kafr Manda', 510, 'MULTIPOLYGON (((222879 744638, 227100 744638, 227100 747019, 222879 747019, 222879 744638)))'],
['טובאס', 'Tubas', 3412, 'MULTIPOLYGON (((233398 690117, 237061 690117, 237061 694127, 233398 694127, 233398 690117)))'],
["מוח'יים פארעה", "Mukhayyam Fari'a", 3540, 'MULTIPOLYGON (((229872 685976, 233469 685976, 233469 690035, 229872 690035, 229872 685976)))'],
['דימונה', 'Dimona', 2200, 'MULTIPOLYGON (((199797 551176, 205196 551176, 205196 555188, 199797 555188, 199797 551176)))'],
['אופקים', 'Ofakim', 31, 'MULTIPOLYGON (((162430 577900, 166197 577900, 166197 581563, 162430 581563, 162430 577900)))'],
['ערערה-בנגב', "Ar'ara BaNegev", 1192, 'MULTIPOLYGON (((200097 561116, 204501 561116, 204501 564058, 200097 564058, 200097 561116)))'],
['לוד', 'Lod', 7000, 'MULTIPOLYGON (((187745 648864, 191461 648864, 191461 653126, 187745 653126, 187745 648864)))'],
['אבן יהודה', 'Even Yehuda', 182, 'MULTIPOLYGON (((188304 684684, 190452 684684, 190452 688421, 188304 688421, 188304 684684)))'],
['פרדס חנה-כרכור', 'Pardes Hanna-Karkur', 7800, 'MULTIPOLYGON (((195129 706444, 200555 706444, 200555 711677, 195129 711677, 195129 706444)))'],
['קבאטיה', 'Kabatiya', 3801, 'MULTIPOLYGON (((224919 700497, 228869 700497, 228869 703383, 224919 703383, 224919 700497)))'],
['א-טירה', 'At-Tira', 2720, 'MULTIPOLYGON (((194199 680557, 198258 680557, 198258 683812, 194199 683812, 194199 680557)))'],
['מעלות-תרשיחא', "Ma'alot-Tarshiha", 1063, 'MULTIPOLYGON (((224636 767172, 227779 767172, 227779 770457, 224636 770457, 224636 767172)))'],
['צפת', 'Tsfat', 8000, 'MULTIPOLYGON (((245138 760210, 250446 760210, 250446 765853, 245138 765853, 245138 760210)))'],
['זיכרון יעקב', "Zikhron Ya'akov", 9300, 'MULTIPOLYGON (((194446 718098, 197217 718098, 197217 721825, 194446 721825, 194446 718098)))'],
['קיסריה', 'Kesarya', 1167, 'MULTIPOLYGON (((190731 709730, 192528 709730, 192528 715180, 190731 715180, 190731 709730)))'],
['ירכא', 'Yirka', 502, 'MULTIPOLYGON (((215819 760796, 222870 760796, 222870 763499, 215819 763499, 215819 760796)))'],
['בית שאן', "Bet She'an", 9200, 'MULTIPOLYGON (((245884 710017, 248675 710017, 248675 713900, 245884 713900, 245884 710017)))'],
['עכו', 'Akko', 7600, 'MULTIPOLYGON (((206482 754601, 209453 754601, 209453 761546, 206482 761546, 206482 754601)))'],
['כרמיאל', "Karmi'el", 1139, 'MULTIPOLYGON (((224765 755745, 233045 755745, 233045 759404, 224765 759404, 224765 755745)))'],
['נמל תעופה בן-גוריון', 'Ben-Gurion Airport', 1748, 'MULTIPOLYGON (((186099 654685, 191288 654685, 191288 658792, 186099 658792, 186099 654685)))'],
['כפר קרע', "Kafr Kar'", 654, 'MULTIPOLYGON (((202732 710536, 206722 710536, 206722 713741, 202732 713741, 202732 710536)))'],
['קריית טבעון', "Kiryat Tiv'on", 2300, 'MULTIPOLYGON (((209848 732689, 214396 732689, 214396 738131, 209848 738131, 209848 732689)))'],
['קריית שמונה', 'Kiryat Shmona', 2800, 'MULTIPOLYGON (((252723 788136, 255817 788136, 255817 792792, 252723 792792, 252723 788136)))'],
['יריחו', 'Yeriho', 3600, 'MULTIPOLYGON (((240894 639139, 245990 639139, 245990 643159, 240894 643159, 240894 639139)))'],
['טבריה', 'Tverya (Tiberias)', 6700, 'MULTIPOLYGON (((246819 740758, 252598 740758, 252598 746349, 246819 746349, 246819 740758)))'],
["איד'נא", 'Idhna', 3005, 'MULTIPOLYGON (((195936 606179, 198937 606179, 198937 609489, 195936 609489, 195936 606179)))'],
['גן יבנה', 'Gan Yavne', 166, 'MULTIPOLYGON (((170235 631170, 174068 631170, 174068 634173, 170235 634173, 170235 631170)))'],
['עפולה', 'Afula', 7700, 'MULTIPOLYGON (((225960 720847, 232023 720847, 232023 727392, 225960 727392, 225960 720847)))'],
['יטא', 'Yatta', 3441, 'MULTIPOLYGON (((206282 592287, 213231 592287, 213231 598368, 206282 598368, 206282 592287)))'],
['בית לחם', 'Bet Lehem', 3200, 'MULTIPOLYGON (((216360 619275, 220436 619275, 220436 625741, 216360 625741, 216360 619275)))'],
['נתיבות', 'Netivot', 246, 'MULTIPOLYGON (((158337 590747, 162473 590747, 162473 594777, 158337 594777, 158337 590747)))'],
['רעננה', "Ra'anana", 8700, 'MULTIPOLYGON (((185475 675376, 189913 675376, 189913 679352, 185475 679352, 185475 675376)))'],
['חברון', 'Hevron', 3400, 'MULTIPOLYGON (((205396 600558, 212281 600558, 212281 607912, 205396 607912, 205396 600558)))'],
['הרצלייה', 'Herzliya', 6400, 'MULTIPOLYGON (((180453 672936, 187392 672936, 187392 677697, 180453 677697, 180453 672936)))'],
['סמוע', "Sammu'", 3631, 'MULTIPOLYGON (((204645 587780, 208143 587780, 208143 591149, 204645 591149, 204645 587780)))'],
['אל-יאמון', 'Al-Yamun', 3442, 'MULTIPOLYGON (((220319 708576, 223425 708576, 223425 712550, 220319 712550, 220319 708576)))'],
["ג'ינין", 'Jenin', 3300, 'MULTIPOLYGON (((225200 704160, 231063 704160, 231063 709332, 225200 709332, 225200 704160)))'],
['מגדל העמק', "Migdal Ha'Emek", 874, 'MULTIPOLYGON (((221321 729692, 224646 729692, 224646 733380, 221321 733380, 221321 729692)))'],
['בלאטה', 'Balata', 3090, 'MULTIPOLYGON (((226054 678080, 230215 678080, 230215 680575, 226054 680575, 226054 678080)))'],
['חלחול', 'Halhul', 3305, 'MULTIPOLYGON (((208111 607906, 211709 607906, 211709 611973, 208111 611973, 208111 607906)))'],
['יבנה', 'Yavne', 2660, 'MULTIPOLYGON (((173510 640426, 176783 640426, 176783 645623, 173510 645623, 173510 640426)))'],
["ביר הדאג'", 'Bir Hadaj', 1348, 'MULTIPOLYGON (((169064 546162, 176466 546162, 176466 551100, 169064 551100, 169064 546162)))'],
['שכם', 'Shkhem', 3900, 'MULTIPOLYGON (((220698 678309, 226581 678309, 226581 683406, 220698 683406, 220698 678309)))'],
["ד'ינאבה", 'Dhinnaba', 3211, 'MULTIPOLYGON (((202384 688708, 207453 688708, 207453 692012, 202384 692012, 202384 688708)))'],
['ראמאללה', 'Ramallah', 3800, 'MULTIPOLYGON (((215003 642911, 222047 642911, 222047 648905, 215003 648905, 215003 642911)))'],
['דורא', 'Dura', 3186, 'MULTIPOLYGON (((200836 599594, 205560 599594, 205560 604747, 200836 604747, 200836 599594)))'],
["א-שויוח'", 'Ash-Shuyukh', 3884, 'MULTIPOLYGON (((211603 607519, 215887 607519, 215887 610835, 211603 610835, 211603 607519)))'],
['בית סאחור', 'Bayt Sahur', 3073, 'MULTIPOLYGON (((219903 621216, 223596 621216, 223596 624201, 219903 624201, 219903 621216)))'],
['א-טייבה (בשרון)', 'At-Tayyiba (BaSharon)', 2730, 'MULTIPOLYGON (((198915 683331, 202459 683331, 202459 687709, 198915 687709, 198915 683331)))'],
['טמון', 'Tammun', 3418, 'MULTIPOLYGON (((234346 685648, 240300 685648, 240300 689587, 234346 689587, 234346 685648)))'],
["סח'נין", 'Sakhnin', 7500, 'MULTIPOLYGON (((226581 751046, 230293 751046, 230293 753390, 226581 753390, 226581 751046)))'],
['קריית גת', 'Kiryat Gat', 2630, 'MULTIPOLYGON (((176319 609302, 181445 609302, 181445 616345, 176319 616345, 176319 609302)))'],
['ירוחם', 'Yeroham', 831, 'MULTIPOLYGON (((190569 542784, 195598 542784, 195598 545387, 190569 545387, 190569 542784)))'],
['שדרות', 'Sderot', 1031, 'MULTIPOLYGON (((160154 602750, 163448 602750, 163448 605872, 160154 605872, 160154 602750)))'],
['ערד', 'Arad', 2560, 'MULTIPOLYGON (((217226 570662, 222916 570662, 222916 576043, 217226 576043, 217226 570662)))'],
["מר'אר", 'Mughar', 481, 'MULTIPOLYGON (((237009 753074, 241029 753074, 241029 756159, 237009 756159, 237009 753074)))'],
['נתניה', 'Netanya', 7400, 'MULTIPOLYGON (((184043 684643, 189969 684643, 189969 695559, 184043 695559, 184043 684643)))'],
['חדרה', 'Hadera', 6500, 'MULTIPOLYGON (((188490 702060, 196342 702060, 196342 708276, 188490 708276, 188490 702060)))'],
['ירושלים', 'Jerusalem', 3000, 'MULTIPOLYGON (((213321 624425, 224973 624425, 224973 643358, 213321 643358, 213321 624425)))'],
['נצרת', 'Natsrat', 7300, 'MULTIPOLYGON (((225830 731346, 229805 731346, 229805 737232, 225830 737232, 225830 731346)))'],
['חורה', 'Hura', 1303, 'MULTIPOLYGON (((191945 576261, 196612 576261, 196612 580313, 191945 580313, 191945 576261)))'],
['לקייה', 'Likiya', 1060, 'MULTIPOLYGON (((185406 579477, 189411 579477, 189411 583233, 185406 583233, 185406 579477)))'],
['קלקיליה', 'Kalkilya', 3700, 'MULTIPOLYGON (((196178 675552, 200046 675552, 200046 678754, 196178 678754, 196178 675552)))'],
['נס ציונה', 'Nes Tsiyona', 7200, 'MULTIPOLYGON (((178658 645734, 182531 645734, 182531 649881, 178658 649881, 178658 645734)))'],
['רחובות', 'Rehovot', 8400, 'MULTIPOLYGON (((178113 641566, 184629 641566, 184629 647261, 178113 647261, 178113 641566)))'],
['שפרעם', "Shefar'am", 8800, 'MULTIPOLYGON (((214177 743705, 218864 743705, 218864 747848, 214177 747848, 214177 743705)))'],
['עראבה', 'Arraba', 531, 'MULTIPOLYGON (((230571 749271, 233454 749271, 233454 751981, 230571 751981, 230571 749271)))'],
['עיספייא', 'Isfiya', 534, 'MULTIPOLYGON (((204372 733981, 208340 733981, 208340 738176, 204372 738176, 204372 733981)))'],
['טמרה', 'Tamra', 8900, 'MULTIPOLYGON (((215648 749732, 220495 749732, 220495 752402, 215648 752402, 215648 749732)))'],
['אום אל-פחם', 'Umm al-Fahm', 2710, 'MULTIPOLYGON (((210315 711051, 217923 711051, 217923 716580, 210315 716580, 210315 711051)))'],
['כפר סבא', 'Kfar Sava', 6900, 'MULTIPOLYGON (((189319 673933, 196120 673933, 196120 678661, 189319 678661, 189319 673933)))'],
['חיפה', 'haifa', 4000, 'MULTIPOLYGON (((196006 740322, 207779 740322, 207779 749776, 196006 749776, 196006 740322)))'],
['אילת', 'Elat', 2600, 'MULTIPOLYGON (((190347 378314, 197589 378314, 197589 388216, 190347 388216, 190347 378314)))'],
['באר שבע', "Be'er Sheva", 9000, 'MULTIPOLYGON (((175276 568630, 183985 568630, 183985 577914, 175276 577914, 175276 568630)))'],
['כוסיפה', 'Kusayfa', 1059, 'MULTIPOLYGON (((205417 570325, 210286 570325, 210286 573875, 205417 573875, 205417 570325)))'],
['דאלית אל-כרמל', 'Daliyat al-Karmil', 494, 'MULTIPOLYGON (((203133 731720, 207637 731720, 207637 735205, 203133 735205, 203133 731720)))'],
['נוף הגליל', 'Nof HaGalil', 1061, 'MULTIPOLYGON (((228635 732398, 233273 732398, 233273 737593, 228635 737593, 228635 732398)))'],
['אשדוד', 'Ashdod', 70, 'MULTIPOLYGON (((163743 630402, 171927 630402, 171927 641077, 163743 641077, 163743 630402)))'],
['פתח תקווה', 'Petah Tikva', 7900, 'MULTIPOLYGON (((185612 663776, 193397 663776, 193397 669727, 185612 669727, 185612 663776)))'],
['רמת השרון', 'Ramat HaSharon', 2650, 'MULTIPOLYGON (((181321 669206, 187460 669206, 187460 673977, 181321 673977, 181321 669206)))'],
['רמת גן', 'Ramat Gan', 8600, 'MULTIPOLYGON (((181131 660376, 186333 660376, 186333 668022, 181131 668022, 181131 660376)))'],
['תל אביב-יפו', 'Tel Aviv', 5000, 'MULTIPOLYGON (((175709 659665, 185814 659665, 185814 672651, 175709 672651, 175709 659665)))'],
['תל אביב', 'Yafo', 5000, 'MULTIPOLYGON (((175709 659665, 185814 659665, 185814 672651, 175709 672651, 175709 659665)))'],
['בני ברק', 'Bne Brak', 6100, 'MULTIPOLYGON (((183303 664022, 185713 664022, 185713 668278, 183303 668278, 183303 664022)))'],
['מכחול', "Mak'hul", 1343, 'MULTIPOLYGON (((205230 575713, 208455 575713, 208455 579145, 205230 579145, 205230 575713)))'],
['א-סייד', 'As-Sayid', 1359, 'MULTIPOLYGON (((189331 574886, 195477 574886, 195477 579738, 189331 579738, 189331 574886)))'],
['הוד השרון', 'Hod HaSharon', 9700, 'MULTIPOLYGON (((187825 670558, 193202 670558, 193202 675384, 187825 675384, 187825 670558)))'],
['חולון', 'Holon', 6600, 'MULTIPOLYGON (((176994 655659, 182653 655659, 182653 660622, 176994 660622, 176994 655659)))'],
['בת ים', 'Bat Yam', 6200, 'MULTIPOLYGON (((174936 655606, 177627 655606, 177627 660120, 174936 660120, 174936 655606)))'],
['מודיעין-מכבים-רעות', "Modi'in-Makkabbim-Re'ut", 1200, 'MULTIPOLYGON (((196308 642666, 203813 642666, 203813 648128, 196308 648128, 196308 642666)))'],
['בית שמש', 'Bet Shemesh', 2610, 'MULTIPOLYGON (((195850 622335, 202041 622335, 202041 631700, 195850 631700, 195850 622335)))'],
['רהט', 'Rahat', 1161, 'MULTIPOLYGON (((173567 586694, 179491 586694, 179491 590638, 173567 590638, 173567 586694)))']]

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
		

def dpi(raster):
	RowCount = int(str(arcpy.GetRasterProperties_management(str(raster),"ROWCOUNT")))
	if RowCount > 14000 and RowCount < 16200:
		return 1588
	elif RowCount < 13001 and RowCount > 2000:
		return 1270
	elif RowCount > 16201:
		return 2117
	else:
		return 0

	
def convert_bytes(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.lf %s" % (num,x)
        num /= 1024.0

				
def file_size(file_path):
    if os.path.exists(file_path):
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            return convert_bytes(file_info.st_size)
    else:
        return 'no file found'

				
def GEtTypeFromString(text):
	Types = ['DEM','dem','raster','Raster','Photo','PHOTO','NDSM','DSM','DTM','NDSM','ndsm,dsm','aster']
	for i in Types:
		if i in text:
			return str(i)
		else:
			pass

			
def raster_type(text):
    if text.find('.') > -1:
        return text.split ('.')[-1]
    else:
        return text.split ('\\')[-1]

				
def get_accurancy_dict(dic):
        return {k:list(str(dic.values())).count(i) for k,i in dic.items()}


def modification_date(filename):
    try:
        gt    = os.path.getmtime(filename)
        time  = datetime.datetime.fromtimestamp(gt)
        year_ = time.year
        month_= time.month
        return month_,year_
    except:
        return 0,0


def Get_raster_Min_Max(ras):
    try:
        inRas     = arcpy.Raster             (ras)
        arr       = arcpy.RasterToNumPyArray (inRas, nodata_to_value=0)
        min_,max_ = arr.min(),arr.max()
        return str(min_),str(max_)
    except:
        return "No Data","No Data"


def Get_cell_Size(Ras):
    try:
        cell_size = str(arcpy.GetRasterProperties_management (Ras, "CELLSIZEX"))
        return cell_size
    except:
        return "coudnt find Cell Size"


def Get_bands(Ras):
    try:
        band = str(arcpy.GetRasterProperties_management(str(Ras), "BANDCOUNT"))
        return band
    except:
        return "not Found"



def Create_Csv(outFile,data):
    outFile  = os.path.dirname(outFile)
    output   = os.path.dirname(outFile) +"\\" + "geometry_chack.csv"
    df_csv   = pd.DataFrame(data = [data]    ,columns=["Raster_path","ras_name","ras_date","year","ras_type","min_","max_","size_file","dpi_ras","cell_size","band","TypeRaster","time_","X_Y","Coord"])

    if not os.path.exists(output):
        df_csv.to_csv   (output)
    else:
        df_csv.to_csv   (output,mode = 'a',header = False)

    return output

def Create_Csv_error(outFile,data):
    outFile   = os.path.dirname(outFile)
    output2   = os.path.dirname(outFile) +"\\" + "errors.csv"
    df_error  = pd.DataFrame(data = data,columns=["Raster_path"])

    if not os.path.exists(output2):
        
        df_error.to_csv (output2)
    else:
        df_error.to_csv (output2,mode = 'a',header = False)

    return output2

def fix_str(str1):

    if len(str1) >499:
        num = len(str1)
        while num > 499:
            str1 = os.path.dirname(str1)
            num  = len(str1)
    return str1


def Get_X_Y(Geometry):
    Diff_coord = 'ok'
    if Geometry[0] < 10000 or Geometry[1] < 10000:
        Diff_coord = 'Warning'

    return str(Geometry[0]) + '-' + str(Geometry[1]),Diff_coord


def Envelope_Geom(Xmin, Ymin, Xmax, Ymax,spatial_referance = ''):
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    if spatial_referance == '':
        spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance)
    return polygon


def Get_fcs_shps(folders):
    list_shp = []
    list_fc  = []
    for Folder in folders:
        for root, dirs, files in os.walk(Folder):
            for file in files:
                if file.endswith(".shp"):
                    list_shp.append(root + '\\' +file)
            if root.endswith(".gdb"):
                arcpy.env.workspace = root
                fcs = [root + '\\' + i for i in arcpy.ListFeatureClasses()]
                list_fc.extend(fcs)

    return list_fc,list_shp


def add_field(fc,field,Type = 'TEXT'):
    TYPE = [i.name for i in arcpy.ListFields(fc) if i.name == field]
    if not TYPE:
        arcpy.AddField_management (fc, field, Type, "", "", 500)


def gdb_or_shp(name):
    if name.endswith('.shp'):
        return 'shp'
    elif '.gdb' in name:
        return 'gdb'
    else:
        return 'Unknown'

def Find_Rasters(inDir,outFile):

    exists_rasters = []

    if arcpy.Exists(outFile):
        exists_rasters = [str(i[0]) for i in arcpy.da.SearchCursor(outFile,['RasterPath'])]

    feature_classes = [root +'\\' + file for i in inDir for root, dirs, files in os.walk(i) for file in files if (file.endswith('tiff')\
                   or file.endswith('tif')) and root +'\\' + file if str(root) +'\\' + str(file) not in exists_rasters]
                
    if not arcpy.Exists(outFile): arcpy.CreateFeatureclass_management (os.path.dirname (outFile), os.path.basename (outFile), "POLYGON")

    arcpy.AddMessage("Number of Rasters: " + str(len(feature_classes)))

    sr = arcpy.SpatialReference(2039) # (3765)
    arcpy.DefineProjection_management(outFile, sr)

    list_of_fields = [["RasterName","String"] ,["RasterPath","String"]  ,["Bands",'String']   ,["definition","String"],\
                    ["Cell_Size",'String']    ,["Raster_Type","String"] ,["Time",'String']    ,["File_Size",'String' ],\
                    ["dpi",'double']          ,['Date_made',"double"]   ,['min_pix','String'] ,['max_pix','String'   ] ,\
                    ['X_Y','String']          ,["Year",'double']        ,['Coord','String']   ,['crs','String']      ]
                    

    for i in list_of_fields: arcpy.AddField_management (outFile, i[0], i[1], "", "", 500)

    cursor  = arcpy.InsertCursor (outFile)
    point   = arcpy.Point ()
    array   = arcpy.Array ()
    corners = ["lowerLeft", "lowerRight", "upperRight", "upperLeft"]

    error_files  = []
    min_max_key  = {}
    Geometry_key = {}

    count = 1
    for Ras in feature_classes:
        error_files = []
        try:	
            Geometry     = []
            feat = cursor.newRow ()
            r = arcpy.Raster (Ras)
            for corner in corners:
                    point.X = getattr (r.extent, "%s" % corner).X
                    point.Y = getattr (r.extent, "%s" % corner).Y
                    x = getattr (r.extent, "%s" % corner).X
                    y = getattr (r.extent, "%s" % corner).Y
                    Geometry.append(x)
                    Geometry.append(y)
                    array.add (point)
            
            Geometry_key[Ras] = Geometry
                    
            array.add (array.getObject (0))
            polygon    = arcpy.Polygon (array)
            feat.shape = polygon

            ras_path   = fix_str (Ras)
            date_,year = modification_date  (Ras)
            ras_type   = raster_type        (Ras)
            min_,max_  = Get_raster_Min_Max (Ras)
            size_file  = file_size          (Ras)
            dpi_ras    = dpi                (Ras)
            cell_size  = Get_cell_Size      (Ras)
            band       = Get_bands          (Ras)
            TypeRaster = GEtTypeFromString  (Ras)
            time_      = str(datetime.datetime.now()).split(' ')[0]
            ras_name   = Ras.split ('\\')[-1].split('.')[0]
            X_Y,warn   = Get_X_Y(Geometry)
            crs        = Get_crs(Ras)

            feat.setValue ("RasterName" ,ras_name)
            feat.setValue ("RasterPath" ,ras_path)
            feat.setValue ("Raster_Type",ras_type)
            feat.setValue ("Date_made"  ,date_)
            feat.setValue ("Year"       ,year)
            feat.setValue ("min_pix"    ,min_)
            feat.setValue ("max_pix"    ,max_)
            feat.setValue ("Bands"      ,band)
            feat.setValue ("definition" ,str(TypeRaster))
            feat.setValue ("Cell_Size"  ,cell_size)
            feat.setValue ("dpi"        ,dpi_ras)
            feat.setValue ("Time"       ,time_)
            feat.setValue ("File_Size"  ,size_file)
            feat.setValue ("X_Y"        ,X_Y)
            feat.setValue ("Coord"      ,warn)
            feat.setValue ('crs'        ,crs)


            min_max_key[Ras] = min_+'-'+ max_
            cursor.insertRow (feat)
            array.removeAll  ()
            del Geometry

        except:
            arcpy.AddMessage('failes to add raster: '+ Ras)
            error_files.append(Ras)
            # Create_Csv_error   (outFile,data_excel)

        count += 1

    del cursor


def ShapeType(layer):
    desc          = arcpy.Describe(layer)
    if str(desc.shapeType) == 'Point':
        Geom_type = 'POINT'
    elif str(desc.shapeType) == 'Polyline':
        Geom_type = 'POLYLINE'
    else:
        Geom_type = 'POLYGON'
    return Geom_type


def Get_crs(fc):
    return arcpy.Describe(fc).spatialReference.name


def get_name(path):
    name_all = os.path.basename(path)
    if name_all.endswith('.shp'):
        name_all = name_all.split('.')[0]
    return name_all

def Find_layers(Folder,outFile):

    list_fc,list_shp = Get_fcs_shps(Folder)

    exists_path = []
    if arcpy.Exists(outFile):
        exists_path = [i[0] for i in arcpy.da.SearchCursor(outFile,['Path'])]
    else:
        arcpy.CreateFeatureclass_management (os.path.dirname (outFile), os.path.basename (outFile), "POLYGON")

    fields_to_add = [['Path','TEXT'],['Num_features','DOUBLE'],['Year_Created','LONG'],['Month_Created','LONG'],['Type','TEXT'],['File_size','TEXT'],['Geom_type','TEXT'],['crs','TEXT'],['Name','TEXT']]

    for i in fields_to_add: add_field(outFile,i[0],i[1])

    fields   = ['SHAPE@','Path','Num_features','Year_Created','Month_Created','Type','File_size','Geom_type','crs','Name']
    insert   = arcpy.da.InsertCursor(outFile,fields)
    list_all = list_fc + list_shp
    list_all = [i for i in list_all if i not in exists_path]

    count   = 1
    for layer in list_all:
        num_feat   = int(str(arcpy.GetCount_management(layer)))
        if num_feat < 0:
            count += 1
            continue
        s_r        = arcpy.Describe (layer).spatialReference
        extent     = arcpy.Describe(layer).extent

        Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax

        month_,year_           = modification_date (layer)
        type_                  = gdb_or_shp        (layer)
        file_size_             = file_size         (layer)
        polygon                = Envelope_Geom     (Xmin, Ymin, Xmax, Ymax,s_r)
        geom_type              = ShapeType         (layer)
        crs                    = Get_crs           (layer)
        name                   = get_name          (layer)


        insert.insertRow ([polygon,layer,num_feat,year_,month_,type_,file_size_,geom_type,crs,name])
        count += 1
    del insert
        

    arcpy.RepairGeometry_management(outFile)


def Create_GDB(GDB_file,GDB_name):
    fgdb_name = GDB_file + "\\" + GDB_name + ".gdb"
    if os.path.exists(fgdb_name):
        GDB_name = GDB_name + "_"
    fgdb_name = str(arcpy.CreateFileGDB_management(GDB_file, str(GDB_name), "CURRENT"))
    return fgdb_name

def get_date_as_name():
        time  = datetime.datetime.now()
        return 'Date_' + str(time.year) + '_' + str(time.month) + '_' + str(time.day)



def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def Envelope_Geom_by_Geom(geom,spatial_referance = ''):
    extent = geom.extent
    Xmin, Ymin, Xmax, Ymax = extent.XMin, extent.YMin, extent.XMax, extent.YMax
    Array = arcpy.Array([arcpy.Point(Xmin, Ymin), arcpy.Point(Xmin, Ymax),\
                         arcpy.Point(Xmax, Ymax), arcpy.Point(Xmax, Ymin),\
                         arcpy.Point(Xmin, Ymin)])
    if spatial_referance == '':
        spatial_referance = arcpy.SpatialReference(2039)
    polygon = arcpy.Polygon(Array, spatial_referance)
    return polygon


def remove_decimal(input_str):
    output_str = re.sub(r'(\d+\.\d+)', lambda m: str(int(float(m.group(1)))), input_str)
    return output_str


def isHebrew(name_input:str) -> bool:
    '''
    Check if the input string is in Hebrew, if so return True
    '''
    return any("\u0590" <= c <= "\u05EA" for c in name_input)


def get_settlement_to_layer(data_SETL,name_input:str,out_put:str) -> str:

    if arcpy.Exists(out_put):arcpy.Delete_management(out_put)

    ishebrew    = isHebrew(name_input)
    field_check = 'SETL_NAME' if ishebrew else 'SETL_NAME_LTN'

    df            = pd.DataFrame(data_SETL,columns= ['SETL_NAME','SETL_NAME_LTN','SETL_CODE','SHAPE'])
    df['Similar'] = df[field_check].apply(lambda x: similar(x,name_input))
    df            = df[df['Similar'] > 0.5]
    if not df.empty:
        df   = df[df['Similar'] ==  df['Similar'].max()]
        geom = arcpy.FromWKT(df['SHAPE'].values[0])
        arcpy.CopyFeatures_management(geom,out_put)
        return out_put
    else:
        print ('No settlement found')
        arcpy.AddMessage('No settlement found')

def zoom_in(layer):

    '''
    layer: layer to zoom to
    '''

    extent= arcpy.Describe(layer).extent
    aprx= arcpy.mp.ArcGISProject('CURRENT')
    arcpy.AddMessage(aprx)
    mv  = aprx.activeView
    arcpy.AddMessage(str(mv))
    mv.camera.setExtent(extent)

def create_gdb_temp():
    gdb_temp      = tempfile.gettempdir() + '\\' + 'temp.gdb'
    if arcpy.Exists(gdb_temp): arcpy.Delete_management(gdb_temp)
    arcpy.CreateFileGDB_management(tempfile.gettempdir(),'temp.gdb')
    return gdb_temp

def getRasterOnMap(temp_layer,raster_RGB,intersects,folderName):

    if arcpy.Exists(intersects): arcpy.Delete_management(intersects)

    if not raster_RGB: return
    arcpy.Intersect_analysis([temp_layer,raster_RGB],intersects)

    rasterList = list(set([row[0] for row in arcpy.da.SearchCursor(intersects,[folderName])]))

    try:
        aprx = arcpy.mp.ArcGISProject('CURRENT')
        aprxMap = aprx.listMaps("Map")[0] 

        for row in rasterList:
            lyr = aprxMap.addDataFromPath(row)
            # aprxMap.addLayer(lyr)
            aprx.activeView

        del aprxMap
        del aprx

        return intersects
    except:
        print ('run on test mode')


def removeRastersFromMap(mxd_path,removename):
    p = arcpy.mp.ArcGISProject (mxd_path)
    m   = p.listMaps('Map')[0]
    delete_templates = [m.removeLayer(i) for i in m.listLayers() if (removename in i.dataSource)]


def copyRights(version = '0.0.2'):
    arcpy.AddMessage (f''' 
    -------------------------------------------------
    |                version: {version}                  |
    |              Made by: medad hoze                   |
    |    if bag was found, plz add a pic of the error    |
    |   to the following address: medadhoze@hotmail.com  |''')


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
    


def isLayer(layer):

    if not arcpy.Exists(layer): return False
    desc       = arcpy.Describe(layer)
    type_layer = desc.dataType
    if (type_layer == "FeatureClass") or (type_layer == "ShapeFile"):
        return 'layer'
    elif type_layer == "RasterDataset":
        return 'raster'
    else:
        return 'city'

def delete_if_exist(layers):
    for layer in layers:
        if arcpy.Exists(layer):
            try:
                arcpy.Delete_management(layer)
            except:
                pass



# def removeRastersFromMap(removename):
#     p = arcpy.mp.ArcGISProject ('CURRENT')
#     m   = p.listMaps('Map')[0]
#     delete_templates = [m.removeLayer(i) for i in m.listLayers() if (removename in i.dataSource)]

def find_layers_main(city,Folder):

    temp_gdb  = create_gdb_temp  ()

    out_put   = temp_gdb + '\\' + 'geom'
    fc_raster = temp_gdb + '\\' + 'rasters'
    fc_layer  = temp_gdb + '\\' + 'layers'
    inter_ras = temp_gdb + '\\' + 'intersects'
    inter_vec = temp_gdb + '\\' + 'intersects_vec'

    poly_temp = tempfile.gettempdir() + '\\' + 'temp.shp'

    if isLayer(city) == 'layer':
        arcpy.Dissolve_management(city,out_put)
    elif isLayer(city) == 'raster':
        RasterToPolygon(city,poly_temp)
        arcpy.Dissolve_management (poly_temp,out_put)
    else:
        get_settlement_to_layer  (data_SETL,city,out_put)

    if not arcpy.Exists(out_put): return
    try:
        if out_put      :zoom_in(out_put)
    except:
        pass

    if Folder == '' : sys.exit(1)

    Folder = Folder.strip()
    Find_Rasters ([Folder],fc_raster)
    Find_layers  ([Folder],fc_layer )

    getRasterOnMap(out_put, fc_raster,inter_ras ,'RasterPath')
    getRasterOnMap(out_put, fc_layer ,inter_vec ,'Path'      )


    # delete_if_exist([poly_temp,inter_vec,fc_layer,fc_raster,out_put])