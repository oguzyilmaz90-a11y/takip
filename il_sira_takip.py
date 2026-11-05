
import os
import re
import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.vergibulustayi.com/tercih/sonuc"
DOSYA = "il_siralari.json"

ILLER = {"ANKARA", "İSTANBUL", "KOCAELİ"}

TOKEN = os.getenv("TELEGRAM_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def telegram(mesaj):
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("Telegram bilgileri eksik.")

    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": mesaj},
        timeout=20
    )
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError("Telegram mesaji gonderilemedi.")


def siralari_oku():
    r = requests.get(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    sonuc = {}

    for tablo in soup.find_all("table"):
        basliklar = [
            th.get_text(" ", strip=True).upper()
            for th in tablo.select("thead th")
        ]

        if not any("EN DÜŞÜK" in b for b in basliklar):
            continue

        for tr in tablo.select("tbody tr"):
            hucreler = [
                td.get_text(" ", strip=True)
                for td in tr.find_all("td")
            ]

            if len(hucreler) < 6:
                continue

            il = hucreler[0].upper()
            ilce = hucreler[1].upper()

            if il not in ILLER:
                continue

            sira_metni = hucreler[5]
            eslesme = re.search(r"\d+", sira_metni)
            sira = int(eslesme.group()) if eslesme else None

            sonuc[f"{il} - {ilce}"] = sira

        if sonuc:
            break

    if not sonuc:
        raise RuntimeError(
            "Il bazli liste okunamadi. "
            "Tablo yapisi kontrol edilmeli."
        )

    return sonuc


def kontrol():
    yeni = siralari_oku()

    if not os.path.exists(DOSYA):
        with open(DOSYA, "w", encoding="utf-8") as f:
            json.dump(yeni, f, ensure_ascii=False, indent=2)
        print("Ilk kontrol tamamlandi. Siralar kaydedildi.")
        return

    with open(DOSYA, encoding="utf-8") as f:
        eski = json.load(f)

    for yer, yeni_sira in yeni.items():
        eski_sira = eski.get(yer)

        if yer not in eski:
            continue

        if eski_sira != yeni_sira:
            mesaj = (
                "🔔 YERLEŞME SIRASI DEĞİŞTİ\n\n"
                f"📍 {yer}\n"
                f"Önceki sıra: {eski_sira if eski_sira is not None else '-'}\n"
                f"Yeni sıra: {yeni_sira if yeni_sira is not None else '-'}"
            )
            telegram(mesaj)
            print(f"Bildirim gonderildi: {yer}")

    with open(DOSYA, "w", encoding="utf-8") as f:
        json.dump(yeni, f, ensure_ascii=False, indent=2)

    print(f"{len(yeni)} yer kontrol edildi.")


if __name__ == "__main__":
    kontrol()
  
