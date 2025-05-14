from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import json
import mimetypes

def find_html_file(root_dir, filename):
    """Find the HTML file in the given directory or its subdirectories."""
    for dirpath, _, filenames in os.walk(root_dir):
        if filename in filenames:
            return os.path.join(dirpath, filename)
    return None

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Check if the path is the log viewer page
        if self.path == "/log":
            file_path = find_html_file(".", "log_show.html")
            if file_path:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                self.send_error(404, "HTML file not found")
        
        # Serve the log.json file
        elif self.path == "/log.json":
            if os.path.exists("log.json"):
                with open("log.json", "r", encoding="utf-8") as file:
                    content = file.read()
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            else:
                # Create a sample JSON file if it doesn't exist
                sample_data = {
                    "/api/users": {
                        "status_code": 401,
                        "error": {
                            "message": "Unauthorized access",
                            "description": "Authentication token is missing or invalid",
                            "cause": "Invalid or expired JWT token"
                        }
                    },
                    "/api/products": {
                        "status_code": 500,
                        "error": {
                            "message": "Internal Server Error",
                            "description": "Database connection failed",
                            "cause": "Connection timeout after 30s"
                        }
                    },
                    "/api/orders/1234": {
                        "status_code": 404,
                        "error": {
                            "message": "Not Found",
                            "description": "The requested resource does not exist",
                            "cause": "Order ID does not match any record"
                        }
                    },
                    "/api/payments": {
                        "status_code": 400,
                        "error": {
                            "message": "Bad Request",
                            "description": "Invalid payment information",
                            "cause": "Missing required fields: amount, currency"
                        }
                    },
                    "/api/inventory/update": {
                        "status_code": 409,
                        "error": {
                            "message": "Conflict",
                            "description": "Resource version conflict",
                            "cause": "Another process has modified this resource"
                        }
                    }
                }
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(sample_data).encode("utf-8"))
        
        # Handle static files (CSS, JS, etc.)
        elif "." in self.path:
            file_path = self.path.strip("/")
            if os.path.exists(file_path):
                # Determine the content type based on file extension
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = "application/octet-stream"
                
                with open(file_path, "rb") as file:
                    content = file.read()
                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        
        # Handle other paths
        else:
            self.send_error(404, "Not Found")

def server():
    server_address = ("0.0.0.0", 8092)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Server running at http://{server_address[0]}:{server_address[1]}")
    print("Access the log viewer at http://localhost:8092/log")
    httpd.serve_forever()

if __name__ == "__main__":
    server()