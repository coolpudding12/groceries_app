from flask import Blueprint, request, redirect, render_template
from db import load_rewards_cards, save_rewards_cards, set_active_card
from utils import current_user, encrypt_value, generate_barcode_b64
from routes.auth import require_user

rewards_bp = Blueprint("rewards", __name__)


@rewards_bp.route("/flybuys/edit", methods=["GET", "POST"])
def flybuys_edit():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    error = ""

    if request.method == "POST":
        raw = request.form.get("flybuys_number", "")
        number = "".join(c for c in raw if c.isdigit())
        number = encrypt_value(number)
        if number == "0":
            cards, active = load_rewards_cards(username)
            if 0 <= active < len(cards):
                cards.pop(active)
                save_rewards_cards(username, cards)
            return redirect("/shop")
        if len(number) < 8:
            error = "Please enter a valid Rewards Card number (at least 8 digits)."
        else:
            try:
                generate_barcode_b64(number)
                encrypted = encrypt_value(number)
                save_flybuys(username, encrypted)
                cards, active = load_rewards_cards(username)
                if cards:
                    cards[0] = {"name": cards[0].get("name", "Flybuys"), "number": number}
                else:
                    cards = [{"name": "Flybuys", "number": number}]
                save_rewards_cards(username, cards)
                return redirect("/")
            except:
                error = "Could not generate a barcode for that number. Please check and try again."

    current_val = load_flybuys(username) or ""
    return render_template("rewards/flybuys_edit.html", username=username, current_val=current_val, error=error)


@rewards_bp.route("/rewards/edit")
def rewards_edit_redirect():
    return redirect("/rewards/edit/0")


@rewards_bp.route("/rewards/select/<int:index>")
def select_reward_card(index):
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    set_active_card(username, index)
    return redirect("/shop")


@rewards_bp.route("/rewards/add", methods=["GET", "POST"])
def add_reward_card():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    cards, active = load_rewards_cards(username)
    error = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw = request.form.get("number", "")
        number = "".join(c for c in raw if c.isdigit())
        if number == "0":
            cards, active = load_rewards_cards(username)
            if 0 <= active < len(cards):
                cards.pop(active)
            save_rewards_cards(username, cards)
            return redirect("/shop")
        if len(number) < 8:
            error = "Please enter a valid card number (at least 8 digits)."
        else:
            try:
                generate_barcode_b64(number)
                number = encrypt_value(number)
                if name and number:
                    cards.append({"name": name, "number": number})
                    save_rewards_cards(username, cards)
                    set_active_card(username, len(cards) - 1)
                return redirect("/shop")
            except:
                error = "Could not generate a barcode for that number. Please check and try again."
    return render_template("rewards/add.html", error=error)


@rewards_bp.route("/rewards/edit/<int:index>", methods=["GET", "POST"])
def edit_reward_card(index):
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    cards, active = load_rewards_cards(username)
    if index >= len(cards):
        return redirect("/rewards/add")
    error = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        raw = request.form.get("number", "")
        number = "".join(c for c in raw if c.isdigit())
        if number == "0":
            cards.pop(index)
            save_rewards_cards(username, cards)
            return redirect("/shop")
        if len(number) < 8:
            error = "Please enter a valid card number (at least 8 digits)."
        else:
            try:
                generate_barcode_b64(number)
                number = encrypt_value(number)
                cards[index] = {"name": name, "number": number}
                save_rewards_cards(username, cards)
                return redirect("/shop")
            except:
                error = "Could not generate a barcode for that number. Please check and try again."
    card = cards[index]
    from utils import decrypt_value
    decrypted_number = decrypt_value(card.get("number", ""))
    return render_template("rewards/edit.html", card=card, index=index, decrypted_number=decrypted_number, error=error)
