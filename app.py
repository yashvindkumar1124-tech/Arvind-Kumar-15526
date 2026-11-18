from flask import Flask, Response, request, jsonify
import requests
from datetime import datetime
from html import escape
import base64
import os

app = Flask(__name__)

# ═══════════════════════════════════════════════════════════════
#   🤖 ADMIN NOTIFICATION CONFIG
#   When a user generates a token, Admin (@YASHBHAIx) will receive a message
#   1. Create a bot via @BotFather → paste token here
#   2. Put your Telegram Chat ID here (get it from @userinfobot)
# ═══════════════════════════════════════════════════════════════
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9190836196:AAFhj0dYbaII3jLJEk1OXfTWNXLYqcKzYmc")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "9024082057")
# ═══════════════════════════════════════════════════════════════

FF_API = "https://aruu-eat.onrender.com/eat"


def decode_nickname(encoded):
    if not encoded:
        return "-"
    try:
        decoded = base64.b64decode(encoded).decode("utf-8", errors="ignore")
        if decoded.strip():
            return decoded
    except Exception:
        pass
    return encoded


def extract_fields(result):
    payload = (result.get("jwt_decoded") or {}).get("payload") or {}

    nickname = "-"
    if payload.get("nickname"):
        nickname = decode_nickname(payload["nickname"])
    elif result.get("nickname"):
        nickname = result["nickname"]

    region = result.get("region") or payload.get("noti_region") or "-"

    uid = "-"
    if result.get("account_uid"):
        uid = str(result["account_uid"])
    elif payload.get("account_id"):
        uid = str(payload["account_id"])
    elif result.get("Uid"):
        uid = str(result["Uid"])

    return nickname, region, uid


def find_nested_value(obj, accepted_keys):
    """Find a non-empty string under known token keys in nested API JSON."""
    if isinstance(obj, dict):
        # Prefer explicit JWT keys before generic token keys.
        for key, value in obj.items():
            if str(key).lower() in accepted_keys and isinstance(value, str) and value.strip():
                return value.strip()
        for value in obj.values():
            found = find_nested_value(value, accepted_keys)
            if found:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_nested_value(value, accepted_keys)
            if found:
                return found
    return ""


def collect_response_keys(obj, prefix="", depth=0):
    """Return safe JSON key paths for diagnostics; never returns token values."""
    keys = []
    if depth > 4:
        return keys
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            keys.append(path)
            if isinstance(value, (dict, list)):
                keys.extend(collect_response_keys(value, path, depth + 1))
    elif isinstance(obj, list):
        for index, value in enumerate(obj[:5]):
            if isinstance(value, (dict, list)):
                keys.extend(collect_response_keys(value, f"{prefix}[{index}]", depth + 1))
    return keys[:100]


def send_to_telegram(nickname, region, uid, access_token, jwt_token):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Telegram bot not configured"
    try:
        DIV = "━━━━━━━━━━━━━━━━━━"

        L = []
        L.append("✨ <b>ＮＧ  ＴＯＫＥＮ  ＧＥＮＥＲＡＴＯＲ</b> ✨")
        L.append(DIV)
        L.append("✅ <b>TOKEN DELIVERY SUCCESS</b>")
        L.append("")
        L.append(f"🎮 <b>Player</b>  ›  <code>{escape(nickname)}</code>")
        L.append(f"🆔 <b>UID</b>  ›  <code>{escape(uid)}</code>")
        L.append(f"🌐 <b>Region</b>  ›  <code>{escape(region)}</code>")
        L.append(DIV)
        L.append("💖 <b>ACCESS TOKEN</b>  <i>(tap to copy)</i>")
        L.append(f"<code>{escape(access_token)}</code>")
        L.append("")

        if jwt_token and jwt_token != "-":
            L.append(DIV)
            L.append("❤️ <b>JWT TOKEN</b>  <i>(tap to copy)</i>")
            if len(jwt_token) > 2000:
                L.append(f"<code>{escape(jwt_token[:2000])}</code>")
                L.append("<i>⚠️ JWT truncated — full token available on website</i>")
            else:
                L.append(f"<code>{escape(jwt_token)}</code>")
            L.append("")

        L.append(DIV)
        L.append(f"⏰ <b>Time</b>  ›  <code>{datetime.now().strftime('%d-%m-%Y  %H:%M:%S')}</code>")
        L.append(DIV)
        L.append("⚡ <b>New Token Notification.! </b>")
        
        text = "\n".join(L)
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        r = requests.post(url, json=payload, timeout=8)
        res = r.json()
        if res.get("ok"):
            return True, "Sent"
        return False, res.get("description", "Unknown Telegram error")
    except Exception as e:
        return False, str(e)


@app.route("/api/generate")
def generate():
    eat_token = request.args.get("eat_token", "").strip()
    if not eat_token:
        return jsonify({"success": False, "error": "Missing eat_token"}), 400
    try:
        # New working API uses ?eat= parameter
        r = requests.get(FF_API, params={"eat": eat_token}, timeout=25)
        try:
            api_result = r.json()
        except Exception:
            return jsonify({"success": False, "error": "Invalid JSON from API", "raw": r.text}), 502
    except Exception as e:
        return jsonify({"success": False, "error": f"API request failed: {e}"}), 502

    # Handle new API response format
    if isinstance(api_result, dict) and api_result.get("success") is False:
        return jsonify({"success": False, "error": api_result.get("error", "Unknown error")}), 200

    # Extract data from new API structure
    data = api_result.get("data") or api_result

    nickname = data.get("nickname") or data.get("account_nickname") or "-"
    region   = data.get("region") or data.get("noti_region") or "-"
    uid      = str(data.get("account_id") or data.get("uid") or data.get("account_uid") or "-")
    access_token = (
        find_nested_value(api_result, {"access_token", "token_access", "accessToken".lower()})
        or data.get("access_token") or data.get("token_access") or "-"
    )
    jwt_token = (
        find_nested_value(api_result, {
            "jwt", "jwt_token", "jwttoken", "token_jwt", "jwt_access_token",
            "authorization_token", "bearer_token"
        })
        or data.get("token") or "-"
    )

    # If the upstream service did not return a JWT, report that explicitly
    # instead of displaying a misleading successful TOKEN READY modal.
    if jwt_token == "-":
        app.logger.warning("Token API returned player details but no JWT field. Response keys: %s",
                           collect_response_keys(api_result))

    # Build response in old format so frontend still works
    result = {
        "success": True,
        "nickname": nickname,
        "region": region,
        "account_uid": uid,
        "token_access": access_token,
        "token": jwt_token,
        "raw": api_result
    }

    tg_ok, tg_msg = send_to_telegram(nickname, region, uid, access_token, jwt_token)
    result["telegram_sent"] = tg_ok
    result["telegram_message"] = tg_msg
    return jsonify(result), 200



@app.route("/api/update_bio", methods=["GET", "POST"])
def update_bio():
    """Update the Free Fire social bio and return actionable diagnostics."""
    # POST keeps access tokens out of URL query strings and routine access logs.
    payload = request.get_json(silent=True) if request.method == "POST" else request.args
    payload = payload or {}
    token = str(payload.get("token", "")).strip()
    bio = str(payload.get("bio", "")).strip()
    if not token:
        return jsonify({"success": False, "error": "Missing token"}), 400
    if not bio:
        return jsonify({"success": False, "error": "Missing bio text"}), 400
    if len(bio) > 250:
        return jsonify({"success": False, "error": "Bio too long (max 250)"}), 400

    try:
        try:
            from Cryptodome.Cipher import AES
            from Cryptodome.Util.Padding import pad
        except ImportError as import_error:
            app.logger.exception("Bio update dependency import failed")
            return jsonify({"success": False, "error": "Server dependency missing: pycryptodomex. Check requirements.txt and redeploy."}), 500

        from google.protobuf.descriptor_pb2 import FileDescriptorProto, FieldDescriptorProto
        from google.protobuf.descriptor_pool import DescriptorPool
        from google.protobuf.message_factory import GetMessageClass

        # Build a complete file descriptor in a private pool. This avoids
        # duplicate symbols and uses the FileDescriptorProto expected by Add().
        file_descriptor = FileDescriptorProto()
        file_descriptor.name = "bio_dynamic_message.proto"
        file_descriptor.package = "bio_dynamic"
        file_descriptor.syntax = "proto2"

        message_descriptor_proto = file_descriptor.message_type.add()
        message_descriptor_proto.name = "DynamicMessage"

        field = message_descriptor_proto.field.add()
        field.name = "field_8"
        field.number = 8
        field.label = FieldDescriptorProto.LABEL_OPTIONAL
        field.type = FieldDescriptorProto.TYPE_STRING

        private_pool = DescriptorPool()
        private_pool.Add(file_descriptor)
        message_descriptor = private_pool.FindMessageTypeByName(
            "bio_dynamic.DynamicMessage"
        )
        message_class = GetMessageClass(message_descriptor)
        message = message_class()
        message.field_8 = bio
        encoded_bio = message.SerializeToString().hex()

        # AES-CBC payload format and key/IV from the supplied Bio Changer script.
        plain_text = bytes.fromhex(f"1011{encoded_bio}5a006200")
        key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
        iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(plain_text, AES.block_size))

        # The supplied Bio Changer flow is configured for the IND endpoint and OB55 client header.
        url = "https://client.ind.freefiremobile.com/UpdateSocialBasicInfo"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB55",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; Redmi Note 5 MIUI/V11.0.3.0.PEIMIXM)",
            "Accept-Encoding": "gzip",
            "Connection": "Keep-Alive",
        }
        response = requests.get(url, data=encrypted_data, headers=headers, timeout=(8, 20))
        if response.status_code == 200:
            return jsonify({"success": True, "message": "Bio updated successfully", "new_bio": bio}), 200

        # Return upstream diagnostics to the page; never include the submitted token.
        upstream_detail = (response.text or "").strip()[:500]
        app.logger.warning("Free Fire bio endpoint returned HTTP %s; response body: %s",
                           response.status_code, upstream_detail or "<empty>")
        return jsonify({
            "success": False,
            "error": f"Free Fire rejected the bio update (HTTP {response.status_code}).",
            "detail": upstream_detail or "The game server returned an empty response.",
            "upstream_status": response.status_code,
        }), 200
    except requests.Timeout:
        app.logger.exception("Free Fire bio update timed out")
        return jsonify({"success": False, "error": "Free Fire server timed out. Please try again later."}), 200
    except requests.RequestException as e:
        app.logger.exception("Free Fire bio network request failed")
        return jsonify({"success": False, "error": "Could not connect to Free Fire server.", "detail": str(e)[:300]}), 200
    except Exception as e:
        app.logger.exception("Free Fire bio update failed")
        return jsonify({"success": False, "error": "Bio update failed inside the server.", "detail": str(e)[:300]}), 200

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"/>
<meta name="theme-color" content="#0a0014"/>
<title>YASH Token Generator</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"/>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
:root{--bg:#07000f;--card:#12081c;--card2:#1a0f28;--p:#a855f7;--p2:#c084fc;--text:#f1e9ff;--muted:#9b8fb0;--border:rgba(168,85,247,.25)}
html,body{height:100%;background:var(--bg);font-family:Inter,system-ui,sans-serif;color:var(--text)}
body{background:radial-gradient(ellipse at 20% 0%,rgba(168,85,247,.18),transparent 50%),var(--bg);min-height:100dvh}
.app{max-width:430px;margin:0 auto;min-height:100dvh;display:flex;flex-direction:column}
.header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;position:sticky;top:0;z-index:50;background:rgba(7,0,15,.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border)}
.logo-wrap{display:flex;align-items:center;gap:10px}
.logo-circle{width:40px;height:40px;border-radius:50%;overflow:hidden;border:2px solid rgba(192,132,252,.45);background:#1a0f28}
.logo-circle img{width:100%;height:100%;object-fit:cover}
.logo-text{font-size:15px;font-weight:800;background:linear-gradient(90deg,#e9d5ff,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.contact-btn{background:#2563eb;color:#fff;border:none;border-radius:10px;padding:8px 12px;font-size:12px;font-weight:600;display:flex;align-items:center;gap:6px;text-decoration:none}
.main{flex:1;padding:14px 14px 100px;overflow-y:auto}
.page{display:none}.page.active{display:block}
.section{font-size:11px;font-weight:700;letter-spacing:1px;color:var(--muted);text-transform:uppercase;margin:16px 0 10px;display:flex;align-items:center;gap:6px}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:14px;margin-bottom:12px}
.providers{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:4px}
.provider{width:46px;height:46px;border-radius:12px;background:var(--card2);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .15s}
.provider:hover{border-color:#c084fc;transform:scale(1.06);background:rgba(168,85,247,.12)}
.provider:active{transform:scale(.96)}
.select,.input,textarea{width:100%;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px 16px;color:var(--text);font-size:14px;margin-bottom:10px}
.select{appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23c084fc' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 14px center}
.input::placeholder,textarea::placeholder{color:#6b5f80}
.input:focus,.select:focus,textarea:focus{outline:none;border-color:var(--p);box-shadow:0 0 0 3px rgba(168,85,247,.15)}
.hint{font-size:11px;color:var(--muted);display:flex;justify-content:space-between;margin:-4px 0 14px;padding:0 2px}
.hint b{color:var(--p2);font-weight:600;cursor:pointer}
.btn{width:100%;padding:15px;border:none;border-radius:14px;background:linear-gradient(135deg,#c084fc,#a855f7,#7c3aed);color:#fff;font-size:14px;font-weight:700;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:8px;box-shadow:0 6px 22px rgba(168,85,247,.35)}
.btn:disabled{opacity:.6}
.fmt{display:flex;gap:8px;margin-bottom:10px}
.fmt button{flex:1;padding:12px;border-radius:12px;border:1px solid var(--border);background:var(--card2);color:#fff;font-weight:700;cursor:pointer}
.preview{background:#0d0518;border:1px solid var(--border);border-radius:12px;padding:14px;min-height:64px;font-size:13px;line-height:1.5;color:#e9d5ff;word-break:break-word}
.tags{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 12px}
.tag{padding:6px 12px;border-radius:20px;border:1px solid rgba(168,85,247,.4);color:var(--p2);font-size:11px;font-weight:600}
.social{display:flex;align-items:center;gap:12px;padding:14px;border-radius:14px;background:var(--card2);border:1px solid var(--border);text-decoration:none;color:var(--text);font-weight:600}
.error{display:none;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.35);border-radius:12px;padding:12px;margin-bottom:12px;font-size:13px;color:#fca5a5}
.bottom{position:fixed;bottom:0;left:0;right:0;max-width:430px;margin:0 auto;background:rgba(12,4,22,.95);backdrop-filter:blur(14px);border-top:1px solid var(--border);display:flex;justify-content:space-around;padding:10px 0 14px;z-index:100}
.nav{display:flex;flex-direction:column;align-items:center;gap:3px;background:none;border:none;color:var(--muted);font-size:10px;font-weight:600;cursor:pointer}
.nav i{font-size:18px}.nav.active{color:var(--p2)}
.nav.active .iw{background:rgba(168,85,247,.2);border-radius:12px;padding:6px 12px}
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);backdrop-filter:blur(8px);z-index:200;display:none;align-items:center;justify-content:center;padding:20px}
.modal-bg.show{display:flex}
.modal{width:100%;max-width:360px;background:#12081c;border-radius:20px;border:1px solid var(--border);padding:20px}
.mt{display:flex;align-items:center;gap:8px;font-size:17px;font-weight:800;margin-bottom:14px}
.ic{background:#1a0f28;border-radius:12px;padding:12px;margin-bottom:14px;border:1px solid rgba(168,85,247,.15)}
.ir{display:flex;justify-content:space-between;padding:5px 0;font-size:13px}
.ir .l{color:var(--muted)}.ir .v{font-weight:700}.g{color:#4ade80}.pu{color:#c084fc}
.tb{background:#0d0518;border:1px dashed rgba(168,85,247,.45);border-radius:12px;padding:12px;font-size:12px;font-family:monospace;color:#e9d5ff;word-break:break-all;margin-bottom:14px;max-height:90px;overflow-y:auto}
.cb{width:100%;padding:13px;border:none;border-radius:12px;background:linear-gradient(135deg,#c084fc,#a855f7);color:#fff;font-weight:700;margin-bottom:8px;cursor:pointer}
.xb{width:100%;padding:12px;border:1px solid var(--border);border-radius:12px;background:transparent;color:var(--muted);font-weight:600;cursor:pointer}
h2{font-size:18px;font-weight:800;margin-bottom:6px}
.desc{font-size:12px;color:var(--muted);line-height:1.55;margin-bottom:10px}
.cc{text-align:right;font-size:11px;color:var(--muted);margin:-6px 0 10px}
.preset{cursor:pointer;font-size:12px;line-height:1.6;margin-bottom:8px}
</style>
</head>
<body>
<div class="app">
<header class="header">
  <div class="logo-wrap">
    <div class="logo-circle"><img src="data:image/jpeg;base64,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" alt="YASH"/></div>
    <div class="logo-text" id="hdr">TOKEN GENERATOR</div>
  </div>
  <a href="https://t.me/YASHBHAIx" target="_blank" class="contact-btn"><i class="fab fa-telegram"></i> Contact</a>
</header>

<main class="main">

<!-- ===== HOME ===== -->
<div class="page" id="p-home">
  <div class="card">
    <div style="font-size:11px;font-weight:700;letter-spacing:1px;color:#9b8fb0;margin-bottom:12px"><i class="fas fa-bolt"></i> MAIN TOOLS</div>
    <button onclick="go('token',document.querySelectorAll('.nav')[1])" style="width:100%;padding:14px;margin-bottom:10px;border:none;border-radius:14px;background:linear-gradient(135deg,#c084fc,#a855f7);color:#fff;font-weight:700;cursor:pointer"><i class="fas fa-key"></i> GET EAT / ACCESS / JWT</button>
    <button onclick="go('bio',document.querySelectorAll('.nav')[2])" style="width:100%;padding:14px;border:1px solid rgba(168,85,247,.4);border-radius:14px;background:transparent;color:#fff;font-weight:700;cursor:pointer"><i class="fas fa-fingerprint"></i> ADD FF LONG BIO</button>
  </div>
  <div class="section"><i class="fas fa-link"></i> CONNECT WITH YASH</div>
  <a class="social" href="https://t.me/YASHBHAIx" target="_blank">
    <i class="fab fa-telegram" style="color:#29b6f6;font-size:22px"></i>
    <span>Telegram — @YASHBHAIx</span>
  </a>
</div>

<!-- ===== TOKEN ===== -->
<div class="page active" id="p-token">
  <div class="error" id="errBox"></div>
  <div class="section"><i class="fas fa-sign-in-alt"></i> SELECT PROVIDER & LOGIN</div>
  <div class="providers">
    <div class="provider" onclick="openProvider('google')" title="Login with Google"><svg width="20" height="20" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg></div>
    <div class="provider" onclick="openProvider('facebook')" title="Login with Facebook"><i class="fab fa-facebook-f" style="color:#1877F2"></i></div>
    <div class="provider" onclick="openProvider('apple')" title="Login with Apple"><i class="fab fa-apple" style="color:#fff"></i></div>
    <div class="provider" onclick="openProvider('twitter')" title="Login with X"><i class="fab fa-x-twitter" style="color:#fff"></i></div>
    <div class="provider" onclick="openProvider('vk')" title="Login with VK"><i class="fab fa-vk" style="color:#0077FF"></i></div>
  </div>
  <div style="font-size:11px;color:#9b8fb0;margin:-2px 0 12px;line-height:1.4">Tap provider → login page khulegi. Login ke baad jo URL aaye usko neeche paste karo.</div>
  <div class="section"><i class="fas fa-exchange-alt"></i> CONVERSION ACTION</div>
  <select class="select" id="convType">
    <option value="eat_to_access">EAT → Access Token</option>
    <option value="eat_to_jwt">EAT → JWT Token (Recommended)</option>
    <option value="access_to_jwt">Access Token → JWT Token</option>
  </select>
  <div class="section"><i class="fas fa-bolt"></i> PASTE TOKEN</div>
  <input class="input" id="tokIn" placeholder="Paste Full URL or Token here..."/>
  <div class="hint"><span>Both URL & Token Accepted</span><b onclick="paste('tokIn')"><i class="fas fa-paste"></i> Paste</b></div>
  <button class="btn" id="genBtn" onclick="genToken()">GENERATE TOKEN <i class="fas fa-arrow-right"></i></button>
</div>

<!-- ===== BIO ===== -->
<div class="page" id="p-bio">
  <h2>Free Fire Long Bio Changer — Add Color Bio Instantly</h2>
  <p class="desc">Change your Free Fire bio to a long, colorful, styled text. Supports color codes, bold, italic, underline. Paste token, type bio, update instantly. Works for all FF regions.</p>
  <div class="tags"><span class="tag">FF LONG BIO</span><span class="tag">BIO COLOR CODES</span><span class="tag">BIO CHANGER</span><span class="tag">LIVE PREVIEW</span><span class="tag">ALL REGIONS</span><span class="tag">FREE • INSTANT</span></div>
  <div class="section"><i class="fas fa-key"></i> TOKEN</div>
  <input class="input" id="bioTok" placeholder="Paste Access / JWT / EAT token..."/>
  <select class="select" id="bioReg">
    <option value="IND">Region: IND</option><option value="BD">Region: BD</option>
    <option value="SG">Region: SG</option><option value="BR">Region: BR</option>
    <option value="US">Region: US</option><option value="ME">Region: ME</option>
  </select>
  <div class="section"><i class="fas fa-magic"></i> FORMATTING</div>
  <div class="fmt">
    <button type="button" onclick="wrap('bioTxt','b')"><b>B</b></button>
    <button type="button" onclick="wrap('bioTxt','i')"><i>I</i></button>
    <button type="button" onclick="wrap('bioTxt','u')"><u>U</u></button>
  </div>
  <select class="select" id="bioCol" onchange="insColor('bioTxt','bioCol')">
    <option value="">COLOR CODES</option>
    <option value="[FF0000]">Red</option><option value="[00FF00]">Green</option>
    <option value="[00BFFF]">Blue</option><option value="[FFFF00]">Yellow</option>
    <option value="[FF00FF]">Pink</option><option value="[FFFFFF]">White</option>
    <option value="[A855F7]">Purple</option>
  </select>
  <div class="section"><i class="fas fa-pen"></i> BIO TEXT</div>
  <textarea class="input" id="bioTxt" rows="4" placeholder="[FFFFFF][b]YOUR NAME" oninput="prev('bioTxt','bioPrev','bioCnt')"></textarea>
  <div class="cc"><span id="bioCnt">0</span>/250</div>
  <div class="section"><i class="fas fa-eye"></i> LIVE PREVIEW</div>
  <div class="preview" id="bioPrev">Type above to preview...</div>
  <div style="height:12px"></div>
  <button class="btn" onclick="updBio('bio')"><i class="fas fa-bolt"></i> UPDATE BIO</button>
</div>

</main>

<nav class="bottom">
  <button class="nav" onclick="go('home',this)"><i class="fas fa-home"></i><span>HOME</span></button>
  <button class="nav active" onclick="go('token',this)"><div class="iw"><i class="fas fa-key"></i></div><span>TOKEN</span></button>
  <button class="nav" onclick="go('bio',this)"><i class="fas fa-fingerprint"></i><span>BIO</span></button>
</nav>
</div>

<div class="modal-bg" id="modal">
  <div class="modal">
    <div class="mt"><i class="fas fa-check-circle" style="color:#22c55e"></i> TOKEN READY</div>
    <div class="ic">
      <div class="ir"><span class="l">Name</span><span class="v g" id="rName">-</span></div>
      <div class="ir"><span class="l">UID</span><span class="v g" id="rUid">-</span></div>
      <div class="ir"><span class="l">Region</span><span class="v pu" id="rReg">-</span></div>
    </div>
    <div style="font-size:12px;font-weight:700;color:var(--p2);margin-bottom:8px"><i class="fas fa-key"></i> <span id="rLab">ACCESS TOKEN</span></div>
    <div class="tb" id="rTok">-</div>
    <button class="cb" id="cBtn" onclick="copyTok()"><i class="fas fa-copy"></i> COPY TOKEN</button>
    <button class="xb" onclick="closeM()"><i class="fas fa-times"></i> CLOSE</button>
  </div>
</div>

<script>
const titles={home:'YASH TOOLS',token:'TOKEN GENERATOR',bio:'LONG BIO'};
function go(name,btn){
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
  document.getElementById('p-'+name).classList.add('active');
  document.querySelectorAll('.nav').forEach(n=>{
    n.classList.remove('active');
    const ic=n.querySelector('i'); const sp=n.querySelector('span');
    if(ic&&sp) n.innerHTML=ic.outerHTML+sp.outerHTML;
  });
  btn.classList.add('active');
  const ic=btn.querySelector('i'); const sp=btn.querySelector('span');
  if(ic&&sp) btn.innerHTML='<div class="iw">'+ic.outerHTML+'</div>'+sp.outerHTML;
  document.getElementById('hdr').innerText=titles[name]||'YASH';
}
async function paste(id){try{document.getElementById(id).value=await navigator.clipboard.readText()}catch(e){}}
function showErr(m){const e=document.getElementById('errBox');e.style.display='block';e.innerHTML='<i class="fas fa-exclamation-circle"></i> '+m}
function hideErr(){document.getElementById('errBox').style.display='none'}
function extractEat(s){const m=s.trim().match(/[?&]eat=([^&]+)/i);return m?m[1]:s.trim()}
let cur='';
async function genToken(){
  hideErr();
  const raw=document.getElementById('tokIn').value.trim();
  if(!raw){showErr('Please paste Eat Token or full URL');return}
  const eat=extractEat(raw);
  const type=document.getElementById('convType').value;
  const btn=document.getElementById('genBtn');
  btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i> GENERATING...';
  try{
    const res=await fetch('/api/generate?eat_token='+encodeURIComponent(eat));
    const data=await res.json();
    if(data.error||data.success===false){showErr(data.error||'Failed');return}
    document.getElementById('rName').innerText=data.nickname||'-';
    document.getElementById('rUid').innerText=data.account_uid||'-';
    document.getElementById('rReg').innerText=data.region||'-';
    if(type==='eat_to_jwt'||type==='access_to_jwt'){
      cur=data.token||'-';
      // Show the original dash placeholder when the upstream service
      // does not return a JWT; do not show the diagnostic error on screen.
      document.getElementById('rLab').innerText='JWT TOKEN';
    }else{
      cur=data.token_access||data.token||'-';
      document.getElementById('rLab').innerText='ACCESS TOKEN';
    }
    document.getElementById('rTok').innerText=cur;
    document.getElementById('modal').classList.add('show');
  }catch(e){showErr('Network error')}
  finally{btn.disabled=false;btn.innerHTML='GENERATE TOKEN <i class="fas fa-arrow-right"></i>'}
}
function copyTok(){if(!cur||cur==='-')return;navigator.clipboard.writeText(cur).then(()=>{const b=document.getElementById('cBtn');b.innerHTML='<i class="fas fa-check"></i> COPIED!';setTimeout(()=>b.innerHTML='<i class="fas fa-copy"></i> COPY TOKEN',1500)})}
function closeM(){document.getElementById('modal').classList.remove('show')}
document.getElementById('modal').onclick=e=>{if(e.target.id==='modal')closeM()};

function openProvider(p){
  // Highlight selected provider
  document.querySelectorAll('.provider').forEach(el=>el.style.borderColor='rgba(168,85,247,.25)');
  if(event && event.currentTarget) event.currentTarget.style.borderColor='#c084fc';

  // Working Garena OAuth links (active Free Fire tools - Nov 2026)
  const base = 'https://auth.garena.com/universal/oauth?response_type=code&locale=en-SG&client_id=100067&redirect_uri=' +
    encodeURIComponent('https://api.ff.garena.co.id/auth/auth/callback_n?site=https://api-discountstore.kiosgamer.gameid.garena.co.id/oauth/callback_redirect/');
  const links = {
    google:   base + '&platform=8',
    facebook: base + '&platform=3',
    apple:    base + '&platform=10',
    twitter:  base + '&platform=11',
    vk:       base + '&platform=5'
  };
  const url = links[p] || links.google;
  window.open(url, '_blank');
  alert('Login page open ho gayi.\n\n1. Apna account se login karo (Google/FB etc)\n2. Login ke baad browser history mein ?eat= wali URL dhoondo\n3. Poori URL copy karke neeche Paste Token box mein daalo\n4. Generate Token dabao');
}

// Wrap selected text in Free Fire rich-text tags. If nothing is selected,
// insert both tags and leave the cursor between them so the user can type.
function wrap(id,tag){
  const t=document.getElementById(id);
  const start=t.selectionStart, end=t.selectionEnd, value=t.value;
  const open='['+tag+']', close='[/'+tag+']';
  const selected=value.slice(start,end);
  const replacement=open+selected+close;
  t.value=value.slice(0,start)+replacement+value.slice(end);
  t.focus();
  if(start===end){
    const cursor=start+open.length;
    t.setSelectionRange(cursor,cursor);
  }else{
    t.setSelectionRange(start+open.length,start+open.length+selected.length);
  }
  prev(id,'bioPrev','bioCnt');
}
function insColor(tid,cid){
  const t=document.getElementById(tid), c=document.getElementById(cid).value;
  if(!c)return;
  const start=t.selectionStart, end=t.selectionEnd, value=t.value;
  t.value=value.slice(0,start)+c+value.slice(start);
  t.focus();
  t.setSelectionRange(start+c.length,end+c.length);
  document.getElementById(cid).value='';
  prev(tid,'bioPrev','bioCnt');
}

// Preview Free Fire rich-text tags without treating user text as HTML.
// A new hex colour closes the previous colour span; [-] resets to default.
function renderFF(text){
  if(!text) return 'Type above to preview...';
  const escaped=text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const tokens=/(\[[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?\]|\[-\]|\[\/?(?:b|i|u)\])/gi;
  let out='', last=0, colorOpen=false;
  let match;
  while((match=tokens.exec(escaped))!==null){
    out+=escaped.slice(last,match.index);
    const code=match[0];
    if(/^\[[0-9a-f]{6}(?:[0-9a-f]{2})?\]$/i.test(code)){
      if(colorOpen) out+='</span>';
      out+='<span style="color:#'+code.slice(1,-1).slice(0,6)+'">';
      colorOpen=true;
    }else if(code==='[-]'){
      if(colorOpen){out+='</span>';colorOpen=false;}
    }else{
      const tag=code.slice(1,-1).replace('/','').toLowerCase();
      out+=(code.charAt(1)==='/'?'</':'<')+tag+'>';
    }
    last=tokens.lastIndex;
  }
  out+=escaped.slice(last);
  if(colorOpen) out+='</span>';
  return out;
}
function prev(tid,pid,cid){
  const v = document.getElementById(tid).value;
  document.getElementById(cid).innerText = v.length;
  document.getElementById(pid).innerHTML = renderFF(v);
}
async function updBio(kind){
  const token=document.getElementById('bioTok').value.trim();
  const bio=document.getElementById('bioTxt').value.trim();
  const region=document.getElementById('bioReg').value;
  if(!token){alert('Please paste your Access Token or JWT');return}
  if(!bio){alert('Please enter bio text');return}
  const btn=event.target;const old=btn.innerHTML;btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin"></i> UPDATING...';
  try{
    const res=await fetch('/api/update_bio',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token,bio,region})
    });
    const data=await res.json();
    alert(data.success?('✅ '+(data.message||'Bio updated!')):('❌ '+(data.error||'Failed')+(data.detail?'\n'+data.detail:'')));
  }catch(e){alert('❌ Network error')}
  finally{btn.disabled=false;btn.innerHTML=old}
}
</script>
</body>
</html>
"""


@app.route('/')
def index():
    return Response(HTML_PAGE, mimetype='text/html')


if __name__ == '__main__':
    print("=" * 60)
    print("  YASH TOKEN — Premium")
    print("  Open: http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
