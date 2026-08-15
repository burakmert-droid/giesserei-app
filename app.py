import os
import sqlite3
import urllib.request
import json
import base64
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, Response

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- E-MAIL VERTEILER VIA RESEND API (KEIN SMTP BLOCKING) ---
def send_flipchart_email(empfaenger_email, foto_path, thema=""):
    api_key = os.environ.get('RESEND_API_KEY', '')

    if not api_key:
        print("❌ FEHLER: RESEND_API_KEY fehlt in den Render Variables!")
        return False

    try:
        datum_str = datetime.now().strftime('%d.%m.%Y %H:%M')
        betreff = f"📸 Neues Flipchart-Foto: {thema if thema else datum_str}"
        
        body_text = f"Hallo zusammen,\n\nanbei befindet sich ein neues Flipchart-Foto vom {datum_str}.\n"
        if thema:
            body_text += f"Thema / Betreff: {thema}\n"
        body_text += "\nViele Grüße,\nBMI Deutschland GmbH"

        # Bild in Base64 umwandeln
        attachments = []
        if foto_path and os.path.exists(foto_path):
            with open(foto_path, "rb") as f:
                encoded_string = base64.b64encode(f.read()).decode('utf-8')
                attachments.append({
                    "filename": os.path.basename(foto_path),
                    "content": encoded_string
                })

        # Resend API Payload
        payload = {
            "from": "BMI Flipchart <onboarding@resend.dev>",
            "to": [empfaenger_email],
            "subject": betreff,
            "text": body_text,
            "attachments": attachments
        }

        req = urllib.request.Request(
            'https://api.resend.com/emails',
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )

        with urllib.request.urlopen(req) as response:
            if response.status in [200, 201]:
                print("✅ E-Mail erfolgreich über API versendet!")
                return True

        return False
    except Exception as e:
        print(f"❌ FEHLER BEIM E-MAIL-VERSAND (API): {str(e)}")
        return False

# --- DATENBANK INITIALISIEREN ---
def init_db():
    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ausschuss (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT,
            schicht TEXT,
            arbeitsplatz TEXT,
            fehlergrund TEXT,
            stueckzahl INTEGER,
            foto TEXT,
            zeitstempel TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- MASKENTEMPLATE ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMI Deutschland GmbH - Qualitäts- & Flipchart-Erfassung</title>
    <style>
        :root { --bmi-blue: #009ee3; --bmi-dark: #0f172a; --bmi-bg: #f0f9ff; }
        body { font-family: -apple-system, sans-serif; background-color: var(--bmi-bg); margin: 0; padding: 12px; color: #334155; }
        .card { max-width: 500px; margin: 0 auto 20px auto; background: white; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,158,227,0.12); padding: 20px; border-top: 8px solid var(--bmi-blue); }
        .header { text-align: center; border-bottom: 2px solid #e0f2fe; padding-bottom: 15px; margin-bottom: 20px; }
        .logo-box { background-color: var(--bmi-blue); color: white; display: inline-block; font-size: 32px; font-weight: 900; padding: 6px 20px; border-radius: 8px; }
        .sub-title { font-size: 13px; color: #0369a1; text-transform: uppercase; font-weight: 800; margin-top: 6px; }
        .form-group { margin-bottom: 18px; }
        label { display: block; font-weight: 700; font-size: 14px; margin-bottom: 6px; color: var(--bmi-dark); }
        input, select { width: 100%; padding: 12px; border: 2px solid #bae6fd; border-radius: 10px; font-size: 16px; box-sizing: border-box; background-color: #fff; }
        .btn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .btn-option { background: #f0f9ff; border: 2px solid #bae6fd; padding: 12px 6px; border-radius: 10px; text-align: center; font-weight: 700; font-size: 14px; cursor: pointer; color: #0369a1; }
        input[type="radio"] { display: none; }
        input[type="radio"]:checked + .btn-option { background-color: var(--bmi-blue); color: white; border-color: var(--bmi-blue); }
        .save-btn { width: 100%; background-color: #16a34a; color: white; font-size: 18px; font-weight: 800; padding: 16px; border: none; border-radius: 12px; cursor: pointer; margin-top: 10px; }
        .send-email-btn { width: 100%; background-color: #009ee3; color: white; font-size: 18px; font-weight: 800; padding: 16px; border: none; border-radius: 12px; cursor: pointer; margin-top: 10px; }
        .success-box { background-color: #dcfce7; color: #166534; padding: 12px; border-radius: 10px; text-align: center; font-weight: 700; margin-bottom: 15px; border: 1px solid #bbf7d0; }
        .error-box { background-color: #fee2e2; color: #991b1b; padding: 12px; border-radius: 10px; text-align: center; font-weight: 700; margin-bottom: 15px; border: 1px solid #fca5a5; }
        .section-title { font-weight: 800; color: #0369a1; margin-top: 0; border-bottom: 2px solid #e0f2fe; padding-bottom: 8px; }
    </style>
</head>
<body>

<!-- CARD 1: FLIPCHART VERTEILER -->
<div class="card" style="border-top-color: #009ee3;">
    <h3 class="section-title">📸 Flipchart an Verteiler senden</h3>

    {% if email_sent == '1' %}
    <div class="success-box">📧 Flipchart-Foto wurde erfolgreich per E-Mail versendet!</div>
    {% elif email_sent == '0' %}
    <div class="error-box">⚠️ E-Mail konnte nicht gesendet werden! Bitte RESEND_API_KEY auf Render prüfen.</div>
    {% endif %}

    <form action="/send-flipchart" method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>📌 Thema / Betreff (Optional)</label>
            <input type="text" name="thema" placeholder="z. B. Schichtübergabe / KVP Meeting">
        </div>

        <div class="form-group">
            <label>✉️ Verteiler E-Mail Adresse</label>
            <input type="email" name="verteiler" placeholder="verteiler@bmi-deutschland.de" required>
        </div>

        <div class="form-group">
            <label>📷 Flipchart abfotografieren</label>
            <input type="file" name="flipchart_foto" accept="image/*" capture="environment" required>
        </div>

        <button type="submit" class="send-email-btn">🚀 FLIPCHART JETZT SENDEN</button>
    </form>
</div>

<!-- CARD 2: QUALITÄTS-ERFASSUNG -->
<div class="card">
    <div class="header">
        <div class="logo-box">BMI</div>
        <div class="sub-title">Deutschland GmbH • Gießerei Qualitätssicherung</div>
    </div>

    {% if success %}
    <div class="success-box">✅ Ausschuss erfolgreich gespeichert!</div>
    {% endif %}

    <form action="/speichern" method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label>📅 Datum</label>
            <input type="date" name="datum" value="{{ heute }}" required>
        </div>

        <div class="form-group">
            <label>⏰ Schicht</label>
            <div class="btn-grid">
                <label><input type="radio" name="schicht" value="Früh" checked><div class="btn-option">🌅 Früh</div></label>
                <label><input type="radio" name="schicht" value="Spät"><div class="btn-option">🌆 Spät</div></label>
                <label><input type="radio" name="schicht" value="Nacht"><div class="btn-option">🌙 Nacht</div></label>
            </div>
        </div>

        <div class="form-group">
            <label>📍 Arbeitsplatz / Maschine</label>
            <select name="arbeitsplatz" required>
                <optgroup label="Gießmaschinen">
                    <option value="Gießmaschine 1">Gießmaschine 1</option>
                    <option value="Gießmaschine 2">Gießmaschine 2</option>
                    <option value="Gießmaschine 3">Gießmaschine 3</option>
                    <option value="Gießmaschine 4">Gießmaschine 4</option>
                    <option value="Gießmaschine 5">Gießmaschine 5</option>
                    <option value="Gießmaschine 6">Gießmaschine 6</option>
                    <option value="Gießmaschine 7">Gießmaschine 7</option>
                </optgroup>
                <optgroup label="Bearbeitung">
                    <option value="Bohrstation 1">Bohrstation 1</option>
                    <option value="Bohrstation 2">Bohrstation 2</option>
                    <option value="Bohrstation 3">Bohrstation 3</option>
                    <option value="Schleifzelle">Schleifzelle</option>
                    <option value="Fräsmaschine">Fräsmaschine</option>
                </optgroup>
            </select>
        </div>

        <div class="form-group">
            <label>⚠️ Fehlergrund</label>
            <div class="btn-grid" style="grid-template-columns: repeat(2, 1fr);">
                <label><input type="radio" name="fehlergrund" value="Blasen" checked><div class="btn-option">🫧 Blasen</div></label>
                <label><input type="radio" name="fehlergrund" value="Risse"><div class="btn-option">⚡ Risse</div></label>
                <label><input type="radio" name="fehlergrund" value="Kaltguss"><div class="btn-option">❄️ Kaltguss</div></label>
                <label><input type="radio" name="fehlergrund" value="Einfallstellen"><div class="btn-option">🕳️ Einfallstellen</div></label>
                <label style="grid-column: span 2;"><input type="radio" name="fehlergrund" value="Sonstiges"><div class="btn-option">❓ Sonstiges</div></label>
            </div>
        </div>

        <div class="form-group">
            <label>🔢 Stückzahl Ausschuss</label>
            <input type="number" name="stueckzahl" value="1" min="1" required>
        </div>

        <div class="form-group">
            <label>📷 Foto vom Fehler (Optional)</label>
            <input type="file" name="foto" accept="image/*" capture="environment">
        </div>

        <button type="submit" class="save-btn">💾 AUSSCHUSS SPEICHERN</button>
    </form>
    
    <a href="/liste" style="display:block; text-align:center; margin-top:15px; color:#0284c7; font-weight:bold; text-decoration:none;">📊 Gespeicherte Einträge ansehen</a>
</div>

</body>
</html>
'''

# --- ÜBERSICHTSTEMPLATE (BROWSER-LISTE) ---
LIST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMI - Erfasste Meldungen</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        h2 { color: #009ee3; margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { padding: 12px; border: 1px solid #e2e8f0; text-align: left; }
        th { background-color: #009ee3; color: white; }
        tr:nth-child(even) { background-color: #f8fafc; }
        .btn { display: inline-block; background: #009ee3; color: white; padding: 10px 15px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-bottom: 15px; }
        .img-link { color: #0284c7; font-weight: bold; text-decoration: none; }
    </style>
</head>
<body>

<div class="container">
    <h2>📊 Erfasste Ausschussmeldungen</h2>
    <a href="/" class="btn">⬅️ Zurück zur Erfassung</a>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Datum</th>
                <th>Schicht</th>
                <th>Arbeitsplatz</th>
                <th>Fehlergrund</th>
                <th>Stk.</th>
                <th>Foto</th>
            </tr>
        </thead>
        <tbody>
            {% for row in eintraege %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td><b>{{ row[5] }}</b></td>
                <td>
                    {% if row[6] %}
                    <a href="/uploads/{{ row[6] }}" target="_blank" class="img-link">🖼️ Foto</a>
                    {% else %}
                    -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

</body>
</html>
'''

# --- ROUTEN ---
@app.route('/')
def index():
    heute = datetime.now().strftime('%Y-%m-%d')
    success = request.args.get('success')
    email_sent = request.args.get('email_sent')
    return render_template_string(HTML_TEMPLATE, heute=heute, success=success, email_sent=email_sent)

@app.route('/send-flipchart', methods=['POST'])
def send_flipchart():
    thema = request.form.get('thema', '')
    verteiler = request.form.get('verteiler')
    foto = request.files.get('flipchart_foto')

    if foto and foto.filename != '':
        dateiname = f"flipchart_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{foto.filename}"
        foto_pfad = os.path.join(app.config['UPLOAD_FOLDER'], dateiname)
        foto.save(foto_pfad)

        # E-Mail via API versenden
        erfolg = send_flipchart_email(verteiler, foto_pfad, thema)
        status = "1" if erfolg else "0"
        return redirect(url_for('index', email_sent=status))

    return redirect(url_for('index', email_sent="0"))

@app.route('/speichern', methods=['POST'])
def speichern():
    datum = request.form.get('datum')
    schicht = request.form.get('schicht')
    arbeitsplatz = request.form.get('arbeitsplatz')
    fehlergrund = request.form.get('fehlergrund')
    stueckzahl = request.form.get('stueckzahl')
    
    foto = request.files.get('foto')
    foto_pfad = ""
    if foto and foto.filename != '':
        dateiname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{foto.filename}"
        foto_pfad = dateiname
        foto.save(os.path.join(app.config['UPLOAD_FOLDER'], dateiname))

    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ausschuss (datum, schicht, arbeitsplatz, fehlergrund, stueckzahl, foto)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (datum, schicht, arbeitsplatz, fehlergrund, stueckzahl, foto_pfad))
    conn.commit()
    conn.close()

    return redirect(url_for('index', success=1))

@app.route('/liste')
def liste():
    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, datum, schicht, arbeitsplatz, fehlergrund, stueckzahl, foto FROM ausschuss ORDER BY id DESC')
    eintraege = cursor.fetchall()
    conn.close()
    return render_template_string(LIST_TEMPLATE, eintraege=eintraege)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/export')
def export():
    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, datum, schicht, arbeitsplatz, fehlergrund, stueckzahl, zeitstempel FROM ausschuss')
    data = cursor.fetchall()
    conn.close()

    csv_data = "ID,Datum,Schicht,Arbeitsplatz,Fehlergrund,Stueckzahl,Zeitstempel\n"
    for row in data:
        csv_data += f'"{row[0]}","{row[1]}","{row[2]}","{row[3]}","{row[4]}","{row[5]}","{row[6]}"\n'

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Type": "text/csv; charset=utf-8"}
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
