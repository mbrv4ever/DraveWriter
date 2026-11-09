# -*- coding: utf-8 -*-
# DraveWriter - Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""nevo.py - voedingswaarden uit de NEVO-tabel van het RIVM (offline).

De tabel zelf blijft ONVERANDERD (voorwaarde van het RIVM): we lezen het originele bestand
(zip, csv of xlsx) uit de map NEVO naast de app. Eigen waarden van de gebruiker zijn een aparte laag
erbovenop en worden in het boek als 'eigen' gemarkeerd.

Bron: NEVO-online versie 2025/9.0, RIVM, Bilthoven.
"""
import csv
import io
import os
import re
import zipfile

# de voedingsstoffen die we tonen: (code in de NEVO-tabel, sleutel, NL, EN, eenheid)
STOFFEN = [("ENERCC", "kcal", "Energie", "Energy", "kcal"),
           ("PROT", "eiwit", "Eiwit", "Protein", "g"),
           ("FAT", "vet", "Vet", "Fat", "g"),
           ("FASAT", "verzadigd", "waarvan verzadigd", "of which saturated", "g"),
           ("CHO", "koolh", "Koolhydraten", "Carbohydrates", "g"),
           ("SUGAR", "suiker", "waarvan suikers", "of which sugars", "g"),
           ("FIBT", "vezels", "Vezels", "Fibre", "g"),
           ("NA", "zout", "Zout", "Salt", "g")]          # NA staat in mg natrium; zout = natrium x 2,5
SLEUTELS = [s[1] for s in STOFFEN]
BRON = "NEVO-online versie 2025/9.0, RIVM, Bilthoven"

# ---------------------------------------------------------------- eenheden -> gram
EENHEDEN = ["g", "kg", "ml", "dl", "l", "el", "tl", "kopje", "snufje", "stuk", "teen", "plak", "blik", "zakje", "takje",
            "handje", "naar smaak"]
EENHEDEN_EN = {"g": "g", "kg": "kg", "ml": "ml", "dl": "dl", "l": "l", "el": "tbsp", "tl": "tsp", "kopje": "cup",
               "snufje": "pinch", "stuk": "piece", "teen": "clove", "plak": "slice", "blik": "tin", "zakje": "sachet",
               "takje": "sprig", "handje": "handful", "naar smaak": "to taste"}
VAST = {"g": 1.0, "kg": 1000.0, "ml": 1.0, "dl": 100.0, "l": 1000.0, "el": 15.0, "tl": 5.0, "kopje": 240.0,
        "snufje": 0.4, "takje": 1.0, "handje": 25.0, "zakje": 10.0, "plak": 20.0, "blik": 400.0, "naar smaak": 0.0}
TELBAAR = {"stuk", "teen", "plak", "blik", "zakje", "takje", "handje", "snufje"}

# gram per stuk voor veel voorkomende dingen (de gebruiker kan het altijd zelf bijstellen)
PER_STUK = [("eidooier", 18), ("eiwit", 33), ("ei", 55), ("sjalot", 30), ("ui", 100), ("knoflook", 5), ("tomaat", 100),
            ("cherrytomaat", 15), ("wortel", 80), ("winterpeen", 300), ("aardappel", 150), ("appel", 150),
            ("peer", 160), ("citroen", 100), ("limoen", 70), ("sinaasappel", 180), ("banaan", 120), ("paprika", 150),
            ("courgette", 300), ("aubergine", 300), ("prei", 200), ("komkommer", 350), ("avocado", 150),
            ("champignon", 15), ("bosui", 15), ("lente-ui", 15), ("kipfilet", 150), ("braadworst", 100),
            ("worst", 100), ("tortilla", 40), ("wrap", 60), ("broodje", 60), ("boterham", 35), ("snee", 35),
            ("laurierblad", 0.2), ("rode peper", 10), ("peper", 10), ("bouillonblokje", 10), ("pompoen", 1000),
            ("bloemkool", 600), ("broccoli", 400), ("krop", 300)]


# veelgebruikte woorden -> hoe het in de NEVO-tabel heet (alleen voor de eerste gok)
ALIAS = {"olijfolie": "olie olijf", "zonnebloemolie": "olie zonnebloem", "jonge kaas": "kaas goudse jong",
         "kaas": "kaas goudse", "graskaas": "kaas goudse jong", "boter": "boter ongezouten", "roomboter": "boter ongezouten",
         "melk": "melk halfvolle", "bloem": "bloem tarwe", "tarwebloem": "bloem tarwe", "braadworst": "varkensbraadworst rauw", "suiker": "suiker kristal", "knoflook": "knoflook rauw", "peper": "peper zwart",
         "rijst": "rijst witte gekookt", "pasta": "pasta witte rauw", "spaghetti": "pasta witte rauw", "macaroni": "pasta witte rauw",
         "gehakt": "gehakt hoh rauw", "rundergehakt": "gehakt runder rauw", "room": "slagroom", "aardappels": "aardappelen", "aardappel": "aardappelen",
         "uien": "ui", "tomaten": "tomaat", "wortels": "wortel", "eieren": "ei kippen", "ei": "ei kippen"}

# Vaste eerste keus voor gewone ingrediënten (NEVO-code). Zo pakt DraveWriter bij "boerenkool" de verse groente
# en niet een kant-en-klare stamppot. De gebruiker kan altijd zelf iets anders kiezen.
CODES = {"boerenkool": "959", "zuurkool": "73", "bloemkool": "14", "sperziebonen": "50", "sperzieboon": "50",
         "boontjes": "50", "spitskool": "53", "knolselderij": "558", "bleekselderij": "557", "selderij": "557",
         "groene kool": "24", "chinese kool": "21", "mais": "57", "maïs": "57", "erwten": "23", "doperwten": "23",
         "rijst": "5", "witte rijst": "5", "zilvervliesrijst": "712", "room": "299", "slagroom": "299",
         "rookworst": "324", "slavink": "1431", "speklap": "1432", "speklapjes": "1432", "ontbijtspek": "639",
         "spek": "343", "spekjes": "343", "rookspek": "343", "banaan": "151", "bananen": "151",
         "brood": "246", "volkorenbrood": "246", "bruin brood": "236", "bruinbrood": "236", "witbrood": "241",
         "sojasaus": "5470", "ketjap": "1215", "ketjap manis": "1215", "gember": "832", "verse gember": "832",
         "mie": "5397", "noedels": "5397", "aardappels": "1", "aardappelen": "1", "aardappel": "1",
         "kruimige aardappels": "1", "vastkokende aardappels": "1", "bak en braad": "2066", "bakboter": "2066"}

# Kant-en-klare gerechten, soepen, sappen en toetjes komen pas achteraan bij een eerste gok.
_ACHTERAAN = ("Samengestelde gerechten", "Soepen")
_ACHTERAAN_BEGIN = ("sap ", "vla ", "stamppot ", "soep ", "taart ", "glutenvrij ", "salade ")


def gram_per_stuk(naam):
    n = (naam or "").lower()
    for woord, g in PER_STUK:
        if woord in n:
            return float(g)
    return None


def gram(hoeveel, eenheid, naam="", eigen_per_stuk=None):
    """Hoeveel gram is dit? None = weet ik niet (dan vraagt de app het)."""
    try:
        h = float(hoeveel or 0)
    except Exception:
        return None
    if eenheid in ("stuk", "teen") or (eenheid in TELBAAR and eigen_per_stuk):
        g = eigen_per_stuk or gram_per_stuk(naam)
        if eenheid == "teen" and not eigen_per_stuk:
            g = 5.0
        return None if g is None else h * g
    if eenheid in VAST:
        return h * VAST[eenheid]
    return None


# ---------------------------------------------------------------- afronden bij meer/minder personen
BREUK = {0.25: "¼", 0.5: "½", 0.75: "¾"}


def mooi_getal(x, nl=True):
    if abs(x - round(x)) < 1e-6:
        return str(int(round(x)))
    heel, rest = int(x), x - int(x)
    for b, t in BREUK.items():
        if abs(rest - b) < 1e-6:
            return (str(heel) if heel else "") + t
    s = ("%.1f" % x)
    return s.replace(".", ",") if nl else s


def afgerond(x, eenheid):
    """Netjes afronden (1 ei, niet 1,3 ei)."""
    if x <= 0:
        return 0.0
    if eenheid in ("snufje", "takje", "handje"):
        return float(max(1, int(x + 0.5)))
    if eenheid in TELBAAR:
        if x < 0.75:
            return 0.5
        return float(int(x + 0.5)) if x >= 2 else int(x * 2 + 0.5) / 2
    if eenheid in ("el", "tl", "kopje"):
        return max(0.5, round(x * 2) / 2) if x < 4 else float(round(x))
    if eenheid in ("g", "ml"):
        if x < 10:
            return max(1.0, float(round(x)))
        if x < 100:
            return float(int(x / 5 + 0.5) * 5)
        return float(int(x / 10 + 0.5) * 10)
    if eenheid in ("kg", "l"):
        return max(0.05, round(x * 20) / 20)
    if eenheid == "dl":
        return max(0.5, round(x * 2) / 2)
    return round(x, 1)


# ---------------------------------------------------------------- de tabel lezen
def _getal(s):
    s = (s or "").strip().replace(",", ".")
    if not s or s in ("-", "*"):
        return None
    try:
        return float(s)
    except Exception:
        m = re.match(r"^[<>~]?\s*(-?\d+(?:\.\d+)?)", s)
        return float(m.group(1)) if m else None


def _rijen_csv(tekst):
    eerste = tekst.splitlines()[0] if tekst else ""
    teken = max(("|", ";", "\t", ","), key=lambda t: eerste.count(t))
    return list(csv.reader(io.StringIO(tekst), delimiter=teken))


def _rijen_xlsx(data):
    import openpyxl  # alleen nodig als het RIVM-bestand een Excel-bestand is
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    beste = []
    for ws in wb.worksheets:
        rijen = [["" if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)]
        if len(rijen) > len(beste):
            beste = rijen
    return beste


def _tekst(data):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("latin-1", "replace")


class Tabel:
    def __init__(self):
        self.items = []          # dicts: code, nl, en, groep, w={kcal:..}
        self.per_code = {}
        self.bestand = None
        self.fout = ""

    def __len__(self):
        return len(self.items)

    # -- laden
    def laad_map(self, *mappen):
        for m in mappen:
            if not m or not os.path.isdir(m):
                continue
            for n in sorted(os.listdir(m)):
                if n.lower().endswith((".zip", ".csv", ".xlsx")) and "nevo" in n.lower():
                    if self.laad(os.path.join(m, n)):
                        return True
        return False

    def laad(self, pad):
        try:
            rijen = self._lees(pad)
            self._verwerk(rijen)
            if len(self.items) < 50:
                raise ValueError("te weinig regels (%d)" % len(self.items))
            self.bestand = pad
            return True
        except Exception as e:
            self.fout = "%s: %s" % (os.path.basename(pad), e)
            self.items, self.per_code = [], {}
            return False

    def _lees(self, pad):
        low = pad.lower()
        if low.endswith(".csv"):
            return _rijen_csv(_tekst(open(pad, "rb").read()))
        if low.endswith(".xlsx"):
            return _rijen_xlsx(open(pad, "rb").read())
        with zipfile.ZipFile(pad) as z:
            namen = [n for n in z.namelist() if not n.endswith("/")]
            # liefst de grote csv met alle voedingsmiddelen (niet de 'details' of 'referenties')
            csvs = sorted([n for n in namen if n.lower().endswith(".csv")],
                          key=lambda n: (0 if re.search(r"nevo\d+_v[\d.]+\.csv$", n.lower()) else 1,
                                         any(w in n.lower() for w in ("detail", "nutrient", "recept", "referent")),
                                         -z.getinfo(n).file_size))
            for n in csvs:
                rijen = _rijen_csv(_tekst(z.read(n)))
                if self._kolommen(rijen):
                    return rijen
            for n in sorted([n for n in namen if n.lower().endswith(".xlsx")], key=lambda n: -z.getinfo(n).file_size):
                rijen = _rijen_xlsx(z.read(n))
                if self._kolommen(rijen):
                    return rijen
        raise ValueError("geen NEVO-tabel gevonden in de zip")

    @staticmethod
    def _kolommen(rijen):
        """Zoekt de kopregel en de kolommen. Geeft (kopregel-index, dict) of None."""
        for i, r in enumerate(rijen[:15]):
            low = [c.strip().lower() for c in r]
            code = next((j for j, c in enumerate(low) if c.startswith("nevo-code") or c == "nevo code" or c == "nevocode"), None)
            if code is None:
                continue
            k = dict(code=code)
            k["nl"] = next((j for j, c in enumerate(low) if "dutch food name" in c or c.startswith("voedingsmiddelnaam")), None)
            k["en"] = next((j for j, c in enumerate(low) if c in ("engelse naam/food name", "food name") or c.startswith("engelse naam")), None)
            k["groep"] = next((j for j, c in enumerate(low) if c.startswith("voedingsmiddelgroep")), None)
            for nevo, sleutel, *_ in STOFFEN:
                k[sleutel] = next((j for j, c in enumerate(r) if re.match(r"^%s\b" % nevo, c.strip())), None)
            if k["nl"] is not None and k["kcal"] is not None:
                return i, k
        return None

    def _verwerk(self, rijen):
        gev = self._kolommen(rijen)
        if not gev:
            raise ValueError("kolommen niet herkend")
        start, k = gev
        self.items, self.per_code = [], {}
        for r in rijen[start + 1:]:
            if len(r) <= max(v for v in k.values() if v is not None):
                continue
            naam = r[k["nl"]].strip()
            if not naam:
                continue
            w = {}
            for _nevo, sleutel, *_ in STOFFEN:
                j = k.get(sleutel)
                v = _getal(r[j]) if j is not None else None
                if sleutel == "zout" and v is not None:
                    v = v * 2.5 / 1000.0            # mg natrium -> g zout
                w[sleutel] = v
            it = dict(code=r[k["code"]].strip(), nl=naam, en=(r[k["en"]].strip() if k["en"] is not None else naam),
                      groep=(r[k["groep"]].strip() if k["groep"] is not None else ""), w=w,
                      _z=(naam + " " + (r[k["en"]] if k["en"] is not None else "")).lower())
            self.items.append(it)
            self.per_code[it["code"]] = it

    # -- zoeken
    def zoek(self, tekst, max_n=60):
        t = (tekst or "").lower().strip()
        t = ALIAS.get(t, t)
        woorden = [w for w in re.split(r"[\s,]+", t) if w]
        if not woorden:
            return []
        uit = []
        for it in self.items:
            z = it["_z"]
            if all(w in z for w in woorden):
                nl = it["nl"].lower()
                delen = re.split(r"[\s,/()-]+", nl)
                heel = sum(1 for w in woorden if w in delen)          # hele woorden in de Nederlandse naam
                gerecht = 1 if (it["groep"] in _ACHTERAAN or nl.startswith(_ACHTERAAN_BEGIN)) else 0
                score = (-heel, gerecht, 0 if nl.startswith(woorden[0]) else 1,
                         0 if ("rauw" in nl or "onbereid" in nl or "gem" in delen) else 1, len(nl))
                uit.append((score, it))
        uit.sort(key=lambda x: x[0])
        return [it for _s, it in uit[:max_n]]

    def beste(self, naam):
        """Eerste gok voor een ingrediënt (de gebruiker kan altijd een andere kiezen)."""
        t = (naam or "").lower().strip()
        kern = re.split(r"[(,]", t)[0].strip() or t           # "ui, heel fijn gesnipperd" -> "ui"
        pogingen = [t, kern, _enkelvoud(kern)]
        woorden = [w for w in re.split(r"[\s,]+", kern) if len(w) > 2]
        for w in sorted(woorden, key=len, reverse=True):     # het langste woord is meestal het ding zelf
            pogingen += [w, _enkelvoud(w)]
        for p in pogingen:                                   # per poging: eerst de vaste keus, dan zoeken
            c = CODES.get(p)
            if c and c in self.per_code:
                return self.per_code[c]
            r = self.zoek(p, 1)
            if r:
                return r[0]
        return None


def _enkelvoud(t):
    uit = []
    for w in t.split():
        for eind, nieuw in (("ssen", "s"), ("ijen", "ij"), ("eeën", "ee"), ("en", ""), ("'s", ""), ("s", "")):
            if w.endswith(eind) and len(w) > len(eind) + 2:
                w = w[:-len(eind)] + nieuw
                break
        uit.append(w)
    return " ".join(uit)

def bereken(ingredienten, tabel, personen):
    """Voedingswaarden per portie. Geeft (waarden, ontbreekt, eigen_gebruikt).
    Per ingrediënt: eigen waarden per 100 g ('eigen100') gaan voor de NEVO-waarden."""
    tot = {s: 0.0 for s in SLEUTELS}
    ontbreekt, eigen = [], False
    for ing in ingredienten:
        if ing.get("eenheid") == "naar smaak" or not (ing.get("naam") or "").strip():
            continue
        g = ing.get("gram_eigen")
        if g in (None, ""):
            g = gram(ing.get("hoeveel"), ing.get("eenheid"), ing.get("naam"), ing.get("per_stuk"))
        else:
            eigen = True
        w = None
        if ing.get("eigen100"):
            w, eigen = ing["eigen100"], True
        elif ing.get("nevo") and tabel is not None and ing["nevo"] in tabel.per_code:
            w = tabel.per_code[ing["nevo"]]["w"]
        if g is None or w is None:
            ontbreekt.append(ing.get("naam", "?"))
            continue
        for s in SLEUTELS:
            v = w.get(s)
            if v is not None:
                tot[s] += float(g) * float(v) / 100.0
    p = max(1, int(personen or 1))
    return {s: tot[s] / p for s in SLEUTELS}, ontbreekt, eigen
