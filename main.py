# pico_sip_ringer.py
#
# Minimal SIP ringer endpoint for MicroPython on Raspberry Pi Pico W.
# Registers to Asterisk via Digest auth, detects INVITE/CANCEL,
# and drives GPIO15 to indicate ringing.
#
# Configure the values below before use.

import network
import socket
import time
import machine
import hashlib
import random
from blinker import Blinker

# change these bits
SSID = "wifissid"
PASSWORD = "wifipassword"
ASTERISK_IP = "192.168.1.1"
USERNAME = "ringer"
PASSWORD_SIP = "changeme"
# /change these bits

SIP_DOMAIN = ASTERISK_IP
LOCAL_PORT = 5060
REGISTER_INTERVAL = 90

RING_PIN = Blinker(pin=15, freq=6) 
RING_PIN.off()

# The on-board LED is active-high
BOARD_LED = Blinker(pin="LED", freq=6)
BOARD_LED.off()

def md5(s):
    h = hashlib.md5(s.encode())
    return "".join("%02x" % b for b in h.digest())

def parse_headers(msg):
    h = {}
    for line in msg.split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            h[k.strip()] = v.strip()
    return h

def digest_response(user, realm, password, nonce, method, uri):
    ha1 = md5("%s:%s:%s" % (user, realm, password))
    ha2 = md5("%s:%s" % (method, uri))
    return md5("%s:%s:%s" % (ha1, nonce, ha2))

def extract_auth(msg):
    for line in msg.split("\r\n"):
        if line.startswith("WWW-Authenticate:"):
            out = {}
            for part in line.split(",", 20):
                if "=" in part:
                    k, v = part.split("=", 1)
                    out[k.split()[-1]] = v.strip().strip('"')
            return out
    return {}

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    time.sleep(0.2)

LOCAL_IP = wlan.ifconfig()[0]
print("Wifi Connected: %s" % SSID)
print("            IP: %s" % LOCAL_IP)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LOCAL_PORT))
sock.settimeout(0.1)

call_id = "picow-%d" % random.getrandbits(24)
cseq = 1

def send_register(auth=None):
    print("Sent ==> REGISTER")
    global cseq

    uri = "sip:%s" % SIP_DOMAIN

    msg = [
        "REGISTER %s SIP/2.0" % uri,
        "Via: SIP/2.0/UDP %s:%d;branch=z9hG4bK%d" % (LOCAL_IP, LOCAL_PORT, random.getrandbits(24)),
        "From: <sip:%s@%s>;tag=1" % (USERNAME, SIP_DOMAIN),
        "To: <sip:%s@%s>" % (USERNAME, SIP_DOMAIN),
        "Call-ID: %s" % call_id,
        "CSeq: %d REGISTER" % cseq,
        "Contact: <sip:%s@%s:%d>" % (USERNAME, LOCAL_IP, LOCAL_PORT),
        "Expires: 120",
    ]

    if auth:
        msg.append(
            'Authorization: Digest username="%s", realm="%s", nonce="%s", uri="%s", response="%s"'
            % (USERNAME, auth["realm"], auth["nonce"], uri, auth["response"])
        )

    msg.append("Content-Length: 0")
    msg.append("")
    msg.append("")

    sock.sendto("\r\n".join(msg).encode(), (ASTERISK_IP, 5060))
    cseq += 1

def build_response(code, reason, req):
    print("Sent ==> %s %s" % (code, reason))
    h = parse_headers(req)
    to_hdr = h.get("To", "")
    if ";tag=" not in to_hdr:
        to_hdr += ";tag=picow"

    return (
        "SIP/2.0 %d %s\r\n"
        "Via: %s\r\n"
        "From: %s\r\n"
        "To: %s\r\n"
        "Call-ID: %s\r\n"
        "CSeq: %s\r\n"
        "Content-Length: 0\r\n\r\n"
    ) % (
        code, reason,
        h.get("Via", ""),
        h.get("From", ""),
        to_hdr,
        h.get("Call-ID", ""),
        h.get("CSeq", "")
    )

send_register()
next_reg = time.time() + REGISTER_INTERVAL

while True:
    now = time.time()

    if now >= next_reg:
        send_register()
        next_reg = now + REGISTER_INTERVAL

    try:
        data, addr = sock.recvfrom(4096)
        msg = data.decode()

        # Ignore(but dump) any packet that's not from the asterisk we're registered to
        if (addr[0] != ASTERISK_IP):
            print("Error: Received unexpected packet from %s" % addr[0])
            print(msg)
            continue 

        # Parse the headers
        headers = {}
        for line in msg.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()
        
        if msg.startswith("SIP/2.0 401"):
            print("Recv <== 401 Unauthorized")
            auth = extract_auth(msg)
            if "realm" in auth and "nonce" in auth:
                uri = "sip:%s" % SIP_DOMAIN
                auth["response"] = digest_response(
                    USERNAME,
                    auth["realm"],
                    PASSWORD_SIP,
                    auth["nonce"],
                    "REGISTER",
                    uri,
                )
                send_register(auth)

        elif msg.startswith("INVITE "):
            print("Recv <== INVITE")
            # Check this INVITE is for us, by examining the To: header
            # To: <sip:ringer@10.1.2.3:5060>
            if not headers.get("Call-ID", ""):
                print("Error: INVITE didn't contain a Call-ID")
                print(msg)
                continue
            if headers.get("To", "").startswith("<sip:%s@" % USERNAME):
                BOARD_LED.blink() # Blink the board LED
                RING_PIN.blink()  # Blink the offboard LEDs
                sock.sendto(build_response(100, "Trying", msg).encode(), addr)
                sock.sendto(build_response(180, "Ringing", msg).encode(), addr)
            else:
                print("Error: Received unexpected INVITE")
                print(msg)
                continue

        elif msg.startswith("CANCEL "):
            print("Recv <== CANCEL")
            if headers.get("To").startswith("<sip:%s@" % USERNAME):
                BOARD_LED.off()
                RING_PIN.off()
                sock.sendto(build_response(200, "OK", msg).encode(), addr)
            else:
                print("Error: Received unexpected CANCEL")
                print(msg)

        elif msg.startswith("OPTIONS "):
            print("Recv <== OPTIONS")
            sock.sendto(build_response(200, "OK", msg).encode(), addr)

        elif msg.startswith("SIP/2.0 200"):
            print("Recv <== 200 OK")
            
        else:
            print("Recv <== UNKNOWN")
            print(msg)

    except OSError:
        pass
