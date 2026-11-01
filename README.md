# Castaway :3
> [!WARNING]
> **TEST THIS ON YOUR OWN TV.**
> This exploit modifies NVRAM and will brick the TV's UI into an infinite boot loop if you reboot without restoring it. I am not responsible if you use this on a hotel TV, a friend's TV, or a target you don't have explicit permission to test. Don't be a script kiddie.
## The most important part (summarrrryyyy)

> [!IMPORTANT]
> **Pending CVE:** Authenticated RCE via Webview Injection / Persistent NVRAM DoS.
> **Target:** Vizio E55-E1 Smart TV
> **Firmware:** 11.0.120.1-1 (Chromium 72.0.3626.121, ARMv7l)



## What does this thing do?
This is a zero-day exploit for the Vizio SmartCast API. It abuses the pairing flow to get an `AUTH_TOKEN`, and then injects a malicious `MESSAGE` URL directly into the main Chromium UI process (`APP_ID: 1`). Because the UI is just a webview, this gives us arbitrary JavaScript execution on the TV's OS. 

And because the TV writes this URL to NVRAM, a simple reboot will permanently brick the UI until you physically factory reset the TV.

## Vizio and the most irritating API to ever hit a consumer product
This wasn't as simple as just sending a POST request. The Vizio API is incredibly stateful. If `APP_ID: 1` is already running, it will silently ignore any new `MESSAGE` payloads. You just get a `{"STATUS": "SUCCESS"}` back while the TV does absolutely nothing.

To get around this, the exploit uses `pychromecast` to force a dummy media load on the `CC1AD845` (Default Media Receiver) app. This steals the focus, crashes the main UI process, and clears the state. The split second the UI dies, we hammer the API with our malicious `MESSAGE` payload so the new UI process boots directly into our page. 

## How does this work, even?
1. Poke `/pairing/start` to get a token, input the 4-digit PIN from the TV screen, and complete `/pairing/pair` to get the `AUTH_TOKEN`.

3. **Kill Switch:** Force the Cast receiver to launch and deactivate the main UI.
4. **RCE / DoS:** Inject our `MESSAGE` URL into `APP_ID: 1` and watch it load our web payload.

## Actually. Doing it!

1. `pip install requests urllib3 pychromecast`

3. Run it:
```bash
python3 castaway.py --tv-ip 192.168.1.10
