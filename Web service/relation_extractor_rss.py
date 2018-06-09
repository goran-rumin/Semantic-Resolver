import logging
import re
import sched
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

import feedparser
import requests as req
from pyquery import PyQuery as pq

import database_mysql as db
import processing as proc

_rss_urls = [
    {"link": "http://rss.cnn.com/rss/edition.rss", "selector": ".zn-body__paragraph", "url_mapper": lambda x: x,
     "regex": re.compile("^.*?\(.*?CNN.*?\)")},
    {"link": "http://feeds.bbci.co.uk/news/rss.xml", "selector": ".story-body__inner > p",
     "url_mapper": lambda x: x.replace(".co.uk", ".com"), "regex": re.compile("")},
    {"link": "http://www.huffingtonpost.com/feeds/news.xml", "selector": ".text > p", "url_mapper": lambda x: x,
     "regex": re.compile("")},
    {"link": "http://rss.nytimes.com/services/xml/rss/nyt/World.xml", "selector": ".story-body-text",
     "url_mapper": lambda x: x, "regex": re.compile("^.*? — ")},
    {"link": "https://www.theguardian.com/world/rss", "selector": ".content__article-body > p",
     "url_mapper": lambda x: x, "regex": re.compile("")}]
_scheduler = sched.scheduler()
_executor = ThreadPoolExecutor(max_workers=10)
_logger = logging.getLogger(__name__)


def process_feeds():
    for url in _rss_urls:
        rss_data = feedparser.parse(url["link"])
        news_links = [x["link"] for x in rss_data["entries"]]
        for news_link in news_links:
            if db.is_link_processed(news_link):
                continue
            text = ""
            try:
                document = pq(url=news_link, headers={"User-Agent": "Mozilla/5.0"})
                news_link = url["url_mapper"](get_redirect_url(news_link))
            except Exception as e:
                _logger.error("Cannot get or extract texts from %s: %s", news_link, e)
                continue
            for element in document(url["selector"]).items():
                if contains_sentence(element.text()):
                    text += element.text().strip() + " "
            text = url["regex"].sub("", text)
            _executor.submit(extract_relations, news_link, text)
    _logger.info("RSS batch finished")
    _scheduler.enter(3 * 60 * 60, 1, process_feeds)


def get_redirect_url(url):
    return req.get(url, headers={"User-Agent": "Mozilla/5.0"}).url


def extract_relations(news_link, text):
    if db.is_link_processed(news_link):
        _logger.info("Already processed %s", news_link)
        return
    relations, extra_output = proc.resolve_relations(text, extra_output=True)
    for row in extra_output:
        row["triples"] = proc.relation_as_triples(relations[row["relations_index"]])
    try:
        db.save_relations(news_link, extra_output)
    except Exception as e:
        _logger.info("Cannot save %s: %s", news_link, e)
        return
    _logger.info("Processed %s, %d relations found", news_link, len(relations))


def contains_sentence(text):
    return text.strip().endswith('.') or text.strip().endswith('."') \
           or text.strip().endswith('.)') or text.strip().endswith('.”')


class SchedulerThread(Thread):
    def run(self):
        _scheduler.enter(1, 1, process_feeds)
        _scheduler.run()


def start():
    SchedulerThread().start()
