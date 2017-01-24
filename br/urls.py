#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4
from django.conf.urls import url
from django.http import HttpResponseRedirect
from br.views import *
from locations.api import LocationItemView, TypedLocationListView
from unicefng.backend import HttpBackendView

urlpatterns = [
    url(r'^incoming/', HttpBackendView.as_view(backend_name='polling')),

    #url(r'^(?P<prefix>(monthly)?)/?(?P<state>\d*)/?(?P<year>\d*)/?(?P<month>\d*)/?$', 'unicefng.br.views.dashboard'),
    #url(r'^data/?(?P<prefix>(monthly)?)/?(?P<state>\d*)/?(?P<year>\d*)/?(?P<month>\d*)/?$', 'unicefng.br.views.csv_download'),
    url(r'^api/locations', TypedLocationListView.as_view(), name='api_location_list'),
    url(r'^api/location/(?P<pk>[0-9]+)/?$', LocationItemView.as_view(), name='api_location_detail'),
    url(r'^faq/?$', FAQView.as_view(), name='faq'),
    url(r'^reports/?$', ReportListView.as_view(), name='reports_list'),
    url(r'^report/(?P<pk>\d+)/?$', ReportEditView.as_view(),
        name='report_edit'),
    url(r'^report/(?P<pk>\d+)/delete$', ReportDeleteView.as_view(),
        name='report_delete'),
    url(r'^/?$', dashboardview, name='dashboard'),
    url(r'^(?P<year>\d+)/?$', dashboardview, name='dashboard_with_year'),
    url(r'^(?P<year>\d+)/(?P<month>\d+)/?$', dashboardview,
        name='dashboard_with_year_and_month'),
    url(r'^(?P<state>[a-z\-]+)/?$', dashboardview,
        name='dashboard_with_state'),
    url(r'^(?P<state>[a-z\-]+)/(?P<year>\d+)/?$', dashboardview,
        name='dashboard_with_state_and_year'),
    url(r'^(?P<state>[a-z\-]+)/(?P<year>\d+)/(?P<month>\d+)/?$', dashboardview,
        name='dashboard_with_state_year_and_month'),
    url(r'^center/new/?$', CenterCreationView.as_view(), name='center_add'),
    url(r'^centers/?$', CenterListView.as_view(), name='center_list'),
    url(r'^center/(?P<pk>\d+)/?$', CenterUpdateView.as_view(), name='center_edit'),
]

# authentication urls
urlpatterns += [
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'br/login.html'}, name="user-login"),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout_then_login', name="user-logout")
]
