from flask import Flask, request, redirect, Response, session
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image
import barcode
from barcode.writer import ImageWriter
import json, os, io, base64
from supabase import create_client, Client
from datetime import timedelta
import hashlib
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = "tacobell"
app.config['MAX_CONTENT_LENGTH'] = 8* 1024 * 1024
MAX_ITEMS = 200
UPLOAD_FOLDER = "static/uploads/"
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(DATA_DIR, exist_ok=True)
app.permanent_session_lifetime = timedelta(days=365)

from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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

def flybuys_file(username):
    return f"rewards_{safe_username(username)}.json"

def load_flybuys(username):
    result = supabase.table("users").select("flybuys").eq("username", username).execute()
    if result.data:
        return result.data[0].get("flybuys", "")
    return ""


def save_flybuys(username, number):
    supabase.table("users").update({"flybuys": number}).eq("username", username).execute()


def format_flybuys_display(number):
    # Format raw digits nicely e.g. 27932023822170 -> 2793 2023 8221 70
    digits = "".join(c for c in number if c.isdigit())
    parts = [digits[i:i+4] for i in range(0, len(digits), 4)]
    return " ".join(parts)

def get_flybuys_card_html(username, css_vars=True):
    """Returns flybuys card HTML, or an 'add card' prompt if not set."""
    number = load_flybuys(username)
    border = "var(--border)" if css_vars else "#e8e0d4"
    radius = "var(--radius)" if css_vars else "14px"
    muted = "var(--muted)" if css_vars else "#8a8070"

    if number:
        display = format_flybuys_display(number)
        try:
            barcode_b64 = generate_barcode_b64(number)
            barcode_img = f'<img src="data:image/png;base64,{barcode_b64}" alt="Rewards Card barcode" style="width:100%;max-width:320px;height:66px;object-fit:fill;image-rendering:pixelated;">'
        except:
            barcode_img = '<p style="color:#e05252;font-size:13px;">Could not generate barcode</p>'
        return f"""
        <div style="background:white;border:2px solid {border};border-radius:{radius};padding:16px;margin-bottom:24px;text-align:center;">
          <div style="font-family:\'Righteous\',sans-serif;font-size:13px;color:{muted};letter-spacing:1px;margin-bottom:8px;">REWARDS</div>
          {barcode_img}
          <div style="font-size:13px;color:{muted};margin-top:6px;letter-spacing:3px;">{display}</div>
          <a href="/flybuys/edit" style="display:inline-block;margin-top:10px;font-size:12px;color:{muted};text-decoration:underline;">Change number</a>
        </div>"""
    else:
        return f"""
        <a href="/flybuys/edit" style="display:block;background:white;border:2px dashed {border};border-radius:{radius};
           padding:16px;margin-bottom:24px;text-align:center;color:{muted};">
          <div style="font-size:24px;margin-bottom:6px;">💳</div>
          <div style="font-family:\'Righteous\',sans-serif;font-size:15px;">Add Rewards Card</div>
          <div style="font-size:12px;margin-top:4px;">Tap to enter your number</div>
        </a>"""

CATEGORY_ICONS = {
    "Fruit & Veg": "🥦",
    "Meat & Fish": "🥩",
    "Dairy & Eggs": "🧀",
    "Bakery": "🍞",
    "Pantry": "🥫",
    "Drinks": "🧃",
    "Snacks": "🍫",
    "Household": "🧹",
    "Frozen": "🧊",
    "Other": "👾",
}

CATEGORIES = {
    "Fruit & Veg": [
        "apple", "banana", "orange", "grape", "strawberry", "blueberry", "raspberry",
        "mango", "pineapple", "watermelon", "melon", "peach", "plum", "pear", "cherry",
        "lemon", "lime", "avocado", "tomato", "tomatoes", "potato", "potatoes", "carrot",
        "carrots", "broccoli", "spinach", "lettuce", "cucumber", "zucchini", "courgette",
        "capsicum", "pepper", "onion", "onions", "garlic", "ginger", "celery", "mushroom",
        "mushrooms", "cabbage", "cauliflower", "corn", "peas", "beans", "asparagus",
        "kale", "silverbeet", "leek", "leeks", "sweet potato", "pumpkin", "beetroot",
        "radish", "fennel", "artichoke", "eggplant", "chilli", "herbs", "parsley",
        "coriander", "basil", "mint", "thyme", "rosemary", "salad", "rocket", "bok choy"
    ],
    "Meat & Fish": [
        "chicken", "beef", "lamb", "pork", "steak", "mince", "sausage", "sausages",
        "bacon", "ham", "turkey", "duck", "salami", "prosciutto", "chorizo", "pepperoni",
        "fish", "salmon", "tuna", "cod", "prawns", "shrimp", "crab", "lobster", "oyster",
        "oysters", "squid", "calamari", "sardines", "anchovies", "deli", "meat", "ribs",
        "wings", "thighs", "breast", "fillet", "schnitzel", "rissoles", "patties"
    ],
    "Dairy & Eggs": [
        "milk", "cheese", "butter", "cream", "yoghurt", "yogurt", "egg", "eggs",
        "sour cream", "cheddar", "mozzarella", "parmesan", "brie", "feta", "ricotta",
        "cottage cheese", "cream cheese", "thickened cream", "whipping cream",
        "custard", "milk alternative", "oat milk", "almond milk",
        "soy milk", "coconut milk", "margarine"
    ],
    "Bakery": [
        "bread", "loaf", "rolls", "bun", "buns", "bagel", "bagels", "croissant",
        "croissants", "muffin", "muffins", "cake", "pastry", "pastries", "donut",
        "donuts", "sourdough", "rye", "wrap", "wraps", "pita", "flatbread", "toast",
        "crumpet", "crumpets", "scone", "scones"
    ],
    "Pantry": [
        "pasta", "potato chips", "rice", "noodles", "flour", "sugar", "salt", "pepper", "oil",
        "olive oil", "vinegar", "soy sauce", "tomato sauce", "ketchup", "mustard",
        "mayonnaise", "honey", "jam", "peanut butter", "nutella", "vegemite",
        "stock", "broth", "soup", "canned", "tinned", "beans", "lentils",
        "chickpeas", "coconut cream", "tomatoes", "tuna", "sardines", "cereal",
        "oats", "granola", "muesli", "crackers", "breadcrumbs", "panko",
        "baking powder", "baking soda", "bicarb", "yeast", "cornflour", "cornstarch",
        "spice", "spices", "cumin", "paprika", "turmeric", "cinnamon", "oregano",
        "curry", "sauce", "gravy", "relish", "chutney", "maple syrup", "molasses",
        "tahini", "hummus", "pesto", "passata", "split peas", "herb", "spice", "gherkins",
    ],
    "Drinks": [
        "water", "juice", "coffee", "tea", "cola", "coke", "pepsi", "lemonade",
        "sparkling", "soda", "energy drink", "beer", "wine", "spirits", "whiskey",
        "vodka", "gin", "rum", "kombucha", "smoothie", "soft drink", "cordial",
        "sports drink", "gatorade", "powerade", "hot chocolate", "milo"
    ],
    "Snacks": [
        "chips", "crisps", "popcorn", "nuts", "almonds", "cashews", "peanuts",
        "trail mix", "chocolate", "lollies", "candy", "biscuits", "cookies",
        "tim tam", "shapes", "rice cakes", "dip", "salsa", "guacamole",
        "pretzels", "jerky", "muesli bar", "protein bar", "granola bar"
    ],
    "Household": [
        "toilet paper", "tissues", "paper towel", "bin bags", "garbage bags",
        "cling wrap", "foil", "baking paper", "glad wrap", "zip lock", "ziplock",
        "detergent", "dishwashing", "dishwasher", "washing powder", "laundry",
        "bleach", "cleaner", "spray", "sponge", "mop", "brush", "cloth",
        "shampoo", "conditioner", "soap", "body wash", "deodorant", "toothpaste",
        "toothbrush", "razor", "sunscreen", "moisturiser", "moisturizer",
        "hand wash", "hand sanitiser", "sanitiser", "nappies", "diapers",
        "tampons", "pads", "cotton balls", "cotton buds", "band aid", "bandaid"
    ],
    "Frozen": [
        "frozen", "ice cream", "gelato", "sorbet", "ice block", "ice blocks",
        "fish fingers", "frozen pizza", "frozen meal", "frozen vegetables",
        "edamame", "frozen berries", "frozen fruit", "frozen yoghurt", "popsicle", "icy pole"
    ],
}

# --- Data helpers (per user) ---

def safe_username(username):
    return "".join(c for c in username.lower() if c.isalnum() or c in "-_.").strip()

def ensure_user_exists(username, pin=None):
    result = supabase.table("users").select("*").eq("username", username).execute()
    if not result.data:
        supabase.table("users").insert({
            "username": username,
            "items": [],
            "misc": [],
            "pin": hashlib.sha256(pin.encode()).hexdigest() if pin else None
        }).execute()

def check_pin(username, pin):
    result = supabase.table("users").select("pin").eq("username", username).execute()
    if not result.data:
        return False
    stored_pin = result.data [0].get("pin")
    if not stored_pin:
        return True
    return stored_pin == hashlib.sha256(pin.encode()).hexdigest()

def user_exists(username):
    result = supabase.table("users").select("id").eq("username", username).execute()
    return bool(result.data)

def data_file(username):
    return f"groceries_{safe_username(username)}.json"

def misc_file(username):
    return f"misc_{safe_username(username)}.json"

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

def upload_photo(username, file):
    u = safe_username(username)
    filename = f"{u}/{file.filename}"

    img = Image.open(file)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        filename = f"{u}/{os.path.splitext(file.filename)[0]}.jpg"

    img.thumbnail((800,800))

    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", optimize=True, quality =75)
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

def get_upload_folder(username):
    folder = os.path.join(UPLOAD_FOLDER, safe_username(username))
    os.makedirs(folder, exist_ok=True)
    return folder

def current_user():
    return session.get("username", None)
    
def current_display_name():
    return session.get("display_name") or session.get("username")
    
def require_user():
    user = current_user()
    if not user:
        return redirect("/login")
    return None

# --- Categorisation ---

def categorise_items(items):
    items = [item for item in items if isinstance(item, dict) and "name" in item]
    result = {cat: [] for cat in CATEGORIES}
    result["Other"] = []
    pantry_override = ["tea", "can ", "cans ", " can", " cans", "can of", "cans of", "tin of", "tins of", "loose leaf tea", "soup", "oil", "cream of"]

    for item in items:
        # If user has manually set a category, respect it
        if item.get("category"):
            cat = item["category"]
            if cat in result:
                result[cat].append(item)
            else:
                result["Other"].append(item)
            continue

        # Otherwise fall through to your existing logic
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
    import re
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
                words_a = set(a.split()) - {"a","an","the","of","and","with","&"}
                words_b = set(b.split()) - {"a","an","the","of","and","with","&"}
                if len(words_a & words_b) >= 2:
                    duplicates.add(i)
    return duplicates

# --- Shared styles ---

BASE_HEAD = """
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#3a7d44">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Aisle Get It!">
<link href="https://fonts.googleapis.com/css2?family=Righteous&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service_worker.js');
  }
</script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --green:   #3a7d44;
    --green2:  #52a85e;
    --orange:  #f07d35;
    --orange2: #fda95a;
    --red:     #e05252;
    --cream:   #fdf8f0;
    --card:    #ffffff;
    --border:  #e8e0d4;
    --text:    #2d2a24;
    --muted:   #8a8070;
    --radius:  14px;
  }
  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--cream);
    background-image:
      radial-gradient(circle at 10% 20%, rgba(58,125,68,0.06) 0%, transparent 50%),
      radial-gradient(circle at 90% 80%, rgba(240,125,53,0.06) 0%, transparent 50%);
    min-height: 100vh;
    color: var(--text);
  }
  .page { max-width: 480px; margin: 0 auto; padding: 24px 18px 60px; }
  h1 { font-family: 'Righteous', sans-serif; font-size: 32px; color: var(--green); display: flex; align-items: center; gap: 10px; }
  a { text-decoration: none; color: inherit; }
  ul { list-style: none; }
  .misc-panel {
    position:fixed;top:0;right:0;height:100%;width:min(320px,90vw);
    background:var(--card);box-shadow:-4px 0 24px rgba(0,0,0,0.12);
    transform:translateX(100%);transition:transform 0.3s ease;
    z-index:200;display:flex;flex-direction:column;
  }
  .misc-panel.open { transform:translateX(0); }
  .misc-overlay { position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:199;display:none; }
  .misc-overlay.open { display:block; }
</style>
"""

# --- Login / landing ---

@app.route("/login", methods=["GET", "POST"])
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
                supabase.table("users").update({"pin_display": pin_display}).eq("username", username).execute()
            return {
                "status": "created",
                "username": raw_username,
                "pin_display": pin_display,
                "has_pin": bool(pin)
            }, 200

    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>Aisle Get It!</title>{BASE_HEAD}
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
</head>
<body>
<div class="page" style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;">
  <h1 style="margin-bottom:8px;">🛒 Aisle Get It!</h1>
  <p id="step-subtitle" style="color:var(--muted);font-size:15px;margin-bottom:15px;">The shareable, simplified shopping list.</p>

  <div style="background:var(--card);border:2px solid var(--border);border-radius:var(--radius);
              padding:24px;width:100%;max-width:360px;box-shadow:0 2px 12px rgba(0,0,0,0.05);">

    <!-- Step 1: Username -->
    <div id="step-username">
      <input type="text" id="username-input" placeholder="Enter your list name..." autofocus
        style="width:100%;padding:12px 14px;font-size:16px;font-family:'DM Sans',sans-serif;
               border:2px solid var(--border);border-radius:10px;background:var(--cream);
               color:var(--text);outline:none;margin-bottom:12px;box-sizing:border-box;"
        onfocus="this.style.borderColor='var(--green)'" onblur="this.style.borderColor='var(--border)'"
        onkeydown="if(event.key==='Enter'){{event.preventDefault();checkUsername();}}">
      <div id="username-error" style="color:var(--red);font-size:14px;margin-bottom:8px;display:none;"></div>
      <button onclick="checkUsername()"
        style="width:100%;padding:13px;font-size:17px;font-family:'Righteous',sans-serif;
               background:var(--green);color:white;border:none;border-radius:12px;cursor:pointer;
               box-shadow:0 4px 12px rgba(58,125,68,0.3);">
        Continue →
      </button>
    </div>

    <!-- Step 2: PIN entry (existing user) -->
    <div id="step-pin" style="display:none;">
      <p style="font-size:15px;font-weight:600;margin-bottom:16px;color:var(--text);text-align:center;">
        Welcome back, <span id="display-name-pin"></span>! Enter your PIN.
      </p>
      <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;">
        <span id="pin-val1" style="font-size:48px;font-weight:700;color:var(--green);
              min-width:48px;text-align:center;">0</span>
        <span style="font-size:48px;font-weight:700;color:var(--muted);">•</span>
        <span id="pin-val2" style="font-size:48px;font-weight:700;color:var(--green);
              min-width:48px;text-align:center;">0</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:16px;">
        <input type="range" min="0" max="20" value="0" id="pin-slider1"
          oninput="updateLoginPin()" style="width:100%;">
        <input type="range" min="0" max="20" value="0" id="pin-slider2"
          oninput="updateLoginPin()" style="width:100%;">
      </div>
      <div id="pin-error" style="color:var(--red);font-size:14px;margin-bottom:8px;display:none;">
        Incorrect PIN. Try again.
      </div>
      <button onclick="verifyPin()"
        style="width:100%;padding:13px;font-size:17px;font-family:'Righteous',sans-serif;
               background:var(--green);color:white;border:none;border-radius:12px;cursor:pointer;
               box-shadow:0 4px 12px rgba(58,125,68,0.3);">
        Continue →
      </button>
    </div>

    <!-- Step 3: New user confirmation -->
    <div id="step-new-user" style="display:none;">
      <p style="font-size:16px;font-weight:400;margin-bottom:4px;text-align:center;color:var(--muted);">
        No list found for <strong id="display-name-new" style="color:var(--green);"></strong>.
      </p>
      <p style="font-size:16px;font-weight:600;margin-bottom:16px;text-align:center;">
        Want to create one?
      </p>

      <!-- Optional PIN -->
      <label style="display:flex;align-items:center;justify-content: center;gap:10px;cursor:pointer;font-size:15px;
                    font-weight:600;margin-bottom:16px;">
        <input type="checkbox" id="pin-toggle" onchange="togglePinSection()"
          style="width:20px;height:12px;accent-color:var(--green);cursor:pointer;">
        Keep your list private, add a PIN
      </label>

      <div id="create-pin-section" style="display:none;margin-bottom:16px;">
        <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;">
          <span id="create-val1" style="font-size:40px;font-weight:700;color:var(--green);
                min-width:40px;text-align:center;">0</span>
          <span style="font-size:40px;font-weight:700;color:var(--muted);">•</span>
          <span id="create-val2" style="font-size:40px;font-weight:700;color:var(--green);
                min-width:40px;text-align:center;">0</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:12px;">
          <input type="range" min="0" max="20" value="0" id="create-slider1"
            oninput="updateCreatePin()" style="width:100%;">
          <input type="range" min="0" max="20" value="0" id="create-slider2"
            oninput="updateCreatePin()" style="width:100%;">
        </div>
        <p style="font-size:12px;color:var(--muted);text-align:center;margin-top:10px;">
          Use the sliders above to set your list's permanent PIN number
        </p>
      </div>

      <div style="display:flex;gap:10px;">
        <button onclick="createAccount()"
          style="flex:1;padding:13px;font-size:16px;font-family:'Righteous',sans-serif;
                 background:var(--green);color:white;border:none;border-radius:12px;cursor:pointer;">
          Yes, create it
        </button>
        <button onclick="resetToStart()"
          style="flex:1;padding:13px;font-size:16px;font-family:'Righteous',sans-serif;
                 background:#f0ece4;color:var(--text);border:none;border-radius:12px;cursor:pointer;">
          Cancel
        </button>
      </div>
    </div>

    <!-- Step 4: Download card -->
    <div id="step-card" style="display:none;text-align:center;">
      <h2 style="margin-bottom:16px;">You're all set! 🎉</h2>
      <div id="login-card" style="background:#fff8f0;border:2px solid #e8d5b0;border-radius:20px;
           padding:28px 32px;text-align:center;font-family:'DM Sans',sans-serif;margin-bottom:16px;">
        <p style="font-size:11px;color:#aaa;margin-bottom:6px;letter-spacing:1px;text-transform:uppercase;">Aisle Get It!</p>
        <p style="font-size:11px;color:#aaa;margin-bottom:12px;">grocerylist.devkeo.com</p>
        <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
        <p style="font-size:12px;color:#aaa;margin-bottom:4px;">LIST NAME</p>
        <p id="card-username" style="font-size:24px;font-weight:700;color:#3a7d44;margin-bottom:12px;"></p>
        <div id="card-pin-section">
          <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
          <p style="font-size:12px;color:#aaa;margin-bottom:4px;">PIN</p>
          <p id="card-pin" style="font-size:28px;font-weight:700;letter-spacing:8px;color:#333;"></p>
        </div>
      </div>
      <p style="color:var(--muted);font-size:13px;margin:0 0 16px;">Share your list card to shop collaboratively.</p>
      <button onclick="downloadCard()"
        style="width:100%;padding:12px;background:var(--green);color:white;border:none;
               border-radius:12px;font-family:'Righteous',sans-serif;font-size:16px;
               cursor:pointer;margin-bottom:10px;">
        Download Card
      </button>
      <a id="goto-list" href="/"
        style="display:block;width:100%;padding:12px;background:#f0ece4;color:var(--text);
               border-radius:12px;font-family:'Righteous',sans-serif;font-size:16px;
               text-decoration:none;box-sizing:border-box;">
        Go to my list →
      </a>
    </div>
  </div>
</div>

<script>
let currentUsername = '';
let currentRaw = '';
let currentPin = '';

const STEP_SUBTITLES = {{
  'step-username': 'Enter your list name to get started.',
  'step-pin':      'Welcome back — enter your PIN',
  'step-new-user': 'Create your new grocery list',
}};

function showStep(stepId) {{
  ['step-username', 'step-pin', 'step-new-user', 'step-card'].forEach(id => {{
    document.getElementById(id).style.display = 'none';
  }});
  document.getElementById(stepId).style.display = 'block';
  document.getElementById('step-subtitle').textContent = STEP_SUBTITLES[stepId];
}}

function checkUsername() {{
  const raw = document.getElementById('username-input').value.trim();
  if (!raw) {{
    showError('username-error', 'Please enter a username.');
    return;
  }}
  const form = new FormData();
  form.append('action', 'check_username');
  form.append('username', raw);
  fetch('/login', {{ method: 'POST', body: form }})
    .then(r => r.json())
    .then(data => {{
      if (data.status === 'error') {{
        showError('username-error', data.message);
      }} else if (data.status === 'has_pin') {{
        currentRaw = raw;
        currentUsername = raw;
        document.getElementById('display-name-pin').textContent = raw;
        showStep('step-pin');
      }} else if (data.status === 'login_ok') {{
        window.location.href = '/';
      }} else if (data.status === 'new_user') {{
        currentRaw = raw;
        document.getElementById('display-name-new').textContent = raw;
        showStep('step-new-user');
      }}
    }});
}}

function verifyPin() {{
  const form = new FormData();
  form.append('action', 'verify_pin');
  form.append('username', currentRaw);
  form.append('pin', document.getElementById('login-pin-value') ? 
    document.getElementById('login-pin-value').value : 
    document.getElementById('pin-slider1').value + '-' + document.getElementById('pin-slider2').value);
  fetch('/login', {{ method: 'POST', body: form }})
    .then(r => r.json())
    .then(data => {{
      if (data.status === 'login_ok') {{
        window.location.href = '/';
      }} else {{
        document.getElementById('pin-error').style.display = 'block';
      }}
    }});
}}

function createAccount() {{
  const usePIN = document.getElementById('pin-toggle').checked;
  const pin = usePIN ? 
    document.getElementById('create-slider1').value + '-' + document.getElementById('create-slider2').value
    : '';
  const form = new FormData();
  form.append('action', 'create_account');
  form.append('username', currentRaw);
  if (usePIN) form.append('pin', pin);
  fetch('/login', {{ method: 'POST', body: form }})
    .then(r => r.json())
    .then(data => {{
      if (data.status === 'created') {{
        document.getElementById('card-username').textContent = data.username;
        if (data.has_pin) {{
          document.getElementById('card-pin').textContent = data.pin_display;
          document.getElementById('card-pin-section').style.display = 'block';
        }} else {{
          document.getElementById('card-pin-section').style.display = 'none';
        }}
        showStep('step-card');
      }}
    }});
}}

function togglePinSection() {{
  const section = document.getElementById('create-pin-section');
  section.style.display = document.getElementById('pin-toggle').checked ? 'block' : 'none';
}}

function updateLoginPin() {{
  const v1 = document.getElementById('pin-slider1').value;
  const v2 = document.getElementById('pin-slider2').value;
  document.getElementById('pin-val1').textContent = v1;
  document.getElementById('pin-val2').textContent = v2;
}}

function updateCreatePin() {{
  const v1 = document.getElementById('create-slider1').value;
  const v2 = document.getElementById('create-slider2').value;
  document.getElementById('create-val1').textContent = v1;
  document.getElementById('create-val2').textContent = v2;
}}

function resetToStart() {{
  document.getElementById('username-input').value = '';
  showStep('step-username');
}}

function showError(id, msg) {{
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.display = 'block';
}}

function downloadCard() {{
  const card = document.getElementById('login-card');
  html2canvas(card, {{ backgroundColor: '#fff8f0', scale: 2 }}).then(canvas => {{
    const link = document.createElement('a');
    link.download = currentRaw + '-grocery-login.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  }});

}}
</script>
</body></html>"""

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/login")

@app.route("/set_pin", methods=["POST"])
def set_pin():
    redir = require_user()
    if redir: return redir
    username = current_user()

    # Check pin_set flag — block if already set
    result = supabase.table("users").select("pin, pin_set").eq("username", username).execute()
    user = result.data[0] if result.data else None
    if not user or user.get("pin_set"):
        return {"status": "error", "message": "PIN already set."}, 200

    pin = request.form.get("pin")
    if not pin:
        return {"status": "error", "message": "No PIN provided."}, 200

    hashed = hashlib.sha256(pin.encode()).hexdigest()  # use whatever hashing function you already use
    pin_display = " · ".join(pin.split("-"))
    supabase.table("users").update({
        "pin": hashed,
        "pin_set": True,
        "pin_display": pin_display
    }).eq("username", username).execute()

    return {"status": "ok", "pin_display": pin_display}, 200

@app.route("/flybuys/edit", methods=["GET", "POST"])
def flybuys_edit():
    redir = require_user()
    if redir: 
        return redir
    username = current_user()
    error = ""

    if request.method == "POST":
        raw = request.form.get("flybuys_number","")
        number = "".join(c for c in raw if c.isdigit())
        if number == "0":
            save_flybuys(username, "")
            return redirect("/")
        if len(number) < 8:
            error = "Please enter a valid Rewards Card number (at least 8 digits) or type 0 to clear."
        else:
            try:
                generate_barcode_b64(number)  # validate it works
                save_flybuys(username, number)
                return redirect("/")
            except:
                error = "Could not generate a barcode for that number. Please check and try again."

    current_val = load_flybuys(username) or ""
    error_html = (
        f'<p style="color:var(--red);font-size:14px;margin-top:8px;">{error}</p>' if error else ""
        if error else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>Rewards — {username}</title>{BASE_HEAD}</head>
<body>
<div class="page" style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:80vh;">
  <h1 style="margin-bottom:8px;">💳 Rewards </h1>
  <p style="color:var(--muted);font-size:15px;margin-bottom:32px;">Enter your Rewards card number</p>

  <div style="background:var(--card);border:2px solid var(--border);border-radius:var(--radius);
              padding:24px;width:100%;max-width:360px;box-shadow:0 2px 12px rgba(0,0,0,0.05);">
    <form method="post">
      <input type="text" name="flybuys_number" placeholder="e.g. 2793 2023 8221 70"
        value="{current_val}"
        style="width:100%;padding:12px 14px;font-size:16px;font-family:'DM Sans',sans-serif;
               border:2px solid var(--border);border-radius:10px;background:var(--cream);
               color:var(--text);outline:none;margin-bottom:4px;letter-spacing:2px;"
        onfocus="this.style.borderColor='var(--green)'" onblur="this.style.borderColor='var(--border)'">
      <p style="font-size:12px;color:var(--muted);margin-bottom:12px;">Spaces and dashes are fine — just type the number on your card or type 0 to clear.</p>
      {error_html}
      <button type="submit"
        style="width:100%;padding:13px;font-size:17px;font-family:'Righteous',sans-serif;
               background:var(--green);color:white;border:none;border-radius:12px;cursor:pointer;
               box-shadow:0 4px 12px rgba(58,125,68,0.3);margin-top:8px;">
        Save card
      </button>
    </form>
  </div>

  <a href="/" style="margin-top:20px;color:var(--muted);font-size:15px;">← Back</a>
</div>
</body></html>"""

# --- Home ---

@app.route("/")
def home():
    redir = require_user()
    if redir: return redir
    username = current_user()

    items = load_items(username)
    duplicates = find_duplicates(items)
    last_deleted = session.get("last_deleted", None)
    result = supabase.table("users").select("pin, pin_display").eq("username", username).execute()
    user_data = result.data[0] if result.data else {}
    has_pin = bool(user_data.get("pin"))
    pin_display = user_data.get("pin_display") or ""

    list_html = ""
    for i, item in enumerate(items):
        img_html = ""
        if item.get("photo"):
            url = get_photo_url(item["photo"])
            img_html = f'<img src="{url}" style="width:52px;height:52px;object-fit:cover;border-radius:10px;margin-right:12px;flex-shrink:0;">'
        dupe_badge = ""
        dupe_border = ""
        if i in duplicates:
            dupe_border = "border-color:#f9a825;background:#fffdf0;"
            dupe_badge = '<span style="font-size:11px;font-weight:700;background:#fff3cd;color:#b45309;padding:2px 8px;border-radius:20px;margin-left:8px;white-space:nowrap;">⚠ duplicate?</span>'
        item_id = item.get("id", i)
        item_name = item["name"]
        item_category = item.get("category", "Other")
        list_html += f"""
        <li id="item-{i}" data-id="{item_id}" data-name="{item_name}" data-category="{item_category}"
            style="background:var(--card);border:2px solid var(--border);border-radius:var(--radius);
                   padding:12px 14px;margin-bottom:10px;display:flex;align-items:center;
                   box-shadow:0 2px 8px rgba(0,0,0,0.04);{dupe_border}">
          {img_html}
          <span style="flex:1;font-size:17px;font-weight:600;">{item_name}{dupe_badge}</span>
          <a href="/delete/{i}" style="color:var(--red);font-size:22px;line-height:1;margin-left:10px;opacity:0.7;">×</a>
        </li>"""

    undo_html = ""
    if last_deleted:
        undo_name = last_deleted["item"]["name"]
        undo_html = f"""
        <div id="undo-bar" style="display:flex;justify-content:space-between;align-items:center;
             background:#2d2a24;color:white;padding:12px 16px;border-radius:12px;margin-top:12px;
             font-size:14px;font-weight:600;transition:opacity 0.5s;">
          <span>"{undo_name}" removed</span>
          <a href="/undo" style="color:#86efac;font-size:14px;">↩ Undo</a>
        </div>
        <script>
          setTimeout(() => {{
            const b = document.getElementById('undo-bar');
            if (b) {{ b.style.opacity='0'; setTimeout(()=>b.style.display='none',500); }}
            fetch('/dismiss_undo');
          }}, 5000);
          history.replaceState(null, '', '/');
        </script>"""

    shop_btn = """
    <div style="height:80px;"></div>
    <div style="position:fixed;bottom:0;left:0;right:0;padding:12px 16px;
                background:linear-gradient(to top, var(--cream) 80%, transparent);
                z-index:50;">
      <div style="position:relative;width:100%;height:60px;background:#fff3e0;border-radius:30px;
                  overflow:hidden;border:2px solid #f0a050;
                  animation:pulse-border 2s ease-in-out infinite;">
        <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                    font-family:'Righteous',sans-serif;font-size:17px;color:#e07020;
                    opacity:0.6;user-select:none;pointer-events:none;">
          Swipe to start shopping →
        </div>
        <div id="shop-slider"
             style="position:absolute;left:4px;top:4px;width:52px;height:44px;
                    background:linear-gradient(135deg,var(--orange),var(--orange2));
                    border-radius:26px;cursor:grab;display:flex;align-items:center;
                    justify-content:center;font-size:22px;
                    box-shadow:0 4px 12px rgba(240,125,53,0.4);user-select:none;">
          ✅
        </div>
      </div>
    </div>"""

    count_text = f"{len(items)} item{'s' if len(items) != 1 else ''} on your list" if items else "Your list is empty — add something!"

    misc_items = load_misc(username)
    misc_rows = ""
    for i, name in enumerate(misc_items):
        misc_rows += f"""
        <li style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);gap:10px;">
          <span style="flex:1;font-size:16px;font-weight:600;">{name}</span>
          <a href="/misc/delete/{i}" style="color:var(--red);font-size:20px;line-height:1;">×</a>
        </li>"""
    if not misc_rows:
        misc_rows = '<li style="color:var(--muted);font-size:14px;padding:10px 0;">Nothing here yet.</li>'

    misc_count = f'<span style="background:#ff4444;color:white;border-radius:50%;width:18px;height:18px;font-size:11px;display:inline-flex;align-items:center;justify-content:center;margin-left:6px;">{len(misc_items)}</span>' if misc_items else ""

    # Only show Flybuys for the owner
    display_name = current_display_name()

    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>{display_name}'s Grocery List</title>{BASE_HEAD}
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
<style>
  @keyframes pulse-border {{
    0%   {{ box-shadow: 0 0 0 0 rgba(240,125,53,0.4); }}
    50%  {{ box-shadow: 0 0 0 8px rgba(240,125,53,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(240,125,53,0); }}
  }}
</style>
</head>
<body>
<div class="page">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
    <h1 style="display:flex;align-items:center;gap:{'6px' if len(display_name) <= 10 else '1px'};margin:0;">
      <span style="font-size:{'32px' if len(display_name) <= 10 else '20px'};">🛒</span>
      <span onclick="openUserMenu()" style="font-size:{'32px' if len(display_name) <= 10 else '20px'};
            cursor:pointer;border-bottom:2px dashed var(--green);padding-bottom:2px;">
        {display_name}
      </span>
    </h1>
    <div style="display:flex;gap:8px;">
      <button onclick="openMisc()" style="background:var(--cream);border:2px solid var(--border);
          border-radius:10px;padding:8px 12px;font-family:'Righteous',sans-serif;font-size:14px;
          color:var(--text);cursor:pointer;display:flex;align-items:center;white-space:nowrap;">
        📌 Extras{misc_count}
      </button>
      <a href="/logout" style="background:var(--cream);border:2px solid var(--border);
          border-radius:10px;padding:8px 12px;font-family:'Righteous',sans-serif;font-size:14px;
          color:var(--muted);display:flex;align-items:center;">
        ⇄
      </a>
    </div>
  </div>

  <!-- User menu overlay -->
  <div id="user-menu-overlay" onclick="closeUserMenu()"
    style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:200;"></div>

  <div id="user-menu"
    style="display:none;position:fixed;bottom:0;left:0;right:0;background:var(--card);
           border-radius:20px 20px 0 0;padding:24px;z-index:201;
           box-shadow:0 -4px 30px rgba(0,0,0,0.15);">
    <p style="font-family:'Righteous',sans-serif;font-size:18px;color:var(--green);
              margin:0 0 20px;">👤 {display_name}</p>
    <button onclick="redownloadCard()"
      style="width:100%;padding:14px;margin-bottom:10px;background:var(--cream);
             border:2px solid var(--border);border-radius:12px;font-family:'Righteous',sans-serif;
             font-size:16px;color:var(--text);cursor:pointer;text-align:left;">
      📥 Re-download login card
    </button>
    <button onclick="openLeaderboard()"
      style="width:100%;padding:14px;margin-bottom:10px;background:var(--cream);
             border:2px solid var(--border);border-radius:12px;font-family:'Righteous',sans-serif;
             font-size:16px;color:var(--text);cursor:pointer;text-align:left;">
      🏆 Leaderboard
    </button>
    {('''
    <button onclick="openPinSetup()" 
      style="width:100%;padding:14px;margin-bottom:10px;background:var(--cream);
             border:2px solid var(--border);border-radius:12px;font-family:'Righteous',sans-serif;
             font-size:16px;color:var(--text);cursor:pointer;text-align:left;">
      🔒 Set a PIN
    </button>
    ''') if not has_pin else ""}

    <button onclick="closeUserMenu()"
      style="width:100%;padding:14px;background:none;border:none;
             font-size:15px;color:var(--muted);cursor:pointer;">
      Cancel
    </button>
  </div>

  <!-- PIN setup sheet -->
  <div id="pin-setup-overlay" onclick="closePinSetup()"
    style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:300;"></div>
  <div id="pin-setup"
    style="display:none;position:fixed;bottom:0;left:0;right:0;background:var(--card);
           border-radius:20px 20px 0 0;padding:24px;z-index:301;
           box-shadow:0 -4px 30px rgba(0,0,0,0.15);">
    <p style="font-family:'Righteous',sans-serif;font-size:18px;color:var(--green);margin:0 0 6px;">🔒 Set your PIN</p>
    <p style="font-size:13px;color:var(--muted);margin:0 0 20px;">This can only be set once and cannot be changed.</p>
    <div style="display:flex;justify-content:center;gap:24px;margin-bottom:16px;">
      <span id="new-pin-val1" style="font-size:40px;font-weight:700;color:var(--green);
            min-width:48px;text-align:center;">0</span>
      <span style="font-size:48px;font-weight:700;color:var(--muted);">•</span>
      <span id="new-pin-val2" style="font-size:40px;font-weight:700;color:var(--green);
            min-width:48px;text-align:center;">0</span>
    </div>
    <div style="display:flex;flex-direction:column;gap:12px;margin-bottom:20px;">
      <input type="range" min="0" max="20" value="0" id="new-pin-slider1"
        oninput="updateNewPin()" style="width:100%;">
      <input type="range" min="0" max="20" value="0" id="new-pin-slider2"
        oninput="updateNewPin()" style="width:100%;">
    </div>
    <button onclick="savePin()"
      style="width:100%;padding:14px;background:var(--green);color:white;border:none;
             border-radius:12px;font-family:'Righteous',sans-serif;font-size:17px;
             cursor:pointer;margin-bottom:10px;box-shadow:0 4px 12px rgba(58,125,68,0.3);">
      Save PIN
    </button>
    <button onclick="closePinSetup()"
      style="width:100%;padding:14px;background:none;border:none;
             font-size:15px;color:var(--muted);cursor:pointer;">
      Cancel
    </button>
  </div>

  <div id="leaderboard-overlay" onclick="closeLeaderboard()"
    style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.4);z-index:300;"></div>

  <div id="leaderboard-sheet"
    style="display:none;position:fixed;bottom:0;left:0;right:0;background:var(--card);
           border-radius:20px 20px 0 0;padding:24px;z-index:301;
           box-shadow:0 -4px 30px rgba(0,0,0,0.15);max-height:80vh;overflow-y:auto;">
    <p style="font-family:'Righteous',sans-serif;font-size:18px;color:var(--green);margin:0 0 20px;">🏆 Leaderboard</p>
    <div id="home-leaderboard-list"></div>
    <button onclick="closeLeaderboard()"
      style="width:100%;margin-top:16px;padding:14px;background:none;border:none;
             font-size:15px;color:var(--muted);cursor:pointer;">
      Close
    </button>
  </div>

  <div style="background:var(--card);border:2px solid var(--border);border-radius:var(--radius);
              padding:18px;margin-bottom:20px;box-shadow:0 2px 12px rgba(0,0,0,0.05);">
    <form action="/add" method="post" enctype="multipart/form-data">
      <input type="text" name="item" maxlength="40" placeholder="What do you need?" required
        style="width:100%;padding:12px 14px;font-size:16px;font-family:'DM Sans',sans-serif;
               border:2px solid var(--border);border-radius:10px;background:var(--cream);
               color:var(--text);outline:none;margin-bottom:12px;transition:border-color 0.2s;"
        onfocus="this.style.borderColor='var(--green)'" onblur="this.style.borderColor='var(--border)'">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
        <label style="font-size:13px;color:var(--muted);font-weight:600;white-space:nowrap;">📷 Add photo</label>
        <input type="file" name="photo" accept="image/*" onchange="previewPhoto(this)"
          style="font-size:13px;color:var(--muted);flex:1;min-width:0;">
        <img id="preview" style="width:48px;height:48px;object-fit:cover;border-radius:8px;display:none;border:2px solid var(--border);">
      </div>
      <button type="submit"
        style="width:100%;padding:13px;font-size:17px;font-family:'Righteous',sans-serif;font-weight:600;
               background:var(--green);color:white;border:none;border-radius:12px;cursor:pointer;
               box-shadow:0 4px 12px rgba(58,125,68,0.3);"
        onmousedown="this.style.transform='scale(0.98)'" onmouseup="this.style.transform='scale(1)'">
        + Add to list
      </button>
    </form>
  </div>

  {undo_html}
  <p style="font-size:13px;color:var(--muted);font-weight:600;margin:16px 0 12px;text-transform:uppercase;letter-spacing:0.5px;">{count_text}</p>
  <div id="shop-hint" style="background:linear-gradient(135deg,var(--green),var(--green2));
              border-radius:12px;padding:10px 14px;margin-bottom:16px;
              display:flex;align-items:center;gap:12px;">
    <span style="font-size:20px;">🥦</span>
    <div style="flex:1;">
      <p style="font-family:'Righteous',sans-serif;font-size:14px;color:white;margin:0 0 2px;">
        Ready to shop?
      </p>
      <p style="font-size:12px;color:rgba(255,255,255,0.85);margin:0;">
        Swipe below to get your organised list
      </p>
    </div>
    <button onclick="document.getElementById('shop-hint').style.display='none'"
      style="background:none;border:none;color:white;font-size:20px;cursor:pointer;
             opacity:0.7;padding:0;line-height:1;flex-shrink:0;">
      ×
    </button>
  </div>
  <ul>{list_html}</ul>
  {shop_btn}

</div>

<div class="misc-overlay" id="misc-overlay" onclick="closeMisc()"></div>
<div class="misc-panel" id="misc-panel">
  <div style="padding:20px;border-bottom:2px solid var(--border);display:flex;align-items:center;justify-content:space-between;">
    <span style="font-family:'Righteous',sans-serif;font-size:20px;color:var(--green);">📌 Extras</span>
    <button onclick="closeMisc()" style="background:none;border:none;font-size:24px;cursor:pointer;color:var(--muted);">×</button>
  </div>
  <div style="padding:16px;border-bottom:2px solid var(--border);">
    <form action="/misc/add" method="post" style="display:flex;gap:8px;">
      <input type="text" name="misc_item" placeholder="Add a note..." required
        style="flex:1;padding:10px 12px;font-size:15px;font-family:'DM Sans',sans-serif;
               border:2px solid var(--border);border-radius:10px;background:var(--cream);
               color:var(--text);outline:none;">
      <button type="submit"
        style="padding:10px 14px;background:var(--green);color:white;border:none;
               border-radius:10px;font-size:18px;cursor:pointer;">+</button>
    </form>
  </div>
  <ul style="flex:1;overflow-y:auto;padding:0 16px;list-style:none;margin:0;">
    {misc_rows}
  </ul>
  <div style="padding:16px;border-top:2px solid var(--border);">
    <a href="/misc/clear"
      style="display:block;text-align:center;padding:11px;background:#fff0f0;
             color:var(--red);border:2px solid #ffcccc;border-radius:10px;
             font-size:14px;font-weight:700;font-family:'DM Sans',sans-serif;">
      🗑 Clear all extras
    </a>
  </div>
</div>

<script>
  function previewPhoto(input) {{
    const p = document.getElementById('preview');
    if (input.files && input.files[0]) {{
      const r = new FileReader();
      r.onload = e => {{ p.src = e.target.result; p.style.display = 'block'; }};
      r.readAsDataURL(input.files[0]);
    }}
  }}
  function openMisc() {{
    document.getElementById('misc-panel').classList.add('open');
    document.getElementById('misc-overlay').classList.add('open');
  }}
  function closeMisc() {{
    document.getElementById('misc-panel').classList.remove('open');
    document.getElementById('misc-overlay').classList.remove('open');
  }}
function openUserMenu() {{
    document.getElementById('user-menu').style.display = 'block';
    document.getElementById('user-menu-overlay').style.display = 'block';
  }}
  function closeUserMenu() {{
    document.getElementById('user-menu').style.display = 'none';
    document.getElementById('user-menu-overlay').style.display = 'none';
  }}
  function openPinSetup() {{
    closeUserMenu();
    document.getElementById('pin-setup').style.display = 'block';
    document.getElementById('pin-setup-overlay').style.display = 'block';
  }}
  function closePinSetup() {{
    document.getElementById('pin-setup').style.display = 'none';
    document.getElementById('pin-setup-overlay').style.display = 'none';
  }}
  function updateNewPin() {{
    document.getElementById('new-pin-val1').textContent = document.getElementById('new-pin-slider1').value;
    document.getElementById('new-pin-val2').textContent = document.getElementById('new-pin-slider2').value;

  }}
  (function() {{
    const slider = document.getElementById('shop-slider');
    if (!slider) return;
    const track = slider.parentElement;
    let dragging = false;
    let startX = 0;
    let currentX = 0;
    const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

    function start(x) {{
      dragging = true;
      startX = x - currentX;
      slider.style.cursor = 'grabbing';
    }}

    function move(x) {{
      if (!dragging) return;
      currentX = Math.min(Math.max(0, x - startX), maxX());
      slider.style.left = (4 + currentX) + 'px';
      const pct = currentX / maxX();
      track.style.background = `linear-gradient(to right, #ffe0b2 ${{Math.round(pct*100)}}%, #fff3e0 ${{Math.round(pct*100)}}%)`;
      if (pct >= 0.95) {{
        dragging = false;
        slider.style.left = (4 + maxX()) + 'px';
        slider.textContent = '🚀';
        sessionStorage.setItem('shopStartTime', Date.now());
        setTimeout(() => window.location.href = '/shop', 400);
      }}
    }}

    function end() {{
      if (!dragging) return;
      dragging = false;
      slider.style.cursor = 'grab';
      currentX = 0;
      slider.style.transition = 'left 0.3s';
      slider.style.left = '4px';
      track.style.background = '#fff3e0';
      setTimeout(() => slider.style.transition = '', 300);
    }}

    slider.addEventListener('mousedown', e => start(e.clientX));
    window.addEventListener('mousemove', e => move(e.clientX));
    window.addEventListener('mouseup', end);
    slider.addEventListener('touchstart', e => {{ e.preventDefault(); start(e.touches[0].clientX); }}, {{passive: false}});
    window.addEventListener('touchmove', e => move(e.touches[0].clientX));
    window.addEventListener('touchend', end);
  }})();
  function savePin() {{
    const pin = document.getElementById('new-pin-slider1').value + '-' + 
                document.getElementById('new-pin-slider2').value;
    const form = new FormData();
    form.append('action', 'set_pin');
    form.append('pin', pin);
    fetch('/set_pin', {{ method: 'POST', body: form }})
      .then(r => r.json())
      .then(data => {{
        if (data.status === 'ok') {{
          closePinSetup();
          alert('PIN saved! Re-download your list card to save the new details.');
          location.reload();
        }}
      }});
  }}

  function openLeaderboard() {{
    closeUserMenu();
    fetch('/leaderboard')
      .then(r => r.json())
      .then(data => {{
        const list = document.getElementById('home-leaderboard-list');
        if (data.scores.length === 0) {{
          list.innerHTML = '<p style="font-size:13px;color:var(--muted);text-align:center;">No scores yet - complete a shop in record time to be the first!</p>';
        }} else {{
          list.innerHTML = data.scores.map((s, i) => `
            <div style="display:flex;align-items:center;justify-content:space-between;
                        padding:10px 14px;background:${{i === 0 ? '#f0f9f0' : 'var(--cream)'}};
                        border-radius:10px;margin-bottom:6px;">
              <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--text);">
                ${{i + 1}}. ${{s.arcade_name}}
              </span>
              <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--green);">
                ${{s.score.toLocaleString()}} pts
              </span>
            </div>
          `).join('');
        }}
        document.getElementById('leaderboard-sheet').style.display = 'block';
        document.getElementById('leaderboard-overlay').style.display = 'block';
      }});
  }}

  function closeLeaderboard() {{
    document.getElementById('leaderboard-sheet').style.display = 'none';
    document.getElementById('leaderboard-overlay').style.display = 'none';
  }}

  function redownloadCard() {{
    closeUserMenu();
    const username = "{display_name}";
    const pinDisplay = "{pin_display}";
    const showPin = pinDisplay && pinDisplay !== "None";

    const card = document.createElement('div');
    card.style.cssText = 'background:#fff8f0;border:2px solid #e8d5b0;border-radius:20px;padding:28px 32px;text-align:center;font-family:DM Sans,sans-serif;position:fixed;left:-9999px;top:0;width:300px;';
    card.innerHTML = `
      <p style="font-size:11px;color:#aaa;margin-bottom:6px;letter-spacing:1px;text-transform:uppercase;">Aisle Get It!</p>
      <p style="font-size:11px;color:#aaa;margin-bottom:12px;">grocerylist.devkeo.com</p>
      <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
      <p style="font-size:12px;color:#aaa;margin-bottom:4px;">Username</p>
      <p style="font-size:24px;font-weight:700;color:#3a7d44;margin-bottom:12px;">${{username}}</p>
      ${{showPin ? `
        <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
        <p style="font-size:12px;color:#aaa;margin-bottom:4px;">PIN</p>
        <p style="font-size:28px;font-weight:700;letter-spacing:8px;color:#333;">${{pinDisplay}}</p>
      ` : ''}}
    `;
    document.body.appendChild(card);
    setTimeout(() => {{
      html2canvas(card, {{ backgroundColor: '#fff8f0', scale: 2, width: 300 }}).then(canvas => {{
        const link = document.createElement('a');
        link.download = username + '-grocery-login.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
        document.body.removeChild(card);
      }});
    }}, 100);
  }}
</script>
</body></html>"""

# --- Shop page ---

@app.route("/shop")
def shop():
    redir = require_user()
    if redir: return redir
    username = current_user()
    display_name = current_display_name()
    items = load_items(username)
    categories = categorise_items(items)
    items_count = sum(len(cat_items) for cat_items in categories.values())

    misc_items = load_misc(username)
    misc_section = ""
    if misc_items:
        misc_rows = ""
        for name in misc_items:
            misc_rows += f"""
            <li class="shop-item" style="background:#fff8f0;border:2px solid #f0d9c0;border-radius:12px;
                padding:12px 14px;margin-bottom:8px;transition:opacity 0.3s;">
              <label style="display:grid;grid-template-columns:1fr auto;align-items:center;width:100%;cursor:pointer;gap:12px;">
                <span style="font-size:17px;font-weight:600;text-align:right;display:block;width:100%;">{name}</span>
                <input type="checkbox" onchange="toggleItem(this)"
                  style="width:22px;height:22px;accent-color:var(--orange);cursor:pointer;">
              </label>
            </li>"""
        misc_section = f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin:20px 0 10px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:20px;">📌</span>
              <h2 style="font-family:'Righteous',sans-serif;font-size:18px;font-weight:600;color:var(--orange);">Extras</h2>
            </div>
            <span style="font-size:12px;color:var(--muted);font-weight:600;">separate trip</span>
          </div>
          <ul>{misc_rows}</ul>
        </div>"""
    categories_html = ""
    global_index = 0
    for category, cat_items in categories.items():
        icon = CATEGORY_ICONS.get(category, "🛒")
        rows = ""
        for item in cat_items:
            img_html = ""
            if item.get("photo"):
                try:
                    url = get_photo_url(item["photo"])
                    img_html = f'<img src="{url}" style="width:46px;height:46px;object-fit:cover;border-radius:8px;margin-right:12px;flex-shrink:0;">'
                except:
                    img_html = ""
            checked_attr = "checked" if item.get("checked") else ""
            item_id = item.get("id", global_index)
            item_category = item.get("category", category)
            item_name = item["name"].replace('"', '&quot;')
            rows += f"""
            <li class="shop-item" data-id="{item_id}" data-name="{item_name}" data-category="{item_category}"
                style="background:var(--card);border:2px solid var(--border);border-radius:12px;
                padding:12px 14px;margin-bottom:8px;display:flex;align-items:center;transition:opacity 0.3s;">
              <label style="display:flex;align-items:center;width:100%;cursor:pointer;">
                <input type="checkbox" onchange="toggleItem(this, {global_index})"
                  style="width:22px;height:22px;margin-right:12px;accent-color:var(--green);flex-shrink:0;cursor:pointer;">
                {img_html}
                <span style="font-size:17px;font-weight:600;">{item["name"]}</span>
              </label>
              <span title="Hold to change category"
                style="font-size:16px;color:var(--muted);opacity:0.8;margin-left:8px;flex-shrink:0;font-weight:600;
                       user-select:none;cursor:context-menu;">⋮</span>              
            </li>"""
            global_index += 1
            
        categories_html += f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
            <span style="font-size:20px;">{icon}</span>
            <h2 style="font-family:'Righteous',sans-serif;font-size:18px;font-weight:600;color:var(--green);">{category}</h2>
          </div>
          <ul>{rows}</ul>
        </div>"""

    # Flybuys per user
    flybuys_html = get_flybuys_card_html(username)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><title>Shopping — {display_name}</title>{BASE_HEAD}
<style>
  .shop-item.done {{ opacity:0.4; }}
  .shop-item.done span {{ text-decoration:line-through; }}
  .confirm-overlay {{ display:none;position:fixed;inset:0;background:rgba(0,0,0,0.55);justify-content:center;align-items:center;z-index:100; }}
  .confirm-overlay.visible {{ display:flex; }}
  .confirm-box {{ background:white;border-radius:20px;padding:32px 24px;max-width:300px;width:90%;text-align:center; }}
  .confirm-box h2 {{ font-family:'Righteous',sans-serif;font-size:24px;color:var(--text);margin-bottom:8px; }}
  .confirm-box p {{ font-size:15px;color:var(--muted);margin-bottom:24px;line-height:1.5; }}
  .confirm-btns {{ display:flex;gap:10px; }}
  .btn-cancel {{ flex:1;padding:13px;font-size:16px;font-family:'DM Sans',sans-serif;font-weight:700;background:#f0ece4;color:var(--text);border:none;border-radius:12px;cursor:pointer; }}
  .btn-yes {{ flex:1;padding:13px;font-size:16px;font-family:'DM Sans',sans-serif;font-weight:700;background:var(--red);color:white;border:none;border-radius:12px;cursor:pointer; }}
  @keyframes pulse-border-green {{
    0%   {{ box-shadow: 0 0 0 0 rgba(58,125,68,0.4); }}
    50%  {{ box-shadow: 0 0 0 8px rgba(58,125,68,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(58,125,68,0); }}
  }}
  @keyframes pulse-border-orange {{
    0%   {{ box-shadow: 0 0 0 0 rgba(240,125,53,0.4); }}
    50%  {{ box-shadow: 0 0 0 8px rgba(240,125,53,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(240,125,53,0); }}
  }}
</style>
</head>
<body>
<div class="page">
  <h1>🛒 {display_name}</h1>
  {flybuys_html}
  <div id="shop-tips" style="background:var(--cream);border:2px solid var(--border);
              border-radius:12px;padding:10px 14px;margin-bottom:16px;
              display:flex;align-items:center;gap:8px;">
    <div style="flex:1;">
      <p style="font-size:13px;color:var(--muted);margin:0 0 4px;">
        ✅ Tick items as you add them to your cart
      </p>
      <p style="font-size:13px;color:var(--muted);margin:0;">
        ⋮ Long press on an item to change its category
      </p>
    </div>
    <button onclick="document.getElementById('shop-tips').style.display='none'"
      style="background:none;border:none;color:var(--muted);font-size:20px;cursor:pointer;
             opacity:0.7;padding:0;line-height:1;flex-shrink:0;">
      ×
    </button>
  </div>
  {categories_html}
  {misc_section}

  <a href="/" style="display:flex;align-items:center;gap:6px;margin-top:18px;color:var(--muted);font-size:15px;font-weight:600;">
    ← Back to list
  </a>
  <div style="height:80px;"></div>
  <div style="position:fixed;bottom:0;left:0;right:0;padding:12px 16px;
              background:linear-gradient(to top, var(--cream) 80%, transparent);
              z-index:50;">
    <div style="position:relative;width:100%;height:60px;background:#e8f5e9;border-radius:30px;
                overflow:hidden;border:2px solid #a5d6a7;
                animation:pulse-border-green 2s ease-in-out infinite;">
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                  font-family:'Righteous',sans-serif;font-size:17px;color:var(--green);
                  opacity:0.6;user-select:none;pointer-events:none;">
        Swipe when done →
      </div>
      <div id="complete-slider"
           style="position:absolute;left:4px;top:4px;width:52px;height:44px;
                  background:linear-gradient(135deg,var(--green),var(--green2));
                  border-radius:26px;cursor:grab;display:flex;align-items:center;
                  justify-content:center;font-size:22px;
                  box-shadow:0 4px 12px rgba(58,125,68,0.4);user-select:none;">
        🥕
      </div>
    </div>
  </div>
</div>

<!-- Results overlay -->
<div id="results-overlay"
  style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);
         z-index:200;justify-content:center;align-items:center;">
  <div style="background:var(--card);border-radius:20px 20px 0 0;padding:28px 24px;
              width:100%;max-width:480px;box-shadow:0 -4px 30px rgba(0,0,0,0.2);max-height:90vh;overflow-y:auto;">
        <div style="text-align:center;margin-bottom:16px;">
      <p style="font-size:28px;margin:0;">🏆</p>
      <h2 style="font-family:'Righteous',sans-serif;font-size:26px;color:var(--green);margin:8px 0 4px;">Shop Complete!</h2>
      <p style="font-size:13px;color:var(--muted);margin:0 0 4px;">The faster you shop, the higher your score.</p>
    </div>

    <div style="background:#f0f9f0;border:2px solid #a5d6a7;border-radius:16px;
                padding:12px;text-align:center;margin-bottom:16px;">
      <p style="font-size:13px;color:var(--muted);margin:0 0 4px;text-transform:uppercase;letter-spacing:1px;">Your Score</p>
      <p id="result-score" style="font-family:'Righteous',sans-serif;font-size:40px;
                                   color:var(--green);margin:0;"></p>
    </div>
    <p id="result-time" style="font-size:12px;color:var(--muted);text-align:center;margin:0 0 16px;"></p>
    <p style="font-size:13px;font-weight:700;color:var(--text);margin:0 0 6px;">Enter your name for this list's Leaderboard:</p>
    <div style="display:flex;gap:8px;margin-bottom:16px;">
      <input id="arcade-input" maxlength="8" placeholder="AAA"
        style="flex:1;min-width:0;padding:8px;font-size:18px;font-family:'Righteous',sans-serif;
               text-align:center;text-transform:uppercase;letter-spacing:4px;
               border:2px solid var(--border);border-radius:7px;background:var(--cream);
               color:var(--green);outline:none;"
        oninput="this.value=this.value.toUpperCase()"
        onfocus="this.style.borderColor='var(--green)'"
        onblur="this.style.borderColor='var(--border)'">
      <button onclick="submitScore()"
        style="padding:8px 16px;background:var(--green);color:white;border:none;
               border-radius:12px;font-family:'Righteous',sans-serif;font-size:14px;cursor:pointer;flex-shrink:0;">
        Submit
      </button>
    </div>

    <!-- Leaderboard -->
    <p style="font-size:13px;font-weight:700;color:var(--muted);text-transform:uppercase;
              letter-spacing:1px;margin:0 0 10px;">🏅 Leaderboard</p>
    <div id="leaderboard-list"></div>
    
    <div style="height:70px;"></div>
    <div style="position:fixed;bottom:0;left:0;right:0;padding:12px 16px;
                background:linear-gradient(to top, white 80%, transparent);
                z-index:50;">
      <div style="position:relative;width:100%;height:60px;background:#fff3e0;border-radius:30px;
                  overflow:hidden;border:2px solid #f0a050;
                  animation:pulse-border-orange 2s ease-in-out infinite;">
        <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
                    font-family:'Righteous',sans-serif;font-size:17px;color:#e07020;
                    opacity:0.6;user-select:none;pointer-events:none;">
          Swipe to finish & clear list→
        </div>
        <div id="finish-slider"
             style="position:absolute;left:4px;top:4px;width:52px;height:44px;
                    background:linear-gradient(135deg,var(--orange),var(--orange2));
                    border-radius:26px;cursor:grab;display:flex;align-items:center;
                    justify-content:center;font-size:22px;
                    box-shadow:0 4px 12px rgba(240,125,53,0.4);user-select:none;">
          🛍️
        </div>
      </div>
    </div>

<form id="clear-form" action="/clear" method="post" style="display:none;">
  <input type="hidden" name="ticked" id="ticked-input" value="">
</form>

<script>
  const ticked = new Set();
  let shopStartTime = null;

  shopStartTime = sessionStorage.getItem('shopStartTime');

  function toggleItem(cb) {{
    const li = cb.closest('li');
    li.classList.toggle('done', cb.checked);
    const name = li.querySelector('span').textContent.trim();
    if (cb.checked) {{
      ticked.add(name);
    }} else {{
      ticked.delete(name);
    }}
  }}

  function formatTime(seconds) {{
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${{m}}m ${{s}}s` : `${{s}}s`;
  }}

  function showResults() {{
    const endTime = Date.now();
    const startTime = parseInt(shopStartTime) || endTime;
    const elapsed = Math.floor((endTime - startTime) / 1000);
    const tickedCount = ticked.size;
    const score = tickedCount > 0 ? Math.round((tickedCount * 100000) / Math.max(elapsed / 60, 0.1)) : 0;

    document.getElementById('result-score').textContent = score.toLocaleString();
    document.getElementById('result-time').textContent = `${{getEncouragement()}} ${{tickedCount}} items purchased in ${{formatTime(elapsed)}}`;

    window._shopResult = {{ score, itemsCount: tickedCount, timeSeconds: elapsed }};

    fetch('/leaderboard')
      .then(r => r.json())
      .then(data => {{
        const list = document.getElementById('leaderboard-list');
        if (data.scores.length === 0) {{
          list.innerHTML = '<p style="font-size:13px;color:var(--muted);text-align:center;">No scores yet — be the first!</p>';
          return;
        }}
        list.innerHTML = data.scores.map((s, i) => `
          <div style="display:flex;align-items:center;justify-content:space-between;
                      padding:10px 14px;background:${{i === 0 ? '#f0f9f0' : 'var(--cream)'}};
                      border-radius:10px;margin-bottom:6px;">
            <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--text);">
              ${{i + 1}}. ${{s.arcade_name}}
            </span>
            <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--green);">
              ${{s.score}}
            </span>
          </div>
        `).join('');
      }});

    document.getElementById('results-overlay').style.display = 'flex';
  }}

  function submitScore() {{
    const arcadeName = document.getElementById('arcade-input').value.trim();
    if (!arcadeName || arcadeName.length < 1) {{
      document.getElementById('arcade-input').style.borderColor = 'var(--red)';
      return;
    }}
    const {{ score, itemsCount, timeSeconds }} = window._shopResult;
    const form = new FormData();
    form.append('arcade_name', arcadeName);
    form.append('score', score);
    form.append('items_count', itemsCount);
    form.append('time_seconds', timeSeconds);
    fetch('/save_score', {{ method: 'POST', body: form }})
      .then(r => r.json())
      .then(data => {{
        // Show high score celebration if applicable
        if (data.new_high_score) {{
          const scoreEl = document.getElementById('result-score');
          scoreEl.style.transition = 'transform 0.3s';
          scoreEl.style.transform = 'scale(1.3)';
          setTimeout(() => scoreEl.style.transform = 'scale(1)', 300);
          const badge = document.createElement('p');
          badge.textContent = '🏆 New High Score!';
          badge.style.cssText = 'font-family:Righteous,sans-serif;font-size:18px;color:var(--green);text-align:center;margin:0 0 12px;';
          scoreEl.parentElement.insertBefore(badge, scoreEl);
        }}
        fetch('/leaderboard')
          .then(r => r.json())
          .then(data => {{
            const list = document.getElementById('leaderboard-list');
            list.innerHTML = data.scores.map((s, i) => `
              <div style="display:flex;align-items:center;justify-content:space-between;
                          padding:10px 14px;background:${{i === 0 ? '#f0f9f0' : 'var(--cream)'}};
                          border-radius:10px;margin-bottom:6px;">
                <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--text);">
                  ${{i + 1}}. ${{s.arcade_name}}
                </span>
                <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--green);">
                  ${{s.score.toLocaleString()}} pts
                </span>
              </div>
            `).join('');
            document.getElementById('arcade-input').style.display = 'none';
            document.querySelector('[onclick="submitScore()"]').style.display = 'none';
            // If called from finishShopping, now actually finish
            if (window._finishAfterSubmit) {{
              window._finishAfterSubmit = false;
              sessionStorage.removeItem('shopStartTime');
              if (ticked.size === 0) {{
                window.location.href = '/';
              }} else {{
                document.getElementById('ticked-input').value = JSON.stringify([...ticked]);
                document.getElementById('clear-form').submit();
              }}
            }}
          }});
      }});
  }}
    const randomNames = [
    "supashpr", "mcspeedy", "quickrun", "starshpr", "topshpr",
    "shophero", "winner1", "thegoods", "chckndnr", "number1", "shplegnd"
  ];

  function getRandomName() {{
    return randomNames[Math.floor(Math.random() * randomNames.length)];
  }}
    function finishShopping() {{
    const arcadeInput = document.getElementById('arcade-input');
    if (arcadeInput && arcadeInput.style.display !== 'none' && !arcadeInput.value.trim()) {{
      window._finishAfterSubmit = true;
      arcadeInput.value = getRandomName();
      submitScore();
      return;
    }}
    sessionStorage.removeItem('shopStartTime');
    if (ticked.size === 0) {{
      window.location.href = '/';
      return;
    }}
    document.getElementById('ticked-input').value = JSON.stringify([...ticked]);
    document.getElementById('clear-form').submit();
  }}

  function updateCategory(itemId, itemName, oldCategory, newCategory) {{
    const form = new FormData();
    form.append('item_id', itemId);
    form.append('item_name', itemName);
    form.append('old_category', oldCategory);
    form.append('category', newCategory);
    fetch('/update_category', {{ method: 'POST', body: form }})
      .then(r => r.json())
      .then(data => {{
        if (data.status === 'ok') {{
          location.reload();
        }}
      }})
      .catch(err => console.error('Error:', err));
  }}

  document.addEventListener('DOMContentLoaded', () => {{
    document.querySelectorAll('li[data-id]').forEach(el => {{
      attachItemEvents(el);
    }});
  }});

  let longPressTimer;

  function attachItemEvents(itemEl) {{
    itemEl.addEventListener('contextmenu', (e) => {{
      e.preventDefault();
      showCategoryMenu(e.clientX, e.clientY, itemEl);
    }});
    itemEl.addEventListener('touchstart', () => {{
      longPressTimer = setTimeout(() => {{
        const rect = itemEl.getBoundingClientRect();
        showCategoryMenu(rect.left, rect.bottom, itemEl);
      }}, 500);
    }});
    itemEl.addEventListener('touchend', () => clearTimeout(longPressTimer));
    itemEl.addEventListener('touchmove', () => clearTimeout(longPressTimer));
  }}

  function showCategoryMenu(x, y, itemEl) {{
    removeCategoryMenu();
    const itemId = itemEl.dataset.id;
    const itemName = itemEl.dataset.name;
    const currentCategory = itemEl.dataset.category;
    const categories = ["Fruit & Veg","Meat & Fish","Dairy & Eggs","Bakery","Pantry","Drinks","Snacks","Household","Frozen","Other"];

    const menu = document.createElement('div');
    menu.id = 'category-menu';
    menu.style.cssText = `position:fixed;background:var(--card);
      border:2px solid var(--border);border-radius:12px;padding:8px;z-index:9999;
      box-shadow:0 4px 20px rgba(0,0,0,0.15);min-width:160px;`;
    menu.innerHTML = `<p style="font-size:12px;color:var(--muted);margin:0 0 6px 6px;">Move to...</p>`;

    categories.forEach(cat => {{
      const btn = document.createElement('button');
      btn.textContent = cat;
      btn.style.cssText = `display:block;width:100%;padding:8px 12px;text-align:left;
        background:${{cat === currentCategory ? 'var(--green)' : 'transparent'}};
        color:${{cat === currentCategory ? 'white' : 'var(--text)'}};
        border:none;border-radius:8px;cursor:pointer;font-size:14px;font-family:'DM Sans',sans-serif;`;
      btn.onclick = () => {{
        updateCategory(itemId, itemName, currentCategory, cat);
        itemEl.dataset.category = cat;
        removeCategoryMenu();
      }};
      menu.appendChild(btn);
    }});

    document.body.appendChild(menu);

    const menuHeight = menu.offsetHeight;
    const menuWidth = menu.offsetWidth;
    const windowHeight = window.innerHeight;
    const windowWidth = window.innerWidth;

    let top = y;
    let left = x;

    if (y + menuHeight > windowHeight) top = y - menuHeight;
    if (x + menuWidth > windowWidth) left = x - menuWidth;
    if (top < 0) top = 8;
    if (left < 0) left = 8;

    menu.style.top = top + 'px';
    menu.style.left = left + 'px';

    setTimeout(() => document.addEventListener('click', removeCategoryMenu, {{ once: true }}), 0);
  }}

  function removeCategoryMenu() {{
    document.getElementById('category-menu')?.remove();
  }}

  (function() {{
    const slider = document.getElementById('complete-slider');
    if (!slider) return;
    const track = slider.parentElement;
    let dragging = false;
    let startX = 0;
    let currentX = 0;
    const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

    function start(x) {{
      dragging = true;
      startX = x - currentX;
      slider.style.cursor = 'grabbing';
    }}

    function move(x) {{
      if (!dragging) return;
      currentX = Math.min(Math.max(0, x - startX), maxX());
      slider.style.left = (4 + currentX) + 'px';
      const pct = currentX / maxX();
      track.style.background = `linear-gradient(to right, #c8e6c9 ${{Math.round(pct*100)}}%, #e8f5e9 ${{Math.round(pct*100)}}%)`;
      if (pct >= 0.95) {{
        dragging = false;
        slider.style.left = (4 + maxX()) + 'px';
        slider.textContent = '🎉';
        setTimeout(() => showResults(), 400);
      }}
    }}

    function end() {{
      if (!dragging) return;
      dragging = false;
      slider.style.cursor = 'grab';
      currentX = 0;
      slider.style.transition = 'left 0.3s';
      slider.style.left = '4px';
      track.style.background = '#e8f5e9';
      setTimeout(() => slider.style.transition = '', 300);
    }}

    slider.addEventListener('mousedown', e => start(e.clientX));
    window.addEventListener('mousemove', e => move(e.clientX));
    window.addEventListener('mouseup', end);
    slider.addEventListener('touchstart', e => {{ e.preventDefault(); start(e.touches[0].clientX); }}, {{passive: false}});
    window.addEventListener('touchmove', e => move(e.touches[0].clientX));
    window.addEventListener('touchend', end);
  }})();

    (function() {{
    const slider = document.getElementById('finish-slider');
    if (!slider) return;
    const track = slider.parentElement;
    let dragging = false;
    let startX = 0;
    let currentX = 0;
    const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

    function start(x) {{
      dragging = true;
      startX = x - currentX;
      slider.style.cursor = 'grabbing';
    }}

    function move(x) {{
      if (!dragging) return;
      currentX = Math.min(Math.max(0, x - startX), maxX());
      slider.style.left = (4 + currentX) + 'px';
      const pct = currentX / maxX();
      track.style.background = `linear-gradient(to right, #ffe0b2 ${{Math.round(pct*100)}}%, #fff3e0 ${{Math.round(pct*100)}}%)`;
      if (pct >= 0.95) {{
        dragging = false;
        slider.style.left = (4 + maxX()) + 'px';
        slider.textContent = '✓';
        setTimeout(() => finishShopping(), 400);
      }}
    }}

    function end() {{
      if (!dragging) return;
      dragging = false;
      slider.style.cursor = 'grab';
      currentX = 0;
      slider.style.transition = 'left 0.3s';
      slider.style.left = '4px';
      track.style.background = '#fff3e0';
      setTimeout(() => slider.style.transition = '', 300);
    }}

    slider.addEventListener('mousedown', e => start(e.clientX));
    window.addEventListener('mousemove', e => move(e.clientX));
    window.addEventListener('mouseup', end);
    slider.addEventListener('touchstart', e => {{ e.preventDefault(); start(e.touches[0].clientX); }}, {{passive: false}});
    window.addEventListener('touchmove', e => move(e.touches[0].clientX));
    window.addEventListener('touchend', end);
  }})();

    const encouragements = [
    "Nice!", "Legend!", "Speedy!", "On fire!", "Crushing it!",
    "Superstar!", "Swift!", "Nailed it!", "Impressive!", "Zooming!"
  ];

  function getEncouragement() {{
    return encouragements[Math.floor(Math.random() * encouragements.length)];
  }}
</script>

</body></html>"""

# --- Save score and leaderboard ---

@app.route("/save_score", methods=["POST"])
def save_score():
    redir = require_user()
    if redir: return redir
    username = current_user()
    arcade_name = request.form.get("arcade_name", "???").strip().upper()[:8]
    score = int(request.form.get("score"))
    items_count = int(request.form.get("items_count"))
    time_seconds = int(request.form.get("time_seconds"))

    # Check current #1 score on the leaderboard
    top = supabase.table("leaderboard").select("score").eq("username", username).order("score", desc=True).limit(1).execute()
    current_top_score = top.data[0]["score"] if top.data else 0
    new_high_score = score > current_top_score

    # Check if this arcade name already has an entry
    existing = supabase.table("leaderboard").select("*").eq("username", username).eq("arcade_name", arcade_name).execute()

    if existing.data:
        if score > existing.data[0]["score"]:
            supabase.table("leaderboard").update({
                "score": score,
                "items_count": items_count,
                "time_seconds": time_seconds
            }).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("leaderboard").insert({
            "username": username,
            "arcade_name": arcade_name,
            "score": score,
            "items_count": items_count,
            "time_seconds": time_seconds
        }).execute()

    return {"status": "ok", "new_high_score": new_high_score}, 200

@app.route("/leaderboard")
def get_leaderboard():
    redir = require_user()
    if redir: return redir
    username = current_user()
    result = supabase.table("leaderboard").select("*").eq("username", username).gt("score",0).order("score", desc=True).limit(5).execute()
    return {"status": "ok", "scores": result.data}, 200

# --- Add item ---

@app.route("/add", methods=["POST"])
def add():
    redir = require_user()
    if redir: return redir

    username = current_user()
    name = request.form.get("item", "").strip()
    if not name:
        return redirect("/")

    photo_path = None
    photo = request.files.get("photo")

    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1].lower()
        if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            photo_path = upload_photo(username, photo)
    items = load_items(username)
    if len(items)>= MAX_ITEMS:
        return "List is full. Maximum 200 items allowed.", 400
    items.append({"name": name, "photo": photo_path})

    save_items(username, items)
    return redirect("/")

# --- Delete / undo ---

@app.route("/delete/<int:index>")
def delete(index):
    redir = require_user()
    if redir: return redir
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

@app.route("/dismiss_undo")
def dismiss_undo():
    session.pop("last_deleted", None)
    return "", 204

@app.route("/undo")
def undo():
    redir = require_user()
    if redir: return redir
    username = current_user()
    last = session.pop("last_deleted", None)
    if last:
        items = load_items(username)
        insert_at = min(last["index"], len(items))
        items.insert(insert_at, last["item"])
        save_items(username, items)
    return redirect("/")

# --- Misc / extras ---

@app.route("/misc/add", methods=["POST"])
def misc_add():
    redir = require_user()
    if redir: return redir
    username = current_user()
    name = request.form.get("misc_item", "").strip()
    if name:
        items = load_misc(username)
        items.append(name)
        save_misc(username, items)
    return redirect("/")

@app.route("/toggle/<int:index>", methods=["POST"])
def toggle(index):
    username = current_user()
    categories = load_items(username)
    
    flat = []
    for cat, items in categories.items():
        for item in items:
            flatlappend((cat, item))
    
    if 0 <= index <len(flat):
        cat, item = flat[index]
        item["checked"] = not item.get("checked", False)
    new_categories = {}
    for cat, item in flat:
        new_categories.setdefault(cat,[]).append(item)
        
    save_items(username,items)
    return ("",204)

@app.route("/misc/delete/<int:index>")
def misc_delete(index):
    redir = require_user()
    if redir: return redir
    username = current_user()
    items = load_misc(username)
    if 0 <= index < len(items):
        items.pop(index)
        save_misc(username, items)
    return redirect("/")

@app.route("/misc/clear")
def misc_clear():
    redir = require_user()
    if redir: return redir
    username = current_user()
    save_misc(username, [])
    return redirect("/")

# --- Clear ---

@app.route("/clear", methods=["POST"])
def clear():
    redir = require_user()
    if redir: return redir
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

@app.route("/update_category", methods=["POST"])
def update_category():
    redir = require_user()
    if redir: return redir
    username = current_user()
    item_name = request.form.get("item_name")
    new_category = request.form.get("category")
    old_category = request.form.get("old_category")

    # Load items, find the one by name, update its category
    items = load_items(username)
    for item in items:
        if item.get("name") == item_name:
            item["category"] = new_category
            break

    # Save back to the users table
    save_items(username, items)

    # Log the override for your review
    supabase.table("category_overrides").insert({
        "item_name": item_name,
        "old_category": old_category,
        "new_category": new_category,
        "username": username
    }).execute()

    return {"status": "ok"}, 200

# --- Export ---

@app.route("/export")
def export():
    redir = require_user()
    if redir: return redir
    username = current_user()
    items = load_items(username)
    categories = categorise_items(items)
    misc_items = load_misc(username)

    misc_section_html = ""
    if misc_items:
        misc_rows = ""
        for name in misc_items:
            misc_rows += f"""
            <li style="background:#fff8f0;border:2px solid #f0d9c0;border-radius:12px;
                padding:12px 14px;margin-bottom:8px;transition:opacity 0.3s;">
              <label style="display:grid;grid-template-columns:1fr auto;align-items:center;width:100%;cursor:pointer;gap:12px;">
                <span style="font-size:17px;font-weight:600;text-align:right;display:block;width:100%;">{name}</span>
                <input type="checkbox" onchange="this.closest('li').classList.toggle('done',this.checked)"
                  style="width:22px;height:22px;accent-color:#f07d35;cursor:pointer;">
              </label>
            </li>"""
        misc_section_html = f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin:20px 0 10px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-size:20px;">📌</span>
              <h2 style="font-family:'Righteous',sans-serif;font-size:18px;font-weight:600;color:#f07d35;">Extras</h2>
            </div>
            <span style="font-size:12px;color:#8a8070;font-weight:600;">separate trip</span>
          </div>
          <ul style="list-style:none;padding:0;margin:0;">{misc_rows}</ul>
        </div>"""

    categories_html = ""
    for category, cat_items in categories.items():
        icon = CATEGORY_ICONS.get(category, "🛒")
        rows = ""
        for item in cat_items:
            img_html = ""
            if item.get("photo"):
                try:
                    url = get_photo_url(item["photo"])
                    img_html = f'<img src="{url}" style="width:52px;height:52px;object-fit:cover;border-radius:10px;margin-right:12px;flex-shrink:0;">'
                except:
                    pass
            rows += f"""
            <li style="background:white;border:2px solid #e8e0d4;border-radius:12px;
                padding:12px 14px;margin-bottom:8px;display:flex;align-items:center;">
              <label style="display:flex;align-items:center;width:100%;cursor:pointer;">
                <input type="checkbox" onchange="this.closest('li').classList.toggle('done',this.checked)"
                  style="width:22px;height:22px;margin-right:12px;accent-color:#3a7d44;flex-shrink:0;cursor:pointer;">
                {img_html}
                <span style="font-size:17px;font-weight:600;">{item["name"]}</span>
              </label>
            </li>"""
        categories_html += f"""
        <div style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;gap:8px;margin:20px 0 10px;">
            <span style="font-size:20px;">{icon}</span>
            <h2 style="font-family:'Righteous',sans-serif;font-size:18px;font-weight:600;color:#3a7d44;">{category}</h2>
          </div>
          <ul style="list-style:none;padding:0;margin:0;">{rows}</ul>
        </div>"""

    flybuys_html = get_flybuys_card_html(username, css_vars=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{username}'s Shopping List</title>
  <link href="https://fonts.googleapis.com/css2?family=Righteous&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:'DM Sans',sans-serif;background:#fdf8f0;min-height:100vh;color:#2d2a24;padding:24px 18px 60px;max-width:480px;margin:0 auto; }}
    h1 {{ font-family:'Righteous',sans-serif;font-size:28px;color:#3a7d44;margin-bottom:20px; }}
    .done {{ opacity:0.4; }}
    .done span {{ text-decoration:line-through; }}
    ul {{ list-style:none;padding:0;margin:0; }}
    a {{ text-decoration:none;color:inherit; }}
  </style>
</head>
<body>
  <h1>🛍 {username}'s Shopping</h1>
  {flybuys_html}
  {categories_html}
  {misc_section_html}
  <p style="text-align:center;color:#8a8070;font-size:12px;margin-top:32px;">Exported from Aisle Get It! app</p>
</body>
</html>"""

    headers = {"Content-Disposition": f"attachment; filename={safe_username(username)}-shopping.html"}
    return Response(html, mimetype="text/html", headers=headers)

app.run(host="0.0.0.0", port=5000, debug=True)
