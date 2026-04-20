from __future__ import annotations

import argparse
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class SpaRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, 'index.html')

        if not os.path.exists(path):
            self.path = '/index.html'

        super().do_GET()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Serve a single-page frontend app.')
    parser.add_argument('--host', default=os.environ.get('SPA_HOST', '0.0.0.0'))
    parser.add_argument('--port', type=int, default=int(os.environ.get('SPA_PORT', '3000')))
    parser.add_argument(
        '--dir',
        default=os.environ.get('SPA_DIR', str(Path(__file__).resolve().parent)),
        help='Directory containing the built frontend assets.',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    web_root = Path(args.dir).resolve()
    os.chdir(web_root)

    handler = partial(SpaRequestHandler, directory=str(web_root))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f'Serving frontend from {web_root} at http://{args.host}:{args.port}')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Stopping frontend server.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()