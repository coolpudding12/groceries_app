from flask import Blueprint, render_template, Response, session
from db import load_items, load_misc, load_rewards_cards, get_photo_url
from utils import categorise_items, safe_username, get_flybuys_card_html
from config import CATEGORY_ICONS
from routes.auth import require_user

export_bp = Blueprint("export", __name__)


@export_bp.route("/export")
def export():
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

    categories = categorise_items(items)
    misc_items = load_misc(username)

    cards, active = load_rewards_cards(username)
    flybuys_html = get_flybuys_card_html(cards, active, css_vars=False)

    html = render_template(
        "export.html",
        username=username,
        categories=categories,
        misc_items=misc_items,
        flybuys_html=flybuys_html,
        category_icons=CATEGORY_ICONS,
    )
    headers = {"Content-Disposition": f"attachment; filename={safe_username(username)}-shopping.html"}
    return Response(html, mimetype="text/html", headers=headers)
