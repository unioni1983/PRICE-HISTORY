"""SSG option-specific price fetcher for the existing personal price watch.

No authentication or anti-bot bypass. A price is recorded only when the
requested option and total amount are both verifiably present in the page.
"""
import re
from playwright.sync_api import sync_playwright


def normalize(value):
    return re.sub(r'\s+', '', value or '').casefold()


def extract_selected_total(text, option_name):
    """Extract total purchase price, not the listing starting price.

    Require the full chosen option and a clearly labelled final amount.
    """
    if normalize(option_name) not in normalize(text):
        raise ValueError('선택 옵션 명칭을 페이지에서 확인하지 못했습니다')

    # Match a localized total only, NOT the main product listing price.
    patterns = [
        r'(?:총\s*금액|총\s*상품금액|총\s*구매금액|총\s*결제금액)\s*[:：]?\s*([\d,]+)\s*원',
        r'(?:총\s*금액|총\s*상품금액|총\s*구매금액|총\s*결제금액)\s*[:：]?\s*\n\s*([\d,]+)\s*원',
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, text, re.I))
        if matches:
            value = int(matches[-1].group(1).replace(',', ''))
            if 1_000 <= value < 100_000_000:
                return value
    raise ValueError('선택 옵션의 총 금액을 확인하지 못했습니다')


def get_option_price(url, option_name):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale='ko-KR', viewport={'width': 1360, 'height': 900})
            response = page.goto(url, wait_until='domcontentloaded', timeout=35000)
            page.wait_for_timeout(3000)
            if response is not None and response.status in (401, 403, 429):
                raise ValueError(f'쇼핑몰 자동 접속 제한: HTTP {response.status}')
            body = page.locator('body').inner_text(timeout=10000)
            if any(s in body for s in ('접근이 제한', '비정상적인 접근', 'Access Denied')):
                raise ValueError('쇼핑몰에서 자동 접속을 제한했습니다')

            # If the desired option isn't already selected, try visible option UI.
            # This uses normal UI controls only (no spoofed credentials or bypass).
            if normalize(option_name) not in normalize(body):
                raise ValueError('페이지에서 요청 옵션을 찾을 수 없습니다')

            # Try a visible, exact option choice from common listbox / select flows.
            try:
                selected = page.get_by_text(option_name, exact=True)
                if selected.count() and selected.first.is_visible(timeout=1500):
                    selected.first.click(timeout=2500)
                    page.wait_for_timeout(1200)
            except Exception:
                pass

            body = page.locator('body').inner_text(timeout=10000)
            try:
                return extract_selected_total(body, option_name)
            except ValueError:
                # A closed dropdown often hides the option choices. Click the
                # label and choose the exact option, if accessible.
                for trigger in ['모델선택', '옵션선택', '옵션 선택']:
                    try:
                        element = page.get_by_text(trigger, exact=False).first
                        element.click(timeout=2500)
                        choice = page.get_by_text(option_name, exact=False).last
                        choice.click(timeout=2500)
                        page.wait_for_timeout(1200)
                        body = page.locator('body').inner_text(timeout=10000)
                        return extract_selected_total(body, option_name)
                    except Exception:
                        continue
                raise ValueError('옵션 자동 선택 또는 총 금액 확인 실패 (기본 가격은 저장하지 않음)')
        finally:
            browser.close()
