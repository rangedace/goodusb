"""Capture a fixed local echo message over HTTP and HTTPS, without shell execution."""

import argparse
import datetime
import http.client
import http.server
import ipaddress
import json
import os
from pathlib import Path
import ssl
import subprocess
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class EchoHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/demo':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 4096:
            self.send_error(400)
            return
        try:
            message = json.loads(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        response = json.dumps({'received': message, 'mode': self.server.mode}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, fmt, *args):
        print(f'{self.server.mode}: {fmt % args}', flush=True)


def create_certificate(output):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=1))
            .not_valid_after(now + datetime.timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName('localhost'),
                x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
            ]), critical=False)
            .sign(key, hashes.SHA256()))
    cert_path = output / 'localhost-cert.pem'
    key_path = output / 'localhost-key.pem'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                         serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    return cert_path, key_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.local/http-https-demo'))
    parser.add_argument('--wireshark-dir', type=Path, default=Path('C:/Program Files/Wireshark'))
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    cert_path, key_path = create_certificate(args.output)
    capture_path = args.output / 'http-https.pcapng'
    keylog_path = args.output / 'tls-keys.log'
    keylog_path.write_text('', encoding='ascii')
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert_path, key_path)
    client_context = ssl.create_default_context(cafile=str(cert_path))
    client_context.keylog_filename = str(keylog_path)
    servers = []
    capture = None
    results = []
    try:
        for port, mode in [(8080, 'HTTP'), (8443, 'HTTPS')]:
            server = http.server.ThreadingHTTPServer(('127.0.0.1', port), EchoHandler)
            servers.append(server)
            server.mode = mode
            if mode == 'HTTPS':
                server.socket = server_context.wrap_socket(server.socket, server_side=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
        with (args.output / 'capture.log').open('w', encoding='utf-8') as capture_log:
            capture = subprocess.Popen([
                str(args.wireshark_dir / 'dumpcap.exe'),
                '-i', r'\Device\NPF_Loopback',
                '-f', 'host 127.0.0.1 and (tcp port 8080 or tcp port 8443)',
                '-a', 'duration:8', '-w', str(capture_path),
            ], stdout=capture_log, stderr=capture_log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if capture.poll() is not None:
                    raise RuntimeError('Capture failed; see capture.log')
                if 'File:' in (args.output / 'capture.log').read_text(encoding='utf-8', errors='replace'):
                    break
                time.sleep(0.1)
            else:
                raise TimeoutError('Capture did not become ready; see capture.log')
            for mode in ['HTTP', 'HTTPS']:
                if mode == 'HTTP':
                    connection = http.client.HTTPConnection('127.0.0.1', 8080, timeout=5)
                else:
                    connection = http.client.HTTPSConnection('127.0.0.1', 8443,
                                                             context=client_context, timeout=5)
                try:
                    message = {'message': 'SALUT_WIRESHARK', 'purpose': 'local transport demo'}
                    connection.request('POST', '/demo', json.dumps(message),
                                       {'Content-Type': 'application/json'})
                    response = connection.getresponse()
                    body = json.loads(response.read())
                    assert response.status == 200 and body['received'] == message
                    results.append({'mode': mode, 'status': response.status, 'response': body})
                    print(f'{mode}: echo verified', flush=True)
                finally:
                    connection.close()
            if capture.wait(timeout=15) != 0:
                raise RuntimeError('Capture failed; see capture.log')
    finally:
        if capture is not None and capture.poll() is None:
            capture.terminate()
            capture.wait(timeout=5)
        for server in servers:
            server.shutdown()
            server.server_close()
    (args.output / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    decrypted_path = args.output / 'http-https-with-keys.pcapng'
    subprocess.run([
        str(args.wireshark_dir / 'editcap.exe'), '--inject-secrets',
        f'tls,{keylog_path}', str(capture_path), str(decrypted_path),
    ], check=True)
    print(f'Capture: {capture_path}\nCapture with TLS keys: {decrypted_path}', flush=True)


if __name__ == '__main__':
    main()
