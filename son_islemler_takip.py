
#!/usr/bin/env python3
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

URL = "https://www.vergibulustayi.com/tercih/sonuc"
DOSYA = "gorulen.json"
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TEK_SEFER = os.getenv("TEK_SEFER", "1") == "1"

def log(mesaj):
    print(f"[{datetime.now():%H:%M:%S}] {mesaj}", flush=True)

def telegram(mesaj):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram token veya chat ID eksik.")

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": mesaj},
        timeout=20
    )
    r.raise_for_status()
    cevap = r.json()
    if not cevap.get("ok"):
        raise RuntimeError(f"Telegram bildirimi başarısız: {cevap}")

def kayitlari_oku():
    r = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    baslik = soup.find(
        string=lambda s: s and "Son Yapılan İşlemler" in s
    )
    if not baslik:
        raise RuntimeError("Son Yapılan İşlemler başlığı bulunamadı.")

    tablo = baslik.find_parent().find_next("table")
    if not tablo:
        raise RuntimeError("İşlem tablosu bulunamadı.")

    kayitlar = []

    for tr in tablo.select("tr"):
        hucreler = [
            td.get_text(" ", strip=True)
            for td in tr.find_all(["td", "th"])
        ]

        if len(hucreler) < 5:
            continue

        tarih, ad, sira, islem, detay = hucreler[:5]

        if not re.fullmatch(r"\d{1,3}", sira):
            continue

        sira_no = int(sira)
        if not 1 <= sira_no <= 135:
            continue

        if not re.match(r"\d{2}\.\d{2}\.\d{4}", tarih):
            continue

        if islem not in (
            "Yeni Tercih",
            "Tercih Güncellendi",
            "Tercih Silindi"
        ):
            continue

        kayit = {
            "tarih": tarih,
            "ad": ad,
            "sira": sira_no,
            "islem": islem,
            "detay": detay
        }
        kayitlar.append(kayit)

    if not kayitlar:
        raise RuntimeError(
            "1-135 arasında işlem bulunamadı. "
            "Tablo yapısı kontrol edilmeli."
        )

    log(f"Başarı sırası 1-135: {len(kayitlar)} işlem okundu.")
    return kayitlar

def kimlik(kayit):
    veri = json.dumps(
        kayit, ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(veri.encode("utf-8")).hexdigest()

def kaydedilmisleri_oku():
    if not os.path.exists(DOSYA):
        return None
    with open(DOSYA, encoding="utf-8") as f:
        veri = json.load(f)
    if not isinstance(veri, list):
        raise RuntimeError("Kayıt dosyasının biçimi geçersiz.")
    return set(veri)

def kaydet(gorulen):
    gecici = DOSYA + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(sorted(gorulen), f, ensure_ascii=False)
    os.replace(gecici, DOSYA)

def mesaj_hazirla(k):
    return (
        f"🔔 YENİ TERCİH İŞLEMİ\n\n"
        f"Başarı sırası: {k['sira']}\n"
        f"Ad Soyad: {k['ad']}\n"
        f"İşlem: {k['islem']}\n"
        f"Tarih: {k['tarih']}\n"
        f"{k['detay']}"
    )

def kontrol():
    kayitlar = kayitlari_oku()
    gorulen = kaydedilmisleri_oku()

    if gorulen is None:
        kaydet({kimlik(k) for k in kayitlar})
        log("İlk çalışma tamamlandı. Mevcut işlemler kaydedildi.")
        return

    yeniler = [
        k for k in kayitlar
        if kimlik(k) not in gorulen
    ]

    yeniler.sort(
        key=lambda k: datetime.strptime(
            k["tarih"], "%d.%m.%Y %H:%M"
        )
    )

    if not yeniler:
        log("Yeni işlem yok.")
    else:
        log(f"{len(yeniler)} yeni işlem bulundu.")
        for k in yeniler:
            telegram(mesaj_hazirla(k))
            log(f"Telegram gönderildi: #{k['sira']} {k['ad']}")
            gorulen.add(kimlik(k))
            kaydet(gorulen)

    gorulen.update(kimlik(k) for k in kayitlar)
    kaydet(gorulen)

if __name__ == "__main__":
    try:
        while True:
            kontrol()
            if TEK_SEFER:
                break
            time.sleep(30)
    except Exception as e:
        log(f"HATA: {e}")
        sys.exit(1)
      
