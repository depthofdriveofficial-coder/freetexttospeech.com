from http.server import BaseHTTPRequestHandler
import http.client, json, urllib.parse, tempfile, os, subprocess
import email.parser
import io

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_type = self.headers.get('Content-Type', '')
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)

            # Parse multipart
            boundary = content_type.split('boundary=')[1].strip()
            parts = body.split(('--' + boundary).encode())

            text = ''
            audio_data = b''
            audio_suffix = '.wav'

            for part in parts:
                if b'name="text"' in part:
                    text = part.split(b'\r\n\r\n', 1)[1].rstrip(b'\r\n--')
                    text = text.decode('utf-8', errors='ignore')
                elif b'name="audio"' in part:
                    header, data = part.split(b'\r\n\r\n', 1)
                    audio_data = data.rstrip(b'\r\n--')
                    if b'filename=' in header:
                        fname = header.split(b'filename=')[1].split(b'"')[1].decode()
                        audio_suffix = os.path.splitext(fname)[1] or '.wav'

            # Save audio file
            with tempfile.NamedTemporaryFile(suffix=audio_suffix, delete=False) as f:
                f.write(audio_data)
                input_path = f.name

            # Convert to wav if needed
            if audio_suffix.lower() != '.wav':
                wav_path = input_path.replace(audio_suffix, '.wav')
                subprocess.run(['ffmpeg', '-y', '-i', input_path, '-ar', '16000', '-ac', '1', wav_path],
                    check=True, capture_output=True)
                os.unlink(input_path)
                input_path = wav_path

            # Upload audio to VoxCPM Space and get clone
            # Read audio as base64
            import base64
            with open(input_path, 'rb') as f:
                audio_b64 = base64.b64encode(f.read()).decode()

            os.unlink(input_path)

            # Call Gradio API
            payload = json.dumps({
                "data": [text, {"name": "ref.wav", "data": f"data:audio/wav;base64,{audio_b64}"}, "", 2.0, 10, 42],
                "fn_index": 0
            }).encode()

            conn = http.client.HTTPSConnection("openbmb-voxcpm-demo.hf.space")
            conn.request("POST", "/run/predict",
                body=payload,
                headers={"Content-Type": "application/json"}
            )

            res = conn.getresponse()
            data = json.loads(res.read().decode())

            if 'data' in data and data['data']:
                audio_url = data['data'][0]
                if isinstance(audio_url, dict):
                    audio_url = audio_url.get('url', '') or audio_url.get('name', '')

                parsed = urllib.parse.urlparse(audio_url)
                conn2 = http.client.HTTPSConnection(parsed.netloc)
                conn2.request("GET", parsed.path)
                res2 = conn2.getresponse()
                audio_out = res2.read()

                self.send_response(200)
                self.send_header('Content-Type', 'audio/wav')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(audio_out)
            else:
                raise Exception("No audio: " + str(data)[:200])

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

