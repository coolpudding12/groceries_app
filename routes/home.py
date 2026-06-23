from flask import Blueprint, render_template, session
from db import supabase, load_items, load_misc, get_photo_url
from utils import find_duplicates, current_display_name, decrypt_value
from routes.auth import require_user

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    redir = require_user()
    if redir:
        return redir
    username = session["username"]

    items = load_items(username)
    for item in items:
        if item.get("photo"):
            try:
                item["photo_url"] = get_photo_url(item["photo"])
            except:
                item["photo_url"] = None

    duplicates = find_duplicates(items)
    last_deleted = session.get("last_deleted", None)

    result = supabase.table("users").select("pin, pin_set").eq("username", username).execute()
    user_data = result.data[0] if result.data else {}
    has_pin = bool(user_data.get("pin"))
    pin = decrypt_value(user_data.get("pin", ""))
    pin_display = " · ".join(pin.split("-")) if pin else ""

    misc_items = load_misc(username)
    display_name = current_display_name()

    return render_template(
        "home.html",
        display_name=display_name,
        items=items,
        duplicates=duplicates,
        has_pin=has_pin,
        pin_display=pin_display,
        misc_items=misc_items,
        last_deleted=last_deleted,
    )
