"""
Real-World Benchmark Corpus for ShrinkWrap.
Contains authentic production-like payloads: GitHub API responses, Postgres query results, Slack thread histories, Web Scrapes, and Python stack traces.
"""

def generate_benchmark_cases():
    return [
        {
            "name": "github_pr_payload",
            "source": "mcp",
            "input": {
                "id": 10928374,
                "node_id": "PR_kwDOB2x9cA5A1zXy",
                "number": 142,
                "state": "open",
                "title": "fix(core): resolve memory leak in connection pool event listener",
                "user": {"login": "dev_lead", "id": 48291, "type": "User", "site_admin": False},
                "body": "Fixes #141. Resolves a critical memory leak in the connection pool where event listeners were not properly detached on pool shutdown.",
                "created_at": "2026-10-08T10:15:30Z",
                "updated_at": "2026-10-08T12:00:00Z",
                "labels": [{"name": "bug", "color": "d73a4a"}, {"name": "core", "color": "0075ca"}],
                "assignees": [{"login": "senior_eng", "id": 55102}],
                "requested_reviewers": [{"login": "qa_reviewer", "id": 99120}],
                "commits": 12,
                "additions": 450,
                "deletions": 120,
                "changed_files": 15,
                "files": [
                    {"filename": f"src/connection/pool_{i}.py", "status": "modified", "additions": 30, "deletions": 8, "patch": f"@@ -45,10 +45,12 @@ def release_connection(self):\n- self._listeners.clear()\n+ self._detach_all_listeners()\n+ log.debug('Pool connection {i} released cleanly')"}
                    for i in range(15)
                ],
                "comments": [
                    {"id": 89201 + i, "user": f"reviewer_{i}", "body": f"LGTM! Tested in staging env {i}. Memory footprint remains stable after 10,000 iterations."}
                    for i in range(25)
                ]
            }
        },
        {
            "name": "postgres_query_result",
            "source": "mcp",
            "input": [
                {
                    "transaction_id": f"tx_99827361_{i}",
                    "account_id": f"acc_usr_{i % 50}",
                    "amount": round(14.99 + (i * 3.75), 2),
                    "currency": "USD",
                    "status": "completed",
                    "merchant": "Cloud Hosting Services Inc",
                    "created_at": "2026-10-08T08:30:00.000Z",
                    "metadata": {
                        "ip_address": f"192.168.1.{i % 255}",
                        "device_fingerprint": f"fp_hash_{i * 883}",
                        "risk_score": 0.02
                    }
                }
                for i in range(500)
            ]
        },
        {
            "name": "slack_thread_history",
            "source": "connected_app",
            "input": {
                "ok": True,
                "channel": "C04928174",
                "messages": [
                    {
                        "type": "message",
                        "user": f"U{1000 + i}",
                        "text": f"Update on incident #{i}: Identified high CPU utilization on worker pod {i}. Autoscaling node group from 4 to 8 instances.",
                        "ts": f"172839281{i}.000200",
                        "reactions": [{"name": "eyes", "count": 4}, {"name": "white_check_mark", "count": 2}]
                    }
                    for i in range(150)
                ],
                "has_more": False
            }
        },
        {
            "name": "web_scrape_html_extract",
            "source": "mcp",
            "input": {
                "url": "https://docs.example.org/api/v2/reference",
                "title": "API v2 Complete Endpoint Reference Documentation",
                "headings": [f"Section {i}: API Endpoint Group {i}" for i in range(20)],
                "links": [f"https://docs.example.org/api/v2/ref/{i}" for i in range(100)],
                "paragraphs": [
                    f"Paragraph {i}: The v2 REST API requires Bearer OAuth authentication. All requests must include Content-Type application/json headers. Rate limits are set to 1000 requests per minute per IP address."
                    for i in range(200)
                ]
            }
        },
        {
            "name": "python_real_traceback",
            "source": "shell",
            "input": "Traceback (most recent call last):\n" + "\n".join(
                f'  File "/usr/local/lib/python3.11/site-packages/engine/service_{i}.py", line {i*14+3}, in execute_pipeline\n    result = self._dispatch_handler(step_id={i}, context=ctx)'
                for i in range(100)
            ) + "\nDatabaseConnectionError: Failed to establish TLS handshake with db-cluster.internal:5432 (Connection timed out after 30000ms)"
        }
    ]
