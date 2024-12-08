import json
import logging
import os
import sys
import time

from requests.models import Response
from flask import Flask, request, Request
from flask import jsonify
from hashlib import md5
from flask import send_file
import zipfile
from pathlib import Path

import requests
from flask import stream_with_context
from dotenv import load_dotenv

app = Flask(__name__)

project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

host = os.environ.get("HOST_ORIGINAL", "api.openai.com")
original_url_base = host if host.startswith("http") else f"https://{host}/"

PORT = int(os.environ.get("PORT", "1785"))

archive_path = Path(__file__).parent / "cache.zip"
if not archive_path.exists():
    with zipfile.ZipFile(archive_path, "w") as zf:
        pass

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, stream=sys.stdout)


def calculate_hash(headers: dict[str, str], content: bytes) -> str:
    calculator = md5()
    for key in sorted(headers.keys()):
        calculator.update(key.encode("utf-8"))
        calculator.update(headers[key].encode("utf-8"))
    calculator.update(content)
    return calculator.hexdigest()


@app.route("/", methods=["GET"])
def root():
    return """
        Proxy for llms

        <ul>
            <li> Go  <a href="/cache">here</a> for cache download.
            <li> Go  <a href="/reload">here</a> for .env reload.
        </ul>                         
    """


@app.route("/reload", methods=["GET"])
def reload():
    load_dotenv(dotenv_path=env_path)
    logger.info("Reloading cache")
    return ".env reloaded"


@app.route("/cache", methods=["GET"])
def cache():
    return send_file(archive_path)


@app.route("/version", methods=["GET"])
def version():
    return "0.0.1"


@app.route("/<path:path>", methods=["POST"])
def proxy(path):
    if request.method == "GET":
        return _handle_request(request, method="get")
    elif request.method == "POST":
        return _handle_request(request, method="post")


def _stream_from_response(response: Response, file_name: str):
    chunks = []
    for chunk in response.iter_content():
        chunks.append(chunk.decode("utf-8"))
        yield chunk
    with zipfile.ZipFile(archive_path, "a") as zip_file, zip_file.open(file_name, "w") as file:
        data = _to_cache(chunks, stream=True)
        file.write(json.dumps(data, ensure_ascii=False, indent=4).encode())


def _stream_from_file(data: dict) -> bytes:
    yield from data["content"]


def _from_cache(file_name: str):
    with zipfile.ZipFile(archive_path, "a", compresslevel=9) as archive, archive.open(file_name) as f:
        data = json.loads(f.read().decode())
    if data["stream"]:
        return stream_with_context(_stream_from_file(data))
    else:
        return jsonify(data["content"])


def _response_batch(response: Response, file_name: str):
    content = response.json()

    with zipfile.ZipFile(archive_path, "a") as zip_file, zip_file.open(
            file_name, "w"
    ) as file:
        data = _to_cache(content, stream=False)
        file.write(json.dumps(data, indent=4).encode())
    return jsonify(content)


def _to_cache(content: dict | list, stream: bool) -> dict:
    data = {
        "stream": stream,
        "time": time.time(),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        "content": content,
    }
    print(content)
    return data


def _handle_request(request: Request, method: str):
    root_url = request.root_url
    original_url = original_url_base + request.url[len(root_url):]
    headers = dict(request.headers)
    headers["Host"] = host
    data = request.data if method == "POST" else request.path.encode("utf-8")
    request_hash = calculate_hash(headers=headers, content=data)
    file_name = f"{request_hash}.json"

    if not archive_path.exists():
        logger.info(f"Creating cache archive at {archive_path}")
        with zipfile.ZipFile(archive_path, "w", compresslevel=9):
            namelist = []
    else:
        with zipfile.ZipFile(archive_path, "a", compresslevel=9) as archive:
            namelist = archive.namelist()

    if file_name in namelist:
        logger.info(f"Found in cache {file_name}")
        return _from_cache(file_name)

    else:
        logger.info(f"Not found in cache")
        if method == "post":
            response = requests.post(original_url, data=request.data, headers=headers)
        else:
            response = requests.get(original_url, headers=headers)
        if "text/event-stream" in response.headers.get("Content-Type", ""):
            return stream_with_context(_stream_from_response(response, file_name))
        else:
            return _response_batch(response, file_name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
