# -*- coding: utf-8 -*-
from collections import OrderedDict
from itertools import groupby
import json

from django.db.models import F, Sum
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView

from django.conf import settings

from campaigns.models import Campaign
from ipd.filters import CampaignRelatedFilter
from ipd import helpers
from ipd.models import NonCompliance, Report, Shortage
from locations.models import Location


def dashboard(request, campaign_id=None, location_id=None):
    context = {}
    lgas = None
    vaccination_data = []
    noncompliance_data = []
    shortage_data = []

    if campaign_id and location_id:
        campaign = get_object_or_404(Campaign, pk=campaign_id)
        location = get_object_or_404(Location, pk=location_id)
        context[u'page_title'] = u'{name} ({location_name} ({location_type})'.format(
            name=campaign.name, location_name=location.name, location_type=location.type.name)
    else:
        campaign = location = None
        context[u'page_title'] = u'MNCHW'

    campaign_qs = Campaign.objects.order_by(
        u'-start_date').prefetch_related(u'locations').annotate(
            loc_name=F(u'locations__name'),
            loc_type=F(u'locations__type__name'),
            loc_pk=F(u'locations__pk')
        ).filter(loc_type='State').values(
        u'name', u'loc_name', u'loc_type', u'loc_pk', u'pk')

    if campaign:
        reports, noncompliance_reports, shortages, lgas = helpers.get_campaign_data(campaign, location)

        vaccination_data = helpers.get_vaccination_summary(reports, lgas)
        noncompliance_data = helpers.get_noncompliance_summary(noncompliance_reports, lgas)
        shortage_data = helpers.get_shortage_summary(shortages, lgas)

    context[u'campaigns'] = campaign_qs
    context[u'lgas'] = lgas
    context[u'commodities'] = OrderedDict(Report.IM_COMMODITIES)
    context[u'nc_reasons'] = OrderedDict(NonCompliance.NC_REASONS)
    context[u'shortage_commodities'] = OrderedDict(Shortage.SHORTAGE_COMMODITIES)
    context[u'vaccination_data'] = vaccination_data
    context[u'noncompliance_data'] = noncompliance_data
    context[u'shortage_data'] = shortage_data
    context[u'selected_campaign'] = campaign
    context[u'selected_location'] = location

    return render(request, u'campaigns/dashboard.html', context)


class CampaignRelatedObjectListMixin(object):
    paginate_by = settings.PAGE_SIZE

    def get_campaign(self):
        campaign_id = self.kwargs.get(u'campaign_id')

        campaign = get_object_or_404(Campaign, pk=campaign_id)

        return campaign

    def get_context_data(self, **kwargs):
        context = super(CampaignRelatedObjectListMixin, self).get_context_data(**kwargs)

        context[u'filter_form'] = self.filterset.form

        return context

    def get_queryset(self):
        campaign = self.get_campaign()
        model_class = self.model
        queryset = model_class.objects.filter(
            time__range=(campaign.start_date, campaign.end_date))

        # add in the filter
        self.filterset = CampaignRelatedFilter(self.request.GET, queryset=queryset)

        return self.filterset.qs


class ReportListView(CampaignRelatedObjectListMixin, ListView):
    model = Report
    template_name = u'ipd/report_list.html'


class NonComplianceReportListView(CampaignRelatedObjectListMixin, ListView):
    model = NonCompliance
    template_name = u'ipd/nc_report_list.html'


class ShortageReportListView(CampaignRelatedObjectListMixin, ListView):
    model = Shortage
    template_name = u'ipd/shortage_report_list.html'
