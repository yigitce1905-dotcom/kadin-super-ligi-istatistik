"""Canlı siteye GİRİŞSİZ bir ziyaretçi gibi bağlanır (Streamlit websocket), sayfayı çalıştırır ve çizilen metni döker.
Kullanım: python canli_ziyaretci.py "kulup=kups&dil=EN&k=claude-test" [ikinci çalışma: 1/0]
Kendi sitemizin kendi sayfası için doğrulama aracı (ziyaret sayacı + link kaydı + ziyaretçi görünümü)."""
import asyncio
import html
import re
import sys
import time

from streamlit.proto.BackMsg_pb2 import BackMsg
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
import websockets

sys.stdout.reconfigure(encoding="utf-8")
SITE = "womenfootballscouting.com"
qs = sys.argv[1] if len(sys.argv) > 1 else "kulup=kups&dil=EN&k=claude-test"
ikinci = (sys.argv[2] == "1") if len(sys.argv) > 2 else True


def sade(s):
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S)
    s = re.sub(r"<span style='display:inline-block;height:10px[^>]*></span>", "[GİZLİ]", s)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


async def calistir(ws, etiket):
    m = BackMsg()
    m.rerun_script.query_string = qs
    t0 = time.perf_counter()
    await ws.send(m.SerializeToString())
    metinler, tur = [], set()
    while True:
        ham = await asyncio.wait_for(ws.recv(), timeout=90)
        f = ForwardMsg()
        f.ParseFromString(ham)
        t = f.WhichOneof("type")
        tur.add(t)
        if t == "delta" and f.delta.WhichOneof("type") == "new_element":
            e = f.delta.new_element
            if e.WhichOneof("type") == "markdown":
                x = sade(e.markdown.body)
                if x:
                    metinler.append(x)
        if t == "script_finished":
            break
    print(f"--- {etiket}: {time.perf_counter() - t0:.1f} sn · {len(metinler)} metin bloğu · mesaj türleri {sorted(tur)}")
    return metinler


async def main():
    ws = await websockets.connect(f"wss://{SITE}/_stcore/stream", origin=f"https://{SITE}", subprotocols=["streamlit"],
                                  max_size=300 * 1024 * 1024, open_timeout=40)
    m = await calistir(ws, "1. çalışma")
    for x in m:
        print("  ·", x[:330])
    if ikinci:
        await asyncio.sleep(1.5)
        m2 = await calistir(ws, "2. çalışma (çerez bileşeni sonrası yeniden çalışmayı taklit)")
        print("    ikinci çalışmada blok sayısı:", len(m2))
    await asyncio.sleep(8)          # ziyaret satırı 6 sn gecikmeyle yazılıyor
    await ws.close()


asyncio.run(main())
