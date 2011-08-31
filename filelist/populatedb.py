import filetools 
import os 
import re 
import glob
import models
import datetime 
import filesettings
import scipy as sp
import numpy as np
from odysseus.imageio import imgimport_intelligent
from odysseus.imageprocess import calc_absimage
import Image
import collections

def fullupdateimages(): 
	for ikey, iloc in filesettings.IMG_LOCS.iteritems():
		for imgpath in filetools.get_files_in_dir(iloc):
			mod_time_file = os.lstat(imgpath).st_mtime
			mod_datetime = datetime.datetime.fromtimestamp(mod_time_file)
			imginfo=models.ImageInfo(path=imgpath, time=mod_datetime, loc_key=ikey)
			imginfo.save() 
			imginfo.makeRawFrames()
			imginfo.getClosestSequence()
			imginfo.save()
			imginfo.ProcessImage
			imginfo.save()
			
def getClosestSequence(imginfo):
	sql = "SELECT * FROM filelist_runloginfo ORDER BY ABS(TIMESTAMPDIFF(SECOND, time,'" + imginfo.time.strftime('%Y-%m-%d %H:%M:%S') + "')) LIMIT 1"
	for retrunlog in models.RunLogInfo.objects.raw(sql):
		imginfo.runlog = retrunlog		
					

	
	