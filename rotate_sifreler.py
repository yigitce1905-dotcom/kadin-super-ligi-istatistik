# -*- coding: utf-8 -*-
"""
Kulüp + admin şifrelerini GÜVENLİ şekilde yeniler (bcrypt hash).

- Şifreleri getpass ile girersin → EKRANDA GÖRÜNMEZ, hiçbir dosyaya yazılmaz.
- Sadece bcrypt hash'leri club_credentials.json'a işlenir (düz şifre asla saklanmaz).
- Boş bırakılan (sadece Enter) kullanıcının şifresi DEĞİŞMEZ.

Neden gerekli: club_credentials.json git geçmişinde olduğu için eski hash'ler
herkese açık. Şifreleri yenileyince eski hash'ler işe yaramaz hale gelir.

Kullanım:
    python rotate_sifreler.py            # tüm kullanıcıları sırayla sor
    python rotate_sifreler.py admin      # sadece 'admin'i yenile

Sonra: güncellenen club_credentials.json'ı Render > Secret Files'a yeniden yükle.
"""
import json
import sys
import getpass
import pathlib

import bcrypt

YOL = pathlib.Path(__file__).parent / "club_credentials.json"


def main():
    if not YOL.exists():
        print(f"[HATA] {YOL.name} bulunamadı.")
        return
    creds = json.loads(YOL.read_text(encoding="utf-8"))

    hedef = sys.argv[1] if len(sys.argv) > 1 else None
    if hedef and hedef not in creds:
        print(f"[HATA] '{hedef}' kullanıcısı yok. Mevcut: {', '.join(creds)}")
        return

    kullanicilar = [hedef] if hedef else list(creds)
    print(f"{len(kullanicilar)} kullanıcı. Boş bırakıp Enter = değiştirme.\n")

    degisen = 0
    for ku in kullanicilar:
        rol = creds[ku].get("rol", "kulup")
        s1 = getpass.getpass(f"  {ku} ({rol}) yeni şifre: ")
        if not s1:
            print("    → atlandı")
            continue
        if len(s1) < 8:
            print("    → ÇOK KISA (en az 8 karakter), atlandı")
            continue
        s2 = getpass.getpass(f"  {ku} şifre tekrar       : ")
        if s1 != s2:
            print("    → şifreler uyuşmadı, atlandı")
            continue
        creds[ku]["hash"] = bcrypt.hashpw(s1.encode(), bcrypt.gensalt()).decode()
        degisen += 1
        print("    → güncellendi ✓")

    if degisen:
        YOL.write_text(json.dumps(creds, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[OK] {degisen} şifre yenilendi → {YOL.name}")
        print("Şimdi bu dosyayı Render > Secret Files'a yeniden yükle.")
    else:
        print("\nDeğişiklik yapılmadı.")


if __name__ == "__main__":
    main()
