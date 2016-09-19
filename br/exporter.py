from datetime import datetime
from dateutil.relativedelta import relativedelta
from itertools import product
import pandas as pd
# tablib is needed because apart from CSV, pandas doesn't do much to support
# writing to in-memory buffers.
import tablib
from locations.models import Location
from .models import BirthRegistration

headers = ['Date', 'State', 'LGA', 'Boys < 1', 'Boys 1-4', 'Boys 5-9',
    'Boys 10-17', 'Girls < 1', 'Girls 1-4', 'Girls 5-9', 'Girls 10-17']


def get_location_subnodes(location):
    subnodes = location.nx_descendants(include_self=True)
    center_pks = [node['id'] for node in subnodes if node['type'] == 'RC']
    state_nodes = [node for node in subnodes if node['type'] == 'State']
    location_tree = {}
    for node in state_nodes:
        location_tree[node['name']] = [n['name'] for n in Location._subnodes(node, 'LGA')]

    return center_pks, location_tree


def export_records(location, year, month=None, cumulative=False, format=None):
    if month:
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, 1) + relativedelta(months=1) - relativedelta(seconds=1)
    else:
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 1, 1) + relativedelta(years=1) - relativedelta(seconds=1)

    if cumulative:
        start_date = datetime.fromtimestamp(0)

    center_pks, location_tree = get_location_subnodes(location)

    records = BirthRegistration.objects.filter(
        location__pk__in=center_pks,
        time__range=(start_date, end_date)
    ).values(
        'girls_below1', 'girls_1to4', 'girls_5to9', 'girls_10to18',
        'boys_below1', 'boys_1to4', 'boys_5to9', 'boys_5to9',
        'boys_10to18', 'location__parent__name',
        'location__parent__parent__name', 'time'
    )

    dataframe = pd.DataFrame(list(records))
    dataset = tablib.Dataset(headers=headers)

    if not dataframe.empty:
        dataframe = dataframe.set_index('time').sort() \
            .rename(columns={'location__name': 'rc',
                'location__parent__name': 'lga',
                'location__parent__parent__name': 'state'
            })

        df_export = dataframe.groupby([dataframe.index.to_period('M'), dataframe.state, dataframe.lga]).sum()

        dates = sorted(set([idx[0] for idx in df_export.index]))
        states = sorted(location_tree.keys())
        for state in states:
            lgas = sorted(location_tree[state])
            for m_index in product(dates, [state], lgas):
                row = [str(m_index[0]), m_index[1], m_index[2]]

                try:
                    row.extend(df_export.ix[m_index][[
                            'boys_below1', 'boys_1to4', 'boys_5to9', 'boys_10to18',
                            'girls_below1', 'girls_1to4', 'girls_5to9', 'girls_10to18',
                        ]])
                except KeyError:
                    row.extend(['-'] * 8)
                dataset.append(row)

    if format:
        return getattr(dataset, format, dataset.xlsx)
    else:
        return dataset.xlsx
