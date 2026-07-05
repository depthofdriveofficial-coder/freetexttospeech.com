from http.server import BaseHTTPRequestHandler
import http.client, json, urllib.parse

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
            voice_desc = body.get('voice_desc', '')

            # Voice Design mode — add description in parentheses
            if voice_desc:
                full_text = f"({voice_desc}){text}"
            else:
                full_text = text

            # Call VoxCPM Demo Space Gradio API
            payload = json.dumps({
                "data": [full_text, None, "", 2.0, 10, 42],
                "fn_index": 0
            }).encode()

            conn = http.client.HTTPSConnection("openbmb-voxcpm-demo.hf.space")
            conn.request("POST", "/run/predict",
                body=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
            )

            res = conn.getresponse()
            data = json.loads(res.read().decode())

            if 'data' in data and data['data']:
                audio_url = data['data'][0]
                if isinstance(audio_url, dict):
                    audio_url = audio_url.get('url', '') or audio_url.get('name', '')

                # Fetch actual audio file
                parsed = urllib.parse.urlparse(audio_url)
                conn2 = http.client.HTTPSConnection(parsed.netloc)
                conn2.request("GET", parsed.path)
                res2 = conn2.getresponse()
                audio_data = res2.read()

                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(audio_data)
            else:
                raise Exception("No audio in response: " + str(data)[:200])

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
