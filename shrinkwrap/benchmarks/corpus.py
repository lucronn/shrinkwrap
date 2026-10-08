"""
Benchmark Corpus for ShrinkWrap.
Provides synthetic test cases covering text, structured JSON arrays, stack traces, and app documentation.
"""

def generate_benchmark_cases():
    return [
        {
            "name": "text_small",
            "source": "shell",
            "input": "OK - Build succeeded in 1.2s",
        },
        {
            "name": "text_medium",
            "source": "shell",
            "input": "Line " + "\nLine ".join(str(i) for i in range(100)),
        },
        {
            "name": "text_large",
            "source": "shell",
            "input": "Log entry " + "\nLog entry ".join(str(i) for i in range(1500)),
        },
        {
            "name": "json_small",
            "source": "mcp",
            "input": {"status": "ok", "count": 1},
        },
        {
            "name": "json_medium",
            "source": "mcp",
            "input": [{"id": i, "name": f"user_{i}", "email": f"user_{i}@example.com"} for i in range(50)],
        },
        {
            "name": "json_large",
            "source": "mcp",
            "input": [{"id": i, "sku": f"SKU-{i:05d}", "price": 99.99 + i, "description": "High performance dataset component item details", "tags": ["data", "api", "bench"]} for i in range(1000)],
        },
        {
            "name": "error_small",
            "source": "shell",
            "input": "ValueError: invalid literal for int() with base 10: 'abc'",
        },
        {
            "name": "error_large",
            "source": "shell",
            "input": "Traceback (most recent call last):\n" + "\n".join(f'  File "app/module_{i}.py", line {i*10}, in process\n    res = compute_{i}()' for i in range(200)) + "\nRuntimeError: Connection lost",
        },
        {
            "name": "app_large",
            "source": "connected_app",
            "input": {"messages": [{"id": f"msg_{i}", "sender": f"user_{i}", "text": f"This is message text {i} containing information for token testing."} for i in range(200)]},
        }
    ]
