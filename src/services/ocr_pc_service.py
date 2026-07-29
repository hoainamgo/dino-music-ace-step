"""
PC-side OCR service for caption verification via vilao.ai DeepSeek vision.
"""
import os
import base64
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests

VILAO_KEY = os.environ.get("VILAO_KEY", "")
VILAO_BASE = os.environ.get("VILAO_BASE_URL", "https://api.vilao.ai").rstrip("/")
CHAT_PATH = os.environ.get("VILAO_CHAT_PATH", "/v1/chat/completions")
MODEL = os.environ.get("VILAO_OCR_MODEL", "spd/deepseek-v4-flash")
ALT_MODEL = os.environ.get("VILAO_OCR_ALT_MODEL", "phx/phx_grok_4.5")


class OcrHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/ocr":
            self.send_error(404, "only /ocr")
            return
        try:
            content_type = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            image_bytes = None
            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[1].strip().strip('"')
                parts = raw.split(f"--{boundary}".encode())
                for part in parts:
                    header_block, _, body = part.partition(b"\r\n\r\n")
                    headers = header_block.decode("utf-8", "ignore")
                    body = body.rstrip(b"\r\n").rstrip(b"-")
                    if "Content-Disposition" in headers and 'name="image"' in headers:
                        image_bytes = body
                        break
            else:
                image_bytes = raw
            if not image_bytes:
                self.send_error(400, "Missing image field")
                return

            b64 = base64.b64encode(image_bytes).decode("utf-8")
            payload = {
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all visible text from this image. Return only the exact transcription, line by line. If no text, return empty string."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                        ],
                    }
                ],
                "temperature": 0.1,
            }
            headers = {
                "Authorization": f"Bearer {VILAO_KEY}",
                "Content-Type": "application/json",
            }
            url = f"{VILAO_BASE}{CHAT_PATH}"
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            if r.status_code == 404 and MODEL != ALT_MODEL:
                payload["model"] = ALT_MODEL
                r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            text = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
            body = {"text": text.strip(), "provider": "vilao", "model": payload["model"]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))
        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, fmt, *args):
        pass


def main():
    host = os.environ.get("OCR_HOST", "127.0.0.1")
    port = int(os.environ.get("OCR_PORT", "8790"))
    HTTPServer((host, port), OcrHandler).serve_forever()


if __name__ == "__main__":
    main()
