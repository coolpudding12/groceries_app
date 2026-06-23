import os, re, io, base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv
load_dotenv()
import barcode
from barcode.writer import ImageWriter
from flask import session, redirect

from config import CATEGORIES

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")
fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


def encrypt_value(value):
    if not value or not fernet:
        return value
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(value):
    if not value or not fernet:
        return value
    try:
        decrypted = fernet.decrypt(value.encode()).decode()
        print(f"Decrypted value: {decrypted}")
        return decrypted
    except:
        print(f"Decryption failed for: {value[:20]}...")
        return value


def generate_barcode_b64(number):
    Code128 = barcode.get_barcode_class('code128')
    bc = Code128(number, writer=ImageWriter())
    buf = io.BytesIO()
    bc.write(buf, options={
        'module_width': 1.2, 'module_height': 20.0,
        'font_size': 10, 'text_distance': 4,
        'quiet_zone': 6, 'write_text': False,
    })
    return base64.b64encode(buf.getvalue()).decode()


def format_flybuys_display(number):
    digits = "".join(c for c in number if c.isdigit())
    parts = [digits[i:i+4] for i in range(0, len(digits), 4)]
    return " ".join(parts)


def get_flybuys_card_html(cards, active, css_vars=True):
    border = "var(--border)" if css_vars else "#e8e0d4"
    radius = "var(--radius)" if css_vars else "14px"
    muted = "var(--muted)" if css_vars else "#8a8070"

    if not cards:
        return f"""
        <a href="/rewards/add" style="display:block;background:white;border:2px dashed {border};border-radius:{radius};
           padding:16px;margin-bottom:24px;text-align:center;color:{muted};">
          <div style="font-size:24px;margin-bottom:6px;">💳</div>
          <div style="font-family:'Righteous',sans-serif;font-size:15px;">Add Rewards Card</div>
          <div style="font-size:12px;margin-top:4px;">Tap to enter your number</div>
        </a>"""

    if active >= len(cards):
        active = 0

    card = cards[active]
    number = decrypt_value(card.get("number", ""))
    name = card.get("name", "Rewards Card")

    tabs_html = ""
    if len(cards) > 1:
        tabs = ""
        for i, c in enumerate(cards):
            selected = "background:var(--green);color:white;" if i == active else "background:var(--cream);color:var(--text);"
            tabs += f'<a href="/rewards/select/{i}" style="flex:1;padding:8px;text-align:center;border-radius:8px;font-family:\'Righteous\',sans-serif;font-size:13px;{selected}text-decoration:none;">{c["name"]}</a>'
        tabs_html = f'<div style="display:flex;gap:6px;margin-bottom:12px;">{tabs}</div>'

    display = format_flybuys_display(number)
    try:
        barcode_b64 = generate_barcode_b64(number)
        barcode_img = f'<img src="data:image/png;base64,{barcode_b64}" alt="Rewards Card barcode" style="width:100%;max-width:320px;height:66px;object-fit:fill;image-rendering:pixelated;">'
    except:
        barcode_img = '<p style="color:#e05252;font-size:13px;">Could not generate barcode</p>'

    add_link = ""
    if len(cards) < 2:
        add_link = f'<a href="/rewards/add" style="display:inline-block;margin-top:6px;font-size:12px;color:{muted};text-decoration:underline;">+ Add another card</a><br>'

    return f"""
    <div style="background:white;border:2px solid {border};border-radius:{radius};padding:16px;margin-bottom:24px;text-align:center;">
      {tabs_html}
      <div style="font-family:'Righteous',sans-serif;font-size:13px;color:{muted};letter-spacing:1px;margin-bottom:8px;">{name.upper()}</div>
      <a href="/rewards/edit/{active}">{barcode_img}</a>
      <div style="font-size:13px;color:{muted};margin-top:6px;letter-spacing:3px;">{display}</div>
      {add_link}
    </div>"""


def safe_username(username):
    return "".join(c for c in username.lower() if c.isalnum() or c in "-_.").strip()


def categorise_items(items):
    items = [item for item in items if isinstance(item, dict) and "name" in item]
    result = {cat: [] for cat in CATEGORIES}
    result["Other"] = []
    pantry_override = ["tea", "can ", "cans ", " can", " cans", "can of", "cans of", "tin of", "tins of", "loose leaf tea", "soup", "oil", "cream of"]

    for item in items:
        if item.get("category"):
            cat = item["category"]
            if cat in result:
                result[cat].append(item)
            else:
                result["Other"].append(item)
            continue

        name_lower = item["name"].lower()
        if any(kw in name_lower for kw in pantry_override):
            result["Pantry"].append(item)
            continue
        if any(kw in name_lower for kw in CATEGORIES["Frozen"]):
            result["Frozen"].append(item)
            continue
        assigned = False
        for category, keywords in CATEGORIES.items():
            if category == "Frozen":
                continue
            if any(kw in name_lower for kw in keywords):
                result[category].append(item)
                assigned = True
                break
        if not assigned:
            result["Other"].append(item)

    return {cat: itms for cat, itms in result.items() if itms}


def strip_quantity(name):
    return re.sub(r'\s*[xX]?\s*\d+\s*$', '', name).strip()


def find_duplicates(items):
    items = [item for item in items if isinstance(item, dict) and "name" in item]
    duplicates = set()
    names = [strip_quantity(item["name"].lower().strip()) for item in items]
    for i in range(len(names)):
        for j in range(len(names)):
            if i == j:
                continue
            a, b = names[i], names[j]
            if a == b:
                duplicates.add(i)
            elif a in b or b in a:
                shorter = a if len(a) < len(b) else b
                if len(shorter.split()) >= 2 or a == b:
                    duplicates.add(i)
            else:
                words_a = set(a.split()) - {"a", "an", "the", "of", "and", "with", "&"}
                words_b = set(b.split()) - {"a", "an", "the", "of", "and", "with", "&"}
                if len(words_a & words_b) >= 2:
                    duplicates.add(i)
    return duplicates


def current_user():
    return session.get("username", None)


def current_display_name():
    return session.get("display_name") or session.get("username")
