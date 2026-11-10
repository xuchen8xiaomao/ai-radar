#!/usr/bin/env python3
"""Collect public RSS/Atom metadata into a static JSON index. No API keys required."""
import calendar
import hashlib
import html
import json
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / 'sources.json'
DATA_DIR = ROOT / 'site' / 'data'
ARTICLES_FILE = DATA_DIR / 'articles.json'
MAX_TOTAL = int(os.getenv('MAX_TOTAL', '1500'))
MAX_PER_FEED = int(os.getenv('MAX_PER_FEED', '35'))
USER_AGENT = 'AIRadarPersonalFeedCollector/1.0 (+public RSS indexing; no full-text scraping)'

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
LOGGER = logging.getLogger('collector')
KEYWORDS = {
    'AI Agent': ['agent', 'agents', 'agentic', 'mcp', 'tool calling', 'tool use', 'multi-agent', '智能体', '智能代理', 'workflow', 'codex', 'claude code', 'gemini cli'],
    '大模型': ['large language model', 'llm', 'foundation model', 'gpt-', 'gemini', 'claude', 'qwen', 'deepseek', 'multimodal', '大模型', '模型发布', 'model release'],
    '开源生态': ['open-source', 'open source', 'github', 'hugging face', 'opensource', '开源', 'library', 'framework'],
    'AI 产品': ['product launch', 'product update', 'feature', 'app', 'assistant', '应用发布', '产品更新'],
}


def normalize_url(url):
    try:
        parts = urlsplit(url.strip())
        if parts.scheme not in ('https', 'http') or not parts.netloc:
            return ''
        query = urlencode([(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                           if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')])
        return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip('/') or '/', query, ''))
    except ValueError:
        return ''


def clean(value, limit):
    v = re.sub(r'<[^>]+>', ' ', str(value or ''))
    v = html.unescape(v)
    v = re.sub(r'\s+', ' ', v).strip()
    return v[:limit]


def get_date(entry):
    for key in ('published_parsed', 'updated_parsed', 'created_parsed'):
        t = entry.get(key)
        if t:
            try:
                return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError):
                pass
    return datetime.now(timezone.utc).isoformat()


def classify(title, summary, fallback):
    v = (title + ' ' + summary).lower()
    scores = {k: sum(1 for kw in words if kw in v) for k, words in KEYWORDS.items()}
    top = max(scores, key=scores.get)
    return top if scores[top] >= 2 else fallback


def fetch_one(source):
    name, url = source['name'], source['url']
    try:
        response = requests.get(url, timeout=18, headers={'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml,application/atom+xml,application/xml,text/xml,*/*'})
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        if feed.bozo and not feed.entries:
            raise ValueError(str(feed.bozo_exception))
        records = []
        for item in feed.entries[:MAX_PER_FEED]:
            link = normalize_url(item.get('link', ''))
            title = clean(item.get('title', ''), 260)
            if not link or not title:
                continue
            summary = clean(item.get('summary', item.get('description', '')), 340)
            uid = hashlib.sha256(link.encode('utf-8')).hexdigest()[:20]
            records.append({'id': uid, 'title': title, 'summary': summary, 'url': link,
                            'source': name, 'category': classify(title, summary, source['category']),
                            'published': get_date(item)})
        LOGGER.info('%-27s %3s entries', name, len(records))
        return records
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning('%s: %s', name, str(exc)[:200])
        return []


def main():
    sources = json.loads(SOURCES_FILE.read_text(encoding='utf-8'))
    if not isinstance(sources, list):
        raise ValueError('sources.json must contain a list')
    previous = []
    if ARTICLES_FILE.exists():
        try:
            previous = json.loads(ARTICLES_FILE.read_text(encoding='utf-8')).get('articles', [])
        except (ValueError, TypeError):
            LOGGER.warning('Discarding unreadable old data file')
    merged = {x['id']: x for x in previous if isinstance(x, dict) and x.get('id') and x.get('url')}
    successful = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_one, s): s['name'] for s in sources}
        for future in as_completed(futures):
            records = future.result()
            successful += bool(records)
            for item in records:
                merged[item['id']] = item
    records = sorted(merged.values(), key=lambda a: a.get('published', ''), reverse=True)[:MAX_TOTAL]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {'updated_at': datetime.now(timezone.utc).isoformat(), 'source_count': len(sources),
               'success_count': successful, 'articles': records}
    ARTICLES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DATA_DIR / 'sources.json').write_text(json.dumps(sources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    LOGGER.info('Wrote %d articles from %d configured sources (%d returned entries)',len(records),len(sources),successful)
    if not records:
        raise SystemExit('No articles collected. Check source URLs/network and retry.')


if __name__ == '__main__':
    main()
