"""Small local-only Ollama API adapter. No hosted fallback or automatic generation retry."""
import json
import urllib.error
import urllib.parse
import urllib.request

from . import HOME


def config():
    return json.loads((HOME / "config.json").read_text(encoding="utf-8"))


def request(path, payload=None, timeout=600):
    endpoint = config()["endpoint"]
    parsed = urllib.parse.urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Transcript generation is restricted to a local Ollama server.")
    if payload and (":cloud" in payload.get("model", "") or payload.get("model", "").endswith("-cloud")):
        raise ValueError("Cloud models are disabled for this workflow.")
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(endpoint + path, data=body, headers={"Content-Type": "application/json"})
    try:
        return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout)
    except urllib.error.HTTPError as error:
        detail = error.read(1200).decode(errors="replace")
        raise RuntimeError(f"Local Ollama HTTP {error.code}: {detail}") from None
    except urllib.error.URLError as error:
        raise RuntimeError(f"Local Ollama unavailable at {endpoint}: {error.reason}") from None


def get(path):
    with request(path, timeout=30) as response:
        return json.load(response)


def pull():
    last = {}
    with request("/api/pull", {"model": config()["model"], "stream": True}, timeout=900) as response:
        for line in response:
            event = json.loads(line)
            if event.get("error"):
                raise RuntimeError(event["error"])
            total = event.get("total", 0)
            key = event.get("digest", event.get("status"))
            bucket = int(event.get("completed", 0) / total * 10) if total else -1
            if last.get(key) != bucket:
                print(event.get("status", ""), f"{bucket * 10}%" if total else "", flush=True)
                last[key] = bucket
    return get("/api/tags")


def generate(system, prompt, *, options=None, format=None, partial_path=None):
    cfg = config()
    payload = {"model": cfg["model"], "system": system, "prompt": prompt, "stream": True,
               "think": cfg["think"], "keep_alive": cfg["keep_alive"],
               "options": {**cfg["options"], **(options or {})}}
    if format is not None:
        payload["format"] = format
    parts, final = [], None
    sink = partial_path.open("w", encoding="utf-8") if partial_path else None
    try:
        with request("/api/generate", payload, timeout=900) as response:
            for line in response:
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError(event["error"])
                fragment = event.get("response", "")
                parts.append(fragment)
                if sink and fragment:
                    sink.write(fragment)
                    sink.flush()
                if event.get("done"):
                    final = event
        if final is None:
            raise RuntimeError("Generation disconnected before completion; partial text retained.")
    finally:
        if sink:
            sink.close()
    return "".join(parts).strip(), final


if __name__ == "__main__":
    print(json.dumps(pull(), indent=2))
