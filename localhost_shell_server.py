"""Loopback-only reverse shell listener with harmless automatic smoke tests."""

import argparse
import base64
import json
import logging
import os
import socket
from datetime import datetime, timezone
from pathlib import Path


def run_command(reader, writer, command):
    writer.write(base64.b64encode(command.encode('utf-8')) + b'\n')
    writer.flush()
    response = reader.readline(1024 * 1024)
    if not response:
        raise ConnectionError('PowerShell disconnected before returning a result')
    return base64.b64decode(response.strip(), validate=True).decode('utf-8-sig').strip()


def handle_client(client, address, args):
    client.settimeout(20)
    with client, client.makefile('rb') as reader, client.makefile('wb') as writer:
        greeting = reader.readline(256).decode('ascii').strip()
        if greeting != 'LEONARDO_LOCAL_V1':
            raise ValueError('Unexpected client greeting')
        logging.info('PowerShell connected from %s:%s', *address)
        checks = [
            ('computer', '[Environment]::MachineName', socket.gethostname()),
            ('user', '[Environment]::UserName', os.environ['USERNAME']),
            ('directory', '(Get-Location).Path', None),
            ('echo', "'LEONARDO_OK'", 'LEONARDO_OK'),
            ('process', '(Get-Process -Id $PID).ProcessName', 'powershell'),
        ]
        results = []
        for name, command, expected in checks:
            output = run_command(reader, writer, command)
            passed = bool(output) if expected is None else output.casefold() == expected.casefold()
            results.append({'test': name, 'command': command, 'output': output, 'passed': passed})
            logging.info('%s %s: %s', 'PASS' if passed else 'FAIL', name, output)
        report = {
            'time_utc': datetime.now(timezone.utc).isoformat(),
            'listen_address': '127.0.0.1',
            'port': args.port,
            'peer': list(address),
            'passed': all(result['passed'] for result in results),
            'tests': results,
        }
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if args.interactive:
            client.settimeout(None)
            while True:
                try:
                    command = input('powershell> ')
                except (EOFError, KeyboardInterrupt):
                    break
                if command.strip().lower() == 'exit':
                    break
                if command.strip():
                    print(run_command(reader, writer, command))
        writer.write(b'exit\n')
        writer.flush()
        logging.info('Test session finished; listening for another connection')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4444)
    parser.add_argument('--report', type=Path, default=Path('localhost-shell-report.json'))
    parser.add_argument('--log-file', type=Path)
    parser.add_argument('--interactive', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(filename=args.log_file, level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        server.bind(('127.0.0.1', args.port))
        server.listen(1)
        logging.info('Listening on 127.0.0.1:%s; PID=%s', args.port, os.getpid())
        while True:
            client, address = server.accept()
            try:
                handle_client(client, address, args)
            except Exception:
                client.close()
                logging.exception('Client session failed')


if __name__ == '__main__':
    main()
