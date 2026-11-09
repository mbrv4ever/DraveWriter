# -*- coding: utf-8 -*-
# DraveWriter - Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""DraveWriter - maak je eigen receptenboek. Groot en duidelijk.

Versie 0.1: het receptenboek.  Versie 0.2: ook een gewoon boek (hoofdstukken, lopende tekst, plaatjes) en ongedaan maken.
- Recepten met foto, aantal personen, tijden, ingrediënten, bereiding in stappen en tips.
- Voedingswaarden per portie rekent hij zelf uit met de NEVO-tabel van het RIVM (offline, onveranderd);
  eigen waarden kun je erbovenop zetten (die krijgen een sterretje in het boek).
- Meer of minder personen: de hoeveelheden rekenen mee en worden netjes afgerond (1 ei, niet 1,3 ei).
- Een kaft, een inhoudsopgave en bladzijdenummers komen vanzelf.
- Bewaar als PDF om te delen, of maak hem klaar voor de drukker (binnenwerk + kaft met rug).
Alle gegevens staan naast de app in de map DraveWriter-data (portable).
"""
import copy
import hashlib
import json
import locale
import os
import sys
import time
import traceback
import zipfile

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QMarginsF, QSize, QSizeF, Qt, QTimer, QUrl
from PyQt6.QtGui import (QColor, QDesktopServices, QIcon, QImage, QKeySequence, QPageLayout, QPageSize, QPainter,
                         QPdfWriter, QPixmap, QShortcut)
from PyQt6.QtWidgets import (QStackedWidget, QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
                             QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                             QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

import drukker as dk
import nevo
import pagina as pg

VERSIE = "0.2.0"
APP = "DraveWriter"


def _base():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))


def _res(*delen):
    b = getattr(sys, "_MEIPASS", None) or _base()
    p = os.path.join(b, *delen)
    return p if os.path.exists(p) else os.path.join(_base(), *delen)


DATA = os.path.join(_base(), "DraveWriter-data")
os.makedirs(DATA, exist_ok=True)
INSTEL = os.path.join(DATA, "instellingen.json")
MIJN = os.path.join(DATA, "Mijn boeken")
NEVO_DATA = os.path.join(DATA, "NEVO")
LOG = os.path.join(DATA, "error.log")
EXT = ".drecept"


def _log(t):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + t + "\n")
    except Exception:
        pass


def _taal():
    try:
        t = (locale.getlocale()[0] or "")
    except Exception:
        t = ""
    return "nl" if ("nl" in t.lower() or "dutch" in t.lower() or not t) else "en"


NL = _taal() == "nl"
TX = {
    "nieuw": ("📄  Nieuw", "📄  New"), "open": ("📂  Openen", "📂  Open"), "opslaan": ("💾  Opslaan", "💾  Save"),
    "opslaan_als": ("Opslaan als…", "Save as…"), "pdf": ("📕  PDF", "📕  PDF"), "drukker": ("🖨  Drukker", "🖨  Printer"),
    "boek": ("📘  Boek en kaft", "📘  Book and cover"), "gids": ("📖  Snelgids", "📖  Quick guide"), "over": ("ⓘ  Over", "ⓘ  About"),
    "hoofdstukken": ("Hoofdstukken", "Chapters"), "h_bij": ("+ Hoofdstuk", "+ Chapter"),
    "h_titel": ("Titel van het hoofdstuk", "Chapter title"), "h_tekst": ("Tekst", "Text"),
    "h_tekst_uitleg": ("Typ gewoon door. Druk op Enter voor een nieuwe alinea. De bladzijden maakt DraveWriter zelf.",
                       "Just keep typing. Press Enter for a new paragraph. DraveWriter makes the pages itself."),
    "h_plaatjes": ("Plaatjes in dit hoofdstuk", "Pictures in this chapter"), "p_bij": ("📷  Plaatje erbij…", "📷  Add picture…"),
    "p_weg": ("− Weg", "− Remove"), "p_na": ("Na alinea", "After paragraph"), "p_onder": ("Onderschrift (mag leeg)", "Caption (optional)"),
    "p_bestand": ("Plaatje", "Picture"), "woorden": ("%d woorden · %d alinea's", "%d words · %d paragraphs"),
    "nieuw_hfd": ("Nieuw hoofdstuk", "New chapter"), "naamloos_boek": ("Mijn boek", "My book"),
    "ongedaan": ("↶  Ongedaan", "↶  Undo"), "opnieuw": ("↷  Opnieuw", "↷  Redo"),
    "recepten": ("Recepten", "Recipes"), "r_bij": ("+ Recept", "+ Recipe"), "r_weg": ("− Weg", "− Remove"),
    "titel": ("Naam van het recept", "Name of the recipe"), "cat": ("Soort gerecht", "Kind of dish"),
    "personen": ("Voor hoeveel personen", "Serves"), "t_voor": ("Voorbereiden (minuten)", "Preparation (minutes)"),
    "t_koken": ("Koken / bakken (minuten)", "Cooking / baking (minutes)"), "intro": ("Korte zin erboven (mag leeg)", "Short line on top (optional)"),
    "foto": ("📷  Foto kiezen…", "📷  Choose photo…"), "foto_weg": ("Foto weg", "Remove photo"), "geen_foto": ("(nog geen foto)", "(no photo yet)"),
    "ings": ("Ingrediënten", "Ingredients"), "i_bij": ("+ Ingrediënt", "+ Ingredient"), "i_weg": ("− Weg", "− Remove"),
    "kol_h": ("Hoeveel", "Amount"), "kol_e": ("Eenheid", "Unit"), "kol_n": ("Wat", "What"), "kol_v": ("Voedingswaarde uit", "Nutrition from"),
    "stappen": ("Bereiding", "Method"), "stappen_uitleg": ("Eén stap per regel. Druk op Enter voor de volgende stap.",
                                                          "One step per line. Press Enter for the next step."),
    "tips": ("Tip of eigen verhaal (mag leeg)", "Tip or your own story (optional)"),
    "voeding": ("Voedingswaarden per portie", "Nutrition per serving"),
    "v_uitleg": ("Links wat DraveWriter uitrekent. Weet je het beter? Vul rechts je eigen waarde in; die komt in het boek met een sterretje (*).",
                 "Left is what DraveWriter calculates. Know better? Fill in your own value on the right; it goes in the book with an asterisk (*)."),
    "v_eigen": ("eigen", "own"), "v_ontbreekt": ("⚠  Nog niet meegeteld: %s. Klik op de knop achter het ingrediënt.",
                                              "⚠  Not counted yet: %s. Click the button behind the ingredient."),
    "v_geen_tabel": ("De NEVO-tabel is er nog niet. Zet NEVO2025_v9.0.zip in de map NEVO naast de app, of klik hier:",
                     "The NEVO table is missing. Put NEVO2025_v9.0.zip in the NEVO folder next to the app, or click here:"),
    "v_laden": ("NEVO-tabel laden…", "Load NEVO table…"),
    "voorbeeld": ("Voorbeeld", "Preview"), "vb_personen": ("Bekijk voor", "Show for"), "vb_pers": ("personen", "people"),
    "omrekenen": ("📐  Zet het recept om naar dit aantal", "📐  Convert the recipe to this number"),
    "omreken_vraag": ("Alle hoeveelheden omrekenen van %d naar %d personen (netjes afgerond)?",
                      "Convert all amounts from %d to %d people (neatly rounded)?"),
    "groot": ("A+", "A+"), "klein": ("A−", "A−"),
    "naamloos": ("Mijn receptenboek", "My recipe book"), "nieuw_recept": ("Nieuw recept", "New recipe"),
    "vraag_bewaren": ("Wil je je boek eerst opslaan?", "Save your book first?"), "bewaard": ("Opgeslagen: %s", "Saved: %s"),
    "fout_open": ("Dit bestand kon ik niet openen.", "I could not open this file."),
    "project": ("DraveWriter-boek", "DraveWriter book"),
    "pdf_klaar": ("De PDF staat klaar:\n%s\n\nWil je hem openen?", "The PDF is ready:\n%s\n\nOpen it?"),
    "pdf_een": ("Alleen dit recept als PDF", "Only this recipe as PDF"),
    "druk_klaar": ("Klaar! %d bladzijden binnenwerk, rug %.1f mm, kaft %.1f x %.1f mm.\n\n%s\n%s\n\nMap openen?",
                   "Done! %d inside pages, spine %.1f mm, cover %.1f x %.1f mm.\n\n%s\n%s\n\nOpen the folder?"),
    "druk_map": ("Kies de map voor de drukbestanden", "Choose the folder for the print files"),
    "druk_binnen": ("binnenwerk", "inside"), "druk_kaft": ("kaft", "cover"), "druk_leeg": ("Je boek is nog leeg.", "Your book is still empty."),
    "fout": ("Er ging iets mis: %s", "Something went wrong: %s"),
    "start_kop": ("Wat wil je maken?", "What do you want to make?"),
    "start_recept": ("🍲  Een receptenboek", "🍲  A recipe book"),
    "start_boek": ("📚  Een gewoon boek\n(verhaal, roman, herinneringen)", "📚  An ordinary book\n(story, novel, memories)"),
    "kies_nevo": ("Kies wat het meest lijkt", "Choose the closest match"),
    "nevo_zoek": ("Zoek in de NEVO-tabel (bijv. aardappel, kipfilet, boter)", "Search the NEVO table (e.g. potato, chicken, butter)"),
    "nevo_per_stuk": ("Hoeveel gram is één %s?", "How many grams is one %s?"),
    "nevo_gram": ("Of: hoeveel gram is het totaal? (leeg = uitrekenen)", "Or: how many grams in total? (empty = calculate)"),
    "nevo_eigen": ("Staat het er niet in? Vul zelf de waarden per 100 gram in (van de verpakking):",
                   "Not in the list? Fill in the values per 100 grams yourself (from the package):"),
    "nevo_geen": ("— niet meetellen —", "— don't count —"),
    "kies": ("Kies…", "Choose…"), "eigen_waarden": ("eigen waarden", "own values"),
    "b_titel": ("Titel van het boek", "Title of the book"), "b_sub": ("Ondertitel (mag leeg)", "Subtitle (optional)"),
    "b_auteur": ("Gemaakt door", "Made by"), "b_kleur": ("Kleur van de kaft…", "Cover colour…"),
    "b_foto": ("Foto op de voorkant", "Photo on the front"), "b_geen_foto": ("Geen foto", "No photo"),
    "b_eigen_foto": ("Eigen foto kiezen…", "Choose own photo…"), "b_achter": ("Tekst op de achterkant (mag leeg)", "Text on the back (optional)"),
    "b_inhoud": ("Inhoudsopgave maken", "Make a table of contents"), "b_per_cat": ("In de inhoud per soort gerecht", "Group the contents by kind of dish"),
    "over_tekst": ("<h2>DraveWriter %s</h2><p>Maak je eigen receptenboek of een gewoon boek, groot en duidelijk. Gratis, zonder account en zonder reclame.</p>"
                   "<p>Voedingswaarden: gebaseerd op gegevens van NEVO-online versie 2025/9.0, RIVM, Bilthoven. "
                   "De tabel wordt onveranderd gebruikt; eigen waarden staan er apart bovenop en zijn gemarkeerd met *.</p>"
                   "<p>Van Dravenlock (Roger &amp; Claudio) · <a href='https://dravenlock.nl'>dravenlock.nl</a> · service@dravenlock.nl<br>"
                   "Vrije software onder de GNU GPL v3.0.</p>",
                   "<h2>DraveWriter %s</h2><p>Make your own recipe book or an ordinary book, big and clear. Free, no account, no ads.</p>"
                   "<p>Nutrition: based on data from NEVO-online version 2025/9.0, RIVM, Bilthoven. "
                   "The table is used unchanged; your own values sit on top of it and are marked with *.</p>"
                   "<p>By Dravenlock (Roger &amp; Claudio) · <a href='https://dravenlock.nl'>dravenlock.nl</a> · service@dravenlock.nl<br>"
                   "Free software under the GNU GPL v3.0.</p>"),
}


def T(k):
    a, b = TX[k]
    return a if NL else b


def stijl(f=1.0):
    q = lambda n: "%dpx" % round(n * f)
    return """
* { font-family: 'Segoe UI', Arial; font-size: %(n)s; color: #efeaff; }
QMainWindow, QDialog, QWidget#wortel { background: #16131f; }
QLabel#titel { font-size: %(t)s; font-weight: 800; color: #b59cff; }
QLabel#kop { font-size: %(k)s; font-weight: 700; color: #ffd166; margin-top: 10px; }
QLabel#sub { color: #b9b2d6; font-size: %(s)s; }
QLabel#waarschuw { color: #ffb4a8; font-size: %(s)s; }
QPushButton { background: #221c33; border: 2px solid #4a3d66; border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { border-color: #b59cff; }
QPushButton:disabled { color: #6b6488; border-color: #2e2745; }
QPushButton#paars { background: #7F77DD; color: #16131f; font-weight: 700; }
QPushButton#start { font-size: %(k)s; padding: 22px; min-width: 300px; }
QListWidget { background: #1d1829; border: 2px solid #4a3d66; border-radius: 10px; padding: 6px; }
QListWidget::item { padding: 8px; border-radius: 8px; }
QListWidget::item:selected { background: #3a2f5a; border: 2px solid #ffd166; }
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #221c33; border: 2px solid #4a3d66;
    border-radius: 8px; padding: 6px; }
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #ffd166; }
QComboBox QAbstractItemView { background: #221c33; selection-background-color: #7F77DD; }
QTableWidget { background: #1d1829; border: 2px solid #4a3d66; border-radius: 10px; gridline-color: #2e2745; }
QTableWidget::item:selected { background: #3a2f5a; }
QHeaderView::section { background: #221c33; color: #ffd166; border: none; padding: 6px; font-weight: 700; }
QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: #16131f; }
QSplitter::handle { background: #2e2745; width: 4px; }
QStatusBar { color: #b9b2d6; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 24px; height: 24px; }
""" % dict(n=q(16), t=q(26), k=q(18), s=q(14))


# ---------------------------------------------------------------- boek en recepten
def nieuw_recept():
    return dict(titel=T("nieuw_recept"), categorie="hoofdgerecht", personen=4, tijd_voor=0, tijd_koken=0, intro="",
                foto=None, ingredienten=[], stappen=[], tips="", voeding_eigen={})


def nieuw_boek():
    return dict(soort="recept", titel=T("naamloos"), ondertitel="", auteur="", kaftkleur="#2a2140", kaftfoto=None,
                achtertekst="", inhoud=True, inhoud_per_cat=True, recepten=[nieuw_recept()])


def nieuw_hoofdstuk():
    return dict(titel=T("nieuw_hfd"), tekst="", plaatjes=[])


def nieuw_gewoon_boek():
    return dict(soort="boek", titel=T("naamloos_boek"), ondertitel="", auteur="", kaftkleur="#1f2a40", kaftfoto=None,
                achtertekst="", inhoud=True, hoofdstukken=[nieuw_hoofdstuk()])


def sleutel(boek):
    return "hoofdstukken" if boek.get("soort") == "boek" else "recepten"


def omgerekend(rec, n):
    """Kopie van het recept voor n personen, hoeveelheden netjes afgerond."""
    r = copy.deepcopy(rec)
    oud = max(1, int(rec.get("personen") or 1))
    if n == oud:
        return r
    f = n / oud
    for ing in r.get("ingredienten", []):
        try:
            h = float(ing.get("hoeveel") or 0)
        except Exception:
            h = 0.0
        if h > 0 and ing.get("eenheid") != "naar smaak":
            ing["hoeveel"] = nevo.afgerond(h * f, ing.get("eenheid") or "")
        if ing.get("gram_eigen") not in (None, ""):
            ing["gram_eigen"] = round(float(ing["gram_eigen"]) * f, 1)
    r["personen"] = n
    return r


def foto_bytes(pad_of_beeld, max_px=1600):
    im = pad_of_beeld if isinstance(pad_of_beeld, QImage) else QImage(pad_of_beeld)
    if im.isNull():
        return None
    if max(im.width(), im.height()) > max_px:
        im = im.scaled(max_px, max_px, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    if im.hasAlphaChannel():
        # doorzichtige delen (PNG) worden wit, niet zwart
        wit = QImage(im.size(), QImage.Format.Format_RGB32)
        wit.fill(QColor("#ffffff"))
        q = QPainter(wit)
        q.drawImage(0, 0, im)
        q.end()
        im = wit
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    im.convertToFormat(QImage.Format.Format_RGB32).save(buf, "JPG", 88)
    return bytes(ba)


# ---------------------------------------------------------------- NEVO-keuze voor één ingrediënt
class NevoDialoog(QDialog):
    def __init__(self, ouder, tabel, ing):
        super().__init__(ouder)
        self.tabel, self.ing = tabel, copy.deepcopy(ing)
        self.setWindowTitle(T("kies_nevo"))
        self.resize(900, 760)
        v = QVBoxLayout(self)
        k = QLabel("%s: <b>%s</b>" % (T("kies_nevo"), (ing.get("naam") or "").replace("<", "&lt;")))
        k.setObjectName("kop")
        v.addWidget(k)
        self.zoek = QLineEdit(ing.get("naam", ""))
        self.zoek.setPlaceholderText(T("nevo_zoek"))
        self.zoek.textChanged.connect(self._zoek)
        v.addWidget(self.zoek)
        self.lijst = QListWidget()
        self.lijst.setMinimumHeight(300)
        self.lijst.itemDoubleClicked.connect(lambda _i: self.accept())
        v.addWidget(self.lijst, 1)
        g = QGridLayout()
        e = ing.get("eenheid") or ""
        self.per_stuk = None
        r = 0
        if e in nevo.TELBAAR:
            g.addWidget(QLabel(T("nevo_per_stuk") % (e if NL else nevo.EENHEDEN_EN.get(e, e))), r, 0)
            self.per_stuk = QDoubleSpinBox()
            self.per_stuk.setRange(0, 5000)
            self.per_stuk.setDecimals(1)
            self.per_stuk.setSuffix(" g")
            gok = ing.get("per_stuk") or (5.0 if e == "teen" else nevo.gram_per_stuk(ing.get("naam"))) or nevo.VAST.get(e) or 0
            self.per_stuk.setValue(float(gok))
            g.addWidget(self.per_stuk, r, 1)
            r += 1
        g.addWidget(QLabel(T("nevo_gram")), r, 0)
        self.gram = QLineEdit("" if ing.get("gram_eigen") in (None, "") else str(ing["gram_eigen"]))
        self.gram.setPlaceholderText("g")
        g.addWidget(self.gram, r, 1)
        v.addLayout(g)
        u = QLabel(T("nevo_eigen"))
        u.setObjectName("sub")
        u.setWordWrap(True)
        v.addWidget(u)
        eg = QGridLayout()
        self.eigen = {}
        for i, (_c, s, a, b, eenh) in enumerate(nevo.STOFFEN):
            eg.addWidget(QLabel((a if NL else b) + " (%s)" % eenh), i // 2, (i % 2) * 2)
            le = QLineEdit("" if not ing.get("eigen100") or ing["eigen100"].get(s) is None else str(ing["eigen100"][s]))
            le.setMaximumWidth(120)
            self.eigen[s] = le
            eg.addWidget(le, i // 2, (i % 2) * 2 + 1)
        v.addLayout(eg)
        kn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        kn.accepted.connect(self.accept)
        kn.rejected.connect(self.reject)
        v.addWidget(kn)
        self._zoek()

    def _zoek(self):
        self.lijst.clear()
        it = QListWidgetItem(T("nevo_geen"))
        it.setData(Qt.ItemDataRole.UserRole, None)
        self.lijst.addItem(it)
        kies = self.lijst.item(0)
        gevonden = self.tabel.zoek(self.zoek.text(), 80) if self.tabel is not None else []
        huidig = self.ing.get("nevo")
        if huidig and self.tabel is not None and huidig in self.tabel.per_code and all(x["code"] != huidig for x in gevonden):
            gevonden = [self.tabel.per_code[huidig]] + gevonden
        for x in gevonden:
            w = x["w"]
            t = "%s   —   %s kcal / 100 g" % (x["nl"] if NL else x["en"], "?" if w.get("kcal") is None else int(round(w["kcal"])))
            it = QListWidgetItem(t)
            it.setData(Qt.ItemDataRole.UserRole, x["code"])
            self.lijst.addItem(it)
            if x["code"] == huidig:
                kies = it
        if not huidig and self.lijst.count() > 1:
            kies = self.lijst.item(1)
        self.lijst.setCurrentItem(kies)

    def resultaat(self):
        ing = self.ing
        it = self.lijst.currentItem()
        ing["nevo"] = it.data(Qt.ItemDataRole.UserRole) if it else None
        if self.per_stuk is not None:
            ing["per_stuk"] = self.per_stuk.value() or None
        t = self.gram.text().strip().replace(",", ".")
        try:
            ing["gram_eigen"] = float(t) if t else None
        except Exception:
            ing["gram_eigen"] = None
        e = {}
        for s, le in self.eigen.items():
            t = le.text().strip().replace(",", ".")
            if t:
                try:
                    e[s] = float(t)
                except Exception:
                    pass
        ing["eigen100"] = e or None
        if e:
            for s in nevo.SLEUTELS:
                e.setdefault(s, None)
        return ing


# ---------------------------------------------------------------- boek en kaft
class BoekDialoog(QDialog):
    def __init__(self, ouder, boek, fotos):
        super().__init__(ouder)
        self.boek, self.fotos = copy.deepcopy({k: v for k, v in boek.items() if k not in ("recepten", "hoofdstukken")}), fotos
        self.recepten = boek.get("recepten", [])
        self.nieuwe_foto = None
        self.setWindowTitle(T("boek").strip("📘 "))
        self.resize(760, 760)
        v = QVBoxLayout(self)
        g = QGridLayout()
        self.titel = QLineEdit(self.boek.get("titel", ""))
        self.sub = QLineEdit(self.boek.get("ondertitel", ""))
        self.auteur = QLineEdit(self.boek.get("auteur", ""))
        for r, (k, w) in enumerate((("b_titel", self.titel), ("b_sub", self.sub), ("b_auteur", self.auteur))):
            g.addWidget(QLabel(T(k)), r, 0)
            g.addWidget(w, r, 1)
        g.addWidget(QLabel(T("b_foto")), 3, 0)
        self.foto = QComboBox()
        self.foto.addItem(T("b_geen_foto"), None)
        for rec in self.recepten:
            if rec.get("foto"):
                self.foto.addItem(rec.get("titel", "?"), rec["foto"])
        for h in boek.get("hoofdstukken", []):
            for pl in h.get("plaatjes", []):
                if pl.get("foto") and self.foto.findData(pl["foto"]) < 0:
                    self.foto.addItem("%s (%s)" % (pl.get("onder") or T("p_bestand"), h.get("titel", "")), pl["foto"])
        if self.boek.get("kaftfoto") and self.foto.findData(self.boek["kaftfoto"]) < 0:
            self.foto.addItem(T("eigen_waarden").replace("waarden", "foto") if NL else "Own photo", self.boek["kaftfoto"])
        i = self.foto.findData(self.boek.get("kaftfoto"))
        self.foto.setCurrentIndex(max(0, i))
        g.addWidget(self.foto, 3, 1)
        b = QPushButton(T("b_eigen_foto"))
        b.clicked.connect(self._eigen_foto)
        g.addWidget(b, 4, 1)
        self.kleur = self.boek.get("kaftkleur") or "#2a2140"
        self.k_kleur = QPushButton(T("b_kleur"))
        self.k_kleur.clicked.connect(self._kies_kleur)
        g.addWidget(self.k_kleur, 5, 1)
        v.addLayout(g)
        v.addWidget(QLabel(T("b_achter")))
        self.achter = QPlainTextEdit(self.boek.get("achtertekst", ""))
        self.achter.setMaximumHeight(150)
        v.addWidget(self.achter)
        self.inhoud = QCheckBox(T("b_inhoud"))
        self.inhoud.setChecked(bool(self.boek.get("inhoud", True)))
        v.addWidget(self.inhoud)
        self.per_cat = QCheckBox(T("b_per_cat"))
        self.per_cat.setChecked(bool(self.boek.get("inhoud_per_cat", True)))
        v.addWidget(self.per_cat)
        self.per_cat.setVisible(self.boek.get("soort") != "boek")
        v.addStretch(1)
        kn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        kn.accepted.connect(self.accept)
        kn.rejected.connect(self.reject)
        v.addWidget(kn)
        self._kleur_knop()

    def _kleur_knop(self):
        self.k_kleur.setStyleSheet("border-bottom: 10px solid %s;" % self.kleur)

    def _kies_kleur(self):
        k = QColorDialog.getColor(QColor(self.kleur), self, T("b_kleur"))
        if k.isValid():
            self.kleur = k.name()
            self._kleur_knop()

    def _eigen_foto(self):
        pad, _ = QFileDialog.getOpenFileName(self, T("b_eigen_foto"), "", "Foto (*.jpg *.jpeg *.png *.webp *.bmp)")
        if not pad:
            return
        data = foto_bytes(pad)
        if not data:
            return
        fid = hashlib.md5(data).hexdigest()[:16]
        self.fotos.data[fid] = data
        self.foto.addItem(os.path.basename(pad), fid)
        self.foto.setCurrentIndex(self.foto.count() - 1)

    def resultaat(self):
        return dict(titel=self.titel.text().strip(), ondertitel=self.sub.text().strip(), auteur=self.auteur.text().strip(),
                    kaftfoto=self.foto.currentData(), kaftkleur=self.kleur, achtertekst=self.achter.toPlainText().strip(),
                    inhoud=self.inhoud.isChecked(), inhoud_per_cat=self.per_cat.isChecked())


# ---------------------------------------------------------------- startkeuze
class Start(QDialog):
    def _boek(self):
        self.keuze = "boek"
        self.accept()

    def __init__(self, ouder=None):
        super().__init__(ouder)
        self.setWindowTitle(APP)
        v = QVBoxLayout(self)
        k = QLabel(T("start_kop"))
        k.setObjectName("titel")
        k.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(k)
        r = QHBoxLayout()
        b = QPushButton(T("start_recept"))
        b.setObjectName("start")
        b.clicked.connect(self.accept)
        r.addWidget(b)
        b2 = QPushButton(T("start_boek"))
        b2.setObjectName("start")
        b2.clicked.connect(self._boek)
        r.addWidget(b2)
        self.keuze = "recept"
        v.addLayout(r)


# ---------------------------------------------------------------- het hoofdvenster
class Hoofd(QMainWindow):
    def __init__(self):
        super().__init__()
        self.instel = self._lees()
        self.f = float(self.instel.get("groot", 1.0))
        self.setWindowTitle(APP)
        ico = _res("assets", "icon.ico")
        if os.path.exists(ico):
            self.setWindowIcon(QIcon(ico))
        self.tabel = nevo.Tabel()
        self.tabel.laad_map(NEVO_DATA, _res("NEVO"), os.path.join(_base(), "NEVO"))
        self.fotos = pg.Fotos()
        self.boek = nieuw_boek()
        self.pad = None
        self.veranderd = False
        self.ri = 0
        self.vb_blz = 0
        self._bezig = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self.ververs_voorbeeld)
        self._timer.timeout.connect(self._onthoud)
        self._terug, self._vooruit = [], []
        self._bouw()
        self.setStyleSheet(stijl(self.f))
        self.resize(1600, 980)
        self.ververs_lijst()
        self.toon_recept()
        self._onthoud()
        if not len(self.tabel):
            self.statusBar().showMessage(T("v_geen_tabel"), 15000)

    # -- instellingen
    def _lees(self):
        try:
            return json.load(open(INSTEL, encoding="utf-8"))
        except Exception:
            return {}

    def _bewaar_instel(self):
        try:
            json.dump(self.instel, open(INSTEL, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception as e:
            _log("instellingen: %s" % e)

    # -- opbouw
    def _bouw(self):
        w = QWidget()
        w.setObjectName("wortel")
        self.setCentralWidget(w)
        v = QVBoxLayout(w)
        bal = QHBoxLayout()
        logo = QLabel()
        lp = _res("assets", "icon.png")
        if os.path.exists(lp):
            logo.setPixmap(QPixmap(lp).scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        bal.addWidget(logo)
        t = QLabel(APP)
        t.setObjectName("titel")
        bal.addWidget(t)
        bal.addSpacing(12)
        for k, f in (("nieuw", self.nieuw), ("open", self.openen), ("opslaan", self.opslaan), ("opslaan_als", self.opslaan_als),
                     ("boek", self.boek_instellen), ("pdf", self.pdf), ("drukker", self.drukklaar)):
            b = QPushButton(T(k))
            b.clicked.connect(f)
            bal.addWidget(b)
        for k, f in (("ongedaan", self.ongedaan), ("opnieuw", self.opnieuw)):
            b = QPushButton(T(k))
            b.clicked.connect(f)
            bal.addWidget(b)
        bal.addStretch(1)
        for k, f in (("klein", lambda: self.zoom(-0.1)), ("groot", lambda: self.zoom(0.1)), ("gids", self.gids), ("over", self.over)):
            b = QPushButton(T(k))
            b.clicked.connect(f)
            bal.addWidget(b)
        v.addLayout(bal)
        sp = QSplitter(Qt.Orientation.Horizontal)
        v.addWidget(sp, 1)
        # links: de recepten
        links = QWidget()
        lv = QVBoxLayout(links)
        lv.setContentsMargins(0, 0, 6, 0)
        self.l_kop = QLabel(T("recepten"))
        self.l_kop.setObjectName("kop")
        lv.addWidget(self.l_kop)
        self.lijst = QListWidget()
        self.lijst.currentRowChanged.connect(self.kies_recept)
        lv.addWidget(self.lijst, 1)
        r = QHBoxLayout()
        self.k_bij = QPushButton(T("r_bij"))
        self.k_bij.clicked.connect(self.recept_bij)
        r.addWidget(self.k_bij)
        b = QPushButton(T("r_weg"))
        b.clicked.connect(self.recept_weg)
        r.addWidget(b)
        lv.addLayout(r)
        r = QHBoxLayout()
        for tekst, d in (("▲", -1), ("▼", 1)):
            b = QPushButton(tekst)
            b.clicked.connect(lambda _=False, d=d: self.recept_schuif(d))
            r.addWidget(b)
        lv.addLayout(r)
        sp.addWidget(links)
        # midden: het recept invullen
        self.form = QWidget()
        self.form.setObjectName("wortel")
        fv = QVBoxLayout(self.form)
        g = QGridLayout()
        self.e_titel = QLineEdit()
        self.e_cat = QComboBox()
        for c, a, b in pg.CATS:
            self.e_cat.addItem((a if NL else b) or "—", c)
        self.e_pers = QSpinBox()
        self.e_pers.setRange(1, 60)
        self.e_voor = QSpinBox()
        self.e_voor.setRange(0, 1440)
        self.e_koken = QSpinBox()
        self.e_koken.setRange(0, 1440)
        self.e_intro = QLineEdit()
        rij = 0
        for k, wdg in (("titel", self.e_titel), ("cat", self.e_cat), ("personen", self.e_pers), ("t_voor", self.e_voor),
                       ("t_koken", self.e_koken), ("intro", self.e_intro)):
            g.addWidget(QLabel(T(k)), rij, 0)
            g.addWidget(wdg, rij, 1)
            rij += 1
        fv.addLayout(g)
        fr = QHBoxLayout()
        self.f_klein = QLabel(T("geen_foto"))
        self.f_klein.setFixedSize(180, 120)
        self.f_klein.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.f_klein.setStyleSheet("border: 2px dashed #4a3d66; border-radius: 10px; color: #6b6488;")
        fr.addWidget(self.f_klein)
        fk = QVBoxLayout()
        b = QPushButton(T("foto"))
        b.clicked.connect(self.foto_kies)
        fk.addWidget(b)
        b = QPushButton(T("foto_weg"))
        b.clicked.connect(self.foto_weg)
        fk.addWidget(b)
        fk.addStretch(1)
        fr.addLayout(fk)
        fr.addStretch(1)
        fv.addLayout(fr)
        k = QLabel(T("ings"))
        k.setObjectName("kop")
        fv.addWidget(k)
        self.tab = QTableWidget(0, 4)
        self.tab.setHorizontalHeaderLabels([T("kol_h"), T("kol_e"), T("kol_n"), T("kol_v")])
        hh = self.tab.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.tab.verticalHeader().setVisible(False)
        self.tab.verticalHeader().setDefaultSectionSize(48)
        self.tab.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tab.setMinimumHeight(300)
        fv.addWidget(self.tab)
        r = QHBoxLayout()
        for tekst, f in ((T("i_bij"), self.ing_bij), (T("i_weg"), self.ing_weg), ("▲", lambda: self.ing_schuif(-1)), ("▼", lambda: self.ing_schuif(1))):
            b = QPushButton(tekst)
            b.clicked.connect(f)
            r.addWidget(b)
        r.addStretch(1)
        fv.addLayout(r)
        k = QLabel(T("stappen"))
        k.setObjectName("kop")
        fv.addWidget(k)
        u = QLabel(T("stappen_uitleg"))
        u.setObjectName("sub")
        fv.addWidget(u)
        self.e_stappen = QPlainTextEdit()
        self.e_stappen.setMinimumHeight(220)
        fv.addWidget(self.e_stappen)
        k = QLabel(T("tips"))
        k.setObjectName("kop")
        fv.addWidget(k)
        self.e_tips = QPlainTextEdit()
        self.e_tips.setMaximumHeight(120)
        fv.addWidget(self.e_tips)
        k = QLabel(T("voeding"))
        k.setObjectName("kop")
        fv.addWidget(k)
        u = QLabel(T("v_uitleg"))
        u.setObjectName("sub")
        u.setWordWrap(True)
        fv.addWidget(u)
        self.v_geen = QWidget()
        gl = QHBoxLayout(self.v_geen)
        gl.setContentsMargins(0, 0, 0, 0)
        u = QLabel(T("v_geen_tabel"))
        u.setObjectName("waarschuw")
        u.setWordWrap(True)
        gl.addWidget(u, 1)
        b = QPushButton(T("v_laden"))
        b.clicked.connect(self.nevo_laden)
        gl.addWidget(b)
        fv.addWidget(self.v_geen)
        vg = QGridLayout()
        self.v_ber, self.v_eigen = {}, {}
        for i, (_c, s, a, b2, eenh) in enumerate(nevo.STOFFEN):
            vg.addWidget(QLabel((a if NL else b2)), i, 0)
            lb = QLabel("–")
            lb.setMinimumWidth(110)
            lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.v_ber[s] = lb
            vg.addWidget(lb, i, 1)
            le = QLineEdit()
            le.setPlaceholderText(T("v_eigen") + " (" + eenh + ")")
            le.setMaximumWidth(160)
            le.textEdited.connect(self._eigen_voeding)
            self.v_eigen[s] = le
            vg.addWidget(le, i, 2)
        vg.setColumnStretch(3, 1)
        fv.addLayout(vg)
        self.v_ontbreekt = QLabel("")
        self.v_ontbreekt.setObjectName("waarschuw")
        self.v_ontbreekt.setWordWrap(True)
        fv.addWidget(self.v_ontbreekt)
        fv.addStretch(1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.form)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.midden = QStackedWidget()
        self.midden.addWidget(sc)
        self.midden.addWidget(self._bouw_hoofdstuk())
        sp.addWidget(self.midden)
        # rechts: het voorbeeld
        rechts = QWidget()
        rv = QVBoxLayout(rechts)
        rv.setContentsMargins(6, 0, 0, 0)
        k = QLabel(T("voorbeeld"))
        k.setObjectName("kop")
        rv.addWidget(k)
        self.vb_rij = QWidget()
        r = QHBoxLayout(self.vb_rij)
        r.setContentsMargins(0, 0, 0, 0)
        r.addWidget(QLabel(T("vb_personen")))
        self.vb_pers = QSpinBox()
        self.vb_pers.setRange(1, 60)
        self.vb_pers.valueChanged.connect(lambda _v: self.ververs_voorbeeld())
        r.addWidget(self.vb_pers)
        r.addWidget(QLabel(T("vb_pers")))
        r.addStretch(1)
        rv.addWidget(self.vb_rij)
        self.k_omreken = QPushButton(T("omrekenen"))
        self.k_omreken.clicked.connect(self.omrekenen)
        rv.addWidget(self.k_omreken)
        self.vb = QLabel()
        self.vb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vb.setMinimumSize(420, 560)
        rv.addWidget(self.vb, 1)
        r = QHBoxLayout()
        self.vb_terug = QPushButton("◀")
        self.vb_terug.setStyleSheet("font-size: 22px; padding: 6px 22px;")
        self.vb_terug.clicked.connect(lambda: self.vb_blader(-1))
        self.vb_teller = QLabel("")
        self.vb_teller.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vb_verder = QPushButton("▶")
        self.vb_verder.setStyleSheet("font-size: 22px; padding: 6px 22px;")
        self.vb_verder.clicked.connect(lambda: self.vb_blader(1))
        r.addWidget(self.vb_terug)
        r.addWidget(self.vb_teller, 1)
        r.addWidget(self.vb_verder)
        rv.addLayout(r)
        self.k_pdf_een = QPushButton(T("pdf_een"))
        self.k_pdf_een.clicked.connect(self.pdf_een)
        rv.addWidget(self.k_pdf_een)
        sp.addWidget(rechts)
        sp.setSizes([260, 760, 560])
        sp.setStretchFactor(1, 1)
        # veranderingen bijhouden
        for wdg in (self.e_titel, self.e_intro):
            wdg.textEdited.connect(self._uit_form)
        for wdg in (self.e_pers, self.e_voor, self.e_koken):
            wdg.valueChanged.connect(self._uit_form)
        self.e_cat.currentIndexChanged.connect(self._uit_form)
        self.e_stappen.textChanged.connect(self._uit_form)
        self.e_tips.textChanged.connect(self._uit_form)
        self.tab.cellChanged.connect(self._uit_tabel)
        QShortcut(QKeySequence.StandardKey.Save, self, self.opslaan)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.ongedaan)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.opnieuw)
        QShortcut(QKeySequence.StandardKey.Open, self, self.openen)

    def _bouw_hoofdstuk(self):
        w = QWidget()
        w.setObjectName("wortel")
        v = QVBoxLayout(w)
        g = QHBoxLayout()
        g.addWidget(QLabel(T("h_titel")))
        self.h_titel = QLineEdit()
        g.addWidget(self.h_titel, 1)
        v.addLayout(g)
        k = QLabel(T("h_tekst"))
        k.setObjectName("kop")
        v.addWidget(k)
        u = QLabel(T("h_tekst_uitleg"))
        u.setObjectName("sub")
        u.setWordWrap(True)
        v.addWidget(u)
        self.h_tekst = QPlainTextEdit()
        self.h_tekst.setStyleSheet("font-family: Georgia, serif; font-size: %dpx;" % round(19 * self.f))
        v.addWidget(self.h_tekst, 3)
        self.h_tel = QLabel("")
        self.h_tel.setObjectName("sub")
        v.addWidget(self.h_tel)
        k = QLabel(T("h_plaatjes"))
        k.setObjectName("kop")
        v.addWidget(k)
        self.p_tab = QTableWidget(0, 3)
        self.p_tab.setHorizontalHeaderLabels([T("p_bestand"), T("p_na"), T("p_onder")])
        hh = self.p_tab.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.p_tab.verticalHeader().setVisible(False)
        self.p_tab.verticalHeader().setDefaultSectionSize(64)
        self.p_tab.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.p_tab.setMinimumHeight(150)
        self.p_tab.cellChanged.connect(self._uit_plaatjes)
        v.addWidget(self.p_tab, 1)
        r = QHBoxLayout()
        for tekst, f in ((T("p_bij"), self.plaatje_bij), (T("p_weg"), self.plaatje_weg)):
            b = QPushButton(tekst)
            b.clicked.connect(f)
            r.addWidget(b)
        r.addStretch(1)
        v.addLayout(r)
        self.h_titel.textEdited.connect(self._uit_hoofdstuk)
        self.h_tekst.textChanged.connect(self._uit_hoofdstuk)
        return w

    def is_boek(self):
        return self.boek.get("soort") == "boek"

    def items(self):
        return self.boek.setdefault(sleutel(self.boek), [])

    def _soort_bij(self):
        """Knoppen en panelen passend bij receptenboek of gewoon boek."""
        b = self.is_boek()
        self.l_kop.setText(T("hoofdstukken") if b else T("recepten"))
        self.k_bij.setText(T("h_bij") if b else T("r_bij"))
        self.midden.setCurrentIndex(1 if b else 0)
        self.vb_rij.setVisible(not b)
        self.k_omreken.setVisible(not b)
        self.k_pdf_een.setVisible(not b)

    def toon_hoofdstuk(self):
        h = self.rec()
        self._bezig = True
        try:
            self.h_titel.setText(h.get("titel", "") if h else "")
            self.h_tekst.setPlainText(h.get("tekst", "") if h else "")
            self._plaatjes_vullen()
        finally:
            self._bezig = False
        self._tel()
        self.ververs_voorbeeld()

    def _tel(self):
        t = self.h_tekst.toPlainText()
        self.h_tel.setText(T("woorden") % (len(t.split()), len(pg.alineas(t))))

    def _uit_hoofdstuk(self, *_a):
        if self._bezig:
            return
        h = self.rec()
        if h is None:
            return
        oud = h.get("titel")
        h["titel"] = self.h_titel.text().strip()
        h["tekst"] = self.h_tekst.toPlainText()
        if oud != h["titel"]:
            it = self.lijst.item(self.ri)
            if it:
                it.setText("%d.  %s" % (self.ri + 1, h["titel"] or "?"))
        self._tel()
        self._veranderd()

    def _plaatjes_vullen(self):
        h = self.rec()
        self.p_tab.blockSignals(True)
        self.p_tab.setRowCount(0)
        for i, pl in enumerate((h or {}).get("plaatjes", [])):
            self.p_tab.insertRow(i)
            lb = QLabel()
            im = self.fotos.beeld(pl.get("foto"))
            if im is not None and not im.isNull():
                lb.setPixmap(QPixmap.fromImage(im).scaled(90, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                          Qt.TransformationMode.SmoothTransformation))
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.p_tab.setCellWidget(i, 0, lb)
            sb = QSpinBox()
            sb.setRange(0, 9999)
            sb.setValue(int(pl.get("na", 0)))
            sb.valueChanged.connect(lambda v, rij=i: self._plaatje_na(rij, v))
            self.p_tab.setCellWidget(i, 1, sb)
            self.p_tab.setItem(i, 2, QTableWidgetItem(pl.get("onder", "")))
        self.p_tab.blockSignals(False)

    def _plaatje_na(self, rij, v):
        h = self.rec()
        if h and 0 <= rij < len(h.get("plaatjes", [])):
            h["plaatjes"][rij]["na"] = v
            self._veranderd()

    def _uit_plaatjes(self, rij, kol):
        h = self.rec()
        if kol == 2 and h and 0 <= rij < len(h.get("plaatjes", [])):
            h["plaatjes"][rij]["onder"] = self.p_tab.item(rij, 2).text().strip()
            self._veranderd()

    def plaatje_bij(self):
        h = self.rec()
        if h is None:
            return
        pad, _ = QFileDialog.getOpenFileName(self, T("p_bij").strip("📷 "), self.instel.get("foto_map") or os.path.expanduser("~"),
                                             "Foto (*.jpg *.jpeg *.png *.webp *.bmp)")
        if not pad:
            return
        self.instel["foto_map"] = os.path.dirname(pad)
        data = foto_bytes(pad)
        if not data:
            QMessageBox.warning(self, APP, T("fout_open"))
            return
        fid = hashlib.md5(data).hexdigest()[:16]
        self.fotos.data[fid] = data
        im = self.fotos.beeld(fid)
        # standaard: na de alinea waar de cursor nu staat
        voor = self.h_tekst.toPlainText()[:self.h_tekst.textCursor().position()]
        na = len(pg.alineas(voor))
        h.setdefault("plaatjes", []).append(dict(foto=fid, na=na, onder="", verhouding=im.height() / max(1, im.width())))
        if not self.boek.get("kaftfoto"):
            self.boek["kaftfoto"] = fid
        self._plaatjes_vullen()
        self._veranderd()

    def plaatje_weg(self):
        h = self.rec()
        i = self.p_tab.currentRow()
        if h and 0 <= i < len(h.get("plaatjes", [])):
            del h["plaatjes"][i]
            self._plaatjes_vullen()
            self._veranderd()

    # -- ongedaan maken: kopieën van het boek (de foto's zelf blijven in self.fotos)
    def _stand(self):
        return json.dumps(self.boek, ensure_ascii=False, sort_keys=True)

    def _onthoud(self):
        st = self._stand()
        if not self._terug or self._terug[-1] != st:
            self._terug.append(st)
            del self._terug[:-100]
            self._vooruit.clear()

    def _herstel(self, st):
        self._bezig = True
        self.boek = json.loads(st)
        self._bezig = False
        self.ververs_lijst()
        self.toon_recept()
        self.veranderd = True
        self._titel()

    def ongedaan(self):
        self._onthoud()
        if len(self._terug) < 2:
            return
        self._vooruit.append(self._terug.pop())
        self._herstel(self._terug[-1])

    def opnieuw(self):
        if not self._vooruit:
            return
        st = self._vooruit.pop()
        self._terug.append(st)
        self._herstel(st)

    # -- het huidige recept
    def rec(self):
        rs = self.items()
        if not rs:
            return None
        self.ri = max(0, min(self.ri, len(rs) - 1))
        return rs[self.ri]

    def ververs_lijst(self):
        self.lijst.blockSignals(True)
        self.lijst.clear()
        for i, r in enumerate(self.items()):
            self.lijst.addItem("%d.  %s" % (i + 1, r.get("titel") or "?"))
        self.lijst.setCurrentRow(self.ri)
        self.lijst.blockSignals(False)

    def kies_recept(self, i):
        if i < 0:
            return
        self.ri = i
        self.vb_blz = 0
        self.toon_recept()

    def toon_recept(self):
        self._soort_bij()
        if self.is_boek():
            self.toon_hoofdstuk()
            return
        r = self.rec()
        self.form.setEnabled(r is not None)
        if r is None:
            self.ververs_voorbeeld()
            return
        self._bezig = True
        try:
            self.e_titel.setText(r.get("titel", ""))
            self.e_cat.setCurrentIndex(max(0, self.e_cat.findData(r.get("categorie", ""))))
            self.e_pers.setValue(int(r.get("personen") or 4))
            self.e_voor.setValue(int(r.get("tijd_voor") or 0))
            self.e_koken.setValue(int(r.get("tijd_koken") or 0))
            self.e_intro.setText(r.get("intro", ""))
            self.e_stappen.setPlainText("\n".join(r.get("stappen", [])))
            self.e_tips.setPlainText(r.get("tips", ""))
            self.vb_pers.blockSignals(True)
            self.vb_pers.setValue(int(r.get("personen") or 4))
            self.vb_pers.blockSignals(False)
            for s, le in self.v_eigen.items():
                v = (r.get("voeding_eigen") or {}).get(s)
                le.setText("" if v in (None, "") else str(v))
            self._foto_klein()
            self._tabel_vullen()
        finally:
            self._bezig = False
        self.ververs_voeding()
        self.ververs_voorbeeld()

    def _foto_klein(self):
        r = self.rec()
        im = self.fotos.beeld(r.get("foto")) if r and r.get("foto") else None
        if im is not None and not im.isNull():
            self.f_klein.setPixmap(QPixmap.fromImage(im).scaled(176, 116, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                                Qt.TransformationMode.SmoothTransformation))
        else:
            self.f_klein.setPixmap(QPixmap())
            self.f_klein.setText(T("geen_foto"))

    def _tabel_vullen(self):
        r = self.rec()
        self.tab.blockSignals(True)
        self.tab.setRowCount(0)
        for i, ing in enumerate(r.get("ingredienten", [])):
            self.tab.insertRow(i)
            h = ing.get("hoeveel")
            hv = "" if h in (None, "", 0, 0.0) else nevo.mooi_getal(float(h), NL)
            self.tab.setItem(i, 0, QTableWidgetItem(hv))
            cb = QComboBox()
            for e in nevo.EENHEDEN:
                cb.addItem(e if NL else nevo.EENHEDEN_EN.get(e, e), e)
            cb.setCurrentIndex(max(0, cb.findData(ing.get("eenheid") or "g")))
            cb.currentIndexChanged.connect(lambda _x, rij=i, c=cb: self._eenheid(rij, c))
            self.tab.setCellWidget(i, 1, cb)
            self.tab.setItem(i, 2, QTableWidgetItem(ing.get("naam", "")))
            b = QPushButton(self._nevo_tekst(ing))
            b.clicked.connect(lambda _=False, rij=i: self.nevo_kies(rij))
            self.tab.setCellWidget(i, 3, b)
        self.tab.blockSignals(False)

    def _nevo_tekst(self, ing):
        if ing.get("eenheid") == "naar smaak":
            return "—"
        if ing.get("eigen100"):
            return "✎ " + T("eigen_waarden")
        c = ing.get("nevo")
        if c and c in self.tabel.per_code:
            x = self.tabel.per_code[c]
            t = x["nl"] if NL else x["en"]
            g = ing.get("gram_eigen")
            if g in (None, ""):
                g = nevo.gram(ing.get("hoeveel"), ing.get("eenheid"), ing.get("naam"), ing.get("per_stuk"))
            if g is None:
                return "⚠ %s  (? g)" % t
            return "✓ %s" % t
        return "⚠ " + T("kies")

    def _leesgetal(self, t):
        t = (t or "").strip().replace(",", ".")
        for b, s in nevo.BREUK.items():
            if s in t:
                voor = t.replace(s, "").strip()
                return (float(voor) if voor else 0.0) + b
        try:
            return float(t) if t else 0.0
        except Exception:
            return 0.0

    def _uit_tabel(self, rij, kol):
        if self._bezig:
            return
        r = self.rec()
        ings = r["ingredienten"]
        if not (0 <= rij < len(ings)):
            return
        ing = ings[rij]
        if kol == 0:
            ing["hoeveel"] = self._leesgetal(self.tab.item(rij, 0).text())
        elif kol == 2:
            oud = ing.get("naam", "")
            ing["naam"] = self.tab.item(rij, 2).text().strip()
            if len(self.tabel) and ing["naam"] and (not ing.get("nevo") or not oud):
                b = self.tabel.beste(ing["naam"])
                ing["nevo"] = b["code"] if b else None
        self._veranderd()
        knop = self.tab.cellWidget(rij, 3)
        if knop is not None:
            knop.setText(self._nevo_tekst(ing))
        self.ververs_voeding()

    def _eenheid(self, rij, cb):
        r = self.rec()
        if 0 <= rij < len(r["ingredienten"]):
            r["ingredienten"][rij]["eenheid"] = cb.currentData()
            knop = self.tab.cellWidget(rij, 3)
            if knop is not None:
                knop.setText(self._nevo_tekst(r["ingredienten"][rij]))
            self._veranderd()
            self.ververs_voeding()

    def _uit_form(self, *_a):
        if self._bezig:
            return
        r = self.rec()
        if r is None:
            return
        oud_titel = r.get("titel")
        r["titel"] = self.e_titel.text().strip()
        r["categorie"] = self.e_cat.currentData()
        oud_p = r.get("personen")
        r["personen"] = self.e_pers.value()
        r["tijd_voor"] = self.e_voor.value()
        r["tijd_koken"] = self.e_koken.value()
        r["intro"] = self.e_intro.text().strip()
        r["stappen"] = [s.strip() for s in self.e_stappen.toPlainText().split("\n") if s.strip()]
        r["tips"] = self.e_tips.toPlainText().strip()
        if oud_p != r["personen"]:
            self.vb_pers.blockSignals(True)
            self.vb_pers.setValue(r["personen"])
            self.vb_pers.blockSignals(False)
            self.ververs_voeding()
        if oud_titel != r["titel"]:
            it = self.lijst.item(self.ri)
            if it:
                it.setText("%d.  %s" % (self.ri + 1, r["titel"] or "?"))
        self._veranderd()

    def _eigen_voeding(self, *_a):
        r = self.rec()
        e = {}
        for s, le in self.v_eigen.items():
            t = le.text().strip().replace(",", ".")
            if t:
                try:
                    e[s] = float(t)
                except Exception:
                    pass
        r["voeding_eigen"] = e
        self._veranderd()

    def _veranderd(self):
        self.veranderd = True
        self._titel()
        self._timer.start()

    def _titel(self):
        n = os.path.basename(self.pad) if self.pad else (self.boek.get("titel") or T("naamloos"))
        self.setWindowTitle("%s%s - %s %s" % ("● " if self.veranderd else "", n, APP, VERSIE))

    # -- voedingswaarden
    def ververs_voeding(self):
        r = self.rec()
        self.v_geen.setVisible(not len(self.tabel))
        if r is None:
            return
        w, ontbreekt, _e = nevo.bereken(r.get("ingredienten", []), self.tabel, r.get("personen") or 1)
        for _c, s, _a, _b, eenh in nevo.STOFFEN:
            v = w[s]
            t = ("%d kcal" % round(v)) if s == "kcal" else ("%.1f g" % v)
            self.v_ber[s].setText(t.replace(".", ",") if NL else t)
        self.v_ontbreekt.setText((T("v_ontbreekt") % ", ".join(ontbreekt)) if ontbreekt and len(self.tabel) else "")
        self._timer.start()

    def nevo_kies(self, rij):
        if not len(self.tabel):
            self.nevo_laden()
            if not len(self.tabel):
                return
        r = self.rec()
        if not (0 <= rij < len(r["ingredienten"])):
            return
        d = NevoDialoog(self, self.tabel, r["ingredienten"][rij])
        d.setStyleSheet(stijl(self.f))
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        r["ingredienten"][rij] = d.resultaat()
        self.tab.cellWidget(rij, 3).setText(self._nevo_tekst(r["ingredienten"][rij]))
        self._veranderd()
        self.ververs_voeding()

    def nevo_laden(self):
        pad, _ = QFileDialog.getOpenFileName(self, T("v_laden"), os.path.expanduser("~"), "NEVO (*.zip *.csv *.xlsx)")
        if not pad:
            return
        t = nevo.Tabel()
        if not t.laad(pad):
            QMessageBox.warning(self, APP, T("fout") % t.fout)
            return
        os.makedirs(NEVO_DATA, exist_ok=True)
        doel = os.path.join(NEVO_DATA, os.path.basename(pad))
        try:
            if os.path.abspath(pad) != os.path.abspath(doel):
                with open(pad, "rb") as a, open(doel, "wb") as b:   # onveranderd kopiëren
                    b.write(a.read())
            t.bestand = doel
        except Exception as e:
            _log("nevo kopie: %s" % e)
        self.tabel = t
        # de eerste gok voor ingrediënten die nog niets hebben
        for rec in self.boek.get("recepten", []):
            for ing in rec.get("ingredienten", []):
                if not ing.get("nevo") and ing.get("naam"):
                    b = t.beste(ing["naam"])
                    ing["nevo"] = b["code"] if b else None
        self.toon_recept()

    # -- ingrediënten
    def ing_bij(self):
        r = self.rec()
        if r is None:
            return
        r["ingredienten"].append(dict(hoeveel=0, eenheid="g", naam="", nevo=None))
        self._tabel_vullen()
        n = len(r["ingredienten"]) - 1
        self.tab.setCurrentCell(n, 0)
        self.tab.editItem(self.tab.item(n, 0))
        self._veranderd()

    def ing_weg(self):
        r = self.rec()
        i = self.tab.currentRow()
        if r is None or not (0 <= i < len(r["ingredienten"])):
            return
        del r["ingredienten"][i]
        self._tabel_vullen()
        self._veranderd()
        self.ververs_voeding()

    def ing_schuif(self, d):
        r = self.rec()
        i = self.tab.currentRow()
        j = i + d
        if r is None or not (0 <= i < len(r["ingredienten"])) or not (0 <= j < len(r["ingredienten"])):
            return
        ings = r["ingredienten"]
        ings[i], ings[j] = ings[j], ings[i]
        self._tabel_vullen()
        self.tab.setCurrentCell(j, 2)
        self._veranderd()

    # -- recepten
    def recept_bij(self):
        rs = self.items()
        rs.insert(self.ri + 1 if rs else 0, nieuw_hoofdstuk() if self.is_boek() else nieuw_recept())
        self.ri = self.ri + 1 if len(rs) > 1 else 0
        self.ververs_lijst()
        self.toon_recept()
        veld = self.h_titel if self.is_boek() else self.e_titel
        veld.setFocus()
        veld.selectAll()
        self._veranderd()

    def recept_weg(self):
        r = self.rec()
        if r is None:
            return
        if QMessageBox.question(self, APP, (("'%s' weghalen?" if NL else "Remove '%s'?") % (r.get("titel") or "?"))) \
                != QMessageBox.StandardButton.Yes:
            return
        del self.items()[self.ri]
        self.ri = max(0, self.ri - 1)
        self.ververs_lijst()
        self.toon_recept()
        self._veranderd()

    def recept_schuif(self, d):
        rs = self.items()
        j = self.ri + d
        if not (0 <= j < len(rs)):
            return
        rs[self.ri], rs[j] = rs[j], rs[self.ri]
        self.ri = j
        self.ververs_lijst()
        self._veranderd()

    # -- foto
    def foto_kies(self):
        r = self.rec()
        if r is None:
            return
        pad, _ = QFileDialog.getOpenFileName(self, T("foto").strip("📷 "), self.instel.get("foto_map") or os.path.expanduser("~"),
                                             "Foto (*.jpg *.jpeg *.png *.webp *.bmp)")
        if not pad:
            return
        self.instel["foto_map"] = os.path.dirname(pad)
        data = foto_bytes(pad)
        if not data:
            QMessageBox.warning(self, APP, T("fout_open"))
            return
        fid = hashlib.md5(data).hexdigest()[:16]
        self.fotos.data[fid] = data
        r["foto"] = fid
        if not self.boek.get("kaftfoto"):
            self.boek["kaftfoto"] = fid
        self._foto_klein()
        self._veranderd()

    def foto_weg(self):
        r = self.rec()
        if r is not None and r.get("foto"):
            r["foto"] = None
            self._foto_klein()
            self._veranderd()

    # -- voorbeeld
    def _paginas_recept(self):
        r = self.rec()
        if r is None:
            return []
        n = self.vb_pers.value()
        r2 = omgerekend(r, n)
        b = dict(self.boek, recepten=[r2], inhoud=False)
        return [p for p in pg.bladzijden(b, self.tabel, NL) if p["soort"] == "recept"]

    def ververs_voorbeeld(self):
        if self.is_boek():
            ps = [x for x in self._alle() if x["soort"] == "hoofdstuk" and x["hi"] == self.ri]
            self._toon_blz(ps)
            return
        ps = self._paginas_recept()
        if not ps:
            self.vb.clear()
            self.vb_teller.setText("")
            return
        self.vb_blz = max(0, min(self.vb_blz, len(ps) - 1))
        p = ps[self.vb_blz]
        # het echte bladzijdenummer in het boek
        alle = self._alle()
        echte = [x for x in alle if x["soort"] == "recept" and x["ri"] == self.ri]
        if self.vb_blz < len(echte):
            p["nr"] = echte[self.vb_blz]["nr"]
        self._toon_blz(ps, klaar=True)
        r = self.rec()
        self.k_omreken.setEnabled(r is not None and self.vb_pers.value() != int(r.get("personen") or 1))

    def _toon_blz(self, ps, klaar=False):
        if not ps:
            self.vb.clear()
            self.vb_teller.setText("")
            return
        self.vb_blz = max(0, min(self.vb_blz, len(ps) - 1))
        p = ps[self.vb_blz]
        hoog = max(400, self.vb.height() - 10)
        breed = int(hoog * pg.PB / pg.PH)
        if breed > self.vb.width() - 10:
            breed = max(300, self.vb.width() - 10)
            hoog = int(breed * pg.PH / pg.PB)
        dpr = self.devicePixelRatioF()
        im = QImage(int(breed * dpr), int(hoog * dpr), QImage.Format.Format_ARGB32_Premultiplied)
        im.fill(QColor("#ffffff"))
        q = QPainter(im)
        try:
            pg.teken(q, p, breed * dpr / pg.PB, self.boek, self.fotos, NL)
        except Exception:
            _log("voorbeeld: " + traceback.format_exc())
        q.end()
        pm = QPixmap.fromImage(im)
        pm.setDevicePixelRatio(dpr)
        self.vb.setPixmap(pm)
        self.vb_teller.setText(("Bladzijde %d van %d" if NL else "Page %d of %d") % (self.vb_blz + 1, len(ps)))
        self.vb_terug.setEnabled(self.vb_blz > 0)
        self.vb_verder.setEnabled(self.vb_blz < len(ps) - 1)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_timer"):
            self._timer.start()

    def vb_blader(self, d):
        self.vb_blz += d
        self.ververs_voorbeeld()

    def omrekenen(self):
        r = self.rec()
        n = self.vb_pers.value()
        oud = int(r.get("personen") or 1)
        if n == oud:
            return
        if QMessageBox.question(self, APP, T("omreken_vraag") % (oud, n)) != QMessageBox.StandardButton.Yes:
            return
        self.boek["recepten"][self.ri] = omgerekend(r, n)
        self.toon_recept()
        self._veranderd()

    # -- boek
    def _alle(self):
        return pg.bladzijden(self.boek, self.tabel, NL)

    def boek_instellen(self):
        d = BoekDialoog(self, self.boek, self.fotos)
        d.setStyleSheet(stijl(self.f))
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self.boek.update(d.resultaat())
        self._veranderd()

    def _teken_fn(self):
        return lambda p, pagina, s: pg.teken(p, pagina, s, self.boek, self.fotos, NL)

    def pdf(self):
        if not self.items():
            QMessageBox.information(self, APP, T("druk_leeg"))
            return
        self._maak_pdf(self._alle(), self.boek.get("titel") or (T("naamloos_boek") if self.is_boek() else T("naamloos")))

    def pdf_een(self):
        ps = self._paginas_recept()
        if ps:
            self._maak_pdf(ps, self.rec().get("titel") or T("nieuw_recept"))

    def _maak_pdf(self, paginas, naam):
        start = os.path.join(self.instel.get("laatste_map") or MIJN, naam + ".pdf")
        os.makedirs(MIJN, exist_ok=True)
        pad, _ = QFileDialog.getSaveFileName(self, T("pdf").strip("📕 "), start, "PDF (*.pdf)")
        if not pad:
            return
        if not pad.lower().endswith(".pdf"):
            pad += ".pdf"
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            w = QPdfWriter(pad)
            w.setTitle(naam)
            w.setCreator("%s %s - Dravenlock" % (APP, VERSIE))
            w.setResolution(200)
            w.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)))
            p = QPainter(w)
            teken = self._teken_fn()
            s = w.width() / pg.PB
            for i, pagina in enumerate(paginas):
                if i:
                    w.newPage()
                teken(p, pagina, s)
            p.end()
        except Exception as e:
            _log("pdf: " + traceback.format_exc())
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, APP, T("fout") % e)
            return
        QApplication.restoreOverrideCursor()
        self.instel["laatste_map"] = os.path.dirname(pad)
        self._bewaar_instel()
        if QMessageBox.question(self, APP, T("pdf_klaar") % pad) == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(pad))

    def drukklaar(self):
        alle = self._alle()
        binnen = [p for p in alle if p["soort"] not in ("voor", "achter")]
        if not self.items():
            QMessageBox.information(self, APP, T("druk_leeg"))
            return
        voor = next(p for p in alle if p["soort"] == "voor")
        achter = next(p for p in alle if p["soort"] == "achter")
        titel = self.boek.get("titel") or T("naamloos")
        d = dk.DrukDialoog(self, NL, len(binnen), True, True, titel, self.instel)
        d.setStyleSheet(stijl(self.f))
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        w = d.waarden()
        self.instel.update(druk_formaat=w["formaat"], druk_afloop=w["afloop"], druk_vel=w["vel"], druk_aanvul=w["aanvul"],
                           druk_tekens=w["tekens"], druk_rugkleur=w["rugkleur"], druk_rugtekst=bool(w["rugtekst"]))
        self._bewaar_instel()
        map_ = QFileDialog.getExistingDirectory(self, T("druk_map"), self.instel.get("laatste_map") or MIJN)
        if not map_:
            return
        maker = "%s %s - Dravenlock" % (APP, VERSIE)
        p1 = os.path.join(map_, "%s - %s.pdf" % (titel, T("druk_binnen")))
        p2 = os.path.join(map_, "%s - %s.pdf" % (titel, T("druk_kaft")))
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            teken = self._teken_fn()
            n = dk.maak_binnenwerk(p1, binnen, teken, pg.PB, pg.PH, w["breed"], w["hoog"], w["afloop"], w["tekens"],
                                   w["aanvul"], titel, maker)
            kb, kh = dk.maak_kaft(p2, voor, achter, teken, pg.PB, pg.PH, w["breed"], w["hoog"], w["afloop"], w["rug"],
                                  w["tekens"], w["rugkleur"], w["rugtekst"], titel, maker)
        except Exception as e:
            _log("drukklaar: " + traceback.format_exc())
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, APP, T("fout") % e)
            return
        QApplication.restoreOverrideCursor()
        if QMessageBox.question(self, APP, T("druk_klaar") % (n, w["rug"], kb, kh, p1, p2)) == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(map_))

    # -- bestanden
    def _mag_weg(self):
        if not self.veranderd:
            return True
        k = QMessageBox.question(self, APP, T("vraag_bewaren"), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                 QMessageBox.StandardButton.Cancel)
        if k == QMessageBox.StandardButton.Cancel:
            return False
        if k == QMessageBox.StandardButton.Yes:
            return self.opslaan()
        return True

    def nieuw(self):
        if not self._mag_weg():
            return
        d = Start(self)
        d.setStyleSheet(stijl(self.f))
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        self.boek = nieuw_gewoon_boek() if d.keuze == "boek" else nieuw_boek()
        self.fotos = pg.Fotos()
        self.pad, self.ri, self.veranderd = None, 0, False
        self._terug, self._vooruit = [], []
        self._onthoud()
        self.ververs_lijst()
        self.toon_recept()
        self._titel()

    def openen(self, pad=None):
        if not self._mag_weg():
            return
        if not pad:
            os.makedirs(MIJN, exist_ok=True)
            pad, _ = QFileDialog.getOpenFileName(self, T("open").strip("📂 "), self.instel.get("laatste_map") or MIJN,
                                                 "%s (*%s)" % (T("project"), EXT))
        if not pad:
            return
        try:
            with zipfile.ZipFile(pad) as z:
                boek = json.loads(z.read("boek.json").decode("utf-8"))
                fotos = pg.Fotos()
                for n in z.namelist():
                    if n.startswith("fotos/") and n.endswith(".jpg"):
                        fotos.data[n[6:-4]] = z.read(n)
        except Exception:
            _log("openen: " + traceback.format_exc())
            QMessageBox.warning(self, APP, T("fout_open"))
            return
        base = nieuw_gewoon_boek() if boek.get("soort") == "boek" else nieuw_boek()
        base.update(boek)
        self.boek, self.fotos, self.pad, self.ri, self.veranderd = base, fotos, pad, 0, False
        self._terug, self._vooruit = [], []
        self._onthoud()
        self.instel["laatste_map"] = os.path.dirname(pad)
        self._bewaar_instel()
        self.ververs_lijst()
        self.toon_recept()
        self._titel()

    def opslaan(self):
        if not self.pad:
            return self.opslaan_als()
        return self._schrijf(self.pad)

    def opslaan_als(self):
        os.makedirs(MIJN, exist_ok=True)
        start = os.path.join(self.instel.get("laatste_map") or MIJN, (self.boek.get("titel") or T("naamloos")) + EXT)
        pad, _ = QFileDialog.getSaveFileName(self, T("opslaan_als"), start, "%s (*%s)" % (T("project"), EXT))
        if not pad:
            return False
        if not pad.lower().endswith(EXT):
            pad += EXT
        return self._schrijf(pad)

    def _schrijf(self, pad):
        gebruikt = {r.get("foto") for r in self.boek.get("recepten", []) if r.get("foto")}
        for h in self.boek.get("hoofdstukken", []):
            gebruikt |= {pl.get("foto") for pl in h.get("plaatjes", []) if pl.get("foto")}
        if self.boek.get("kaftfoto"):
            gebruikt.add(self.boek["kaftfoto"])
        tmp = pad + ".tmp"
        try:
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("boek.json", json.dumps(dict(self.boek, app=APP, versie=VERSIE), ensure_ascii=False, indent=1))
                for fid in gebruikt:
                    if fid in self.fotos.data:
                        z.writestr("fotos/%s.jpg" % fid, self.fotos.data[fid])
            os.replace(tmp, pad)
        except Exception as e:
            _log("opslaan: " + traceback.format_exc())
            QMessageBox.warning(self, APP, T("fout") % e)
            return False
        self.pad, self.veranderd = pad, False
        self.instel["laatste_map"] = os.path.dirname(pad)
        self._bewaar_instel()
        self._titel()
        self.statusBar().showMessage(T("bewaard") % pad, 6000)
        return True

    # -- overig
    def zoom(self, d):
        self.f = max(0.8, min(1.8, round(self.f + d, 2)))
        self.instel["groot"] = self.f
        self._bewaar_instel()
        self.setStyleSheet(stijl(self.f))

    def gids(self):
        p = _res("%s-Snelgids.pdf" % APP)
        if os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    def over(self):
        m = QMessageBox(self)
        m.setWindowTitle(APP)
        m.setTextFormat(Qt.TextFormat.RichText)
        m.setText(T("over_tekst") % VERSIE)
        m.exec()

    def closeEvent(self, e):
        if self._mag_weg():
            e.accept()
        else:
            e.ignore()


def main():
    sys.excepthook = lambda t, v, tb: _log("".join(traceback.format_exception(t, v, tb)))
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    w = Hoofd()
    try:
        import drave_doneer
        drave_doneer.voeg_toe(w, "nl" if NL else "en")
    except Exception:
        pass
    w.show()
    w._titel()
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith(EXT) and os.path.exists(sys.argv[1]):
        w.openen(sys.argv[1])
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
