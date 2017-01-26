from dr.helpers import death_report_summary, compute_rankings
from dr.models import DeathReport
from django.shortcuts import render
from django.http import HttpResponse

def dashboard(request):
    context = {}
    df = death_report_summary(DeathReport.objects.all())

    if not df.empty:
        general_data = df.groupby('country').sum().astype('int')
        states_data = compute_rankings(df.groupby('state').sum()).astype('int')

        context = {
            'general_male':        general_data.ix[0]['general_male'],
            'general_female':      general_data.ix[0]['general_female'],
            'general_certified':   general_data.ix[0]['general_certified'],
            'general_uncertified': general_data.ix[0]['general_uncertified'],
            'general_childbirth':  general_data.ix[0]['general_childbirth'],
            'general_fevers':      general_data.ix[0]['general_fevers'],
            'general_accidents':   general_data.ix[0]['general_accidents'],
            'general_hiv':         general_data.ix[0]['general_hiv'],
            'general_others':      general_data.ix[0]['general_others'],

            'female_1':          general_data.ix[0]['female_1'],
            'female_4':          general_data.ix[0]['female_4'],
            'female_5':          general_data.ix[0]['female_5'],
            'female_childbirth': general_data.ix[0]['female_childbirth'],
            'female_fevers':     general_data.ix[0]['female_fevers'],
            'female_accidents':  general_data.ix[0]['female_accidents'],
            'female_hiv':        general_data.ix[0]['female_hiv'],
            'female_others':     general_data.ix[0]['female_others'],

            'male_1':         general_data.ix[0]['male_1'],
            'male_4':         general_data.ix[0]['male_4'],
            'male_5':         general_data.ix[0]['male_5'],
            'male_fevers':    general_data.ix[0]['male_fevers'],
            'male_accidents': general_data.ix[0]['male_accidents'],
            'male_hiv':       general_data.ix[0]['male_hiv'],
            'male_others':    general_data.ix[0]['male_others'],
        }

        context['states_data'] = []

        for state in sorted(states_data.index):
            data = {'state': state}
            data.update(states_data.ix[state])
            context['states_data'].append(data)

    return render(request, 'dr/dashboard.html', context)
