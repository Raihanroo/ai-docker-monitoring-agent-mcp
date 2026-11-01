from http.server import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        body = b"OK - sales-chatbot is running\n"
        self.wfile.write(body)

HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
