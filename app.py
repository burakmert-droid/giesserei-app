import os
import sqlite3
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, Response

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

# --- MASKENTEMPLATE (ERFASSUNG) ---
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMI Deutschland GmbH - Qualitäts-Erfassung</title>
    <style>
        :root {
            --bmi-blue: #009ee3;
            --bmi-dark: #0f172a;
            --bmi-bg: #f0f9ff;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bmi-bg);
            margin: 0;
            padding: 12px;
            color: #334155;
        }
        .card {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,158,227,0.12);
            padding: 20px;
            border-top: 8px solid var(--bmi-blue);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #e0f2fe;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .logo-box {
            background-color: var(--bmi-blue);
            color: white;
            display: inline-block;
            font-size: 32px;
            font-weight: 900;
            letter-spacing: 2px;
            padding: 6px 20px;
            border-radius: 8px;
        }
        .sub-title {
            font-size: 13px;
            color: #0369a1;
            text-transform: uppercase;
            font-weight: 800;
            margin-top: 6px;
        }
        .form-group {
            margin-bottom: 18px;
        }
        label {
            display: block;
            font-weight: 700;
            font-size: 14px;
            margin-bottom: 6px;
            color: var(--bmi-dark);
        }
        input, select {
            width: 100%;
            padding: 12px;
            border: 2px solid #bae6fd;
            border-radius: 10px;
            font-size: 16px;
            box-sizing: border-box;
            background-color: #fff;
            color: #0f172a;
        }
        .btn-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
        }
        .btn-option {
            background: #f0f9ff;
            border: 2px solid #bae6fd;
            padding: 12px 6px;
            border-radius: 10px;
            text-align: center;
            font-weight: 700;
            font-size: 14px;
            cursor: pointer;
            color: #0369a1;
            transition: all 0.2s;
        }
        input[type="radio"] {
            display: none;
        }
        input[type="radio"]:checked + .btn-option {
            background-color: var(--bmi-blue);
            color: white;
            border-color: var(--bmi-blue);
        }
        .save-btn {
            width: 100%;
            background-color: #16a34a;
            color: white;
            font-size: 18px;
            font-weight: 800;
            padding: 16px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            margin-top: 10px;
            box-shadow: 0 4px 12px rgba(22, 163, 74, 0.3);
        }
        .success-box {
            background-color: #dcfce7;
            color: #166534;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            font-weight: 700;
            margin-bottom: 15px;
            border: 1px solid #bbf7d0;
        }
        .list-link {
            display: block;
            text-align: center;
            margin-top: 15px;
            color: #0284c7;
            font-weight: bold;
            text-decoration: none;
        }
    </style>
</head>
<body>

<div class="card">
    <div class="header">
        <div class="logo-box">BMI</div>
        <div class="sub-title">Deutschland GmbH • Gießerei Qualitätssicherung</div>
    </div>

    {% if success %}
    <div class="success-box">
        ✅ Erfolgreich gespeichert!
    </div>
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

        <button type="submit" class="save-btn">💾 SPEICHERN</button>
    </form>
    
    <a href="/liste" class="list-link">📊 Gespeicherte Einträge ansehen</a>
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
    return render_template_string(HTML_TEMPLATE, heute=heute, success=success)

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
        foto.save(os.path.join(app.config['UPLOAD_FOLDER'], dateiname))
        foto_pfad = dateiname

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

# --- GOOGLE SHEETS LIVE EXPORT ---
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
