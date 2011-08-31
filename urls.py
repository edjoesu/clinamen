from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'^clinamen/images/([A-Za-z]+)', 'clinamen.filelist.views.imagelist'),
    (r'^clinamen/runlogs/([A-Za-z]+)', 'clinamen.filelist.views.runloglist'),
    (r'^clinamen/filters/([A-Za-z]+)', 'clinamen.filelist.views.filteredlist'),
    # Example:
    # (r'^clinamen/', include('clinamen.foo.urls')),
    
    (r'^clinamen/imgproc/methodlist', 'clinamen.filelist.views.methodlist'),
    (r'^clinamen/imgproc/remove', 'clinamen.filelist.views.removemethod'),
    (r'^clinamen/imgproc/add', 'clinamen.filelist.views.addmethod'),
    (r'^clinamen/imgproc/edit', 'clinamen.filelist.views.editparams'),
    (r'^clinamen/imgproc/update', 'clinamen.filelist.views.updateparams'),
    (r'^clinamen/imgproc/process', 'clinamen.filelist.views.processtype'),    
    
    (r'^clinamen/imgproc/countsample', 'clinamen.filelist.views.countsample'),
    (r'^clinamen/imgproc/getsample', 'clinamen.filelist.views.getsample'),
    (r'^clinamen/imgproc/setsample', 'clinamen.filelist.views.setsample'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'static'}),
)