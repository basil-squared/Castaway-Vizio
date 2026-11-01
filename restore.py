#!/usr/bin/env python3

# castaway restore :3
# fixes the tv by pointing the app_id: 1 message back to the local factory ui.
# if the tv is stuck in a boot loop, run this script and it will wait for the api to come online.
# you might need to run this a few times while the tv is booting.

import argparse
import json
import urllib3
import requests
import uuid
import time
import sys
import pychromecast

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- color codes for fancy logging ---
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

def main():
    parser = argparse.ArgumentParser(description="castaway restore")
    parser.add_argument("--tv-ip", required=True, help="IP address of the Vizio TV")
    args = parser.parse_args()

    target = f"https://{args.tv_ip}:7345"
    device_id = str(uuid.uuid4())
    
    print("")
    print(f"{C_BOLD}{C_GREEN}--- castaway restore :3 ---{C_RESET}")
    log_info(f"target: {target}")

    # wait for the api to come on
    log_info("waiting for the tv api to respond (this might take a minute if it's boot looping)...")
    while True:
        try:
            # we just ping the app/current endpoint to see if the api is alive
            r = requests.get(f"{target}/app/current", verify=False, timeout=2)
            if r.status_code == 200:
                log_success("api is online.")
                break
        except Exception:
            pass
        
        print(".", end="", flush=True)
        time.sleep(2)

    # pair with the tv
    log_info("poking the pairing endpoint...")
    pair_body = {"DEVICE_ID": device_id, "DEVICE_NAME": "castaway_restore", "CHALLENGE_TYPE": 1}
    
    try:
        r = requests.put(f"{target}/pairing/start", json=pair_body, verify=False, timeout=5)
        pairing_token = r.json()["ITEM"]["PAIRING_REQ_TOKEN"]
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

    # same process as the exploit
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

    # give it back to the factory UI
    print("")
    log_info("restoring factory UI...")
    restore_url = "http://127.0.0.1:12345/scfs/sctv/main.html"
    restore_body = {"TYPE": "T_APP_V1", "VALUE": {"MESSAGE": restore_url, "APP_ID": "1", "NAME_SPACE": 4}}
    
    for i in range(5):
        try:
            requests.post(exploit_url, headers=headers, json=restore_body, verify=False, timeout=2)
        except Exception:
            pass
        time.sleep(0.2)

    print("")
    log_success("restore complete. your tv should boot normally now. :3")
    print("")

if __name__ == "__main__":
    main()