import datetime
import socket
import re
import time
import os
import multiprocessing

class HTTPServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        print("Server running at {} on port {}".format(self.host, self.port))
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        processes = []
        while True:
            try:
                sock_obj, ip = self.sock.accept()
            except KeyboardInterrupt:
                break
            
            print("New connection from {}".format(ip[0]))

            # It kept crashing in single process  mode when using the web browser, so that's why I spawn a new process per request now...
            
            process = multiprocessing.Process(target=self.handle, args=(sock_obj,))
            process.start()            
            processes.append(process)

        for process in processes:
            process.terminate()

    def handle(self, sock_obj):
        request_data = ""
        while True:
            next_block = sock_obj.recv(1024).decode()
            request_data += next_block
            if "\r\n\r\n" in next_block:
                break
        
        req =  Request(request_data, sock_obj)
        self.send_response(req)

    def send_response(self, req):

        for header in req.headers:
            print(header + ": " + req.headers[header])

        current_directory = os.getcwd()
        file_path = req.headers['route'].replace("../", "/") # Don't want the LFI now, do we?
        html_file = current_directory + file_path
        if not os.path.isfile(html_file): # If path to HTML file is a folder return index.html file in that folder if it exists.
            html_file += "/index.html"
        html_file = html_file.replace("//", "/")
        headers = {
            "Date":self.get_date(),
            "Content-Type":"text/html"
        }
        
        resp = Response("<h1>404 Page Not Found</h1>", 404, req.sock_obj, headers=headers)
       
        if os.path.exists(html_file):
            if not req.headers.get("If-Modified-Since"):
                with open(html_file, 'r') as html:
                    html_data = html.read()
                    headers['Content-Length'] = str(len(html_data))
                    headers['Last-Modified'] = self.get_date(timestamp=os.path.getmtime(html_file))
                    resp = Response(html_data, 200, req.sock_obj, headers=headers)
            else:
                if_mod_since = self.rfc2822_to_seconds(req.headers.get("If-Modified-Since"))
                modified = time.mktime(time.gmtime(os.path.getmtime(html_file)))
                
                resp = Response("<h1>Not Modified</h1>", 304, req.sock_obj, headers=headers)
                if modified > if_mod_since:
                    with open(html_file, 'r') as html:
                        html_data = html.read()
                        headers['Content-Length'] = str(len(html_data))
                        headers['Last-Modified'] = self.get_date(timestamp=os.path.getmtime(html_file))
                        resp = Response(html_data, 200, req.sock_obj, headers=headers)
        
        resp.send()

    def get_date(self, timestamp=None):
        return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(timestamp) if timestamp else time.gmtime())

    def rfc2822_to_seconds(self, string):
        date = time.mktime(time.strptime(string, "%a, %d %b %Y %H:%M:%S %Z"))
        return date

class Response(object):
    def __init__(self, html, status, sock_obj, headers={}):
        self.headers = headers
        self.status = status
        self.html = html
        self.sock_obj = sock_obj

    def status_message(self):
        messages = {
            200:"OK",
            404:"Not Found",
            304:"Not Modified",
        }
        message = messages.get(self.status)
        return message if message else "Not Sure"
    
    def build_response(self):
        response = "HTTP/1.1 {} {}\r\n".format(self.status, self.status_message())
        for header in self.headers:
            response += "{}: {}\r\n".format(header, self.headers[header])
        response += "\r\n"
        response += self.html
        return response

    def send(self):
        resp = self.build_response()
        self.sock_obj.send(resp.encode())
        self.sock_obj.close()
    
class Request(object):
    def __init__(self, data, sock_obj):
        method_route_version = re.findall("[A-Z]+\s.*?\sHTTP/1.1", data)
        if not method_route_version:
           self.headers = {} 
        method_route_version = method_route_version[0].split()
        method = method_route_version[0]
        route = ' '.join(method_route_version[1:-1])
        version = method_route_version[-1]
        headers = dict(re.findall("(.*?)\: (.*)\r\n", data))
        headers['method'] = method
        headers['route'] = route
        headers['version'] = version
        self.headers = headers
        self.sock_obj = sock_obj

    def __str__(self):
        headers = ""
        for item in self.headers:
            headers += "{}: {}\n".format(item, self.headers[item])
        return headers

if __name__ == "__main__":
    http = HTTPServer("0.0.0.0", 5000)
    http.start()
