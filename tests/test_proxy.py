import pytest
from shrinkwrap.proxy.stdio_proxy import StdioMCPProxy
from shrinkwrap.proxy.http_proxy import HttpMCPProxy
from shrinkwrap.proxy.config_manager import ConfigManager

def test_stdio_proxy_jsonrpc_compaction():
    proxy = StdioMCPProxy(["echo"])
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": '[{"id": 1, "data": "item1"}, {"id": 2, "data": "item2"}]' * 50
                }
            ]
        }
    }
    processed = proxy.process_jsonrpc(payload)
    text = processed["result"]["content"][0]["text"]
    assert "_shrinkwrap_summary" in text

def test_config_manager_discovery():
    cm = ConfigManager()
    configs = cm.discover_configs()
    assert isinstance(configs, list)
