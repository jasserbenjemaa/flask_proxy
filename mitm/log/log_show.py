from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

def find_html_file(root_dir, preferred_filename):
    root_path = Path(root_dir)

    # Step 1: Try to find the exact filename
    for path in root_path.rglob(preferred_filename):
        return path

    # Step 2: If not found, return the first .html file
    for path in root_path.rglob("*.html"):
        return path
    return ""
    
file_path=find_html_file(".","log_show.html")
print(f"file path {file_path}")
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/log":
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

if __name__ == "__main__":
    httpd = HTTPServer(("0.0.0.0", 8092), SimpleHandler)
    print("Serving at http://0.0.0.0:8092/log")
    httpd.serve_forever()