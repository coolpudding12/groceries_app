from flask import Blueprint, request, redirect, session, render_template
from db import supabase, ensure_user_exists, check_pin, user_exists
from utils import safe_username, encrypt_value, decrypt_value, current_user

auth_bp = Blueprint("auth", __name__)


def require_user():
    if "username" not in session:
        print("No username in session - redirecting to login")
        return redirect("/login")
    result = supabase.table("users").select("username").eq("username", session["username"]).execute()
    print(f"User check result: {result.data}")
    if not result.data:
        session.clear()
        print("User not found - redirecting to login?deleted=1")
        return redirect("/login?deleted=1")
    return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action")
        raw_username = request.form.get("username", "").strip()
        username = safe_username(raw_username)

        if action == "check_username":
            if not username:
                return {"status": "error", "message": "Please enter a username."}, 200
            elif user_exists(username):
                result = supabase.table("users").select("pin").eq("username", username).execute()
                has_pin = result.data and result.data[0].get("pin")
                if has_pin:
                    return {"status": "has_pin"}, 200
                else:
                    session.permanent = True
                    session["username"] = username
                    session["display_name"] = raw_username
                    return {"status": "login_ok"}, 200
            else:
                return {"status": "new_user"}, 200

        elif action == "verify_pin":
            pin = request.form.get("pin", "")
            if check_pin(username, pin):
                session.permanent = True
                session["username"] = username
                session["display_name"] = raw_username
                return {"status": "login_ok"}, 200
            else:
                return {"status": "wrong_pin"}, 200

        elif action == "create_account":
            pin = request.form.get("pin") or None
            ensure_user_exists(username, pin=pin)
            session.permanent = True
            session["username"] = username
            session["display_name"] = raw_username
            pin_display = ""
            if pin:
                pin_display = " · ".join(pin.split("-"))
            return {
                "status": "created",
                "username": raw_username,
                "pin_display": pin_display,
                "has_pin": bool(pin)
            }, 200

    return render_template("login.html", deleted=bool(request.args.get("deleted")))


@auth_bp.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")


@auth_bp.route("/set_pin", methods=["POST"])
def set_pin():
    redir = require_user()
    if redir:
        return redir
    username = current_user()

    result = supabase.table("users").select("pin, pin_set").eq("username", username).execute()
    user = result.data[0] if result.data else None
    if not user or user.get("pin_set"):
        return {"status": "error", "message": "PIN already set."}, 200

    pin = request.form.get("pin")
    if not pin:
        return {"status": "error", "message": "No PIN provided."}, 200

    encrypted = encrypt_value(pin)
    pin_display = " · ".join(pin.split("-"))
    supabase.table("users").update({
        "pin": encrypted,
        "pin_set": True,
    }).eq("username", username).execute()

    return {"status": "ok", "pin_display": pin_display}, 200


@auth_bp.route("/delete_list", methods=["POST"])
def delete_list():
    redir = require_user()
    if redir:
        return redir
    username = current_user()
    supabase.table("leaderboard").delete().eq("username", username).execute()
    supabase.table("users").delete().eq("username", username).execute()
    return {"status": "ok"}, 200
