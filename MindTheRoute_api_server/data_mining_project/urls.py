from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = patterns('bike_routing.views', 
    url(r'^bike_api$', 'bike_api'),
    url(r'^init$', 'make_graph'))

urlpatterns = format_suffix_patterns(urlpatterns)