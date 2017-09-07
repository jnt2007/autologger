import json

from django.db import connection
from datetime import datetime

from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404, redirect
from dashboard.models import AutomationResult, Panel, Version, FeatureMatching, Feature
from django.core import serializers
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage


def obj_to_dict(model_instance):
    serial_obj = serializers.serialize('json', [model_instance])
    obj_as_dict = json.loads(serial_obj)[0]['fields']
    obj_as_dict['id'] = model_instance.pk
    return obj_as_dict


def serialize_panel(panel_instance, version_id):
    serialized_panel = obj_to_dict(panel_instance)
    if hasattr(panel_instance, 'min_automation_result_date'):
        min_date = panel_instance.min_automation_result_date(version_id).get('start_time__min')
        serialized_panel['min_result_date'] = datetime.strftime(min_date, '%d-%m-%Y %H:%M:%S') if min_date else ''
    return serialized_panel


def sql_to_dict(result):
    new_result = []
    try:
        for (filename, date, ip) in result:
            date = datetime.strftime(date, '%d-%m-%Y %H:%M:%S')
            new_result.append({'filename': filename, 'date': date, 'ip': ip})
    except:
        pass
    return new_result


def serialize_result(result):
    return {'id': result.id,
            'version': obj_to_dict(result.version),
            'panel': serialize_panel(result.panel, result.version.id),
            'total': result.total,
            'feature': obj_to_dict(result.feature),
            'passed': result.passed(),
            'fail': result.fail,
            'matched_count': get_matched_count(result.version.id, result.panel.id)
            }


def serialize_feature_matching(result):
    return {
        'version': result.version,
        'panel': result.panel,
        'feature': obj_to_dict(result.feature),
    }


def get_parsing_statistic():
    cursor = connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM arch_logs_files WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=0')
    queue = cursor.fetchone()
    cursor.execute('SELECT COUNT(*) FROM arch_logs_files WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=1')
    fail = cursor.fetchone()

    return queue[0], fail[0]


def get_matched_count(version_id, panel_id):
    cursor = connection.cursor()
    cursor.execute("""SELECT count(DISTINCT (feature_id))
        FROM dashboard_automationresult
        WHERE dashboard_automationresult.version_id = {version_id}
        AND dashboard_automationresult.panel_id ={panel_id} and exists (
            SELECT feature_id
              FROM dashboard_featurematching, dashboard_featurematching_feature
              WHERE dashboard_featurematching.version_id={version_id} AND dashboard_featurematching.id=dashboard_featurematching_feature.featurematching_id
            	AND dashboard_featurematching_feature.feature_id = dashboard_automationresult.feature_id
              AND dashboard_featurematching.panel_id={panel_id}
        )
        """.format(
        panel_id=panel_id, version_id=version_id
    ))
    found_in_results_count = cursor.fetchone()[0]

    cursor.execute("""SELECT count(DISTINCT (feature_id))
        FROM dashboard_automationresult
        WHERE dashboard_automationresult.version_id = {version_id}
        AND dashboard_automationresult.panel_id ={panel_id} and not exists (
            SELECT feature_id
              FROM dashboard_featurematching, dashboard_featurematching_feature
              WHERE dashboard_featurematching.version_id={version_id} AND dashboard_featurematching.id=dashboard_featurematching_feature.featurematching_id
            	AND dashboard_featurematching_feature.feature_id = dashboard_automationresult.feature_id
              AND dashboard_featurematching.panel_id={panel_id}
        )
        """.format(
        panel_id=panel_id, version_id=version_id
    ))
    found_in_results_count_delta = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
          FROM dashboard_featurematching, dashboard_featurematching_feature
          WHERE dashboard_featurematching.version_id={version_id} AND dashboard_featurematching.id=dashboard_featurematching_feature.featurematching_id
          AND dashboard_featurematching.panel_id={panel_id}""".format(
        panel_id=panel_id, version_id=version_id
    ))
    found_in_matchings_count = cursor.fetchone()[0]
    return '%s / %s + %s' % (found_in_results_count, found_in_matchings_count, found_in_results_count_delta)


def result_to_dict(results):
    dict_result = {}
    for result in results:
        if result.feature in dict_result.keys():
            dict_result[result.feature]['total'] += int(result.total)
            dict_result[result.feature]['passed'] += int(result.total) - int(result.fail)
            dict_result[result.feature]['failed'] += int(result.fail)
            if result.start_time < dict_result[result.feature]['start_date']:
                dict_result[result.feature]['start_date'] = result.start_time

        else:
            dict_result[result.feature] = {'total': int(result.total),
                                           'passed': int(result.total) - int(result.fail),
                                           'failed': int(result.fail),
                                           'start_date': result.start_time,
                                           }

    for date in dict_result.values():
        date['start_date'] = datetime.strftime(date['start_date'], '%d-%m-%Y %H:%M:%S')

    return dict_result


def count_matching(results, matched_features=None):
    present_features, absent_features, present_list, not_in_list = {}, [], [], {}
    try:
        for required_feature in matched_features:
            for tested_feature in results.keys():
                if required_feature == tested_feature:
                    present_features[tested_feature] = results[tested_feature]

        for tested_feature in matched_features:
            if tested_feature not in present_features:
                absent_features.append(tested_feature)

        for tested_feature in results:
            if tested_feature not in matched_features:
                not_in_list[tested_feature] = results[tested_feature]

        no_feature_list = False

    except:
        no_feature_list = results

    return {
        'no_feature_list': no_feature_list,
        'present': present_features,
        'absent': absent_features,
        'not_in_list': not_in_list,
    }


def update_date_and_link(results):
    for date in results:
        link_date = datetime.strftime(date.start_time, '%d-%m-%Y_%H-%M-%S')
        date.link = 'http://10.51.112.30/tmc/{}/{}/{}/{}-total.html'.format(
            date.version.id, date.panel.id, link_date, date.feature.file_mask
        )
        date.start_time = datetime.strftime(date.start_time, '%d-%m-%Y %H:%M:%S')

    return results


def set_results_in_cache(results):
    output = json.dumps(map(serialize_result, results))
    cache.set('automation_results', results)
    cache.set('json_results', output)

    return output


def check_cache(results):
    if not cache.get('automation_results'):
        output_results = set_results_in_cache(results)
    else:
        if list(results) == list(cache.get('automation_results')):
            output_results = cache.get('json_results')
        else:
            output_results = set_results_in_cache(results)

    return output_results


# @cache_page(60 * 5)
# @cached_view_as(AutomationResult)
def index(request):
    queue, fail = get_parsing_statistic()

    # versions = Version.objects.order_by('automationresult__start_time').all()
    versions = set(AutomationResult.objects.order_by('-start_time').values_list('version'))
    version_list = []
    for (id,) in versions:
        version_list.append(id)
    paginator = Paginator(sorted(version_list, reverse=True), 3)

    page = request.GET.get('page')
    try:
        versions_on_page = paginator.page(page)
        automation_results = AutomationResult.objects.order_by('version__name').filter(version__in=versions_on_page)

    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        versions_on_page = paginator.page(1)
        automation_results = AutomationResult.objects.order_by('version__name').filter(version__in=versions_on_page)

    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        versions_on_page = paginator.page(paginator.num_pages)
        automation_results = AutomationResult.objects.order_by('version__name').filter(version__in=versions_on_page)

    context = {
        'results': check_cache(automation_results),
        'num_pages': list(range(1, paginator.num_pages + 1)),
        'current_page': int(page or 1),
        'queue': queue,
        'fail': fail
    }
    return render_to_response(u'dashboard/main.html', context)


def panel_details(request, panel_id=None, version_id=None):
    panel = get_object_or_404(Panel, id=panel_id)
    version = get_object_or_404(Version, id=version_id)
    automation_results = AutomationResult.objects.filter(
        panel__id=panel.id, version__id=version.id
    ).order_by('feature__name').all()
    feature_matching = FeatureMatching.objects.filter(
        panel__id=panel.id, version__id=version.id
    ).all()

    queue, fail = get_parsing_statistic()

    if feature_matching:
        matching_context = count_matching(result_to_dict(automation_results), feature_matching[0].feature.all())
    else:
        matching_context = count_matching(result_to_dict(automation_results))

    context = {
        'panel': panel,
        'version': version,
        'queue': queue,
        'fail': fail
    }

    context.update(matching_context)

    return render_to_response(u'dashboard/panel_details.html', context)


def feature_details(request, panel_id=None, version_id=None, feature_id=None):
    panel = get_object_or_404(Panel, id=panel_id)
    version = get_object_or_404(Version, id=version_id)
    feature = get_object_or_404(Feature, id=feature_id)
    automation_results = AutomationResult.objects.filter(
        panel__id=panel.id, version__id=version.id, feature__id=feature.id
    ).order_by('start_time').all()

    queue, fail = get_parsing_statistic()

    changed_results = update_date_and_link(automation_results)

    context = {
        'results': changed_results,
        'panel': panel,
        'version': version,
        'feature': feature,
        'queue': queue,
        'fail': fail
    }

    return render_to_response(u'dashboard/feature_details.html', context)


def feature_cases_details(request, feature_id=None):
    feature = get_object_or_404(Feature, id=feature_id)
    automation_results = AutomationResult.objects.filter(feature__id=feature.id).order_by('-version__name',
                                                                                          'panel__name').all()

    queue, fail = get_parsing_statistic()

    changed_results = update_date_and_link(automation_results)

    context = {
        'results': changed_results,
        'feature': feature,
        'queue': queue,
        'fail': fail
    }

    return render_to_response(u'dashboard/feature_cases_details.html', context)


def features(request):
    features_list = Feature.objects.order_by('name').all()

    queue, fail = get_parsing_statistic()

    context = {
        'features': features_list,
        'queue': queue,
        'fail': fail
    }

    return render_to_response(u'dashboard/features.html', context)


def file_progress(request):
    cursor = connection.cursor()
    # cursor.execute('SELECT COUNT(*) FROM arch_logs_files WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=0')
    # queue = cursor.fetchone()
    # cursor.execute('SELECT COUNT(*) FROM arch_logs_files WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=1')
    # fail = cursor.fetchone()
    cursor.execute('SELECT filename FROM arch_logs_files WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=0')
    queue_files = cursor.fetchall()
    cursor.execute('''SELECT filename, insert_time, remote_ip FROM arch_logs_files
                   WHERE passed_flag=0 AND loaded_flag=1 AND processing_flag=1''')
    fail_files = cursor.fetchall()
    cursor.execute('''SELECT filename, insert_time, remote_ip FROM arch_logs_files
                   WHERE passed_flag=1 AND loaded_flag=1 AND processing_flag=0 order by insert_time desc''')
    processed_files = cursor.fetchall()
    context = {
        'queue': len(queue_files),
        'fail': len(fail_files),
        'queue_files': sql_to_dict(queue_files),
        'fail_files': sql_to_dict(fail_files),
        'processed_files': sql_to_dict(processed_files)
    }

    return render_to_response(u'dashboard/file_progress.html', context)


def charts(request):
    queue, fail = get_parsing_statistic()

    automation_results = AutomationResult.objects.all()

    def results():
        dict_result = {}
        for result in automation_results:
            if str(result.version) in dict_result.keys():
                dict_result[str(result.version)][0] += int(result.total)
                dict_result[str(result.version)][1] += int(result.total) - int(result.fail)
                dict_result[str(result.version)][2] += int(result.fail)

            else:
                dict_result[str(result.version)] = [int(result.total),
                                                    int(result.total) - int(result.fail),
                                                    int(result.fail),
                                                    ]
        return dict_result

    context = {
        'results': results(),
        'queue': queue,
        'fail': fail
    }

    return render_to_response(u'dashboard/charts.html', context)


def flush_cache(request):
    cache.clear()
    return redirect('/')
