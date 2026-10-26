import unittest

from llms_txt_generator import PageMeta, build_llms_txt, clean_title, section_for


class Tests(unittest.TestCase):
    def test_sections(self):
        self.assertEqual(section_for("https://x.com/"), "Main")
        self.assertEqual(section_for("https://x.com/about/"), "Pages")
        self.assertEqual(section_for("https://x.com/blog/my-post/"), "Blog")
        self.assertEqual(section_for("https://x.com/case-studies/a/"), "Case Studies")

    def test_clean_title(self):
        self.assertEqual(clean_title("Pricing | Acme", "Acme"), "Pricing")
        self.assertEqual(clean_title("Pricing - Acme", "acme"), "Pricing")
        self.assertEqual(clean_title("Acme Pricing", "Acme"), "Acme Pricing")

    def test_meta_parser(self):
        p = PageMeta()
        p.feed('<html><head><title> Hello &amp; World </title>'
               '<meta name="description" content="Desc here">'
               '<meta name="robots" content="noindex, follow"></head></html>')
        self.assertIn("Hello", p.title)
        self.assertEqual(p.description, "Desc here")
        self.assertTrue(p.noindex)

    def test_build(self):
        pages = [
            {"url": "https://x.com/about/", "title": "About", "description": "Who we are"},
            {"url": "https://x.com/blog/a/", "title": "Post A", "description": ""},
        ]
        out = build_llms_txt("Acme", "We make things.", pages, optional_sections={"Blog"})
        self.assertTrue(out.startswith("# Acme\n\n> We make things.\n"))
        self.assertIn("## Pages\n\n- [About](https://x.com/about/): Who we are", out)
        self.assertIn("## Optional\n\n- [Post A](https://x.com/blog/a/)", out)
        self.assertLess(out.index("## Pages"), out.index("## Optional"))


if __name__ == "__main__":
    unittest.main()
