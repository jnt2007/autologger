from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^panel/(?P<panel_id>\d+)/(?P<version_id>\d+)$', views.panel_details, name='panel_details'),
    url(r'^features/(?P<feature_id>\d+)$', views.feature_cases_details, name='feature_cases_details'),
    url(r'^features/$', views.features, name='features'),
    url(r'^panel/(?P<panel_id>\d+)/(?P<version_id>\d+)/(?P<feature_id>\d+)$', views.feature_details,
        name='feature_details'),
    url(r'^charts', views.charts, name='charts'),
    url(r'^progress', views.file_progress, name='file_progress'),
    url(r'^flush_cache', views.flush_cache, name='flush_cache'),
]
