from http.server import BaseHTTPRequestHandler
import http.client, json
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))

            text = body.get('text', '')
            voice = body.get('voice', 'alloy')
            prompt = body.get('prompt', '')

            boundary = '----WebKitFormBoundarya027BOtfh6crFn7A'

            def field(name, value):
                return (
                    f'--{boundary}\r\n'
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                    f'{value}\r\n'
                ).encode()

            body_parts = (
                field('input', text) +
                field('voice', voice) +
                field('prompt', prompt) +
                f'--{boundary}--\r\n'.encode()
            )

            conn = http.client.HTTPSConnection("www.openai.fm")
            conn.request("POST", "/api/generate",
                body=body_parts,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "Accept": "*/*",
                    "Origin": "https://www.openai.fm",
                    "Referer": "https://www.openai.fm/worker-444eae9e2e1bdd6edd8969f319655e70.js",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                    "Priority": "u=1, i",
                }
            )

            res = conn.getresponse()
            content_type = res.getheader('Content-Type', '')
            audio_data = res.read()

            if 'audio' in content_type:
                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(audio_data)
            else:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': audio_data.decode('utf-8', errors='ignore')[:200]}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
