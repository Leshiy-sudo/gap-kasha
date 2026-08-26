import base64
import unittest

from app.parsers.fb2 import parse_fb2_metadata


class FB2MetadataTests(unittest.TestCase):
    def test_extracts_title_author_and_cover(self):
        cover = b"fake-cover"
        data = f'''<FictionBook xmlns="urn:fb2" xmlns:l="http://www.w3.org/1999/xlink">
          <description><title-info><book-title>Книга</book-title>
          <author><first-name>Иван</first-name><last-name>Иванов</last-name></author>
          <coverpage><image l:href="#cover.jpg"/></coverpage>
          </title-info></description><body><section><p>Текст</p></section></body>
          <binary id="cover.jpg">{base64.b64encode(cover).decode()}</binary>
        </FictionBook>'''.encode()

        result = parse_fb2_metadata(data)

        self.assertEqual(result.title, "Книга")
        self.assertEqual(result.author, "Иван Иванов")
        self.assertEqual(result.cover_bytes, cover)

    def test_leading_image_without_text_can_be_cover(self):
        cover = b"image"
        data = f'''<FictionBook xmlns="urn:fb2" xmlns:l="http://www.w3.org/1999/xlink">
          <description><title-info><book-title>Книга</book-title></title-info></description>
          <body><section><p><image l:href="#first"/></p><p>Текст</p></section></body>
          <binary id="first">{base64.b64encode(cover).decode()}</binary>
        </FictionBook>'''.encode()

        self.assertEqual(parse_fb2_metadata(data).cover_bytes, cover)


if __name__ == "__main__":
    unittest.main()
