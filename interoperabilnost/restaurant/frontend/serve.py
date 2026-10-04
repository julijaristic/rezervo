"""Static server za restoran UI - port 3001."""
import http.server
import os
import urllib.parse

PORT = 3001
DIR = os.path.dirname(os.path.abspath(__file__))


class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        path = urllib.parse.unquote(self.path).split("?")[0]
        if path != "/" and not path.startswith("/css/") and not path.startswith("/js/"):
            self.path = "/index.html"
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == "__main__":
    with http.server.ThreadingHTTPServer(("", PORT), SPAHandler) as httpd:
        print("Restoran UI: http://127.0.0.1:%s/" % PORT)
        httpd.serve_forever()
