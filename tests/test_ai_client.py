import os, sys, tempfile, threading, http.server, json, time, hashlib, logging

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(os.path.dirname(HERE), "backend")
sys.path.insert(0, BACKEND)
# Import test_api first so it establishes the shared DB path/connection.
import test_api  # noqa: F401
os.environ["REFLECTION_API_KEY"] = "super-secret-key-xyz"

import db
import migrate
migrate.run()

from ai.beam import BeamClient, ModelError
from ai.stub import StubClient


def _start_server(handler_cls):
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, port


def test_reasoning_turn1_in_request_turn2():
    state = {"bodies": []}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(n)
            state["bodies"].append(json.loads(body))
            resp = {"choices": [{"message": {"content": "ok", "reasoning_content": "think1"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="k", timeout=5)
    import asyncio

    async def run():
        await client.complete("sys", [{"role": "user", "content": "q1"}], 10, purpose="chat")
        msgs = [{"role": "assistant", "content": "ok", "reasoning_content": "think1"},
                {"role": "user", "content": "q2"}]
        await client.complete("sys", msgs, 10, purpose="chat")

    asyncio.get_event_loop().run_until_complete(run())
    srv.shutdown()
    second = state["bodies"][1]
    am = [m for m in second["messages"] if m.get("role") == "assistant"][0]
    assert am.get("reasoning_content") == "think1"


def test_502_then_200_retries():
    state = {"calls": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            state["calls"] += 1
            if state["calls"] == 1:
                self.send_response(502)
                self.end_headers()
                self.wfile.write(b"bad")
                return
            resp = {"choices": [{"message": {"content": "good", "reasoning_content": None}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="k", timeout=5)
    import asyncio

    async def run():
        return await client.complete("sys", [{"role": "user", "content": "q"}], 10, purpose="chat")

    res = asyncio.get_event_loop().run_until_complete(run())
    srv.shutdown()
    assert res.text == "good"
    assert state["calls"] == 2


def test_looping_then_good_retries():
    state = {"calls": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            state["calls"] += 1
            if state["calls"] == 1:
                txt = "This is a repeated sentence. " * 5
            else:
                txt = "good answer"
            resp = {"choices": [{"message": {"content": txt}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="k", timeout=5)
    import asyncio

    async def run():
        return await client.complete("sys", [{"role": "user", "content": "q"}], 10, purpose="chat")

    res = asyncio.get_event_loop().run_until_complete(run())
    srv.shutdown()
    assert res.text == "good answer"
    assert state["calls"] == 2


def test_two_looping_raises_modelerror():
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            txt = "This is a repeated sentence. " * 5
            resp = {"choices": [{"message": {"content": txt}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="k", timeout=5)
    import asyncio

    async def run():
        await client.complete("sys", [{"role": "user", "content": "q"}], 10, purpose="chat")

    try:
        asyncio.get_event_loop().run_until_complete(run())
    except ModelError:
        pass
    else:
        srv.shutdown()
        raise AssertionError("expected ModelError")
    srv.shutdown()


def test_ai_calls_row_hashes_tokens_nosubstring():
    prompt = "secret prompt content AAA"
    reply = "secret reply content BBB"

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            resp = {"choices": [{"message": {"content": reply}}],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 22, "total_tokens": 33}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="k", timeout=5)
    import asyncio

    async def run():
        return await client.complete("sys", [{"role": "user", "content": prompt}], 10, purpose="chat")

    asyncio.get_event_loop().run_until_complete(run())
    srv.shutdown()
    rows = db.query("SELECT purpose, model, prompt_tokens, completion_tokens, request_sha256, response_sha256, ok FROM ai_calls")
    assert rows, "no ai_calls row"
    row = rows[-1]
    assert row[2] == 11
    assert row[3] == 22
    for h in (row[4], row[5]):
        assert isinstance(h, str) and len(h) == 64
    rowstr = str(rows)
    assert prompt not in rowstr
    assert reply not in rowstr


def test_key_not_in_logs(caplog):
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(n)
            resp = {"choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
            b = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def log_message(self, *a):
            pass

    srv, port = _start_server(H)
    client = BeamClient(base_url=f"http://127.0.0.1:{port}", api_key="super-secret-key-xyz", timeout=5)
    import asyncio

    with caplog.at_level(logging.DEBUG):
        asyncio.get_event_loop().run_until_complete(
            client.complete("sys", [{"role": "user", "content": "q"}], 10, purpose="chat")
        )
    srv.shutdown()
    assert "super-secret-key-xyz" not in caplog.text
