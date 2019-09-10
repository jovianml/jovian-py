from functools import wraps
from os.path import basename
from time import sleep

from requests import get as mkget
from requests import post as mkpost

from jovian._version import __version__
from jovian.utils.credentials import (API_TOKEN_KEY, get_guest_key,
                                      purge_api_key, read_api_url, read_creds,
                                      read_or_request_api_key, read_org_id,
                                      request_api_key, write_api_key)
from jovian.utils.jupyter import get_notebook_name, in_notebook, save_notebook
from jovian.utils.logger import log
from jovian.utils.misc import timestamp_ms


class ApiError(Exception):
    """Error class for web API related Exceptions"""
    pass


def _u(path):
    """Make a URL from the path"""
    return read_api_url() + path


def _msg(res):
    try:
        data = res.json()
        if 'errors' in data and len(data['errors']) > 0:
            return data['errors'][0]['message']
        if 'message' in data:
            return data['message']
        if 'msg' in data:
            return data['msg']
    except:
        if res.text:
            return res.text
        return 'Something went wrong'


def _pretty(res):
    """Make a human readable output from an HTML response"""
    return '(HTTP ' + str(res.status_code) + ') ' + _msg(res)


def retry(request):
    """Decorator to make get/post requests retryable"""
    @wraps(request)
    def _request_wrapper(*args, **kwargs):
        for i in range(2):
            res = request(*args, **kwargs)
            if res.status_code == 401:
                log('The current API key is invalid or expired.', error=True)
                purge_api_key()
                # This will ensure that fresh api token is requested
                kwargs['headers'] = _h()
            else:
                return res
        return res

    return _request_wrapper


@retry
def get(url, params=None, **kwargs):
    """Retryable GET request"""
    return mkget(url, params=None, **kwargs)


@retry
def post(url, data=None, json=None, **kwargs):
    """Retryable POST request"""
    return mkpost(url, data=None, json=None, **kwargs)


def validate_api_key(key):
    """Validate the API key by making a request to server"""
    res = mkget(_u('/user/profile'), headers={'Authorization': 'Bearer ' + key})
    return res.status_code == 200


def get_api_key():
    """Retrieve and validate the API Key (from memory, config or user input)"""
    creds = read_creds()
    if API_TOKEN_KEY not in creds:
        key, _ = read_or_request_api_key()
        if not validate_api_key(key):
            log('The current API key is invalid or expired.', error=True)
            key, _ = request_api_key(), 'request'
            if not validate_api_key(key):
                raise ApiError('The API key provided is invalid or expired.')
        write_api_key(key)
        return key
    return creds[API_TOKEN_KEY]


def _h():
    """Create authorization header with API key"""
    return {"Authorization": "Bearer " + get_api_key(),
            "x-jovian-source": "library",
            "x-jovian-library-version": __version__,
            "x-jovian-guest": get_guest_key(),
            "x-jovian-org": read_org_id()}


def _v(version):
    """Create version query parameter string"""
    if version is not None:
        return "?gist_version=" + str(version)
    return ""


def get_gist(slug):
    """Get the metadata for a gist"""
    res = get(url=_u('/gist/' + slug), headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    raise Exception('Failed to retrieve metadata for notebook "' +
                    slug + '": ' + _pretty(res))


def get_gist_access(slug):
    """Get the access permission of a gist"""
    res = get(url=_u('/gist/' + slug + '/check-access'), headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    raise Exception('Failed to retrieve access permission for notebook "' +
                    slug + '" (retry with create_new=True to create a new notebook): ' + _pretty(res))


def create_gist_simple(filename=None, gist_slug=None, secret=False):
    """Upload the current notebook to create a gist"""
    auth_headers = _h()

    with open(filename, 'rb') as f:
        nb_file = (filename, f)
        log('Uploading notebook..')
        if gist_slug:
            return upload_file(gist_slug=gist_slug, file=nb_file)
        else:
            res = post(url=_u('/gist/create'),
                       data={'public': 0 if secret else 1},
                       files={'files': nb_file},
                       headers=auth_headers)
            if res.status_code == 200:
                return res.json()['data']
            raise ApiError('File upload failed: ' + _pretty(res))


def upload_file(gist_slug, file, version=None, artifact=False):
    """Upload an additional file to a gist"""
    data = {'artifact': 'true'} if artifact else {}
    res = post(url=_u('/gist/' + gist_slug + '/upload' + _v(version)),
               files={'files': file}, data=data, headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    raise ApiError('File upload failed: ' + _pretty(res))


def post_blocks(blocks, version=None):
    url = _u('/data/record' + _v(version))
    res = post(url, json=blocks, headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    else:
        raise ApiError('Data logging failed: ' + _pretty(res))


def post_block(data, data_type, version=None):
    """Upload metrics, hyperparameters and other information to server"""
    blocks = [{"localTimestamp": timestamp_ms(),
               "data": data,
               'recordType': data_type}]
    return post_blocks(blocks, version)


def commit_records(gist_slug, tracking_slugs, version=None):
    """Associated tracked records with a commit"""
    url = _u('/data/' + gist_slug + '/commit' + _v(version))
    res = post(url, json=tracking_slugs, headers=_h())
    if res.status_code == 200:
        return res.json()['data']
    else:
        raise ApiError('Data logging failed: ' + _pretty(res))


def post_slack_message(data, safe=False):
    """Push data to Slack, if slack is integrated with jovian account"""
    url = _u('/slack/notify')
    res = post(url, json=data, headers=_h())
    if res.status_code == 200:
        return res.json()
    elif safe:
        return {'data': {'messageSent': False}}
    else:
        raise ApiError('Slack trigger failed: ' + _pretty(res))
