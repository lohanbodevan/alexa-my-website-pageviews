import os
import sys
from datetime import datetime
import logging

log = logging.getLogger()
log.setLevel(logging.INFO)

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, 'vendored'))

import httplib2
from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials


def get_service(api_name, api_version, scope, key_file_location,
                service_account_email):
    credentials = ServiceAccountCredentials.from_p12_keyfile(
    service_account_email, key_file_location, scopes=scope)

    http = credentials.authorize(httplib2.Http())

    return build(api_name, api_version, http=http, cache_discovery=False)

def get_profile_id(service):
    property_id = os.environ.get('PROPERTY_ID')
    properties = property_id.split('-')

    profiles = service.management().profiles().list(
      accountId=properties[1],
      webPropertyId=property_id).execute()

    if profiles.get('items'):
        return profiles.get('items')[0].get('id')

    return None

def get_pageviews(service, profile_id, begin_date, end_date):
    end_date = begin_date if end_date is None else end_date
    return service.data().ga().get(
            ids='ga:' + profile_id,
            start_date=begin_date,
            end_date=end_date,
            metrics='ga:pageviews').execute()

def format_results(results, begin_date, end_date):
    if end_date is None:
        period = 'on {}'.format(format_date(begin_date))
    else:
        period = 'between {} and {}'.format(
            format_date(begin_date), format_date(end_date))

    output = 'Your website had no page views {}'.format(period)
    if results:
        output = 'Your website had {} page views {}'.format(
                results.get('rows')[0][0], period)

    return {
        'version': '1.0',
        'sessionAttributes': {},
        'response': {
            'outputSpeech': {
                'type': 'SSML',
                'ssml': '<speak>{}</speak>'.format(output)
            },
            'card': {
                'type': 'Standard',
                'title': 'My website page views',
                'content': output
            }
        },
        'shouldEndSession': True
    }

def format_date(date_time):
    return datetime.strptime(date_time, '%Y-%m-%d').strftime('%B %d')

def lambda_handler(event, context):
    log.info('Incoing request {}'.format(event.get('request')))

    scope = ['https://www.googleapis.com/auth/analytics.readonly']

    service_account_email = os.environ.get('ACCOUNT_EMAIL')
    key_file_location = 'keyfile.p12'

    service = get_service('analytics', 'v3', scope, key_file_location, service_account_email)
    profile = get_profile_id(service)

    begin_date = event['request']['intent']['slots']['beginDate']['value']
    end_date = None

    if 'value' in event['request']['intent']['slots']['endDate']:
        end_date = event['request']['intent']['slots']['endDate']['value']

    results = get_pageviews(service, profile, begin_date, end_date)
    return format_results(results, begin_date, end_date)
