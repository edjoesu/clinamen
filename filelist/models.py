import os
import numpy as np
import scipy as sp
import re
import inspect
import collections
#from odysseus.imageio import imgimport_intelligent, list_of_frames
os.environ['DJANGO_SETTINGS_MODULE'] = "settings"
from django.db import models
import filelist.filesettings as filesettings
import Image

class RunLogInfo(models.Model):
	#path = models.FilePathField(filesettings.RL_DIR, primary_key=True)
	path = models.CharField(max_length=200, primary_key=True)
	loc_key = models.CharField(max_length=100)
	time = models.DateTimeField()
	sequencepath = models.CharField(max_length=200)
	listiterationnumber = models.IntegerField(null=True, blank=True)
	liststarttime = models.DateTimeField(null=True,blank=True)
	sequenceduration = models.FloatField(null=True,blank=True)
	description = models.TextField(null=True, blank=True)
	exceptions = models.TextField(null=True, blank=True)
	class Meta:
		ordering=['-time']
		
class VariableValue(models.Model):
	name = models.CharField(max_length=30)
	value = models.FloatField()
	runlog = models.ForeignKey('RunLogInfo')

class ImageInfo(models.Model):
	#path = models.FilePathField(filesettings.IMG_DIR, primary_key=True)
	path = models.CharField(max_length=100, primary_key=True)
	loc_key = models.CharField(max_length=100)
	time = models.DateTimeField()
	height = models.IntegerField(null=True, blank=True)
	width = models.IntegerField(null=True, blank=True)
	number_of_frames = models.IntegerField(null=True, blank=True)
	imgtype = models.ForeignKey('ImageType', null=True, blank=True)
	runlog = models.ForeignKey('RunLogInfo', null=True, blank=True)	
	def makeRawFrames(self):
		frames = np.dstack(list_of_frames(self.path))
		
		self.width = np.size(frames,0)
		self.height = np.size(frames,1)	
		self.number_of_frames = np.size(frames,2)
				
		for ii in range(np.size(frames,2)):
			filename = os.path.splitext(os.path.split(self.path)[1])[0]+'_'+str(ii)+'.png'
			
			newframe = RawFrame(sourceimage=self, framenumber=ii)
			newframe.saveframe(frames[:,:,ii], filename)
			newframe.save()
	def deleteProcFrames(self):
		ProcessedFrame.objects.filter(sourceimage=self).delete()
	def ProcessImage(self): 
		for method in self.imgtype.methods.all():
			procmodule = __import__(method.modulename)
			procmethod = getattr(procmodule, method.name)
			argdict = {}
			for param in TypeParameters.objects.filter(imagetype=self.imgtype, methodargument__method=method):
				argdict[param.methodargument.name]=param.value
			for ROIparam in TypeROI.objects.filter(imagetype=self.imgtype, methodargument__method=method):
				argdict[ROIParam.methodargument.name]=ROIparam.ToDict()
			result=procmethod(self.path, **argdict)
			if not isinstance(result,tuple):
				result = (result,)
			for ii in range(len(result)):
				if isarray(result[ii]):
					filename=os.path.splitext(os.path.split(self.path)[1])[0]+'_'+method.name+'_'+str(ii)+'.png'
						
					newrecord = ProcessedFrame(sourceimage=self, method=method, framenumber=ii) 
					newrecord.saveframe(result[ii], filename)
					newrecord.save()
				else:
					newrecord = ProcessedValue(sourceimage=self, method=method, value=float(item[ii]), index=ii)
					newrecord.save()
	def getClosestSequence(self):
		sql = "SELECT * FROM filelist_runloginfo ORDER BY ABS(TIMESTAMPDIFF(SECOND, time,'" + self.time.strftime('%Y-%m-%d %H:%M:%S') + "')) LIMIT 1"
		for retrunlog in RunLogInfo.objects.raw(sql):
			self.runlog = retrunlog
	def getTypeFromDescription(self): 
		matchObj = re.search("imgtype=(\w+)", self.runlog.description)
		if matchObj:
			self.imgtype= matchObj.group(1)		
	class Meta:
		ordering=['-time']

class FrameInfo(models.Model):
	pngpath = models.CharField(max_length=100, primary_key=True)
	pngurl = models.CharField(max_length=100)
	pngheight = models.IntegerField()
	pngwidth = models.IntegerField()
	thumbpath = models.CharField(max_length=100)
	thumburl = models.CharField(max_length=100)	
	thumbheight = models.IntegerField()
	thumbwidth = models.IntegerField()
	framenumber = models.IntegerField(null=True, blank=True)
	sourceimage = models.ForeignKey('ImageInfo', null=True, blank=True)	
	def saveframe(self, frame, filename):
		self.pngpath=os.path.join(filesettings.PNG_DIR,filename)
		self.pngurl=filesettings.PNG_URL+filename
		self.thumbpath=os.path.join(filesettings.THUMB_DIR,filename)
		self.thumburl=filesettings.THUMB_URL+filename		
		
		im=sp.misc.toimage(frame)
		im.save(self.pngpath)
			
		self.pngwidth = np.size(frame,0)
		self.pngheight = np.size(frame,1)			
		aspect=float(self.pngwidth)/float(self.pngheight)
		
		if aspect>1:
			self.thumbwidth = filesettings.THUMB_SIZE
			self.thumbheight = int(filesettings.THUMB_SIZE/aspect)
		else:
			self.thumbwidth = int(filesettings.THUMB_SIZE * aspect)
			self.thumbheight = filesettings.THUMB_SIZE
		im.thumbnail([self.thumbwidth, self.thumbheight], Image.ANTIALIAS) 		
		im.save(self.thumbpath)				
	class Meta:
		abstract=True
		ordering=['framenumber']
	
class ProcessingMethod(models.Model):
	modulename = models.CharField(max_length=100)
	name = models.CharField(max_length=30) 
	def getargs(self):
		procmodule = __import__(self.modulename)
		#procmethod = procmodule.getAttr(procmodule, self.name)
		procmethod = getattr(procmodule, self.name)
		argspec = inspect.getargspec(procmethod)
		for keyword in argspec.args[1:]:
			newmetharg, created = MethodArgument.objects.get_or_create(method=self, name=keyword)
			if re.search("roi_(\w+)", keyword):
				newmetharg.isROI = True
			newmetharg.save()
	class Meta:
		unique_together = ("modulename", "name")
	
class MethodArgument(models.Model):
	method = models.ForeignKey('ProcessingMethod')
	name = models.CharField(max_length=30)	
	isROI = models.NullBooleanField(null=True, blank=True)

class ImageType(models.Model):
	name = models.CharField(max_length=30, primary_key=True)
	methods = models.ManyToManyField('ProcessingMethod')
	parameters = models.ManyToManyField('MethodArgument', through='TypeParameters')	
	sample = models.ForeignKey('RawFrame', null=True, blank=True)
	def ClearProcessed(self):
		ProcessedFrame.objects.filter(sourceimage__imgtype=self).delete()
	def ProcessType(self):
		#imtype = ImageType.objects.get(name=self.name)
		#for iminfo in imtype.ImageInfo_set.all():
		for iminfo in self.imageinfo_set.all():
			iminfo.ProcessImage()
	
class TypeParameters(models.Model):
	imagetype = models.ForeignKey('ImageType')
	methodargument = models.ForeignKey('MethodArgument')
	value = models.FloatField()	
	class Meta:
		unique_together = ("imagetype", "methodargument")
		
class TypeROI(models.Model):
	imagetype = models.ForeignKey('ImageType')
	methodargument = models.ForeignKey('MethodArgument')
	x1 = models.IntegerField(null=True, blank=True)
	x2 = models.IntegerField(null=True, blank=True)
	y1 = models.IntegerField(null=True, blank=True)
	y2 = models.IntegerField(null=True, blank=True)
	def ToDict(self):
		return {"x1": x1, "x2": x2, "y1": y1, "y2": y2}
	class Meta:
		unique_together = ("imagetype", "methodargument")

class ProcessedFrame(FrameInfo):
	method = models.ForeignKey('ProcessingMethod', null=True, blank=True)
	
class RawFrame(FrameInfo):
	class Meta:
		abstract=False
	
class ProcessedValue(models.Model):
	sourceimage = models.ForeignKey('ImageInfo')
	method = models.ForeignKey('ProcessingMethod', null=True, blank=True)
	value = models.FloatField()
	index = models.IntegerField(null=True, blank=True)
	class Meta:
		unique_together = ("sourceimage", "method")

def get_iterable(x):
	if isinstance(x, collections.Iterable):
		return x
	else:
		return (x,)

def isarray(s):
	try:
		len(s)
		return True
	except TypeError:
		return False
	
	