import os
import json
import requests
from bs4 import BeautifulSoup
import datetime
from urllib import parse

HEADERS = {"Content-Type": "html",
           'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}


def get_value_from_link(url: str, key: str):
    query = parse.urlsplit(url).query
    query_map = dict(parse.parse_qsl(query))
    return query_map.get(key)


def parse_game_time(date_str, time_str):
    year = str(datetime.datetime.now().year)
    return datetime.datetime.strptime(year + ' ' + date_str + ' ' + time_str, '%Y %a %b %d %I:%M %p')


def get_html(url: str, params={}):
    print('Reading HTML from %s...' % url)
    html = requests.get(url, params=params, headers=HEADERS)
    return BeautifulSoup(html.text, 'html5lib')


def cache_json(file_format, max_age=datetime.timedelta(days=1), reload_kwarg='reload'):
    """
    A function that creates a decorator which will use "cache_json" for caching the results of the decorated function "fn".
    """
    def decorator(fn):  # define a decorator for a function "fn"
        # define a wrapper that will finally call "fn" with all arguments
        def wrapped(*args, **kwargs):
            # Format filepath and create intermediate directories
            path = os.path.join('__cache__', file_format.format(
                *args, **kwargs) + '.json')
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            try_load = not kwargs.get(reload_kwarg, False)
            if try_load and os.path.exists(path):
                modify_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                age = datetime.datetime.now() - modify_time
                if max_age is not None and age < max_age:
                    with open(path, 'r') as cachehandle:
                        print("using cached result from '%s'" % path)
                        return json.load(cachehandle)
                else:
                    print('cache is stale. Reloading...')

            # execute the function with all arguments passed
            res = fn(*args, **kwargs)
            # write to cache file
            with open(path, 'w') as cachehandle:
                print("saving result to cache '%s'" % path)
                json.dump(res, cachehandle)
            return res
        return wrapped
    return decorator
