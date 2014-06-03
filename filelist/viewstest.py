from django.shortcuts import render_to_response, get_list_or_404
from django.http import HttpResponse
import numpy 
import datetime 

def tester(request):
	return HttpResponse("Test succeeded")
