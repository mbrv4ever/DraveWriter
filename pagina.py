# -*- coding: utf-8 -*-
# DraveWriter - Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""pagina.py - zet het receptenboek op bladzijden en tekent ze (scherm, PDF en drukker).

Een bladzijde is 1000 x 1414 eenheden (de verhouding van A4/A5/B5). Alles wordt eerst opgemeten
(opmaak) en daarna getekend, zodat het voorbeeld op het scherm precies gelijk is aan de PDF.
"""
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen

import os

import nevo

PB, PH = 1000.0, 1414.0
M = 72.0                         # marge
HV = 104.0                       # breedte van de kolom met hoeveelheden
INK = QColor("#2b2340")
PAARS = QColor("#6c5fc7")
LICHT = QColor("#f3effd")
GRIJS = QColor("#6f6880")
WIT = QColor("#ffffff")

LETTERS = {"titel": ("Georgia", 60, True, False), "kaft": ("Georgia", 84, True, False), "kop": ("Georgia", 30, True, False),
           "tekst": ("Segoe UI", 21, False, False), "vet": ("Segoe UI", 21, True, False), "klein": ("Segoe UI", 16, False, False),
           "cat": ("Segoe UI", 19, True, False), "info": ("Segoe UI", 19, False, False), "nr": ("Segoe UI", 20, True, False),
           "tip": ("Georgia", 22, False, True), "sub": ("Georgia", 34, False, True), "inhoud": ("Segoe UI", 25, False, False)}


_COMPACT = [False]          # iets kleinere letters als een recept dan op één bladzijde past
KLEINER = {"tekst", "vet", "info", "nr", "tip", "klein", "kop", "cat"}


def letter(soort):
    fam, px, vet, schuin = LETTERS[soort]
    if _COMPACT[0] and soort in KLEINER:
        px = max(12, round(px * 0.86))
    f = QFont(fam)
    f.setPixelSize(px)
    f.setBold(vet)
    f.setItalic(schuin)
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return f


WRAP = int(Qt.TextFlag.TextWordWrap)


def hoogte(soort, breed, tekst):
    if not tekst:
        return 0.0
    fm = QFontMetricsF(letter(soort))
    return fm.boundingRect(QRectF(0, 0, breed, 100000), WRAP, tekst).height() * 1.04 + 2


# ---------------------------------------------------------------- teksten in de goede taal
def L(nl, a, b):
    return a if nl else b


CATS = [("", "", ""), ("ontbijt", "Ontbijt", "Breakfast"), ("lunch", "Lunch", "Lunch"), ("soep", "Soep", "Soup"),
        ("voorgerecht", "Voorgerecht", "Starter"), ("hoofdgerecht", "Hoofdgerecht", "Main course"),
        ("bijgerecht", "Bijgerecht", "Side dish"), ("salade", "Salade", "Salad"), ("nagerecht", "Nagerecht", "Dessert"),
        ("gebak", "Gebak en koekjes", "Baking"), ("snack", "Hapjes en snacks", "Snacks"), ("drank", "Drankjes", "Drinks"),
        ("saus", "Sauzen", "Sauces")]


def cat_naam(code, nl):
    for c, a, b in CATS:
        if c == code:
            return a if nl else b
    return code or ""


def hoeveel_tekst(ing, factor, nl):
    e = ing.get("eenheid") or ""
    if e == "naar smaak":
        return L(nl, "naar smaak", "to taste")
    try:
        h = float(ing.get("hoeveel") or 0)
    except Exception:
        h = 0.0
    if h <= 0:
        return ""
    x = nevo.afgerond(h * factor, e) if abs(factor - 1) > 1e-9 else h
    getal = nevo.mooi_getal(x, nl)
    eenh = e if nl else nevo.EENHEDEN_EN.get(e, e)
    if e == "stuk":
        eenh = ""
    elif e == "teen" and nl:
        eenh = "teen" if x <= 1 else "tenen"
    elif e == "plak" and nl and x > 1:
        eenh = "plakken"
    elif e == "blik" and nl and x > 1:
        eenh = "blikken"
    elif e == "zakje" and nl and x > 1:
        eenh = "zakjes"
    elif e == "takje" and nl and x > 1:
        eenh = "takjes"
    elif e == "handje" and nl and x > 1:
        eenh = "handjes"
    elif e == "kopje" and nl and x > 1:
        eenh = "kopjes"
    elif e == "snufje" and nl and x > 1:
        eenh = "snufjes"
    return (getal + " " + eenh).strip()


def tijd_tekst(rec, nl):
    d = []
    if rec.get("personen"):
        d.append(L(nl, "%d personen", "serves %d") % int(rec["personen"]) if int(rec["personen"]) != 1 else L(nl, "1 persoon", "serves 1"))
    if rec.get("tijd_voor"):
        d.append(L(nl, "%d min voorbereiden", "%d min prep") % int(rec["tijd_voor"]))
    if rec.get("tijd_koken"):
        d.append(L(nl, "%d min koken", "%d min cooking") % int(rec["tijd_koken"]))
    return "   ·   ".join(d)


def voeding_regels(rec, tabel, nl):
    """[(naam, waarde-tekst, eigen?)] voor de tabel per portie, of [] als er niets bekend is."""
    w, ontbreekt, eigen_ing = nevo.bereken(rec.get("ingredienten", []), tabel, rec.get("personen") or 1)
    eigen = rec.get("voeding_eigen") or {}
    iets = any(w[s] for s in nevo.SLEUTELS) or any(v not in (None, "") for v in eigen.values())
    if not iets:
        return [], ontbreekt, False
    uit, gebruikt_eigen = [], eigen_ing
    for _c, s, a, b, eenh in nevo.STOFFEN:
        v, e = w[s], False
        if eigen.get(s) not in (None, ""):
            try:
                v, e = float(eigen[s]), True
                gebruikt_eigen = True
            except Exception:
                pass
        if s == "kcal":
            t = "%d kcal" % round(v)
        elif s == "zout":
            t = ("%.1f g" % v)
        else:
            t = ("%.1f g" % v) if v < 10 else ("%d g" % round(v))
        if nl:
            t = t.replace(".", ",")
        uit.append((a if nl else b, t, e))
    return uit, ontbreekt, gebruikt_eigen


# ---------------------------------------------------------------- opmaak: boek -> bladzijden
def bladzijden(boek, tabel, nl):
    """Lijst bladzijden: dicts met 'soort' (voor/inhoud/recept/hoofdstuk/achter) en wat er op komt."""
    if boek.get("soort") == "boek":
        return _boek_bladzijden(boek, nl)
    ps = [dict(soort="voor")]
    recepten = boek.get("recepten", [])
    inhoud = dict(soort="inhoud", regels=[])
    if boek.get("inhoud", True) and recepten:
        ps.append(inhoud)
    start = {}
    for i, rec in enumerate(recepten):
        start[i] = len(ps)
        ps.extend(_recept_paginas(boek, i, rec, tabel, nl))
    # bladzijdenummers: de voorkant telt niet mee
    for n, p in enumerate(ps):
        p["nr"] = n if p["soort"] not in ("voor",) else 0
    if inhoud in ps:
        regels, vorige = [], None
        for i, rec in enumerate(recepten):
            c = rec.get("categorie", "")
            if boek.get("inhoud_per_cat", True) and c != vorige and c:
                regels.append(("cat", cat_naam(c, nl), ""))
            vorige = c
            regels.append(("rec", rec.get("titel") or L(nl, "(zonder naam)", "(untitled)"), str(ps[start[i]]["nr"])))
        inhoud["regels"] = regels
    ps.append(dict(soort="achter", nr=0))
    return ps


def _recept_paginas(boek, ri, rec, tabel, nl, fh=330.0):
    pogingen = [(fh, False)]
    if rec.get("foto"):
        pogingen.append((200.0, False))       # kleinere foto als alles dan op één bladzijde past
        pogingen.append((200.0, True))        # en anders ook iets kleinere letters
    else:
        pogingen.append((fh, True))
    eerste = None
    for f, compact in pogingen:
        _COMPACT[0] = compact
        try:
            ps = _recept_opmaak(boek, ri, rec, tabel, nl, f)
        finally:
            _COMPACT[0] = False
        if compact:
            for p in ps:
                p["compact"] = True
        if eerste is None:
            eerste = ps
        if len(ps) == 1 and any(it[0] in ("voeding", "tip") for it in ps[0]["items"]) or len(ps) == 1:
            return ps
    return eerste


def _recept_opmaak(boek, ri, rec, tabel, nl, fh):
    factor = 1.0
    breed = PB - 2 * M
    paginas = []
    blad = dict(soort="recept", ri=ri, items=[])
    y = M
    if rec.get("foto"):
        blad["items"].append(("foto", QRectF(M, y, breed, fh), rec["foto"]))
        y += fh + 30
    cat = cat_naam(rec.get("categorie", ""), nl)
    if cat:
        blad["items"].append(("tekst", QRectF(M, y, breed, 30), "cat", PAARS, cat.upper()))
        y += 34
    titel = rec.get("titel") or L(nl, "(zonder naam)", "(untitled)")
    h = hoogte("titel", breed, titel)
    blad["items"].append(("tekst", QRectF(M, y, breed, h), "titel", INK, titel))
    y += h + 6
    info = tijd_tekst(rec, nl)
    if info:
        blad["items"].append(("tekst", QRectF(M, y, breed, 30), "info", GRIJS, info))
        y += 34
    if rec.get("intro"):
        h = hoogte("tip", breed, rec["intro"])
        blad["items"].append(("tekst", QRectF(M, y, breed, h), "tip", INK, rec["intro"]))
        y += h + 6
    y += 22
    blad["items"].append(("lijn", QRectF(M, y, breed, 0)))
    y += 26
    # -- twee kolommen: ingrediënten (links, in een vakje) en bereiding (rechts)
    kb = 300.0
    kx = M + kb + 40
    rb = PB - M - kx
    onder = PH - M - 40          # ruimte voor het bladzijdenummer
    ings = [i for i in rec.get("ingredienten", []) if (i.get("naam") or "").strip()]
    stappen = [s for s in rec.get("stappen", []) if (s or "").strip()]
    regels_ing = []
    for ing in ings:
        hv = hoeveel_tekst(ing, factor, nl)
        regels_ing.append((hv, ing.get("naam", "").strip()))

    def nieuw_blad():
        nonlocal blad
        paginas.append(blad)
        blad = dict(soort="recept", ri=ri, items=[], vervolg=True)
        blad["items"].append(("tekst", QRectF(M, M, breed, 40), "kop", INK,
                              titel + L(nl, "  (vervolg)", "  (continued)")))
        return M + 70

    # ingrediënten
    ky = y
    blokken = []
    for hv, naam in regels_ing:
        h = max(hoogte("vet", HV, hv), hoogte("tekst", kb - 36 - HV - 10, naam)) + 8
        blokken.append((naam, h, hv))
    iy = ky + 64
    stuk = []
    for b in blokken:
        if iy + b[1] > onder - 24 and stuk:
            break
        stuk.append((b, iy))
        iy += b[1]
    rest_y = iy + 18
    if blokken:
        blad["items"].append(("vak", QRectF(M, ky, kb, rest_y - ky)))
        blad["items"].append(("tekst", QRectF(M + 18, ky + 16, kb - 36, 40), "kop", INK, L(nl, "Ingrediënten", "Ingredients")))
        for (naam, h, hv), by in stuk:
            blad["items"].append(("ing", QRectF(M + 18, by, kb - 36, h), hv, naam))
    else:
        rest_y = ky
    ing_klaar = len(stuk)
    # bereiding
    sy = y
    blad["items"].append(("tekst", QRectF(kx, sy, rb, 40), "kop", INK, L(nl, "Bereiding", "Method")))
    sy += 54
    links_vrij = rest_y if ing_klaar >= len(blokken) else onder
    for n, st in enumerate(stappen, 1):
        tb = rb - 54
        h = max(40.0, hoogte("tekst", tb, st)) + 18
        if sy + h > onder:
            # past niet meer: rest op een nieuwe bladzijde, nu over de hele breedte
            if ing_klaar < len(blokken):
                pass
            sy = nieuw_blad()
            kx, rb, links_vrij = M, breed, M
            # nog ingrediënten over? die eerst
            if ing_klaar < len(blokken):
                sy = _rest_ingredienten(blad, blokken, ing_klaar, sy, nl, breed)
                ing_klaar = len(blokken)
                sy += 20
            tb = rb - 54
            h = max(40.0, hoogte("tekst", tb, st)) + 18
        blad["items"].append(("stap", QRectF(kx, sy, rb, h), n, st))
        sy += h
    if ing_klaar < len(blokken):
        sy = nieuw_blad()
        sy = _rest_ingredienten(blad, blokken, ing_klaar, sy, nl, breed)
        links_vrij = sy
    y = max(sy, links_vrij) + 26
    # -- tips en voedingswaarden onderaan
    tips = (rec.get("tips") or "").strip()
    regels, ontbreekt, eigen = voeding_regels(rec, tabel, nl)
    kop_v = L(nl, "Voedingswaarden per portie", "Nutrition per serving")
    _bron = L(nl, "Gebaseerd op gegevens van %s en eigen gegevens (*)", "Based on data from %s and own data (*)") % nevo.BRON
    hv = 44 + 30 * ((len(regels) + 1) // 2) + hoogte("klein", 520 - 44, _bron) + 14
    bron_h = hoogte("klein", kb - 44, _bron)
    hv_smal = 22 + hoogte("vet", kb - 30, kop_v) + 30 * len(regels) + bron_h + 14
    eerste = not paginas and not blad.get("vervolg")
    tip_h_rechts = hoogte("tip", rb - 56, tips) + 66 if tips else 0
    if tips and regels:
        # tip en voedingswaarden naast elkaar, onderaan
        vb = 520.0
        tb = breed - vb - 24
        h = max(hoogte("tip", tb - 56, tips) + 66, hv)
        if y + h <= onder:
            y = max(y, onder - h)
            blad["items"].append(("tip", QRectF(M, y, tb, h), tips, L(nl, "Tip", "Tip")))
            blad["items"].append(("voeding", QRectF(M + tb + 24, y, vb, h), regels, eigen, kop_v, 2))
        elif eerste and rest_y + 24 + hv_smal <= onder:
            # past niet onderaan: voedingswaarden links onder de ingrediënten; de tip waar nog plek is
            vy = onder - hv_smal
            blad["items"].append(("voeding", QRectF(M, vy, kb, hv_smal), regels, eigen, kop_v, 1))
            tip_h_links = hoogte("tip", kb - 56, tips) + 66
            if sy + 20 + tip_h_rechts <= onder:
                blad["items"].append(("tip", QRectF(kx, sy + 20, rb, tip_h_rechts), tips, L(nl, "Tip", "Tip")))
            elif rest_y + 24 + tip_h_links <= vy - 20:
                blad["items"].append(("tip", QRectF(M, rest_y + 24, kb, tip_h_links), tips, L(nl, "Tip", "Tip")))
            else:
                y = nieuw_blad()
                blad["items"].append(("tip", QRectF(M, y, breed, hoogte("tip", breed - 56, tips) + 66), tips, L(nl, "Tip", "Tip")))
        else:
            y = nieuw_blad()
            blad["items"].append(("tip", QRectF(M, y, tb, h), tips, L(nl, "Tip", "Tip")))
            blad["items"].append(("voeding", QRectF(M + tb + 24, y, vb, h), regels, eigen, kop_v, 2))
    elif tips:
        h = hoogte("tip", breed - 56, tips) + 66
        if y + h <= onder:
            blad["items"].append(("tip", QRectF(M, y, breed, h), tips, L(nl, "Tip", "Tip")))
        elif eerste and sy + 20 + tip_h_rechts <= onder:
            blad["items"].append(("tip", QRectF(kx, sy + 20, rb, tip_h_rechts), tips, L(nl, "Tip", "Tip")))
        else:
            y = nieuw_blad()
            blad["items"].append(("tip", QRectF(M, y, breed, h), tips, L(nl, "Tip", "Tip")))
    elif regels:
        if y + hv <= onder:
            y = max(y, onder - hv)
            blad["items"].append(("voeding", QRectF(M, y, breed, hv), regels, eigen, kop_v, 2))
        elif eerste and rest_y + 24 + hv_smal <= onder:
            blad["items"].append(("voeding", QRectF(M, onder - hv_smal, kb, hv_smal), regels, eigen, kop_v, 1))
        else:
            y = nieuw_blad()
            blad["items"].append(("voeding", QRectF(M, y, breed, hv), regels, eigen, kop_v, 2))
    paginas.append(blad)
    return paginas


def _rest_ingredienten(blad, blokken, vanaf, y, nl, breed):
    blad["items"].append(("tekst", QRectF(M, y, breed, 40), "kop", INK, L(nl, "Ingrediënten (vervolg)", "Ingredients (continued)")))
    y += 54
    kol = (breed - 40) / 2
    rest = blokken[vanaf:]
    helft = (len(rest) + 1) // 2
    y0 = y
    ymax = y
    for k, deel in enumerate((rest[:helft], rest[helft:])):
        yy = y0
        for naam, h, hv in deel:
            blad["items"].append(("ing", QRectF(M + k * (kol + 40), yy, kol, h), hv, naam))
            yy += h
        ymax = max(ymax, yy)
    return ymax



# ---------------------------------------------------------------- een gewoon boek: hoofdstukken met lopende tekst
LETTERS.update({"boek": ("Georgia", 25, False, False), "hfd_nr": ("Segoe UI", 22, True, False),
                "hfd": ("Georgia", 56, True, False), "onder": ("Georgia", 19, False, True)})
REGEL = 1.5                        # regelafstand van de lopende tekst


def _layout(tekst, breed):
    from PyQt6.QtGui import QTextLayout, QTextOption
    lay = QTextLayout(tekst, letter("boek"))
    opt = QTextOption()
    opt.setWrapMode(QTextOption.WrapMode.WordWrap)
    opt.setAlignment(Qt.AlignmentFlag.AlignJustify)
    lay.setTextOption(opt)
    lay.beginLayout()
    while True:
        ln = lay.createLine()
        if not ln.isValid():
            break
        ln.setLineWidth(breed)
    lay.endLayout()
    return lay


def alineas(tekst):
    """Alinea's: gescheiden door een lege regel (een enkele Enter mag ook)."""
    uit = []
    for blok in (tekst or "").replace("\r", "").split("\n"):
        blok = blok.strip()
        if blok:
            uit.append(blok)
    return uit


def _boek_bladzijden(boek, nl):
    ps = [dict(soort="voor")]
    hs = boek.get("hoofdstukken", [])
    inhoud = dict(soort="inhoud", regels=[])
    if boek.get("inhoud", True) and hs:
        ps.append(inhoud)
    start = {}
    for i, h in enumerate(hs):
        start[i] = len(ps)
        ps.extend(_hoofdstuk_paginas(i, h, nl))
    for n, p in enumerate(ps):
        p["nr"] = n if p["soort"] != "voor" else 0
    if inhoud in ps:
        inhoud["regels"] = [("rec", "%d.  %s" % (i + 1, h.get("titel") or L(nl, "(zonder titel)", "(untitled)")),
                             str(ps[start[i]]["nr"])) for i, h in enumerate(hs)]
    ps.append(dict(soort="achter", nr=0))
    return ps


def _hoofdstuk_paginas(hi, h, nl):
    breed = PB - 2 * M
    onder = PH - M - 40
    fm = QFontMetricsF(letter("boek"))
    lh = fm.height() * REGEL
    paginas = []
    blad = dict(soort="hoofdstuk", hi=hi, items=[])
    y = M + 170
    blad["items"].append(("tekst", QRectF(M, y, breed, 34), "hfd_nr", PAARS, L(nl, "HOOFDSTUK %d", "CHAPTER %d") % (hi + 1)))
    y += 44
    titel = h.get("titel") or L(nl, "(zonder titel)", "(untitled)")
    th = hoogte("hfd", breed, titel)
    blad["items"].append(("tekst", QRectF(M, y, breed, th), "hfd", INK, titel))
    y += th + 70

    wachtend = []           # plaatjes die niet meer pasten: die komen bovenaan de volgende bladzijde

    def maat(pl):
        r = pl.get("verhouding") or 0.66
        ph = min(breed * r, 560.0)
        pb = min(breed, ph / r if r else breed)
        ph = pb * r
        ond = (pl.get("onder") or "").strip()
        oh = hoogte("onder", breed, ond) + 8 if ond else 0
        return pb, ph, ond, oh

    def zet(pl):
        nonlocal y
        pb, ph, ond, oh = maat(pl)
        blad["items"].append(("foto", QRectF(M + (breed - pb) / 2, y, pb, ph), pl.get("foto")))
        y += ph + 10
        if ond:
            blad["items"].append(("tekst", QRectF(M, y, breed, oh), "onder", GRIJS, ond, int(Qt.AlignmentFlag.AlignHCenter)))
            y += oh
        y += 24

    def nieuw():
        nonlocal blad, y
        paginas.append(blad)
        blad = dict(soort="hoofdstuk", hi=hi, items=[])
        y = M + 10
        while wachtend:
            zet(wachtend.pop(0))
        return y

    plaatjes = {}
    for pl in h.get("plaatjes", []):
        plaatjes.setdefault(int(pl.get("na", 0)), []).append(pl)

    def zet_plaatjes(n):
        for pl in plaatjes.get(n, []):
            pb, ph, ond, oh = maat(pl)
            if wachtend or y + ph + oh + 20 > onder:
                wachtend.append(pl)
            else:
                zet(pl)

    zet_plaatjes(0)
    for ai, al in enumerate(alineas(h.get("tekst", "")), 1):
        n = _layout(al, breed).lineCount()
        i = 0
        while i < n:
            past = int((onder - y) // lh)
            rest = n - i
            if rest <= past:
                k = rest
            else:
                k = past
                if rest - k == 1:
                    k -= 1                      # geen eenzame laatste regel bovenaan de volgende bladzijde
                if k < 2 and y > M + 20:        # geen eenzame eerste regel onderaan
                    y = nieuw()
                    continue
                k = max(1, k)
            blad["items"].append(("alinea", QRectF(M, y, breed, k * lh), al, i, i + k, lh))
            y += k * lh
            i += k
        y += lh * 0.45
        zet_plaatjes(ai)
    if wachtend:
        nieuw()
    paginas.append(blad)
    return paginas


def _alinea(p, r, tekst, van, tot, lh):
    lay = _layout(tekst, r.width())
    fm = QFontMetricsF(letter("boek"))
    p.setPen(INK)
    for i in range(van, tot):
        ln = lay.lineAt(i)
        ln.setPosition(QPointF(0, 0))
        ln.draw(p, QPointF(r.x(), r.y() + (i - van) * lh + (lh - fm.height()) / 2))


# ---------------------------------------------------------------- tekenen
class Fotos:
    """Foto's (jpg-bytes) per id, met een cache van QImages."""

    def __init__(self):
        self.data, self.cache = {}, {}

    def beeld(self, fid):
        if fid not in self.cache and fid in self.data:
            self.cache[fid] = QImage.fromData(self.data[fid])
        return self.cache.get(fid)


def _vul_foto(p, im, r, rond=18.0):
    if im is None or im.isNull():
        p.fillRect(r, LICHT)
        return
    s = max(r.width() / im.width(), r.height() / im.height())
    bw, bh = r.width() / s, r.height() / s
    bron = QRectF((im.width() - bw) / 2, (im.height() - bh) / 2, bw, bh)
    p.save()
    if rond:
        pad = QPainterPath()
        pad.addRoundedRect(r, rond, rond)
        p.setClipPath(pad, Qt.ClipOperation.IntersectClip)
    p.drawImage(r, im, bron)
    p.restore()


def teken(p, pg, s, boek, fotos, nl):
    """Tekent bladzijde pg op schaal s (1 eenheid = s pixels)."""
    _COMPACT[0] = bool(pg.get("compact"))
    try:
        _teken(p, pg, s, boek, fotos, nl)
    finally:
        _COMPACT[0] = False


def _teken(p, pg, s, boek, fotos, nl):
    p.save()
    p.scale(s, s)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    soort = pg["soort"]
    if soort == "voor":
        _voorkant(p, boek, fotos, nl)
    elif soort == "achter":
        _achterkant(p, boek, nl)
    else:
        p.fillRect(QRectF(0, 0, PB, PH), WIT)
        if soort == "inhoud":
            _inhoud(p, pg, boek, nl)
        else:
            _recept(p, pg, fotos, nl)          # recepten en hoofdstukken gebruiken dezelfde onderdelen
        if pg.get("nr"):
            p.setFont(letter("klein"))
            p.setPen(GRIJS)
            p.drawText(QRectF(0, PH - M + 10, PB, 30), int(Qt.AlignmentFlag.AlignCenter), str(pg["nr"]))
            p.drawText(QRectF(M, PH - M + 10, PB / 2 - M, 30), int(Qt.AlignmentFlag.AlignLeft), boek.get("titel", ""))
    p.restore()


def _tekst(p, r, soort, kleur, t, flags=0):
    p.setFont(letter(soort))
    p.setPen(kleur)
    p.drawText(r.adjusted(0, 0, 0, 2000), WRAP | int(flags), t)


def _recept(p, pg, fotos, nl):
    for it in pg["items"]:
        k = it[0]
        if k == "foto":
            _vul_foto(p, fotos.beeld(it[2]), it[1])
        elif k == "tekst":
            _tekst(p, it[1], it[2], it[3], it[4], it[5] if len(it) > 5 else 0)
        elif k == "alinea":
            _alinea(p, it[1], it[2], it[3], it[4], it[5])
        elif k == "lijn":
            p.setPen(QPen(QColor("#d9d2f0"), 3))
            p.drawLine(it[1].topLeft(), it[1].topRight())
        elif k == "vak":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(LICHT)
            p.drawRoundedRect(it[1], 16, 16)
        elif k == "ing":
            r, hv, naam = it[1], it[2], it[3]
            if hv:
                _tekst(p, QRectF(r.x(), r.y(), HV, r.height()), "vet", PAARS, hv)
            _tekst(p, QRectF(r.x() + HV + 10, r.y(), r.width() - HV - 10, r.height()), "tekst", INK, naam)
        elif k == "stap":
            r, n, t = it[1], it[2], it[3]
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(PAARS)
            p.drawEllipse(QRectF(r.x(), r.y(), 38, 38))
            p.setFont(letter("nr"))
            p.setPen(WIT)
            p.drawText(QRectF(r.x(), r.y(), 38, 38), int(Qt.AlignmentFlag.AlignCenter), str(n))
            _tekst(p, QRectF(r.x() + 54, r.y() + 4, r.width() - 54, r.height()), "tekst", INK, t)
        elif k == "tip":
            r, t, kop = it[1], it[2], it[3]
            p.setPen(QPen(QColor("#ffd166"), 4))
            p.setBrush(QColor("#fff8e6"))
            p.drawRoundedRect(r, 16, 16)
            _tekst(p, QRectF(r.x() + 28, r.y() + 16, 200, 40), "kop", QColor("#8a5a00"), "💡 " + kop)
            _tekst(p, QRectF(r.x() + 28, r.y() + 56, r.width() - 56, r.height()), "tip", INK, t)
        elif k == "voeding":
            r, regels, eigen, kop = it[1], it[2], it[3], it[4]
            kols = it[5] if len(it) > 5 else 2
            p.setPen(QPen(QColor("#d9d2f0"), 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r, 14, 14)
            kh = hoogte("vet", r.width() - 30, kop)
            _tekst(p, QRectF(r.x() + 22, r.y() + 12, r.width() - 30, kh), "vet", INK, kop)
            per = (len(regels) + kols - 1) // kols
            kol = (r.width() - 44) / kols
            for i, (naam, w, e) in enumerate(regels):
                x = r.x() + 22 + (i // per) * kol
                y = r.y() + 16 + kh + (i % per) * 30
                sub = naam.startswith("waarvan") or naam.startswith("of which")
                _tekst(p, QRectF(x + (18 if sub else 0), y, kol * 0.62, 34), "klein" if sub else "info", GRIJS if sub else INK, naam)
                _tekst(p, QRectF(x + kol * 0.6, y, kol * 0.38 - 6, 34), "info", INK, w + (" *" if e else ""),
                       Qt.AlignmentFlag.AlignRight)
            bron = L(nl, "Gebaseerd op gegevens van %s", "Based on data from %s") % nevo.BRON
            if eigen:
                bron += L(nl, " en eigen gegevens (*)", " and own data (*)")
            bh = hoogte("klein", r.width() - 44, bron)
            _tekst(p, QRectF(r.x() + 22, r.bottom() - bh - 8, r.width() - 44, bh), "klein", GRIJS, bron)


def _inhoud(p, pg, boek, nl):
    _tekst(p, QRectF(M, M, PB - 2 * M, 80), "titel", INK, L(nl, "Inhoud", "Contents"))
    y = M + 110
    fm = QFontMetricsF(letter("inhoud"))
    for soort, naam, nr in pg.get("regels", []):
        if y > PH - M - 60:
            break
        if soort == "cat":
            y += 14
            _tekst(p, QRectF(M, y, PB - 2 * M, 34), "cat", PAARS, naam.upper())
            y += 40
            continue
        p.setFont(letter("inhoud"))
        p.setPen(INK)
        nw = fm.horizontalAdvance(nr)
        tw = min(fm.horizontalAdvance(naam), PB - 2 * M - nw - 60)
        p.drawText(QRectF(M, y, tw + 4, 40), int(Qt.AlignmentFlag.AlignLeft), fm.elidedText(naam, Qt.TextElideMode.ElideRight, tw))
        p.drawText(QRectF(PB - M - nw - 2, y, nw + 4, 40), int(Qt.AlignmentFlag.AlignLeft), nr)
        p.setPen(QPen(QColor("#cfc8e6"), 2, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(M + tw + 14, y + fm.ascent()), QPointF(PB - M - nw - 14, y + fm.ascent()))
        y += 44


def _voorkant(p, boek, fotos, nl):
    kleur = QColor(boek.get("kaftkleur") or "#2a2140")
    p.fillRect(QRectF(0, 0, PB, PH), kleur)
    fid = boek.get("kaftfoto")
    if fid:
        _vul_foto(p, fotos.beeld(fid), QRectF(0, 0, PB, PH * 0.62), 0)
        # zachte overgang naar de kleur
        from PyQt6.QtGui import QLinearGradient
        g = QLinearGradient(0, PH * 0.45, 0, PH * 0.62)
        t = QColor(kleur)
        t.setAlpha(0)
        g.setColorAt(0, t)
        g.setColorAt(1, kleur)
        p.fillRect(QRectF(0, PH * 0.45, PB, PH * 0.17 + 1), g)
        y = PH * 0.64
    else:
        y = PH * 0.30
    licht = kleur.lightness() < 140
    tk = WIT if licht else INK
    titel = boek.get("titel") or (L(nl, "Mijn boek", "My book") if boek.get("soort") == "boek" else L(nl, "Mijn receptenboek", "My recipe book"))
    h = hoogte("kaft", PB - 2 * M, titel)
    _tekst(p, QRectF(M, y, PB - 2 * M, h), "kaft", tk, titel, Qt.AlignmentFlag.AlignHCenter)
    y += h + 20
    if boek.get("ondertitel"):
        h = hoogte("sub", PB - 2 * M, boek["ondertitel"])
        _tekst(p, QRectF(M, y, PB - 2 * M, h), "sub", QColor("#ffd166") if licht else PAARS, boek["ondertitel"],
               Qt.AlignmentFlag.AlignHCenter)
        y += h + 10
    if boek.get("auteur"):
        _tekst(p, QRectF(M, PH - M - 60, PB - 2 * M, 50), "kop", tk, boek["auteur"], Qt.AlignmentFlag.AlignHCenter)


def _achterkant(p, boek, nl):
    kleur = QColor(boek.get("kaftkleur") or "#2a2140")
    p.fillRect(QRectF(0, 0, PB, PH), kleur)
    licht = kleur.lightness() < 140
    tk = WIT if licht else INK
    t = (boek.get("achtertekst") or "").strip()
    if t:
        _tekst(p, QRectF(M + 40, PH * 0.25, PB - 2 * M - 80, PH * 0.5), "sub", tk, t, Qt.AlignmentFlag.AlignHCenter)
    _tekst(p, QRectF(M, PH - M - 40, PB - 2 * M, 30), "klein", QColor("#b9b2d6") if licht else GRIJS,
           L(nl, "Gemaakt met DraveWriter · dravenlock.nl", "Made with DraveWriter · dravenlock.nl"), Qt.AlignmentFlag.AlignHCenter)
