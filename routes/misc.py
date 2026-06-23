import json
from flask import Blueprint, request, redirect
from db import load_misc, save_misc
from utils import current_user
from routes.auth import require_user

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/misc/add", methods=["POST"])
def misc_add():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    name = request.form.get("misc_item", "").strip()
    if name:
        misc = load_misc(username)
        misc.append(name)
        save_misc(username, misc)
    return {"status": "ok"}, 200


@misc_bp.route("/misc/delete/<int:index>")
def misc_delete(index):
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    items = load_misc(username)
    if 0 <= index < len(items):
        items.pop(index)
        save_misc(username, items)
    return redirect("/")


@misc_bp.route("/misc/clear_selected", methods=["POST"])
def misc_clear_selected():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    items_to_remove = json.loads(request.form.get("items", "[]"))
    misc = load_misc(username)
    misc = [item for item in misc if item not in items_to_remove]
    save_misc(username, misc)
    return {"status": "ok"}, 200
