# -*- coding: utf-8 -*-
# Maakt "Hollandse pot.drecept" - het eerste echte receptenboek van Roger, uit zijn eigen woorden (9-11-2026).
# Gebruik: py -3.12 maak_pa_boek.py   (vanuit de map Pa_recepten; leest nevo.py uit de DraveWriter-map erboven)
import json, os, sys, zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
import nevo


def ing(h, e, naam, code, per_stuk=None):
    d = dict(hoeveel=h, eenheid=e, naam=naam, nevo=code)
    if per_stuk:
        d["per_stuk"] = per_stuk
    return d


SMAAK = "naar smaak"

gehaktbal = dict(
    titel="Gehaktbal", categorie="hoofdgerecht", personen=2, tijd_voor=15, tijd_koken=20,
    intro="Twee goede gehaktballen van 250 gram gehakt. Volkoren beschuit in plaats van paneermeel, "
          "en paprika en verse knoflook erdoor. Lekker bij elke stamppot.",
    foto=None, voeding_eigen={},
    ingredienten=[
        ing(250, "g", "gehakt (soort maakt niet uit)", "1434"),
        ing(1, "stuk", "ui, heel fijn gesnipperd", "63"),
        ing(0.25, "stuk", "paprika, heel fijn gesnipperd", "2742", 150),
        ing(3, "teen", "knoflook (vers), heel fijn gesneden", "830"),
        ing(1, "stuk", "ei", "83"),
        ing(1, "stuk", "volkoren beschuit, verkruimeld", "655", 10),
        ing(1, "snufje", "zout (puntje van een theelepel)", "2819"),
        ing(0, SMAAK, "koriander", None),
        ing(0, SMAAK, "peper", None),
        ing(1, "el", "bak en braad", "2066"),
    ],
    stappen=[
        "Meng alle ingrediënten (behalve de bak en braad) in een kom met de keukenmachine.",
        "Draai er twee ballen van. Een kommetje helpt om ze een mooie vorm te geven.",
        "Laat de bak en braad aanbruinen in een diepe pan en leg de ballen erin.",
        "Bak ze ongeveer 15 minuten en draai ze om de vijf minuten om.",
        "Zet het vuur zachter, doe er een klein beetje water bij, deksel erop en laat ze nog 5 minuten garen.",
    ],
    tips="Met de hand mengen kan ook. Liever kleine balletjes? Draai er vier van en bak ze iets korter. "
         "Kruiden altijd naar eigen smaak.",
)

braadworst = dict(
    titel="Braadworst", categorie="hoofdgerecht", personen=2, tijd_voor=2, tijd_koken=15,
    intro="Een gekochte braadworst, maar dan goed gebakken: eerst mooi bruin, daarna zacht gegaard in de stoom.",
    foto=None, voeding_eigen={},
    ingredienten=[
        ing(2, "stuk", "braadworst", "1417", 100),
        ing(1, "el", "bak en braad (of je eigen bakboter)", "2066"),
    ],
    stappen=[
        "Belangrijk: prik eerst met een vork overal gaatjes in de worst.",
        "Laat de bak en braad bruin worden in de pan en leg de worst erin.",
        "Draai de worst om de vijf minuten om, en prik er elke keer weer even in.",
        "Is hij mooi bruin? Zet het gas lager, doe er een klein beetje water bij en doe de deksel erop. "
        "De stoom gaart hem lekker zacht.",
    ],
    tips="Ongeveer 15 minuten in totaal, maar dat hangt af van hoe groot en dik de worst is. "
         "Kijk naar de kleur, niet naar de klok.",
)

STAMP_TIP = ("Kook de groente en de aardappels altijd apart: je wilt geen zetmeel in de groente. "
             "Stamp met een klein beetje melk of roomboter; een snufje baking soda tijdens het stampen maakt het luchtiger.")
ERBIJ = "Erbij naar keuze: rookworst, braadworst of de gehaktbal uit dit boek."


def stamppot(titel, intro, groente, kooktijd_groente, tijd_koken, extra_tip=""):
    return dict(
        titel=titel, categorie="hoofdgerecht", personen=2, tijd_voor=15, tijd_koken=tijd_koken,
        intro=intro + " " + ERBIJ, foto=None, voeding_eigen={},
        ingredienten=[ing(500, "g", "aardappels (kruimig)", "1")] + groente + [
            ing(50, "ml", "melk", "286"),
            ing(0, SMAAK, "peper", None),
        ],
        stappen=[
            "Schil de aardappels, snijd ze in stukken en kook ze in ongeveer 20 minuten gaar.",
            "Kook ondertussen de groente apart, " + kooktijd_groente + ".",
            "Giet de groente af en zet hem terug in de pan, met een deksel of een bord erop, tot de rest klaar is.",
            "Giet de aardappels af en stamp ze met een klein beetje melk (of roomboter).",
            "Schep de groente erdoor en stamp alles goed door elkaar.",
        ],
        tips=STAMP_TIP + (" " + extra_tip if extra_tip else ""),
    )


boerenkool = stamppot(
    "Boerenkool", "Echte winterkost, met lekker veel groente.",
    [ing(400, "g", "boerenkool (vers, gesneden of diepvries)", "959")],
    "10 tot 20 minuten (hoe zacht je hem wilt, bepaal je zelf)", 30)

andijvie = stamppot(
    "Andijviestamppot", "Frisse stamppot met veel andijvie.",
    [ing(400, "g", "andijvie", "7")],
    "ongeveer 5 minuten, andijvie is snel gaar", 25,
    "Rauwe andijvie door de hete puree kan ook - eigen keuze.")

hutspot = stamppot(
    "Hutspot", "Ui en wortel, zoet en hartig tegelijk.",
    [ing(250, "g", "winterpeen, in stukjes", "2728"), ing(150, "g", "ui, in ringen", "63")],
    "ongeveer 20 minuten", 30)

boek = dict(
    soort="recept", titel="Hollandse pot", ondertitel="Stamppot en wat erbij hoort", auteur="Roger",
    kaftkleur="#2a2140", kaftfoto=None, inhoud=True, inhoud_per_cat=False,
    achtertekst="De gulden regel: kruiden altijd naar eigen smaak. Mijn hoeveelheden zijn hoe wij het lekker vinden "
                "- een vertrekpunt, geen wet. Geen pakjes, geen zakjes, geen magnetron. Zout strooi je aan tafel.",
    recepten=[boerenkool, andijvie, hutspot, gehaktbal, braadworst],
    app="DraveWriter", versie="0.2.0",
)

if __name__ == "__main__":
    t = nevo.Tabel()
    t.laad_map(os.path.join(os.path.dirname(HIER), "NEVO"))
    print("NEVO geladen:", len(t))
    for r in boek["recepten"]:
        w, ontbreekt, _ = nevo.bereken(r["ingredienten"], t, r["personen"])
        print("%-22s %4.0f kcal/p  eiwit %4.1f  ontbreekt: %s" % (r["titel"], w["kcal"], w.get("eiwit", 0), ontbreekt))
    uit = os.path.join(HIER, "Hollandse pot.drecept")
    with zipfile.ZipFile(uit, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("boek.json", json.dumps(boek, ensure_ascii=False, indent=1))
    print("KLAAR", uit)
