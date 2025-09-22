# app.py
import os
import sqlite3
import imaplib, email
from email.header import decode_header
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort

# ---------- Config ----------
APP_NAME = "MyMailerApp"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")  # change in production
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# ---------- App & DB helpers ----------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "chg_me_now")  # change in production

def app_data_dir():
    """Return a writable folder for the app data."""
    if os.name == "nt":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        d = os.path.join(base, APP_NAME)
    else:
        d = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")
    os.makedirs(d, exist_ok=True)
    return d

DB_FILE = os.path.join(app_data_dir(), "accounts.db")

def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT NOT NULL UNIQUE,
      app_password TEXT NOT NULL,
      label TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    con.commit()
    con.close()

def get_accounts():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT id, email, label FROM accounts ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    return rows

def get_account_by_id(acc_id):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("SELECT id, email, app_password, label FROM accounts WHERE id=?", (acc_id,))
    row = cur.fetchone()
    con.close()
    return row

def add_account(email_addr, app_pass, label=None):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO accounts (email, app_password, label) VALUES (?, ?, ?)", (email_addr, app_pass, label))
        con.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        con.close()

def delete_account(acc_id):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("DELETE FROM accounts WHERE id=?", (acc_id,))
    con.commit()
    con.close()

# ---------- Mail helpers ----------
def clean_subject(raw_subj):
    if not raw_subj:
        return ""
    parts = decode_header(raw_subj)
    result = []
    for subj, enc in parts:
        if isinstance(subj, bytes):
            try:
                result.append(subj.decode(enc or "utf-8", errors="ignore"))
            except:
                result.append(subj.decode(errors="ignore"))
        else:
            result.append(str(subj))
    return "".join(result).strip()

def fetch_last_subjects(email_user, email_pass, days=1, limit=5):
    results = {"INBOX": [], "SPAM": [], "PROMOTIONS": [], "UPDATES": []}
    folders = {
        "INBOX": "INBOX",
        "SPAM": "[Gmail]/Spam",
        "PROMOTIONS": "[Gmail]/Promotions",
        "UPDATES": "[Gmail]/Updates"
    }
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(email_user, email_pass)
            for name, path in folders.items():
                try:
                    imap.select(path, readonly=True)
                    date_since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
                    status, data = imap.search(None, f'(SINCE {date_since})')
                    if status == "OK" and data[0]:
                        ids = data[0].split()[-limit:]
                        for msg_id in ids:
                            res, msg_data = imap.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
                            if res == "OK" and msg_data and msg_data[0]:
                                msg = email.message_from_bytes(msg_data[0][1])
                                results[name].append(clean_subject(msg.get("Subject")))
                except Exception:
                    results[name].append("<error>")
            imap.logout()
    except Exception as e:
        return {"error": str(e)}
    return results

# ---------- Bulk import ----------
def import_boites_file():
    """
mailvrni@gmail.com:cucv qpaq ttwf siyv
deathelement2602@gmail.com:dnys kcsj wqqv abmk
juliabutler1967@gmail.com:dtzj utme chyh jvmc
terry2019britt@gmail.com:dxye jmak hkus nani
danielolm763@gmail.com:dydv bhzx wlux vkqf
craigsmetzinger@gmail.com:dytv igae bmfj eetr
yhnmlkj4@gmail.com:ebkg fvwz ujvd czts
reportingboite@gmail.com:ejdz vdix ilfj ohcg
merrymlk72@gmail.com:fbpg zucz hwcr xhnq
ew9474756@gmail.com:flez elke ylmn wqfu
diazluisto752@gmail.com:fppn apak bpgy ovff
raphador9@gmail.com:frxg suwm dvnl jnvw
franchraphinha@gmail.com:hfqs jgev osld yvao
liamhanran@gmail.com:hhet wlfz xbxb qcvk
oliviabouhrouz@gmail.com:hjha dvii amig tyka
gensedits@gmail.com:cxdn tprf npyq ohob
millseve02@gmail.com:iypi baro zknm pfxs
aidanrohu@gmail.com:laoe ijxj pdte sqtk
reportinganass@gmail.com:ljxd wcaa yoyd newa
mdsaifulisla40@gmail.com:mcvq tycl qbng kpqn
    """
    file_path = os.path.join(app_data_dir(), "boites.txt")
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            parts = line.split(":")
            email_addr = parts[0].strip()
            app_pass = parts[1].strip()
            label = parts[2].strip() if len(parts) > 2 else None
            ok, err = add_account(email_addr, app_pass, label)
            if not ok and "UNIQUE" not in (err or ""):
                print(f"Error adding {email_addr}: {err}")

# ---------- Routes ----------
@app.route("/")
def index():
    accounts = get_accounts()
    return render_template("index.html", accounts=accounts)

@app.route("/check/<int:acc_id>")
def check(acc_id):
    row = get_account_by_id(acc_id)
    if not row:
        return "Account not found", 404
    _, email_addr, app_pass, _ = row
    results = fetch_last_subjects(email_addr, app_pass)
    return render_template("results.html", email=email_addr, results=results)

def is_admin_ok(pw):
    return pw and pw == ADMIN_PASSWORD

@app.route("/admin", methods=["GET", "POST"])
def admin():
    pw = request.args.get("pw") or request.form.get("pw")
    if not is_admin_ok(pw):
        return render_template("admin.html", authorized=False)
    if request.method == "POST":
        email_addr = request.form.get("email")
        app_pass = request.form.get("app_password")
        label = request.form.get("label") or None
        if not email_addr or not app_pass:
            flash("Email and app password are required", "error")
            return redirect(url_for("admin", pw=pw))
        ok, err = add_account(email_addr.strip(), app_pass.strip(), label)
        if ok:
            flash("Account added", "success")
        else:
            flash(f"Error: {err}", "error")
        return redirect(url_for("admin", pw=pw))
    accounts = get_accounts()
    return render_template("admin.html", authorized=True, accounts=accounts, pw=pw)

@app.route("/delete/<int:acc_id>", methods=["POST"])
def do_delete(acc_id):
    pw = request.form.get("pw")
    if not is_admin_ok(pw):
        abort(403)
    delete_account(acc_id)
    flash("Deleted", "success")
    return redirect(url_for("admin", pw=pw))

@app.route("/export", methods=["GET"])
def export_db():
    pw = request.args.get("pw")
    if not is_admin_ok(pw):
        abort(403)
    return send_file(DB_FILE, as_attachment=True, download_name="accounts.db")

# ---------- Startup ----------
init_db()
import_boites_file()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
