import time
import socket
from urllib.parse import urlparse
import sys
import re

class Request:
    def __init__(self, url, headers={}):
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        url_obj = urlparse(url)
        self.domain = url_obj.netloc
        if ":" in self.domain:
            self.domain, self.port = self.domain.split(":")
            self.port = int(self.port)
        else:
            self.port = 80
        self.path = url_obj.path
        self.sock = socket.socket()
        self.headers = {
            "Host":self.domain,
        }

        self.headers.update(headers)

    def send(self):
        self.sock.connect((self.domain, self.port))
        request = self.build_request()
        
        print("Request Headers\n")
        print(request.decode())
        
        self.sock.send(request)
        response = ""
        content_length = None
        splitter = "\r\n\r\n"
        while True:
            data = self.sock.recv(1024).decode()
            response += data
            if splitter in data:
                cl = re.findall("Content-Length: ([0-9]+)", data)
                if cl:
                    content_length = int(cl[0])
                else:
                    break
            if not data:
                break 
            if content_length:
                if len(response.split(splitter)[1]) >= content_length:
                    break
        
        splitter_loc = response.find(splitter)
        print("\nResponse Headers\n")
        print(response[:splitter_loc])
        print("\nResponse Body\n")
        print(response[splitter_loc:])

    def build_request(self):
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        for header in self.headers:
            request += "{}: {}\r\n".format(header, self.headers[header])
        return request.encode() + b"\r\n"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 client.py <url>")
    url = sys.argv[1]

    # Regular GET
    timestamp = time.time()
    date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(timestamp) if timestamp else time.gmtime())
    req1 = Request(url)
    req1.send()
    
    # Conditional GET    
    #time.sleep(10)
    #req2 = Request(url, headers={"If-Modified-Since":date})
    #req2.send()
