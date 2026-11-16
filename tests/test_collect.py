import unittest
from collect import parse_amount, extract_price, valid_url


class PriceTests(unittest.TestCase):
    def test_amount(self):
        self.assertEqual(parse_amount('129,000원'), 129000)
        self.assertEqual(parse_amount('₩43,500'), 43500)
        self.assertIsNone(parse_amount('가격 12,000원'))
        self.assertIsNone(parse_amount('-100'))

    def test_jsonld_product(self):
        html = '<script type="application/ld+json">{"@type":"Product","offers":{"@type":"Offer","price":"49,900","priceCurrency":"KRW"}}</script>'
        self.assertEqual(extract_price(html), 49900)

    def test_meta_price(self):
        self.assertEqual(extract_price('<meta property="product:price:amount" content="19900">'), 19900)

    def test_explicit_selector(self):
        self.assertEqual(extract_price('<span class="sale-price">129,000원</span>', '.sale-price'), 129000)

    def test_no_unstructured_guess(self):
        with self.assertRaises(ValueError):
            extract_price('<div>123000원</div>')

    def test_valid_url(self):
        self.assertTrue(valid_url('https://shop.example.com/p/1'))
        self.assertFalse(valid_url('http://shop.example.com'))
        self.assertFalse(valid_url('https://localhost/test'))


if __name__ == '__main__':
    unittest.main()
