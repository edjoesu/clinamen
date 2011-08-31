# Create your views here.
from django.shortcuts import render_to_response, get_list_or_404
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from clinamen.filelist.models import *
import datetime 
import json
import zipfile, tempfile 

def tester(request):
	return HttpResponse("Test succeeded again")

def imagelist(request, url):
	img_list = get_list_or_404(ImageInfo)
	return render_to_response('imglist.html', {'img_list': img_list})

def runloglist(request, url):
	runlog_list = get_list_or_404(RunLogInfo)
	return render_to_response('runloglist.html', {'runlog_list': runlog_list})

def render_methodlist(imagetype):
	activetype, created = ImageType.objects.get_or_create(name=imagetype)
	activetype.save()
	active_list = ProcessingMethod.objects.filter(imagetype__name=imagetype)
	method_list = get_list_or_404(ProcessingMethod)
	return render_to_response('methodlist.html', {'method_list': method_list, 'active_list': active_list, 'activetype': activetype})

def methodlist(request):
	return render_methodlist(request.GET['txttype'])
			
def addmethod(request):
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	selectedmethod = ProcessingMethod.objects.get(modulename = request.GET['modulename'], name=request.GET['methodname'])
	activetype.methods.add(selectedmethod)
	
	return render_methodlist(request.GET['activetype'])

def removemethod(request):
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	selectedmethod = ProcessingMethod.objects.get(modulename = request.GET['modulename'], name=request.GET['methodname'])
	activetype.methods.remove(selectedmethod)
	
	return render_methodlist(request.GET['activetype'])

def editparams(request):
	arg_list = MethodArgument.objects.filter(method__modulename=request.GET['modulename'], method__name=request.GET['methodname'])
	#arg_list = MethodArgument.objects.filter(method__modulename=request.GET['modulename'], method__name=request.GET['methodname']).exclude(isROI=True)
	#argROI_list = MethodArgument.objects.filter(method__modulename=request.GET['modulename'], method__name=request.GET['methodname']).filter(isROI=True)
	
	activemethod = ProcessingMethod.objects.get(modulename = request.GET['modulename'], name=request.GET['methodname'])
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	
	param_list = TypeParameters.objects.filter(imagetype__name=request.GET['activetype'], methodargument__method__modulename=request.GET['modulename'], methodargument__method__name=request.GET['methodname'])
	ROI_list = TypeROI.objects.filter(imagetype__name=request.GET['activetype'], methodargument__method__modulename=request.GET['modulename'], methodargument__method__name=request.GET['methodname'])
	
	sampleframe = activetype.sample 
	
	arg_params = {}
	arg_rois ={}
	
	for arg in arg_list:
		if arg.isROI:
			if sampleframe: 
				ROI=ROI_list.filter(methodargument=arg)
				if ROI: 
					arg_rois[arg.name]=json.dumps({"x1": ROI[0].x1, "x2": ROI[0].x2, "y1": ROI[0].y1, "y2": ROI[0].y2})
				else:
					arg_rois[arg.name]=''		
		else:
			param=param_list.filter(methodargument=arg)
			if param: 
				arg_params[arg.name]=param[0].value
			else:
				arg_params[arg.name]=''
	return render_to_response('paramlist.html', {'arg_list': arg_list, 'arg_params': arg_params, 'activemethod': activemethod, 'arg_rois': arg_rois, 'sampleframe': sampleframe})

def updateparams(request):
	arg_list = MethodArgument.objects.filter(method__modulename=request.GET['activemodulename'], method__name=request.GET['activemethodname'])
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	activemethod = ProcessingMethod.objects.get(modulename = request.GET['activemodulename'], name=request.GET['activemethodname'])
	
	roi_dict = json.loads(request.GET['rois'])
	
	for arg in arg_list:
		if arg.name in request.GET:
			if request.GET[arg.name] != '':
				try:
					param = TypeParameters.objects.get(imagetype = activetype, methodargument=arg)	
					param.value=request.GET[arg.name]
				except TypeParameters.DoesNotExist:
					param = TypeParameters.objects.create(imagetype = activetype, methodargument=arg, value=request.GET[arg.name])					
				param.save()	
		if arg.name in roi_dict:						
				try:
					roi = TypeROI.objects.get(imagetype = activetype, methodargument=arg)					
				except TypeROI.DoesNotExist:
					roi = TypeROI.objects.create(imagetype = activetype, methodargument=arg)	
					
				roi.x1 = roi_dict[arg.name][0]
				roi.y1 = roi_dict[arg.name][1]
				roi.x2 = roi_dict[arg.name][2]				
				roi.y2 = roi_dict[arg.name][3]
				roi.save()	
	return HttpResponse("Success.")

def processtype(request):
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	activetype.ClearProcessed()
	activetype.ProcessType()
	return HttpResponse("Success.")

def isnumber(s):
	try:
		float(s)
		return True
	except ValueError:
		return False
	
def filteredlist(request, url):
	q=applyfilters(request)
	return render_to_response('runloglist.html', {'runlog_list': q})

def filteredzip(request, url):
	q=applyfilters(request)
	tmp = tempfile.TemporaryFile()
	zf = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
	for runlog in q:
		for img in runlog.imageinfo_set.all():
			zf.write(img.path)
	zf.close
	wrapper = FileWrapper(tmp)
	response = HttpResponse(wrapper, content_type='application/zip')
	response['Content-Disposition'] = 'attachment; filename=myfile.zip'
	response['Content-Length'] = tmp.tell()
	tmp.seek(0)
	return response

def applyfilters(request): 
	q=RunLogInfo.objects.all()
	
	if request.GET['name'] != "":
		q=q.filter(sequencepath__contains=request.GET['name'])
	if request.GET['description'] != "":
		q=q.filter(description__contains=request.GET['description'])
	if request.GET['starttime'] != "":
		q=q.filter(time__gt=datetime.datetime.strptime(request.GET['starttime'],"%m/%d/%Y %H:%M:%S"))
	if request.GET['endtime'] != "":
		q=q.filter(time__lt=datetime.datetime.strptime(request.GET['endtime'],"%m/%d/%Y %H:%M:%S"))
	if request.GET['varname'] != "":
		if request.GET['varcomp'] == "ex":
			q=q.filter(variablevalue__name__contains=request.GET['varname'])
		elif isnumber(request.GET['varvalue']):
		        if request.GET['varcomp'] == "lt":
				q=q.filter(variablevalue__name__contains=request.GET['varname'], variablevalue__value__lt=float(request.GET['varvalue']))
			elif request.GET['varcomp'] == "eq":
				q=q.filter(variablevalue__name__contains=request.GET['varname'], variablevalue__value__eq=float(request.GET['varvalue']))
		        elif request.GET['varcomp'] == "gt":
				q=q.filter(variablevalue__name__contains=request.GET['varname'], variablevalue__value__gt=float(request.GET['varvalue']))
	return q

def countsample(request):	
	imgcount=ImageInfo.objects.filter(imgtype__name=request.GET['txttype']).count()
	return HttpResponse(str(imgcount))

def getsample(request):
	samplecount=int(request.GET['samplecount'])
	sampleimage=ImageInfo.objects.filter(imgtype__name=request.GET['activetype'])[samplecount-1]
	return render_to_response('sampleimages.html', {'sampleimage': sampleimage})

def setsample(request):
	activetype = ImageType.objects.get(name=request.GET['activetype'])
	src = RawFrame.objects.get(pngurl=request.GET['src'])
	activetype.sample = src
	activetype.save()
	return HttpResponse("Success.")


	

	
	
	




		

		
		
	        
