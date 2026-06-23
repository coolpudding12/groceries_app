import json, os
from flask import Blueprint, request, redirect, session
from db import supabase, load_items, save_items, upload_photo
from utils import current_user
from config import MAX_ITEMS
from routes.auth import require_user

items_bp = Blueprint("items", __name__)


@items_bp.route("/add", methods=["POST"])
def add():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    name = request.form.get("item", "").strip()
    if not name:
        return {"status": "error", "message": "No item name"}, 400
    photo_path = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            photo_path = upload_photo(username, photo)
    items = load_items(username)
    if len(items) >= MAX_ITEMS:
        return {"status": "error", "message": "List is full. Maximum 200 items allowed."}, 400
    new_item = {"name": name, "photo": photo_path}
    items.append(new_item)
    save_items(username, items)
    return {"status": "ok", "item": new_item}, 200


@items_bp.route("/delete/<int:index>")
def delete(index):
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    items = load_items(username)
    if 0 <= index < len(items):
        removed = items.pop(index)
        session["last_deleted"] = {"item": removed, "index": index}
        if removed.get("photo"):
            try:
                supabase.storage.from_("item-photos").remove([removed["photo"]])
            except:
                pass
        save_items(username, items)
    return redirect("/")


@items_bp.route("/dismiss_undo")
def dismiss_undo():
    session.pop("last_deleted", None)
    return "", 204


@items_bp.route("/undo")
def undo():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    last = session.pop("last_deleted", None)
    if last:
        items = load_items(username)
        insert_at = min(last["index"], len(items))
        items.insert(insert_at, last["item"])
        save_items(username, items)
    return redirect("/")


@items_bp.route("/clear", methods=["POST"])
def clear():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    session.pop("last_deleted", None)

    try:
        ticked = json.loads(request.form.get("ticked", "[]"))
    except:
        ticked = []

    items = load_items(username)
    remaining = []
    for item in items:
        if item["name"] in ticked:
            if item.get("photo"):
                try:
                    supabase.storage.from_("item-photos").remove([item["photo"]])
                except:
                    pass
        else:
            remaining.append(item)

    save_items(username, remaining)
    return redirect("/")


@items_bp.route("/update_category", methods=["POST"])
def update_category():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    item_name = request.form.get("item_name")
    new_category = request.form.get("category")
    old_category = request.form.get("old_category")

    items = load_items(username)
    for item in items:
        if item.get("name") == item_name:
            item["category"] = new_category
            break

    save_items(username, items)

    supabase.table("category_overrides").insert({
        "item_name": item_name,
        "old_category": old_category,
        "new_category": new_category,
        "username": username
    }).execute()

    return {"status": "ok"}, 200


@items_bp.route("/toggle/<int:index>", methods=["POST"])
def toggle(index):
    username = current_user()
    categories = load_items(username)

    flat = []
    for cat, items in categories.items():
        for item in items:
            flatlappend((cat, item))

    if 0 <= index < len(flat):
        cat, item = flat[index]
        item["checked"] = not item.get("checked", False)
    new_categories = {}
    for cat, item in flat:
        new_categories.setdefault(cat, []).append(item)

    save_items(username, items)
    return ("", 204)
