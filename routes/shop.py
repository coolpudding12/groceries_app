from flask import Blueprint, request, render_template, session
from db import supabase, load_items, load_misc, load_rewards_cards, get_photo_url
from utils import categorise_items, current_display_name, get_flybuys_card_html
from config import CATEGORY_ICONS
from routes.auth import require_user

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/shop")
def shop():
    redir = require_user()
    if redir:
        return redir
    username = session["username"]
    display_name = current_display_name()

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
    flybuys_html = get_flybuys_card_html(cards, active)

    return render_template(
        "shop.html",
        display_name=display_name,
        categories=categories,
        flybuys_html=flybuys_html,
        misc_items=misc_items,
        category_icons=CATEGORY_ICONS,
    )


@shop_bp.route("/save_score", methods=["POST"])
def save_score():
    redir = require_user()
    if redir:
        return redir
    username = session["username"]
    arcade_name = request.form.get("arcade_name", "???").strip().upper()[:8]
    score = int(request.form.get("score"))
    items_count = int(request.form.get("items_count"))
    time_seconds = int(request.form.get("time_seconds"))

    top = supabase.table("leaderboard").select("score").eq("username", username).order("score", desc=True).limit(1).execute()
    current_top_score = top.data[0]["score"] if top.data else 0
    new_high_score = score > current_top_score

    supabase.table("leaderboard").insert({
        "username": username,
        "arcade_name": arcade_name,
        "score": score,
        "items_count": items_count,
        "time_seconds": time_seconds
    }).execute()

    return {"status": "ok", "new_high_score": new_high_score}, 200


@shop_bp.route("/leaderboard")
def get_leaderboard():
    redir = require_user()
    if redir:
        return redir
    username = session["username"]
    result = supabase.table("leaderboard").select("*").eq("username", username).gt("score", 0).order("score", desc=True).limit(5).execute()
    return {"status": "ok", "scores": result.data}, 200
