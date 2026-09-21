import os
import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestOcrApi(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("version", data)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("service", data)
        self.assertIn("ocr_endpoint", data)

    def test_ocr_recognize_test1(self):
        img_path = os.path.join(self.images_dir, "test1.bmp")
        with open(img_path, "rb") as f:
            response = self.client.post(
                "/api/v1/ocr/recognize",
                files={"file": ("test1.bmp", f, "image/bmp")},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["weight_text"], "-30.37")
        self.assertAlmostEqual(data["numeric_value"], -30.37, places=2)
        self.assertGreater(data["processing_time_ms"], 0)

    def test_ocr_recognize_test2(self):
        img_path = os.path.join(self.images_dir, "test2.bmp")
        with open(img_path, "rb") as f:
            response = self.client.post(
                "/api/v1/ocr/recognize",
                files={"file": ("test2.bmp", f, "image/bmp")},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["weight_text"], "177.7")
        self.assertAlmostEqual(data["numeric_value"], 177.7, places=1)

    def test_ocr_recognize_test3(self):
        img_path = os.path.join(self.images_dir, "test3.bmp")
        with open(img_path, "rb") as f:
            response = self.client.post(
                "/api/v1/ocr/recognize",
                files={"file": ("test3.bmp", f, "image/bmp")},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["weight_text"], "078.3")
        self.assertAlmostEqual(data["numeric_value"], 78.3, places=1)

    def test_ocr_recognize_test4(self):
        img_path = os.path.join(self.images_dir, "test4.bmp")
        with open(img_path, "rb") as f:
            response = self.client.post(
                "/api/v1/ocr/recognize",
                files={"file": ("test4.bmp", f, "image/bmp")},
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["weight_text"], "072.6")
        self.assertAlmostEqual(data["numeric_value"], 72.6, places=1)

    def test_ocr_recognize_invalid_mime(self):
        response = self.client.post(
            "/api/v1/ocr/recognize",
            files={"file": ("document.pdf", b"%PDF-1.4", "application/pdf")},
        )
        self.assertEqual(response.status_code, 415)


if __name__ == "__main__":
    unittest.main()

