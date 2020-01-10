# -*- coding: utf-8 -*-

# Copyright (C) 2005 - 2011, TUBITAK/UEKAE
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# Please read the COPYING file.
#

"""Yet another Pisi module for fetching files from various sources. Of
course, this is not limited to just fetching source files. We fetch
all kinds of things: source tarballs, index files, packages, and God
knows what."""

# python standard library modules
import contextlib
import os
import time
import base64
import shutil

import gettext

__trans = gettext.translation('pisi', fallback=True)
_ = __trans.gettext

# pisi modules
import pisi
import pisi.util as util
import pisi.context as ctx
import pisi.uri


class FetchError(pisi.Error):
    pass


class FetchHandler:
    def __init__(self, url, archive, bandwidth_limit):
        self.url = url
        self.percent = None
        self.rate = 0.0
        self.size = 0
        self.eta = '--:--:--'
        self.symbol = '--/-'
        self.last_updated = 0
        self.filename = url.filename()
        self.total_size = 0
        self.exist_size = 0
        self.bandwidth_limit = bandwidth_limit
        if os.path.exists(archive):
            self.exist_size = os.path.getsize(archive)

        self.now = lambda: time.time()
        self.t_diff = lambda: self.now() - self.s_time

        self.s_time = self.now()

    def update(self, blocknum, bs, size):
        self.total_size = size + self.exist_size
        self.size = blocknum * bs + self.exist_size
        if self.total_size:
            self.percent = self.size * 100 / self.total_size
            if self.percent > 100:
                self.percent = 100
        else:
            self.percent = 0

        if int(self.now()) != int(self.last_updated) and self.size > 0:
            try:
                self.rate, self.symbol = util.human_readable_rate(self.size / (self.now() - self.s_time))
            except ZeroDivisionError:
                return
            if self.total_size:
                self.eta = '%02d:%02d:%02d' %\
                    tuple([i for i in time.gmtime((self.t_diff() * (100 - self.percent)) / self.percent)[3:6]])

        self._update_ui()
        self._limit_bandwidth()

    def _limit_bandwidth(self):
        if self.bandwidth_limit:
            expected_time = (self.size - self.exist_size) / self.bandwidth_limit
            sleep_time = expected_time - self.t_diff()
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _update_ui(self):
        ctx.ui.display_progress(
            operation="fetching",
            percent=self.percent,
            filename=self.filename,
            total_size=self.total_size,
            downloaded_size=self.size,
            rate=self.rate,
            eta=self.eta,
            symbol=self.symbol
        )

        self.last_updated = self.now()


class Fetcher:
    """Fetcher can fetch a file from various sources using various
    protocols."""
    def __init__(self, url, destdir="/tmp", destfile=None):
        if not isinstance(url, pisi.uri.URI):
            url = pisi.uri.URI(url)

        if ctx.config.get_option("authinfo"):
            url.set_auth_info(ctx.config.get_option("authinfo"))

        self.url = url
        self.destdir = destdir
        self.destfile = destfile

        self.archive_file = os.path.join(destdir, destfile or url.filename())
        self.partial_file = os.path.join(self.destdir, self.url.filename()) + ctx.const.partial_suffix

        util.ensure_dirs(self.destdir)

    def fetch(self):
        """Return value: Fetched file's full path.."""

        if not self.url.filename():
            raise FetchError(_('Filename error'))

        if not os.access(self.destdir, os.W_OK):
            raise FetchError(_('Access denied to write to destination directory: "%s"') % self.destdir)

        if os.path.exists(self.archive_file) and not os.access(self.archive_file, os.W_OK):
            raise FetchError(_('Access denied to destination file: "%s"') % self.archive_file)

        import urllib.request

        try:
            fetch_handler = FetchHandler(self.url, self.partial_file, self._get_bandwidth_limit())

            proxy = urllib.request.ProxyHandler(self._get_proxies())
            opener = urllib.request.build_opener(proxy)
            opener.addheaders = self._get_headers()
            urllib.request.install_opener(opener)
            has_range_support = self._test_range_support()

            if has_range_support and os.path.exists(self.partial_file):
                partial_file_size = os.path.getsize(self.partial_file)
                opener.addheaders.append(('Range', 'bytes=%s-' % partial_file_size))

            with contextlib.closing(urllib.request.urlopen(self.url.get_uri())) as fp:
                headers = fp.info()

                if self.url.is_local_file():
                    return os.path.normpath(self.url.path())

                if has_range_support:
                    tfp = open(self.partial_file, 'ab')
                else:
                    tfp = open(self.partial_file, 'wb')

                with tfp:
                    bs = 1024 * 8
                    size = -1
                    read = 0
                    blocknum = 0
                    if "content-length" in headers:
                        size = int(headers["Content-Length"])
                    fetch_handler.update(blocknum, bs, size)
                    while True:
                        block = fp.read(bs)
                        if not block:
                            break
                        read += len(block)
                        tfp.write(block)
                        blocknum += 1
                        fetch_handler.update(blocknum, bs, size)
        except urllib.request.URLError as e:
            raise FetchError(_('Could not fetch destination file "%s": %s') % (self.url.get_uri(), e))

        if os.stat(self.partial_file).st_size == 0:
            os.remove(self.partial_file)
            raise FetchError(_('A problem occurred. Please check the archive address and/or permissions again.'))

        shutil.move(self.partial_file, self.archive_file)

        return self.archive_file

    def _get_headers(self):
        headers = []
        if self.url.auth_info():
            enc = base64.encodestring('%s:%s' % self.url.auth_info())
            headers.append(('Authorization', 'Basic %s' % enc))
        headers.append(('User-Agent', 'PiSi Fetcher/' + pisi.__version__))
        return headers

    def _get_proxies(self):
        proxies = {}
        
        if ctx.config.values.general.http_proxy and self.url.scheme() == "http":
            proxies[pisi.uri.URI(ctx.config.values.general.http_proxy).scheme()] = ctx.config.values.general.http_proxy

        if ctx.config.values.general.https_proxy and self.url.scheme() == "https":
            proxies[pisi.uri.URI(ctx.config.values.general.https_proxy).scheme()] = ctx.config.values.general.https_proxy

        if ctx.config.values.general.ftp_proxy and self.url.scheme() == "ftp":
            proxies[pisi.uri.URI(ctx.config.values.general.ftp_proxy).scheme()] = ctx.config.values.general.ftp_proxy

        if self.url.scheme() in proxies:
            ctx.ui.info(_("Proxy configuration has been found for '%s' protocol") % self.url.scheme())

        return proxies

    def _get_bandwidth_limit(self):
        bandwidth_limit = ctx.config.options.bandwidth_limit or ctx.config.values.general.bandwidth_limit
        if bandwidth_limit and bandwidth_limit != "0":
            ctx.ui.warning(_("Bandwidth usage is limited to %s KB/s") % bandwidth_limit)
            return 1024 * int(bandwidth_limit)
        else:
            return 0

    def _test_range_support(self):
        if not os.path.exists(self.partial_file):
            return False

        import urllib.request
        import urllib.error

        try:
            file_obj = urllib.request.urlopen(urllib.request.Request(self.url.get_uri()))
        except urllib.error.URLError:
            ctx.ui.debug(_("Remote file can not be reached. Previously downloaded part of the file will be removed."))
            os.remove(self.partial_file)
            return False

        headers = file_obj.info()
        file_obj.close()
        if 'Content-Length' in headers:
            return True
        else:
            ctx.ui.debug(_("Server doesn't support partial downloads. Previously downloaded part of the file will be over-written."))
            os.remove(self.partial_file)
            return False


# helper function
def fetch_url(url, destdir, progress=None, destfile=None):
    fetch = Fetcher(url, destdir, destfile)
    fetch.progress = progress
    fetch.fetch()
