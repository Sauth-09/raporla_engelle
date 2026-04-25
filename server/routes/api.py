"""
REST API routes for Chrome extension communication.
These endpoints are consumed by the client extensions running on school devices.
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Service references (injected by app factory)
_log_service = None
_blocklist_service = None
_config_service = None


def init_api_services(log_service, blocklist_service, config_service):
    """Inject service dependencies into the API blueprint."""
    global _log_service, _blocklist_service, _config_service
    _log_service = log_service
    _blocklist_service = blocklist_service
    _config_service = config_service


@api_bp.route("/logs", methods=["POST"])
def receive_logs():
    """
    Receive a batch of browsing logs from a client extension.

    Expected JSON body:
    {
        "logs": [
            {
                "url": "https://...",
                "title": "Page Title",
                "video_id": "dQw4w9WgXcQ",  (optional)
                "channel_name": "...",        (optional)
                "channel_id": "UC...",        (optional)
                "hostname": "PC-LAB-01",      (optional)
                "log_type": "page_visit",     (optional)
                "timestamp": 1713600000000    (optional, epoch ms)
            }
        ]
    }
    """
    data = request.get_json(silent=True)
    if not data or "logs" not in data:
        return jsonify({"error": "Missing 'logs' field in request body"}), 400

    logs = data["logs"]
    if not isinstance(logs, list):
        return jsonify({"error": "'logs' must be an array"}), 400

    # Limit batch size to prevent abuse
    max_batch = 500
    if len(logs) > max_batch:
        logs = logs[:max_batch]

    client_ip = request.remote_addr or "unknown"
    logger.info("[LOG] Received %d logs from %s", len(logs), client_ip)

    try:
        count = _log_service.create_batch(logs, client_ip)
        logger.info("[LOG] Stored %d logs from %s", count, client_ip)
        return jsonify({"status": "ok", "received": count}), 201
    except Exception as e:
        logger.error("[LOG] Failed to store logs from %s: %s", client_ip, e)
        return jsonify({"error": f"Failed to store logs: {str(e)}"}), 500


@api_bp.route("/config", methods=["GET"])
def get_config():
    """
    Return the current configuration for the extension.
    Extensions poll this endpoint periodically to get updated settings.

    Response:
    {
        "sync_interval_minutes": 5,
        "kill_switch_enabled": false,
        "block_message": "..."
    }
    """
    client_ip = request.remote_addr or "unknown"
    logger.debug("[CONFIG] Config requested by %s", client_ip)
    try:
        config = _config_service.get_extension_config()
        return jsonify(config), 200
    except Exception as e:
        logger.error("[CONFIG] Error serving config to %s: %s", client_ip, e)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/blocklist", methods=["GET"])
def get_blocklist():
    """
    Return the current blocklist and whitelist for the extension.
    Extensions use this data to filter YouTube content via DOM manipulation.

    Response:
    {
        "blocklist": {
            "keyword": [{"pattern": "...", "is_regex": false}],
            "channel_id": [...],
            ...
        },
        "whitelist": {
            "channel_id": [{"pattern": "..."}],
            ...
        }
    }
    """
    try:
        data = _blocklist_service.get_blocklist_for_extension()
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/heartbeat", methods=["POST"])
def heartbeat():
    """
    Receive a heartbeat ping from a client extension.
    Used to track which devices are currently online.

    Expected JSON body:
    {
        "hostname": "PC-LAB-01"  (optional)
    }
    """
    data = request.get_json(silent=True) or {}
    client_ip = request.remote_addr or "unknown"
    hostname = data.get("hostname", "")
    logger.info("[HEARTBEAT] from %s (%s)", hostname or "no-hostname", client_ip)

    # Store as a special log entry for tracking
    try:
        _log_service.create_batch(
            [
                {
                    "url": f"heartbeat://{client_ip}",
                    "title": f"Heartbeat from {hostname or client_ip}",
                    "hostname": hostname,
                    "log_type": "heartbeat",
                }
            ],
            client_ip,
        )
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error("[HEARTBEAT] Error from %s: %s", client_ip, e)
        return jsonify({"error": str(e)}), 500
