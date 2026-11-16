#!/usr/bin/env python3
"""Collect public product prices into docs/data/history.json."""
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / 'products.json'
HISTORY = ROOT / 'docs' / 'data' / 'history.json'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; PersonalPriceWatch/1.0; +https://github.com/)'}
MAX_POINTS = 730


def valid_url(url):
    try:
        p = urlsplit(url)
        host = p.hostname or ''
        return p.scheme == 'https' and bool(host) and '.' in host and not host.endswith('.local') and not p.username and not p.password
    except ValueError:
        return False


def parse_amount(value):
    """Prefer plain KRW numeric values; no conversion from other currencies."""
    if isinstance(value, (int, float)):
        amount = float(value)
    elif isinstance(value, str):
        cleaned = value.replace(',', '').replace(' ', '').strip()
        cleaned = re.sub(r'^(?:₩|KRW|원)', '', cleaned, flags=re.I)
        cleaned = re.sub(r'(?:₩|KRW|원)$', '', cleaned, flags=re.I)
        if not re.fullmatch(r'\d+(?:\.\d{1,2})?', cleaned):
            return None
        amount = float(cleaned)
    else:
        return None
    return int(round(amount)) if 0 < amount < 10**10 else None


def extract_jsonld(soup):
    def visit(node):
        if isinstance(node, list):
            for item in node:
                yield from visit(item)
        elif isinstance(node, dict):
            if '@graph' in node:
                yield from visit(node['@graph'])
            types = node.get('@type', [])
            if isinstance(types, str):
                types = [types]
            if any(str(t).lower().endswith('product') for t in types):
                offers = node.get('offers', [])
                if isinstance(offers, dict):
                    offers = [offers]
                for offer in offers:
                    if not isinstance(offer, dict):
                        continue
                    currency = offer.get('priceCurrency', 'KRW')
                    if str(currency).upper() != 'KRW':
                        continue
                    price = parse_amount(offer.get('price'))
                    if price is None and isinstance(offer.get('priceSpecification'), dict):
                        price = parse_amount(offer['priceSpecification'].get('price'))
                    if price is not None:
                        yield price
            # nested structural nodes sometimes contain product records
            for key in ('mainEntity', 'itemListElement'):
                if key in node:
                    yield from visit(node[key])
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            doc = json.loads(tag.string or tag.get_text())
            yield from visit(doc)
        except (TypeError, ValueError):
            continue


def extract_price(html, selector=None):
    soup = BeautifulSoup(html, 'html.parser')
    if selector:
        try:
            element = soup.select_one(selector)
        except Exception as ex:
            raise ValueError('CSS 선택자가 올바르지 않습니다') from ex
        if not element:
            raise ValueError('지정한 CSS 선택자로 가격을 찾지 못했습니다')
        price = parse_amount(element.get('content', '') or element.get_text(' ', strip=True))
        if price is None:
            raise ValueError('선택자에서 숫자 가격을 해석하지 못했습니다')
        return price
    for price in extract_jsonld(soup):
        return price
    for attrs in [
        {'property': 'product:price:amount'},
        {'property': 'og:price:amount'},
        {'itemprop': 'price'},
    ]:
        tag = soup.find('meta', attrs=attrs)
        if tag:
            currency = tag.get('data-currency', 'KRW')
            if str(currency).upper() == 'KRW':
                amount = parse_amount(tag.get('content'))
                if amount is not None:
                    return amount
    raise ValueError('가격 정보(JSON-LD/meta)를 찾지 못했습니다')


def get_html(url):
    r = requests.get(url, headers=HEADERS, timeout=22, allow_redirects=True)
    r.raise_for_status()
    if not valid_url(r.url):
        raise ValueError('리다이렉트 주소가 허용되지 않습니다')
    return r.text


def browser_html(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale='ko-KR', user_agent=HEADERS['User-Agent'])
            page.goto(url, wait_until='domcontentloaded', timeout=25000)
            page.wait_for_timeout(1800)
            return page.content()
        finally:
            browser.close()


def collect_one(item):
    url = item['url']
    if not valid_url(url):
        raise ValueError('https:// 상품 URL만 등록할 수 있습니다')
    selector = item.get('selector') or None
    try:
        return extract_price(get_html(url), selector)
    except (ValueError, requests.RequestException) as first:
        try:
            return extract_price(browser_html(url), selector)
        except Exception as second:
            raise ValueError(f'기본 요청: {str(first)[:90]} / 브라우저: {str(second)[:90]}') from second


def main():
    products = json.loads(CONFIG.read_text(encoding='utf-8'))
    if not isinstance(products, list):
        raise SystemExit('products.json must be an array')
    ids = [p.get('id') for p in products]
    if any(not isinstance(p.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,50}', p['id']) for p in products) or len(ids) != len(set(ids)):
        raise SystemExit('Each product needs a unique alphanumeric id')
    data = json.loads(HISTORY.read_text(encoding='utf-8')) if HISTORY.exists() else {'products': {}}
    records = data.setdefault('products', {})
    today = datetime.now(timezone.utc).isoformat(timespec='seconds')
    for item in products:
        if not valid_url(item.get('url', '')):
            print(f"SKIP {item['id']}: invalid URL")
            continue
        entry = records.setdefault(item['id'], {'history': []})
        entry.update({'name': item.get('name', item['id']), 'url': item['url'], 'currency': 'KRW'})
        try:
            price = collect_one(item)
            entry['history'].append({'at': today, 'price': price})
            entry['history'] = entry['history'][-MAX_POINTS:]
            entry.update({'last_status': 'ok', 'last_checked': today, 'last_error': ''})
            print(f"OK {item['id']}: {price:,} KRW")
        except Exception as ex:
            entry.update({'last_status': 'error', 'last_checked': today, 'last_error': str(ex)[:220]})
            print(f"ERROR {item['id']}: {ex}", file=sys.stderr)
    data['updated_at'] = today
    data['configured_ids'] = ids
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=HISTORY.parent, delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_name = f.name
    os.replace(tmp_name, HISTORY)


if __name__ == '__main__':
    main()
