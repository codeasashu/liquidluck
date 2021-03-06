#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib
import logging
import datetime
from jinja2 import contextfunction, contextfilter
from liquidluck.options import settings
from liquidluck.utils import to_unicode, to_bytes, get_relative_base


def xmldatetime(value):
    """ this is a jinja filter """
    if not isinstance(value, datetime.datetime):
        return value
    value = value.strftime('%Y-%m-%dT%H:%M:%S')
    return '%s%s' % (value, settings.timezone)


def feed_updated(feed):
    latest = None
    for post in feed.posts:
        if not latest:
            latest = post.updated
        elif post.updated > latest:
            latest = post.updated

    return xmldatetime(latest)


@contextfunction
def content_url(ctx, base, *args):
    writer = ctx.get('writer')

    def fix_index(url):
        if url.endswith('/index.html'):
            return url[:-10]
        return url

    args = list(args)
    base = to_unicode(base)

    if base.startswith('http://') or base.startswith('https://'):
        prefix = '%s/' % base.rstrip('/')
    elif settings.use_relative_url and writer:
        prefix = '%s/' % get_relative_base(writer['filepath'])
        args.insert(0, base)
    else:
        prefix = '/'
        args.insert(0, base)

    args = map(lambda o: to_unicode(o).strip('/'), args)
    url = '/'.join(args).replace('//', '/').replace(' ', '-')
    url = prefix + url.lstrip('/')
    url = to_unicode(fix_index(url.lower()))

    if url.endswith('/'):
        return url

    if settings.permalink.endswith('.html'):
        if url.endswith('.html'):
            return url
        if url.endswith('.xml'):
            return url
        return '%s.html' % url

    if settings.permalink.endswith('/'):
        if url.endswith('.html'):
            url = fix_index(url)
            url = url.rstrip('.html')
        if url.endswith('.xml'):
            url = url.rstrip('.xml')

        return '%s/' % url

    if url.endswith('.html'):
        url = fix_index(url)
        return url.rstrip('.html')
    if url.endswith('.xml'):
        return url.rstrip('.xml')
    return url


@contextfilter
def tag_url(ctx, tag, prepend_site=False):
    prefix = settings.site.get('prefix', '')
    url = settings.site.get('url')
    tagcloud = settings.writers.get('tagcloud', None)

    if prepend_site and tagcloud:
        return '%s#%s' % (content_url(ctx, url, prefix, 'tag', 'index.html'),
                          tag)
    if tagcloud:
        return '%s#%s' % (content_url(ctx, prefix, 'tag', 'index.html'), tag)

    if prepend_site:
        return content_url(ctx, url, prefix, 'tag', tag, 'index.html')

    return content_url(ctx, prefix, 'tag', tag, 'index.html')


@contextfilter
def year_url(ctx, post):
    prefix = settings.site.get('prefix', '')
    return content_url(ctx, prefix, post.date.year, 'index.html')


_Cache = {}


def static_url(base):
    global _Cache

    def get_hsh(path):
        if path in _Cache:
            return _Cache[path]
        abspath = os.path.join(base, path)
        if not os.path.exists(abspath):
            logging.warn('%s does not exists' % path)
            return ''

        with open(abspath) as f:
            content = f.read()
            hsh = hashlib.md5(to_bytes(content)).hexdigest()
            _Cache[path] = hsh
            return hsh

    @contextfunction
    def create_url(ctx, path):
        hsh = get_hsh(path)[:5]
        prefix = settings.static_prefix.rstrip('/')

        if settings.use_relative_url and not prefix.startswith('http'):
            base = get_relative_base(ctx.get('writer')['filepath'])
            prefix = '%s/%s' % (base, prefix.lstrip('/'))

        url = '%s/%s?v=%s' % (prefix, path, hsh)
        return url

    return create_url
