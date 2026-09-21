import os
import unittest
from app.services.ocr_engine import SevenSegmentOcrEngine


class TestSevenSegmentOcrEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SevenSegmentOcrEngine()
        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

    def test_sample_image_test1(self):
        img_path = os.path.join(self.images_dir, "test1.bmp")
        self.assertTrue(os.path.exists(img_path))
        with open(img_path, "rb") as f:
            res = self.engine.process_image(f.read())
        
        self.assertTrue(res.is_valid)
        self.assertEqual(res.weight_text, "-30.37")
        self.assertAlmostEqual(res.numeric_value, -30.37, places=2)

    def test_sample_image_test2(self):
        img_path = os.path.join(self.images_dir, "test2.bmp")
        self.assertTrue(os.path.exists(img_path))
        with open(img_path, "rb") as f:
            res = self.engine.process_image(f.read())
        
        self.assertTrue(res.is_valid)
        self.assertEqual(res.weight_text, "177.7")
        self.assertAlmostEqual(res.numeric_value, 177.7, places=1)

    def test_sample_image_test3(self):
        img_path = os.path.join(self.images_dir, "test3.bmp")
        self.assertTrue(os.path.exists(img_path))
        with open(img_path, "rb") as f:
            res = self.engine.process_image(f.read())
        
        self.assertTrue(res.is_valid)
        self.assertEqual(res.weight_text, "078.3")
        self.assertAlmostEqual(res.numeric_value, 78.3, places=1)

    def test_sample_image_test4(self):
        img_path = os.path.join(self.images_dir, "test4.bmp")
        self.assertTrue(os.path.exists(img_path))
        with open(img_path, "rb") as f:
            res = self.engine.process_image(f.read())
        
        self.assertTrue(res.is_valid)
        self.assertEqual(res.weight_text, "072.6")
        self.assertAlmostEqual(res.numeric_value, 72.6, places=1)

    def test_sample_image_lcd_0110(self):
        img_path = os.path.join(self.images_dir, "test_lcd_0110.png")
        self.assertTrue(os.path.exists(img_path))
        with open(img_path, "rb") as f:
            res = self.engine.process_image(f.read())
        
        self.assertTrue(res.is_valid)
        self.assertEqual(res.weight_text, "0.110")
        self.assertAlmostEqual(res.numeric_value, 0.11, places=2)

    def test_empty_input(self):
        res = self.engine.process_image(b"")
        self.assertFalse(res.is_valid)
        self.assertEqual(res.weight_text, "")
        self.assertIsNone(res.numeric_value)

    def test_leading_zero_decimal_formatting(self):
        # Case 1: Missing dot in '0110' should automatically format as '0.110'
        text, val = self.engine.format_recognized_symbols(["0", "1", "1", "0"])
        self.assertEqual(text, "0.110")
        self.assertAlmostEqual(val, 0.11, places=2)

        # Case 2: Negative leading zero without dot
        text, val = self.engine.format_recognized_symbols(["-", "0", "1", "1", "0"])
        self.assertEqual(text, "-0.110")
        self.assertAlmostEqual(val, -0.11, places=2)

        # Case 3: Single zero stays '0'
        text, val = self.engine.format_recognized_symbols(["0"])
        self.assertEqual(text, "0")
        self.assertAlmostEqual(val, 0.0, places=1)

        # Case 4: Multiple zeros '005' becomes '0.05'
        text, val = self.engine.format_recognized_symbols(["0", "0", "5"])
        self.assertEqual(text, "0.05")
        self.assertAlmostEqual(val, 0.05, places=2)

        # Case 5: Already has dot after zero '0.110' stays '0.110'
        text, val = self.engine.format_recognized_symbols(["0", ".", "1", "1", "0"])
        self.assertEqual(text, "0.110")
        self.assertAlmostEqual(val, 0.11, places=2)

        # Case 6: Dot already present elsewhere (e.g. '078.3') preserves dot position
        text, val = self.engine.format_recognized_symbols(["0", "7", "8", ".", "3"])
        self.assertEqual(text, "078.3")
        self.assertAlmostEqual(val, 78.3, places=1)


if __name__ == "__main__":
    unittest.main()
