import logging
import sys
from logging.handlers import RotatingFileHandler

from bottle import get, post, run, request, static_file, HTTPResponse

import database_mysql as db
import rdf_exporter as rdf
import relation_extractor_rss as rss

logging.basicConfig(format="%(asctime)s %(levelname)s - %(name)s:%(message)s", level=logging.INFO,
                    handlers=[logging.StreamHandler(sys.stdout),
                              RotatingFileHandler("logs/output.log", maxBytes=10 * 1024 * 1024, backupCount=10,
                                                  encoding="UTF-8")])
_logger = logging.getLogger(__name__)


@post('/relations/find')
def find_relations():
    try:
        if request.json is None:
            return HTTPResponse(status=415)
    except:
        return HTTPResponse(status=400)
    text = request.json.get("text", None)
    link = request.json.get("link", None)
    if text is None or type(text) != str or len(text) == 0 or link is None or type(link) != str or len(link) == 0:
        return HTTPResponse(status=400)
    if db.is_link_processed(link):
        return {"relations": db.get_relations(link)}
    rss.extract_relations(link, text)
    return {"relations": db.get_relations(link)}


@post('/relations/<id>/agree')
def agree_relation(id=None):
    if id is None:
        return HTTPResponse(status=400)
    try:
        db.save_vote(id, 1)
    except ValueError:
        return HTTPResponse(status=404)
    return HTTPResponse(status=204)


@post('/relations/<id>/disagree')
def disagree_relation(id=None):
    if id is None:
        return HTTPResponse(status=400)
    try:
        db.save_vote(id, -1)
    except ValueError:
        return HTTPResponse(status=404)
    return HTTPResponse(status=204)


@get('/relations')
def get_relations():
    return {"relations": rdf.get_triples()}


@get('/public/<filename>')
def server_static(filename):
    return static_file("web/" + filename, root='')


rss.start()
rdf.start()
run(host='localhost', port=8080, server="cherrypy")
