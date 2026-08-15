import os
import sqlite3
import io
import base64
from datetime import datetime
from flask import Flask, request, redirect, url_for, send_from_directory
import qrcode

app = Flask(__name__)

# Ordner für Uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Datenbank initialisieren
def init_db():
    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ausschuss (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            datum TEXT,
            bauteil TEXT,
            grund TEXT,
            menge INTEGER,
            foto_pfad TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Globale Variable für den QR-Code
GLOBAL_QR_BASE64 = ""

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        bauteil = request.form.get('bauteil')
        grund = request.form.get('grund')
        menge = request.form.get('menge')
        foto = request.files.get('foto')
        
        foto_dateiname = ""
        if foto and foto.filename != '':
            zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S")
            foto_dateiname = f"{zeitstempel}_{foto.filename}"
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_dateiname))

        conn = sqlite3.connect('giesserei.db')
        cursor = conn.cursor()
        datum_aktuell = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor.execute('''
            INSERT INTO ausschuss (datum, bauteil, grund, menge, foto_pfad)
            VALUES (?, ?, ?, ?, ?)
        ''', (datum_aktuell, bauteil, grund, menge, foto_dateiname))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    # Alle Daten aus der Datenbank laden
    conn = sqlite3.connect('giesserei.db')
    cursor = conn.cursor()
    cursor.execute('SELECT datum, bauteil, grund, menge, foto_pfad FROM ausschuss ORDER BY id DESC')
    eintraege = cursor.fetchall()
    conn.close()

    tabelle_html = ""
    for e in eintraege:
        foto_link = f'<a href="/uploads/{e[4]}" target="_blank" style="color: #007bff; font-weight: bold;">📷 Ansehen</a>' if e[4] else "Kein Foto"
        tabelle_html += f"""
        <tr style="border-bottom: 1px solid #ddd;">
            <td style="padding: 12px 8px;">{e[0]}</td>
            <td style="padding: 12px 8px;"><b>{e[1]}</b></td>
            <td style="padding: 12px 8px;">{e[2]}</td>
            <td style="padding: 12px 8px; text-align: center;"><b>{e[3]}</b></td>
            <td style="padding: 12px 8px;">{foto_link}</td>
        </tr>
        """

    # QR-Code Anzeige
    qr_html = ""
    if GLOBAL_QR_BASE64:
        qr_html = f'''
        <div style="text-align: center; margin-bottom: 25px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <p style="margin-top: 0; font-weight: bold; color: #333; font-size: 16px;">📱 Mit dem Handy scannen (LTE/5G & WLAN):</p>
            <img src="data:image/png;base64,{GLOBAL_QR_BASE64}" style="width: 220px; height: 220px; border: 2px solid #333; border-radius: 8px;">
        </div>
        '''

    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gießerei Erfassung</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 15px; background-color: #f0f2f5; }}
            .container {{ max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            h2 {{ text-align: center; color: #1a1a1a; margin-top: 0; }}
            label {{ font-size: 16px; font-weight: bold; color: #444; display: block; margin-top: 15px; }}
            input, select {{ width: 100%; padding: 14px; margin-top: 6px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 8px; font-size: 16px; background-color: #f9f9f9; }}
            input[type="file"] {{ background-color: white; padding: 10px; }}
            button {{ width: 100%; padding: 16px; background-color: #d9534f; color: white; border: none; font-size: 18px; font-weight: bold; cursor: pointer; border-radius: 8px; margin-top: 25px; }}
            button:active {{ background-color: #c9302c; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }}
            th {{ background-color: #222; color: white; padding: 10px; text-align: left; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔥 Gießerei Erfassung</h2>
            
            {qr_html}

            <form method="POST" enctype="multipart/form-data">
                <label>Bauteil Name / Nummer:</label>
                <input type="text" name="bauteil" placeholder="z.B. Gehäuse V8 / Guss-ID 402" required>

                <label>Ausschussgrund:</label>
                <select name="grund">
                    <option value="Lunker / Porosität">Lunker / Porosität</option>
                    <option value="Formfehler / Sandeinschluss">Formfehler / Sandeinschluss</option>
                    <option value="Rissbildung">Rissbildung</option>
                    <option value="Maßabweichung">Maßabweichung</option>
                    <option value="Kaltlauf">Kaltlauf</option>
                </select>

                <label>Menge (Stück):</label>
                <input type="number" name="menge" value="1" min="1" required>

                <label>Foto vom Gussfehler (optional):</label>
                <input type="file" name="foto" accept="image/*">

                <button type="submit">Ausschuss Speichern</button>
            </form>

            <hr style="margin: 35px 0 20px 0; border: 0; border-top: 1px solid #eee;">

            <h3>📊 Erfasste Fehler</h3>
            <table>
                <tr>
                    <th>Datum</th>
                    <th>Bauteil</th>
                    <th>Grund</th>
                    <th>Stk</th>
                    <th>Foto</th>
                </tr>
                {tabelle_html if tabelle_html else '<tr><td colspan="5" style="padding:15px; text-align:center;">Noch keine Einträge vorhanden.</td></tr>'}
            </table>
        </div>
    </body>
    </html>
    """

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    try:
        from pyngrok import ngrok, conf
        conf.get_default().auth_token = "3Hwd4Uh1XHedLe6KHzHHiPq5doX_4bKFz2pgxQMovhAugoxzc"
        public_url = ngrok.connect(5000).public_url
        
        # QR-Code direkt für den HTML-Code erzeugen
        qr_img = qrcode.make(public_url)
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        GLOBAL_QR_BASE64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        print("\n" + "="*60)
        print("📱 ÖFFENTLICHE HANDY-ADRESSE (LTE/5G & WLAN):")
        print(f"   {public_url}")
        print("="*60 + "\n")
    except Exception as e:
        print("\n⚠️ ngrok/QR-Code konnte nicht geladen werden:", e)

    app.run(port=5000, debug=False)