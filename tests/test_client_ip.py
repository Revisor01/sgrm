"""Login-Begrenzung hinter Reverse Proxies: echte Client-IP über einen laufenden waitress-Server. Aufruf: python -m unittest discover -s tests"""
import http.client
import importlib
import os
import socket
import sys
import tempfile
import threading
import unittest
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def lade_app(trusted_proxies):
    os.environ["SGRM_CONFIG_DIR"] = tempfile.mkdtemp()
    os.environ["SGRM_DATA_DIR"] = tempfile.mkdtemp()
    os.environ["SGRM_ADMIN_PASSWORD"] = "test-passwort"
    os.environ["SGRM_TRUSTED_PROXIES"] = str(trusted_proxies)
    import web_interface
    modul = importlib.reload(web_interface)
    modul.app.config["WTF_CSRF_ENABLED"] = False
    return modul


class Server:
    def __init__(self, modul):
        from waitress import create_server
        port = socket.socket()
        port.bind(("127.0.0.1", 0))
        self.port = port.getsockname()[1]
        port.close()
        self.server = create_server(modul.app, host="127.0.0.1", port=self.port, **modul.waitress_optionen())
        threading.Thread(target=self.server.run, daemon=True).start()

    def login(self, xff=None, passwort="falsch"):
        kopf = {"Content-Type": "application/x-www-form-urlencoded"}
        if xff:
            kopf["X-Forwarded-For"] = xff
        verbindung = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        verbindung.request("POST", "/login", urllib.parse.urlencode({"username": "testname", "password": passwort}), kopf)
        status = verbindung.getresponse().status
        verbindung.close()
        return status

    def schliessen(self):
        self.server.close()


class HinterZweiProxies(unittest.TestCase):
    def setUp(self):
        self.modul = lade_app(2)
        self.server = Server(self.modul)

    def tearDown(self):
        self.server.schliessen()

    def test_erlaubt_echte_client_ip_hinter_proxy(self):
        self.server.login("198.51.100.20, 192.168.128.1")
        self.assertEqual(list(self.modul._failed_logins), ["198.51.100.20"])

    def test_verboten_gefaelschter_kopf_von_aussen(self):
        self.server.login("203.0.113.9, 198.51.100.20, 192.168.128.1")
        self.assertEqual(list(self.modul._failed_logins), ["198.51.100.20"])

    def test_sperre_je_client(self):
        for _ in range(self.modul.LOGIN_MAX_ATTEMPTS):
            self.assertEqual(self.server.login("198.51.100.20, 192.168.128.1"), 200)
        self.assertEqual(self.server.login("198.51.100.20, 192.168.128.1"), 429)
        self.assertEqual(self.server.login("198.51.100.21, 192.168.128.1"), 200)


class OhneProxy(unittest.TestCase):
    def test_verboten_kopf_wird_ohne_proxy_ignoriert(self):
        modul = lade_app(0)
        server = Server(modul)
        try:
            server.login("203.0.113.9")
            self.assertEqual(list(modul._failed_logins), ["127.0.0.1"])
        finally:
            server.schliessen()


if __name__ == "__main__":
    unittest.main()
