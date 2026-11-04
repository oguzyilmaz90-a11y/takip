
from flask import Flask, jsonify
import os
import subprocess

app = Flask(__name__)

@app.route("/")
def home():
    return "Tercih takip servisi aktif."

@app.route("/kontrol")
def kontrol():
    anahtar = os.environ.get("KONTROL_ANAHTARI", "")

    from flask import request
    if not anahtar or request.args.get("key") != anahtar:
        return jsonify({"hata": "Yetkisiz erisim"}), 403

    sonuc = subprocess.run(
        ["python", "son_islemler_takip.py"],
        capture_output=True,
        text=True,
        timeout=90
    )

    if sonuc.returncode != 0:
        return jsonify({
            "durum": "hata",
            "detay": sonuc.stderr[-1000:]
        }), 500

    return jsonify({"durum": "basarili"})
  
