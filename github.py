import re
import base64
import simplejson as json
import urllib2
import httplib
import logging

import app
import request_handler

_USER = 'KhanBugz'
_PASSWD = app.App.khanbugz_passwd
_AUTH_HEADER = "Basic %s" % base64.encodestring("%s:%s" % (_USER, _PASSWD)).strip()
HEADERS = { "Authorization": _AUTH_HEADER, "Content-Type": "application/json" }

class BetterHTTPErrorProcessor(urllib2.BaseHandler):
    # a substitute/supplement to urllib2.HTTPErrorProcessor
    # that doesn't raise exceptions on status codes 201,204,206.
    # code taken from http://stackoverflow.com/questions/7032890/why-does-pythons-urllib2-urlopen-raise-an-httperror-for-successful-status-code
    def http_error_201(self, request, response, code, msg, hdrs):
        return response
    def http_error_204(self, request, response, code, msg, hdrs):
        return response
    def http_error_206(self, request, response, code, msg, hdrs):
        return response


def gh_post(handler, url, data, headers):

    opener = urllib2.build_opener(BetterHTTPErrorProcessor)
    urllib2.install_opener(opener)

    try:
        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)

    except urllib2.HTTPError, e:
        logging.info("Encountered HTTPError %s" % e)
        handler.response.set_status(500)
        handler.render_json(e.read())
        e.close()

    except urllib2.URLError, e:
        logging.info("Encountered URLError %s" % e)
        handler.response.set_status(500)
        handler.render_json(e.read())
        e.close()

    else:
        if response.code == 201:
            handler.response.set_status(201)
            handler.render_json(response.read())
        elif 'callback' in url:
            handler.response.set_status(201)
            handler.response.out.write(response.read())
        else:
            logging.info("Encountered non-201 HTTP status code %s" % response.read())
            handler.response.set_status(500)
            handler.render_json(response.read())

        response.close()

class NewPost(request_handler.RequestHandler):

    def get(self):

        data = self.request.get('json')
        url = "https://api.github.com/repos/jruberg/kathack-fork/issues" + \
              "?callback=" + self.request.get('callback')

        self.response.headers.add_header("Content-Type", "text/javascript")

        gh_post(self, url, data, HEADERS)

    def post(self):

        data = json.loads(self.request.body)["json"]
        url = "https://api.github.com/repos/jruberg/kathack-fork/issues"

        gh_post(self, url, json.dumps(data), HEADERS)

class NewComment(request_handler.RequestHandler):
    def post(self):

        data = json.loads(self.request.body)["json"]
        url = ("https://api.github.com/repos/jruberg/kathack-fork/issues/%d/comments" %
               data['id'])

        gh_post(self, url, json.dumps(data), HEADERS)
