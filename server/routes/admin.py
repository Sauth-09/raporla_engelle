"""
Admin panel routes for the web-based management interface.
Provides dashboard, log viewing, blocklist/whitelist management, and settings.
"""

from functools import wraps
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.security import check_password_hash, generate_password_hash
import socket

def get_server_connection_info():
    hostname = socket.gethostname()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        try:
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"
    
    return {
        "hostname": hostname,
        "local_ip": local_ip,
        "mdns_url": f"http://{hostname}.local:8000",
        "ip_url": f"http://{local_ip}:8000"
    }

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Service references (injected by app factory)
_log_service = None
_blocklist_service = None
_config_service = None
_maintenance_service = None
_app_config = None


def init_admin_services(log_service, blocklist_service, config_service, maintenance_service, app_config):
    """Inject service dependencies into the admin blueprint."""
    global _log_service, _blocklist_service, _config_service, _maintenance_service, _app_config
    _log_service = log_service
    _blocklist_service = blocklist_service
    _config_service = config_service
    _maintenance_service = maintenance_service
    _app_config = app_config


def login_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated_function


# ── Authentication ────────────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    """Admin login page."""
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # Check if password was changed; if not, compare with default
        password_changed = _config_service.get("admin_password_changed", "false") == "true"

        if password_changed:
            stored_hash = _config_service.get("admin_password_hash", "")
            stored_username = _config_service.get("admin_username", _app_config.DEFAULT_ADMIN_USERNAME)
            if username == stored_username and check_password_hash(stored_hash, password):
                session["admin_logged_in"] = True
                return redirect(url_for("admin.dashboard"))
        else:
            if username == _app_config.DEFAULT_ADMIN_USERNAME and password == _app_config.DEFAULT_ADMIN_PASSWORD:
                session["admin_logged_in"] = True
                flash("Varsayılan şifreyi değiştirmeniz önerilir!", "warning")
                return redirect(url_for("admin.dashboard"))

        flash("Geçersiz kullanıcı adı veya şifre.", "error")

    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    """Admin logout."""
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


# ── Dashboard ─────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    """Render dashboard."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    hostname = request.args.get("hostname")

    stats = _log_service.get_stats()
    top_sites = _log_service.get_top_sites(limit=10, date_from=date_from, date_to=date_to, hostname_prefix=hostname)
    top_videos = _log_service.get_top_videos(limit=10, date_from=date_from, date_to=date_to, hostname_prefix=hostname)
    top_channels = _log_service.get_top_channels(limit=10, date_from=date_from, date_to=date_to, hostname_prefix=hostname)
    active_clients = _log_service.get_active_clients(minutes=30)
    db_stats = _maintenance_service.get_db_stats()
    kill_switch = _config_service.get("kill_switch_enabled", "false") == "true"

    connection_info = get_server_connection_info()

    return render_template(
        "dashboard.html",
        stats=stats,
        top_sites=top_sites,
        top_videos=top_videos,
        top_channels=top_channels,
        active_clients=active_clients,
        db_stats=db_stats,
        kill_switch=kill_switch,
        filters={"date_from": date_from, "date_to": date_to, "hostname": hostname},
        connection_info=connection_info
    )


# ── Logs ──────────────────────────────────────────────────────────────

@admin_bp.route("/logs")
@login_required
def logs():
    """Log listing with filters and pagination."""
    page = request.args.get("page", 1, type=int)
    filters = {
        "search": request.args.get("search", ""),
        "log_type": request.args.get("log_type", ""),
        "client_ip": request.args.get("client_ip", ""),
        "date_from": request.args.get("date_from", ""),
        "date_to": request.args.get("date_to", ""),
    }
    # Remove empty filters
    filters = {k: v for k, v in filters.items() if v}

    pagination = _log_service.get_all(page=page, per_page=50, filters=filters)

    return render_template(
        "logs.html",
        logs=pagination.items,
        pagination=pagination,
        filters=request.args,
    )


@admin_bp.route("/logs/clear", methods=["POST"])
@login_required
def clear_all_logs():
    """Clear all log entries."""
    count = _log_service.delete_all_logs()
    flash(f"Tüm log kayıtları başarıyla silindi ({count} kayıt).", "success")
    return redirect(url_for("admin.logs"))


# ── Blocklist ─────────────────────────────────────────────────────────

@admin_bp.route("/blocklist")
@login_required
def blocklist():
    """Blacklist management page."""
    items = _blocklist_service.get_blocked_items(active_only=False)
    return render_template("blocklist.html", items=items)


@admin_bp.route("/blocklist/add", methods=["POST"])
@login_required
def blocklist_add():
    """Add a new item to the blacklist."""
    pattern = request.form.get("pattern", "").strip()
    block_type = request.form.get("block_type", "keyword")
    is_regex = request.form.get("is_regex") == "on"
    description = request.form.get("description", "").strip()

    if not pattern:
        flash("Engelleme kalıbı boş olamaz.", "error")
        return redirect(url_for("admin.blocklist"))

    _blocklist_service.add_blocked_item(pattern, block_type, is_regex, description or None)
    flash(f"'{pattern}' kara listeye eklendi.", "success")
    return redirect(url_for("admin.blocklist"))


@admin_bp.route("/blocklist/delete/<int:item_id>", methods=["POST"])
@login_required
def blocklist_delete(item_id):
    """Remove an item from the blacklist."""
    if _blocklist_service.remove_blocked_item(item_id):
        flash("Öğe kara listeden silindi.", "success")
    else:
        flash("Öğe bulunamadı.", "error")
    return redirect(url_for("admin.blocklist"))


@admin_bp.route("/blocklist/toggle/<int:item_id>", methods=["POST"])
@login_required
def blocklist_toggle(item_id):
    """Toggle active status of a blocked item."""
    item = _blocklist_service.toggle_blocked_item(item_id)
    if item:
        status = "aktif" if item.is_active else "pasif"
        flash(f"Öğe durumu: {status}.", "success")
    else:
        flash("Öğe bulunamadı.", "error")
    return redirect(url_for("admin.blocklist"))


# ── Whitelist ─────────────────────────────────────────────────────────

@admin_bp.route("/whitelist")
@login_required
def whitelist():
    """Whitelist management page."""
    items = _blocklist_service.get_whitelisted_items(active_only=False)
    return render_template("whitelist.html", items=items)


@admin_bp.route("/whitelist/add", methods=["POST"])
@login_required
def whitelist_add():
    """Add a new item to the whitelist."""
    pattern = request.form.get("pattern", "").strip()
    whitelist_type = request.form.get("whitelist_type", "channel_id")
    description = request.form.get("description", "").strip()

    if not pattern:
        flash("Beyaz liste kalıbı boş olamaz.", "error")
        return redirect(url_for("admin.whitelist"))

    _blocklist_service.add_whitelisted_item(pattern, whitelist_type, description or None)
    flash(f"'{pattern}' beyaz listeye eklendi.", "success")
    return redirect(url_for("admin.whitelist"))


@admin_bp.route("/whitelist/delete/<int:item_id>", methods=["POST"])
@login_required
def whitelist_delete(item_id):
    """Remove an item from the whitelist."""
    if _blocklist_service.remove_whitelisted_item(item_id):
        flash("Öğe beyaz listeden silindi.", "success")
    else:
        flash("Öğe bulunamadı.", "error")
    return redirect(url_for("admin.whitelist"))


@admin_bp.route("/whitelist/toggle/<int:item_id>", methods=["POST"])
@login_required
def whitelist_toggle(item_id):
    """Toggle active status of a whitelisted item."""
    item = _blocklist_service.toggle_whitelisted_item(item_id)
    if item:
        status = "aktif" if item.is_active else "pasif"
        flash(f"Öğe durumu: {status}.", "success")
    else:
        flash("Öğe bulunamadı.", "error")
    return redirect(url_for("admin.whitelist"))


# ── Settings ──────────────────────────────────────────────────────────

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """System settings page."""
    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "update_config":
            sync_interval = request.form.get("sync_interval", "5")
            log_retention = request.form.get("log_retention", "30")
            block_message = request.form.get("block_message", "")

            _config_service.set("sync_interval_minutes", sync_interval)
            _config_service.set("log_retention_days", log_retention)
            _config_service.set("block_message", block_message)
            flash("Ayarlar güncellendi.", "success")

        elif action == "change_password":
            new_username = request.form.get("new_username", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()

            if not new_username or not new_password:
                flash("Kullanıcı adı ve şifre boş olamaz.", "error")
            elif new_password != confirm_password:
                flash("Şifreler eşleşmiyor.", "error")
            elif len(new_password) < 6:
                flash("Şifre en az 6 karakter olmalıdır.", "error")
            else:
                _config_service.set("admin_username", new_username)
                _config_service.set("admin_password_hash", generate_password_hash(new_password))
                _config_service.set("admin_password_changed", "true")
                flash("Yönetici bilgileri güncellendi.", "success")

        elif action == "cleanup_logs":
            count = _maintenance_service.cleanup_old_logs()
            flash(f"{count} eski log kaydı temizlendi.", "success")

        elif action == "toggle_kill_switch":
            current = _config_service.get("kill_switch_enabled", "false")
            new_value = "false" if current == "true" else "true"
            _config_service.set("kill_switch_enabled", new_value)
            status = "AKTİF" if new_value == "true" else "KAPALI"
            flash(f"Kill-Switch: {status}", "success")

        return redirect(url_for("admin.settings"))

    config_entries = _config_service.get_all()
    db_stats = _maintenance_service.get_db_stats()
    kill_switch = _config_service.get("kill_switch_enabled", "false") == "true"

    return render_template(
        "settings.html",
        config_entries=config_entries,
        db_stats=db_stats,
        kill_switch=kill_switch,
        sync_interval=_config_service.get("sync_interval_minutes", "5"),
        log_retention=_config_service.get("log_retention_days", "30"),
        block_message=_config_service.get("block_message", "Bu video kullanılamıyor."),
    )


# ── API-style endpoints for AJAX calls ────────────────────────────────

@admin_bp.route("/api/kill-switch", methods=["POST"])
@login_required
def api_kill_switch():
    """Toggle kill-switch via AJAX."""
    current = _config_service.get("kill_switch_enabled", "false")
    new_value = "false" if current == "true" else "true"
    _config_service.set("kill_switch_enabled", new_value)
    return jsonify({"kill_switch_enabled": new_value == "true"})


@admin_bp.route("/api/block-video", methods=["POST"])
@login_required
def api_block_video():
    """Add a video to the blocklist via AJAX."""
    data = request.get_json()
    video_id = data.get("video_id")
    title = data.get("title", "Dashboard'dan engellendi")

    if not video_id:
        return jsonify({"success": False, "message": "Video ID eksik"}), 400

    # Add to blocklist as video_id type
    _blocklist_service.add_blocked_item(video_id, "video_id", False, f"Hızlı Engel: {title}")
    return jsonify({"success": True, "message": f"{video_id} başarıyla engellendi."})


# ── Clients (Sınıflar / Cihazlar) ────────────────────────────────────

@admin_bp.route("/clients")
@login_required
def clients():
    """List all known client devices/classes."""
    all_clients = _log_service.get_all_clients()
    return render_template("clients.html", clients=all_clients)


@admin_bp.route("/client/<path:hostname>")
@login_required
def client_detail(hostname):
    """Detailed activity view for a specific client device/class."""
    page = request.args.get("page", 1, type=int)
    log_type = request.args.get("log_type", "all")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    # Get activity logs
    pagination = _log_service.get_client_activity(
        hostname=hostname,
        page=page,
        per_page=50,
        log_type=log_type if log_type != "all" else None,
        date_from=date_from or None,
        date_to=date_to or None,
    )

    # Get top content for this client
    top_videos = _log_service.get_client_top_videos(hostname, limit=10)
    top_sites = _log_service.get_client_top_sites(hostname, limit=10)

    return render_template(
        "client_detail.html",
        hostname=hostname,
        logs=pagination.items,
        pagination=pagination,
        top_videos=top_videos,
        top_sites=top_sites,
        filters={"log_type": log_type, "date_from": date_from, "date_to": date_to},
    )


@admin_bp.route("/client/<path:hostname>/clear", methods=["POST"])
@login_required
def clear_client_logs(hostname):
    """Clear logs for a specific client."""
    count = _log_service.delete_client_logs(hostname)
    flash(f"{hostname} cihazına ait {count} log kaydı silindi.", "success")
    return redirect(url_for("admin.client_detail", hostname=hostname))


# ── Video Detail ──────────────────────────────────────────────────────

@admin_bp.route("/video/<video_id>")
@login_required
def video_detail(video_id):
    """Detailed view for a specific YouTube video."""
    detail = _log_service.get_video_detail(video_id)
    if not detail:
        flash("Video bulunamadı.", "error")
        return redirect(url_for("admin.dashboard"))

    return render_template("video_detail.html", video=detail)
