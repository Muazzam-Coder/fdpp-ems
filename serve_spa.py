import http.server
import socketserver
import sys
import os
from urllib.parse import unquote

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
WEBROOT = os.path.join(os.getcwd(), "dist")
INDEX = "index.html"

class SPARequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # serve from dist folder
        path = unquote(path.split('?',1)[0])
        full = os.path.join(WEBROOT, path.lstrip("/"))
        return full

    def send_error(self, code, message=None):
        # on 404, serve index.html (SPA fallback)
        if code == 404:
            try:
                f = open(os.path.join(WEBROOT, INDEX), 'rb')
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                fs = os.fstat(f.fileno())
                self.send_header("Content-Length", str(fs.st_size))
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
            except Exception:
                super().send_error(code, message)
        else:
            super().send_error(code, message)

if __name__ == "__main__":
    if not os.path.isdir(WEBROOT):
        print(f"Error: expected dist folder at {WEBROOT}")
        sys.exit(2)
    os.chdir(WEBROOT)
    with socketserver.TCPServer(("", PORT), SPARequestHandler) as httpd:
        print(f"Serving {WEBROOT} at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Stopping server")
