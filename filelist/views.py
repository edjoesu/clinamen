# Create your views here.
from django.shortcuts import render_to_response, get_list_or_404
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.core.paginator import Paginator
from django.template import RequestContext
from clinamen.filelist.models import *
import clinamen.filelist.filesettings as filesettings
import populatedb
import datetime 
import json
import zipfile, tempfile 

def imagelist(request, url):
	img_list = get_list_or_404(ImageInfo)
	return render_to_response('imglist.html', {'img_list': img_list})

def runloglist(request, url):
	runlog_list = get_list_or_404(RunLogInfo)
	addshortpath(runlog_list, filesettings.SHORT_PATH_LEVELS)
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
	if 'updateimg' in request.GET:
		populatedb.updateimagesbytime()	
	q=applyfilters(request)
	addshortpath(q, filesettings.SHORT_PATH_LEVELS)
	return render_to_response('runloglist.html', {'runlog_list': q}, context_instance=RequestContext(request))

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

def dayseqview(request):
	RESULTS_PER_PAGE = 500

	q=applyfilters(request)
	response=render_to_response('dayseq.html', {'runlog_list': q}, context_instance=RequestContext(request))

	if 'page' in request.GET.keys():
		page=int(request.GET['page'])
	else:
		page=1

	q_total = q.count()
	q_end=q[RESULTS_PER_PAGE*(page-1)].time
	q_start=q[min(RESULTS_PER_PAGE*page-1, q_total-1)].time
	q_page = q.filter(time__gte=q_start, time__lte=q_end)

	q_count=q_page.count()
	timelist=q_page.values_list('time', flat=True)
	start_ind=[ii+1 for ii, delta in enumerate([aa-bb for aa,bb in zip(timelist[:q_count], timelist[1:])]) if (delta > datetime.timedelta(hours=6))]
	start_ind.insert(0,0)

	response.write('<UL id="black" class="treeview-black">')

	for ii in range(len(start_ind)):

		endtime=q_page[start_ind[ii]].time
		starttime=q_page[(start_ind[ii+1]-1 if (ii+1)<len(start_ind) else q_count-1)].time
		qday=q_page.filter(time__gte=starttime, time__lte=endtime)
		seqpaths=uniquify(qday.values_list('sequencepath', flat=True))

		html = '<LI class="closed"><SPAN>Run day starting %s and ending %s.</SPAN><UL>' % (starttime, endtime)
		response.write(html)
		if seqpaths is not None:
			seqpaths.reverse()
		for seqpath in seqpaths:
			qdayseq=qday.filter(sequencepath=seqpath)
			response.write('<LI class="closed"><SPAN>'+seqpath+"      "+str(qdayseq.count())+"</SPAN><UL>")

			response.write("<LI><TABLE>")
			for seq in qdayseq:
				response.write("<TR>")
				response.write("<TD>" + str(seq.time)+ "</TD>")

				response.write("<TD>")
				for varvalue in seq.variablevalue_set.all():
					response.write(varvalue.name + "=" + str(varvalue.value) + "<BR>")
				response.write("</TD>")

				response.write("<TD>")
				imset=seq.imageinfo_set.all()
				for imginfo in imset[:2]:
					for frameinfo in imginfo.rawframe_set.all():
						response.write('<a href="'+frameinfo.pngurl+'"><img height="64" width="64" src="'+frameinfo.thumburl+'"></a>')
					response.write("<BR>")
				response.write("</TD>")

				response.write("<TD>")
				imset=seq.imageinfo_set.all()
				for imginfo in imset[:2]:
					for frameinfo in imginfo.processedframe_set.all():
						response.write('<a href="'+frameinfo.pngurl+'"><img height="64" width="64" src="'+frameinfo.thumburl+'"></a>')
					response.write("<BR>")
				response.write("</TD>")

				response.write("</TR>")
			response.write("</LI></TABLE>")
			response.write('</UL></LI>')
		response.write('</UL></LI>')
	response.write('</UL>')

	response.write('</DIV></BODY></HTML>')
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
	if 'imgonly' in request.GET: 
		q=q.filter(imageinfo__isnull=False)
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

def uniquify(seq):
	seen = set()
	seen_add = seen.add
	return [ x for x in seq if x not in seen and not seen_add(x)]

def addshortpath(obj_list, levels_to_keep):
	for obj in obj_list:
		try:			
			match = re.search(r"(\\[^\\]*){1," + str(levels_to_keep) + r"}$", obj.sequencepath)
			obj.shortpath = match.group(0)			                 
		except:
			obj.shortpath = ""














