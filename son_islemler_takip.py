#!/usr/bin/env python3
"""vergibulustayi.com/tercih/sonuc sayfasındaki "Son Yapılan İşlemler"
listesinde yeni giriş çıkınca bildirim gönderir.

Kurulum:  pip install requests
Çalıştır: python son_islemler_takip.py
"""
import html
import json
import os
import random
import re
import time
from datetime import datetime

import requests

# ---------------- AYARLAR ----------------
URL = "https://www.vergibulustayi.com/tercih/sonuc"
ARALIK = 30                    # saniye
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")      # @BotFather'dan alınan token
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")  # @userinfobot'tan öğrenilen chat id
TEK_SEFER = os.environ.get("TEK_SEFER") == "1"             # GitHub Actions: bir kez kontrol edip çık
GORULEN_DOSYA = "gorulen.json" # görülen girişler burada tutulur (yeniden başlatınca tekrar bildirmez)
FILTRE = []                    # boş: tüm yeni girişler. Dolu: sadece bu kelimelerden birini içerenler
                               # (BÜYÜK harfle yaz, örn. ["ANKARA", "KOCAELİ", "BAŞARI 47"])
# -----------------------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

# 04.11.2026 17:59 BARIŞ KISA 47 Tercih Güncellendi Tercihler: İZMİR - MERKEZ
SATIR_RE = re.compile(
    r"(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})\s+(.+?)\s+(\d{1,4})\s+"
    r"(Yeni Tercih|Tercih Güncellendi|Tercih Silindi)\s*(.*)"
)


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def bildir(mesaj):
    log("BİLDİRİM:\n" + mesaj)
    if not (TELEGRAM_TOKEN and TELEGRAM_CHAT_ID):
        print("\a", end="")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": mesaj[:4000]},
            timeout=10,
        )
    except requests.RequestException as e:
        log(f"Telegram hatası: {e}")


def girisleri_ayikla(sayfa):
    """HTML'den işlem satırlarını (tarih, ad, sıra, işlem, detay) listesi olarak döndürür."""
    sayfa = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", sayfa)
    sayfa = re.sub(r"(?i)</tr>|<br\s*/?>", "\n", sayfa)
    sayfa = re.sub(r"<[^>]+>", " ", sayfa)
    sayfa = html.unescape(sayfa)
    sonuc = []
    for satir in sayfa.split("\n"):
        satir = re.sub(r"\s+", " ", satir).strip()
        m = SATIR_RE.search(satir)
        if m:
            tarih, ad, sira, islem, detay = (g.strip() for g in m.groups())
            sonuc.append((tarih, ad, sira, islem, detay))
    return sonuc


def yukle():
    if os.path.exists(GORULEN_DOSYA):
        with open(GORULEN_DOSYA, encoding="utf-8") as f:
            return set(json.load(f))
    return None


def kaydet(gorulen):
    with open(GORULEN_DOSYA, "w", encoding="utf-8") as f:
        json.dump(sorted(gorulen), f, ensure_ascii=False)


def bicimle(g):
    tarih, ad, sira, islem, detay = g
    return f"{tarih} | {ad} (#{sira}) | {islem}\n{detay}"


def filtrele(girisler):
    if not FILTRE:
        return girisler
    return [g for g in girisler
            if any(k in f"{g[1]} BAŞARI {g[2]} {g[4]}".upper() for k in FILTRE)]


def main():
    session = requests.Session()
    gorulen = yukle()
    ilk_calisma = gorulen is None
    gorulen = gorulen or set()
    hata = 0
    log(f"Takip başladı: {URL}")
    while True:
        try:
            r = session.get(URL, headers=HEADERS, timeout=20)
            r.raise_for_status()
            girisler = girisleri_ayikla(r.text)
            if not girisler:
                log("Uyarı: sayfada işlem satırı bulunamadı (yapı değişmiş olabilir).")
            hata = 0
            yeniler = [g for g in girisler if "|".join(g) not in gorulen]
            gorulen.update("|".join(g) for g in girisler)
            if ilk_calisma:
                log(f"İlk çalışma: {len(girisler)} mevcut giriş kaydedildi, bildirim yok.")
                ilk_calisma = False
            elif yeniler:
                yeniler = filtrele(sorted(yeniler, key=lambda g: (g[0][6:10], g[0][3:5], g[0][0:2], g[0][11:])))
                for i in range(0, len(yeniler), 10):
                    bildir("Yeni işlem:\n\n" + "\n\n".join(bicimle(g) for g in yeniler[i:i + 10]))
            else:
                log("Yeni giriş yok.")
            kaydet(gorulen)
        except requests.RequestException as e:
            hata += 1
            log(f"İstek hatası ({hata}): {e}")
            if hata == 5:
                bildir("Siteye 5 kez üst üste ulaşılamadı.")
        if TEK_SEFER:
            break
        time.sleep(ARALIK * random.uniform(0.8, 1.2) + min(hata * 10, 120))


if __name__ == "__main__":
    main()
