// womenfootballscouting.com/oyuncu/* → wfs-oyuncu.pages.dev proxy'si.
// Ayrıca /robots.txt'i servis eder (SEO sitemap keşfi için).
// Diğer tüm trafik Render'daki Streamlit uygulamasına dokunulmadan akar
// (route pattern'leri yalnız /oyuncu* ve /robots.txt'i yakalar).
export default {
  async fetch(req) {
    const url = new URL(req.url);
    let p = url.pathname;
    if (p !== "/robots.txt") {
      p = p.replace(/^\/oyuncu\/?/, "/");
      if (p === "") p = "/";
    }
    const hedef = "https://wfs-oyuncu.pages.dev" + p + url.search;
    const res = await fetch(hedef, {
      headers: { Accept: req.headers.get("Accept") || "*/*" },
      cf: { cacheTtl: 3600, cacheEverything: true },
    });
    const out = new Response(res.body, res);
    out.headers.set("Cache-Control", "public, max-age=3600");
    return out;
  },
};
