import os, io
from PIL import Image
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

from utils import safe_username, encrypt_value, decrypt_value

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def ensure_user_exists(username, pin=None):
    result = supabase.table("users").select("*").eq("username", username).execute()
    if not result.data:
        supabase.table("users").insert({
            "username": username,
            "items": [],
            "misc": [],
            "pin": encrypt_value(pin) if pin else None,
            "pin_set": bool(pin)
        }).execute()


def check_pin(username, pin):
    result = supabase.table("users").select("pin").eq("username", username).execute()
    if result.data:
        stored = result.data[0].get("pin")
        if stored:
            return decrypt_value(stored) == pin
    return False


def user_exists(username):
    result = supabase.table("users").select("id").eq("username", username).execute()
    return bool(result.data)


def load_items(username):
    result = supabase.table("users").select("items").eq("username", username).execute()
    if result.data:
        return result.data[0].get("items", [])
    return []


def save_items(username, items):
    supabase.table("users").update({"items": items}).eq("username", username).execute()


def load_misc(username):
    result = supabase.table("users").select("misc").eq("username", username).execute()
    if result.data:
        return result.data[0].get("misc", [])
    return []


def save_misc(username, items):
    supabase.table("users").update({"misc": items}).eq("username", username).execute()


def load_rewards_cards(username):
    result = supabase.table("users").select("rewards_cards, active_card").eq("username", username).execute()
    if result.data:
        cards = result.data[0].get("rewards_cards") or []
        active = result.data[0].get("active_card") or 0
        return cards, active
    return [], 0


def save_rewards_cards(username, cards):
    supabase.table("users").update({"rewards_cards": cards}).eq("username", username).execute()


def set_active_card(username, index):
    supabase.table("users").update({"active_card": index}).eq("username", username).execute()


def upload_photo(username, file):
    u = safe_username(username)
    filename = f"{u}/{file.filename}"

    img = Image.open(file)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        filename = f"{u}/{os.path.splitext(file.filename)[0]}.jpg"

    img.thumbnail((800, 800))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", optimize=True, quality=75)
    img_bytes.seek(0)

    supabase.storage.from_("item-photos").upload(
        path=filename,
        file=img_bytes.read(),
        file_options={"content-type": "image/jpeg"}
    )

    return filename


def get_photo_url(path):
    res = supabase.storage.from_("item-photos").create_signed_url(path, 3600)
    return res.get("signedURL")


def data_file(username):
    return f"groceries_{safe_username(username)}.json"


def misc_file(username):
    return f"misc_{safe_username(username)}.json"
