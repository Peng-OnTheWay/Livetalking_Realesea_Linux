import os
import sys
import json
import signal
import subprocess
import socket
import urllib.request
import urllib.error
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file

# 静音 Flask/Werkzeug 的 HTTP 请求日志
logging.getLogger('werkzeug').setLevel(logging.WARNING)

BASE = Path(__file__).resolve().parent.parent
AVATARS = BASE / "code" / "data" / "avatars"
ENV_PYTHON = sys.executable  # auto-detect: uses same Python as the launcher
APP_PY = str(BASE / "code" / "app.py")
PORT = 8010
HIS_ENV = BASE.parent.parent / "Digital_Human_Project" / "his-backend" / ".env"
LOCAL_ENV = BASE / ".env"

app = Flask(__name__)
process = None


def _kill_port(port):
    if not port_in_use(port):
        return
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["netstat", "-ano"], capture_output=True, text=True, timeout=10
            )
            for line in r.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                    break
        except Exception:
            pass
    else:
        try:
            r = subprocess.run(
                ["lsof", "-ti", f":{port}"], capture_output=True, text=True, timeout=10
            )
            for pid in r.stdout.strip().split():
                os.kill(int(pid), signal.SIGTERM)
        except Exception:
            pass


def _get_dashscope_key():
    # 1) 环境变量优先
    key = os.environ.get("DASHSCOPE_API_KEY", "")
    if key:
        return key
    # 2) 启动器目录下的 .env（以及上级目录）
    for env_file in (LOCAL_ENV, BASE / "launcher" / ".env", HIS_ENV):
        try:
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("DASHSCOPE_API_KEY="):
                        return line.strip().split("=", 1)[1]
        except Exception:
            pass
    return ""


def _cleanup():
    global process
    if process is not None and process.poll() is None:
        if sys.platform == "win32":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    _kill_port(PORT)
    process = None


def _sigint_handler(signum, frame):
    _cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, _sigint_handler)


def list_avatars():
    result = []
    if not AVATARS.exists():
        return result
    for d in sorted(AVATARS.iterdir()):
        if d.is_dir() and (d / "coords.pkl").exists():
            preview = None
            full_imgs = d / "full_imgs"
            if full_imgs.exists():
                imgs = sorted(full_imgs.glob("*.png")) + sorted(full_imgs.glob("*.jpg"))
                if imgs:
                    preview = imgs[0].name
            result.append({
                "id": d.name,
                "preview": preview,
            })
    return result


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    global process
    running = process is not None and process.poll() is None
    ready = port_in_use(PORT)  # 8010 端口已监听 = 模型加载完毕，可以连接 WebRTC
    runtime_config = app.config.get("current_runtime_config", {})
    return jsonify({
        "running": running or ready,
        "ready": ready,
        "avatar": runtime_config.get("avatar", app.config.get("current_avatar", "")),
        "tts": runtime_config.get("tts", ""),
        "ref_file": runtime_config.get("ref_file", ""),
        "wav2lip_model": runtime_config.get("wav2lip_model", ""),
        "port": PORT,
    })


@app.route("/api/avatars")
def get_avatars():
    return jsonify(list_avatars())


@app.route("/api/avatar/<avatar_id>/preview")
def preview(avatar_id):
    avatar_path = AVATARS / avatar_id
    full_imgs = avatar_path / "full_imgs"
    if full_imgs.exists():
        imgs = sorted(full_imgs.glob("*.png")) + sorted(full_imgs.glob("*.jpg"))
        if imgs:
            return send_file(str(imgs[0]))
    return "", 404


@app.route("/api/start", methods=["POST"])
def start():
    global process
    if process is not None and process.poll() is None:
        return jsonify({"ok": False, "msg": "服务已在运行"})

    data = request.get_json()
    avatar_id = data.get("avatar_id", "").strip()
    tts_engine = data.get("tts", "edgetts").strip()
    ref_file = data.get("ref_file", "").strip()
    wav2lip_model = data.get("wav2lip_model", "256").strip()
    qwen_tts_model = data.get("qwen_tts_model", "qwen3-tts-flash-realtime").strip()
    if not avatar_id:
        return jsonify({"ok": False, "msg": "请选择形象"})

    avatar_path = AVATARS / avatar_id
    if not (avatar_path / "coords.pkl").exists():
        return jsonify({"ok": False, "msg": f"形象 {avatar_id} 不存在"})

    # kill any zombie process left from a previous crashed/exited launcher
    if port_in_use(PORT):
        _kill_port(PORT)
        import time
        for _ in range(10):
            if not port_in_use(PORT):
                break
            time.sleep(0.5)
        if port_in_use(PORT):
            return jsonify({"ok": False, "msg": f"端口 {PORT} 被占用，请手动结束进程"})

    try:
        env = os.environ.copy()
        key = _get_dashscope_key()
        if key:
            env["DASHSCOPE_API_KEY"] = key
        if not ref_file and tts_engine == "edgetts":
            ref_file = "zh-CN-YunxiaNeural"
        args = [ENV_PYTHON, APP_PY, "--transport", "webrtc", "--model", "wav2lip", "--tts", tts_engine, "--avatar_id", avatar_id, "--wav2lip_model", wav2lip_model, "--qwen_tts_model", qwen_tts_model]
        if ref_file:
            args.extend(["--REF_FILE", ref_file])
            
        popen_kwargs = {
            "cwd": str(BASE / "code"),
            "env": env,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(args, **popen_kwargs)
        app.config["current_avatar"] = avatar_id
        app.config["current_runtime_config"] = {
            "avatar": avatar_id,
            "tts": tts_engine,
            "ref_file": ref_file,
            "wav2lip_model": wav2lip_model,
        }
        return jsonify({"ok": True, "msg": f"已启动 {avatar_id}"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


@app.route("/api/stop", methods=["POST"])
def stop():
    try:
        _cleanup()
        return jsonify({"ok": True, "msg": "已停止"})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)})


def _proxy(url, data, timeout=10):
    if not port_in_use(PORT):
        return {"error": f"LiveTalking core port {PORT} is not ready"}, 503
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code
    except Exception as e:
        return {"error": str(e)}, 502


@app.route("/api/proxy/offer", methods=["POST"])
def proxy_offer():
    data = request.get_json()
    result, status = _proxy(f"http://127.0.0.1:{PORT}/offer", data, timeout=45)
    print(f"[proxy] POST /offer → {status}")
    return jsonify(result), status


@app.route("/api/proxy/human", methods=["POST"])
def proxy_human():
    data = request.get_json()
    result, status = _proxy(f"http://127.0.0.1:{PORT}/human", data)
    return jsonify(result), status


@app.route("/api/proxy/humanaudio", methods=["POST"])
def proxy_humanaudio():
    data = request.get_json()
    result, status = _proxy(f"http://127.0.0.1:{PORT}/humanaudio", data)
    return jsonify(result), status


@app.route("/api/proxy/record", methods=["POST"])
def proxy_record():
    data = request.get_json()
    result, status = _proxy(f"http://127.0.0.1:{PORT}/record", data)
    return jsonify(result), status


if __name__ == "__main__":
    _kill_port(PORT)   # 清理上次残留的 LiveTalking 进程
    _kill_port(8000)   # 清理上次残留的启动器进程
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
