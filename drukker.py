# -*- coding: utf-8 -*-
# DraveComic / DraveWriter - Copyright (C) 2026 Dravenlock (Roger & Claudio). Vrije software onder de GNU GPL v3.0.
"""drukker.py - 'Klaar voor de drukker' (0.6.0).

Maakt twee drukklare PDF's voor een drukker of print-on-demand:
  1. het binnenwerk: alle bladzijden behalve de kaft, met afloop (bleed) en eventueel snijtekens;
  2. de kaft: achterkant + rug + voorkant op één vel, de rugdikte rekent hij uit het aantal bladzijden.
"""
from PyQt6.QtCore import QMarginsF, QPointF, QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QFont, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDoubleSpinBox, QGridLayout, QHBoxLayout,
                             QLabel, QPushButton, QVBoxLayout)

# ISO-maten met dezelfde verhouding als de bladzijde in DraveComic (1 : wortel 2)
FORMATEN = [("A4 (21 x 29,7 cm)", "A4 (21 x 29.7 cm)", 210.0, 297.0),
            ("B5 (17,6 x 25 cm)", "B5 (17.6 x 25 cm)", 176.0, 250.0),
            ("A5 (14,8 x 21 cm)", "A5 (14.8 x 21 cm)", 148.0, 210.0)]
DPI = 300
SLUG = 10.0          # mm rand buiten de afloop voor de snijtekens


def mm(x):
    return x * DPI / 25.4


def rug_mm(binnen_bladzijden, vel_dikte):
    """Rugdikte: elk vel papier heeft twee bladzijden."""
    return round((binnen_bladzijden + 1) // 2 * vel_dikte, 2)


def aangevuld(n):
    """Aantal bladzijden aangevuld tot een veelvoud van 4."""
    return n + (-n) % 4


def _writer(pad, breed_mm, hoog_mm, titel, maker):
    pdf = QPdfWriter(pad)
    pdf.setTitle(titel)
    pdf.setCreator(maker)
    pdf.setResolution(DPI)
    pdf.setPageLayout(QPageLayout(QPageSize(QSizeF(breed_mm, hoog_mm), QPageSize.Unit.Millimeter, "Dravenlock",
                                            QPageSize.SizeMatchPolicy.ExactMatch),
                                  QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)))
    return pdf


def _vul(p, teken, pg, doos, pb, ph):
    """Tekent bladzijde pg zo dat hij de hele 'doos' bedekt (midden gelijk, iets bijsnijden mag)."""
    p.save()
    p.setClipRect(doos)
    s = max(doos.width() / pb, doos.height() / ph)
    p.translate(doos.center().x() - pb * s / 2, doos.center().y() - ph * s / 2)
    if pg is not None:
        teken(p, pg, s)
    else:
        p.fillRect(QRectF(0, 0, pb * s, ph * s), QColor("#ffffff"))
    p.restore()


def _snijtekens(p, trim, afloop_px, slug_px):
    """Korte zwarte streepjes in de rand, precies in het verlengde van de snijlijn."""
    pen = QPen(QColor("#000000"), mm(0.15))
    p.setPen(pen)
    gat = afloop_px + mm(1.0)
    lengte = slug_px - mm(1.5)
    for x in (trim.left(), trim.right()):
        p.drawLine(QPointF(x, trim.top() - gat), QPointF(x, trim.top() - gat - lengte))
        p.drawLine(QPointF(x, trim.bottom() + gat), QPointF(x, trim.bottom() + gat + lengte))
    for y in (trim.top(), trim.bottom()):
        p.drawLine(QPointF(trim.left() - gat, y), QPointF(trim.left() - gat - lengte, y))
        p.drawLine(QPointF(trim.right() + gat, y), QPointF(trim.right() + gat + lengte, y))


def maak_binnenwerk(pad, paginas, teken, pb, ph, breed, hoog, afloop, tekens, aanvullen, titel, maker):
    rand = afloop + (SLUG if tekens else 0.0)
    pdf = _writer(pad, breed + 2 * rand, hoog + 2 * rand, titel, maker)
    p = QPainter(pdf)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    lijst = list(paginas)
    if aanvullen:
        lijst += [None] * ((-len(lijst)) % 4)
    trim = QRectF(mm(rand), mm(rand), mm(breed), mm(hoog))
    doos = trim.adjusted(-mm(afloop), -mm(afloop), mm(afloop), mm(afloop))
    for i, pg in enumerate(lijst):
        if i:
            pdf.newPage()
        _vul(p, teken, pg, doos, pb, ph)
        if tekens:
            _snijtekens(p, trim, mm(afloop), mm(SLUG))
    p.end()
    return len(lijst)


def maak_kaft(pad, voor, achter, teken, pb, ph, breed, hoog, afloop, rug, tekens, rugkleur, rugtekst, titel, maker):
    rand = afloop + (SLUG if tekens else 0.0)
    totaal_b = 2 * breed + rug
    pdf = _writer(pad, totaal_b + 2 * rand, hoog + 2 * rand, titel, maker)
    p = QPainter(pdf)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    a = mm(afloop)
    x0, y0 = mm(rand), mm(rand)
    links = QRectF(x0, y0, mm(breed), mm(hoog))                       # achterkant
    rugr = QRectF(x0 + mm(breed), y0, mm(rug), mm(hoog))
    rechts = QRectF(x0 + mm(breed + rug), y0, mm(breed), mm(hoog))    # voorkant
    _vul(p, teken, achter, links.adjusted(-a, -a, 0, a), pb, ph)
    _vul(p, teken, voor, rechts.adjusted(0, -a, a, a), pb, ph)
    p.fillRect(rugr.adjusted(0, -a, 0, a), QColor(rugkleur))
    if rugtekst and rug >= 5.0:
        p.save()
        p.translate(rugr.center())
        p.rotate(90)                                                  # van boven naar beneden te lezen
        f = QFont("Arial")
        f.setBold(True)
        f.setPixelSize(int(min(mm(rug) * 0.55, mm(8))))
        p.setFont(f)
        licht = QColor(rugkleur).lightness() < 128
        p.setPen(QColor("#ffffff" if licht else "#111111"))
        vlak = QRectF(-rugr.height() / 2 + mm(8), -rugr.width() / 2, rugr.height() - mm(16), rugr.width())
        p.drawText(vlak, int(Qt.AlignmentFlag.AlignCenter), rugtekst)
        p.restore()
    if tekens:
        trim = QRectF(x0, y0, mm(totaal_b), mm(hoog))
        _snijtekens(p, trim, a, mm(SLUG))
        # vouwlijnen van de rug: streepjes boven en onder
        p.setPen(QPen(QColor("#000000"), mm(0.15), Qt.PenStyle.DashLine))
        for x in (rugr.left(), rugr.right()):
            p.drawLine(QPointF(x, y0 - a - mm(1)), QPointF(x, y0 - a - mm(SLUG - 0.5)))
            p.drawLine(QPointF(x, y0 + mm(hoog) + a + mm(1)), QPointF(x, y0 + mm(hoog) + a + mm(SLUG - 0.5)))
    p.end()
    return round(totaal_b + 2 * afloop, 1), round(hoog + 2 * afloop, 1)


class DrukDialoog(QDialog):
    """Instellingen voor 'Klaar voor de drukker'."""

    def __init__(self, ouder, nl, n_binnen, heeft_voor, heeft_achter, titel, instel):
        super().__init__(ouder)
        self.nl = nl
        self.n = n_binnen
        L = lambda a, b: a if nl else b
        self.setWindowTitle(L("Klaar voor de drukker", "Ready for the printer"))
        self.resize(720, 640)
        v = QVBoxLayout(self)
        k = QLabel(L("🖨  Klaar voor de drukker", "🖨  Ready for the printer"))
        k.setObjectName("kop")
        v.addWidget(k)
        uitleg = QLabel(L("Je krijgt twee PDF's: het <b>binnenwerk</b> (alle bladzijden) en de <b>kaft</b> "
                          "(achterkant + rug + voorkant). Elke drukker heeft eigen eisen: kijk even naar hun "
                          "<i>aanleverspecificaties</i> en zet de getallen hieronder goed.",
                          "You get two PDFs: the <b>inside</b> (all pages) and the <b>cover</b> (back + spine + front). "
                          "Every printer has its own rules: check their <i>file specifications</i> and set the numbers below."))
        uitleg.setWordWrap(True)
        uitleg.setObjectName("sub")
        v.addWidget(uitleg)
        g = QGridLayout()
        r = 0
        g.addWidget(QLabel(L("Formaat van het boek", "Book size")), r, 0)
        self.formaat = QComboBox()
        for nlnaam, ennaam, _, _ in FORMATEN:
            self.formaat.addItem(nlnaam if nl else ennaam)
        self.formaat.setCurrentIndex(int(instel.get("druk_formaat", 0)))
        g.addWidget(self.formaat, r, 1)
        r += 1
        g.addWidget(QLabel(L("Afloop (mm)", "Bleed (mm)")), r, 0)
        self.afloop = QDoubleSpinBox()
        self.afloop.setRange(0, 10)
        self.afloop.setSingleStep(0.5)
        self.afloop.setValue(float(instel.get("druk_afloop", 3.0)))
        g.addWidget(self.afloop, r, 1)
        r += 1
        g.addWidget(QLabel(L("Dikte van één vel papier (mm)", "Thickness of one sheet (mm)")), r, 0)
        self.vel = QDoubleSpinBox()
        self.vel.setDecimals(3)
        self.vel.setRange(0.03, 0.5)
        self.vel.setSingleStep(0.005)
        self.vel.setValue(float(instel.get("druk_vel", 0.10)))
        self.vel.setToolTip(L("Gewoon papier van 80-90 gram is ongeveer 0,1 mm. Je drukker weet het precies.",
                              "Normal 80-90 gsm paper is about 0.1 mm. Your printer knows exactly."))
        g.addWidget(self.vel, r, 1)
        v.addLayout(g)
        self.aanvul = QCheckBox(L("Aanvullen met lege bladzijden tot een veelvoud van 4", "Pad with blank pages to a multiple of 4"))
        self.aanvul.setChecked(bool(instel.get("druk_aanvul", True)))
        v.addWidget(self.aanvul)
        self.tekens = QCheckBox(L("Snijtekens erbij (de meeste print-on-demand wil ze NIET)", "Add crop marks (most print-on-demand does NOT want them)"))
        self.tekens.setChecked(bool(instel.get("druk_tekens", False)))
        v.addWidget(self.tekens)
        self.rugtekst_aan = QCheckBox(L("Titel op de rug (als de rug minstens 5 mm is)", "Title on the spine (if the spine is at least 5 mm)"))
        self.rugtekst_aan.setChecked(bool(instel.get("druk_rugtekst", True)))
        v.addWidget(self.rugtekst_aan)
        self.titel = titel
        rk = QHBoxLayout()
        self.rugkleur = instel.get("druk_rugkleur", "#16131f")
        self.k_rug = QPushButton(L("Kleur van de rug…", "Spine colour…"))
        self.k_rug.clicked.connect(self._kies_rug)
        rk.addWidget(self.k_rug)
        rk.addStretch(1)
        v.addLayout(rk)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.info.setStyleSheet("background: #221c33; border: 2px solid #4a3d66; border-radius: 10px; padding: 10px;")
        v.addWidget(self.info)
        if not heeft_voor:
            w = QLabel(L("⚠  Er is nog geen <b>voorkant</b>. Maak er eerst een met '📕 Voorkant' (anders blijft die kant wit).",
                         "⚠  There is no <b>front cover</b> yet. Make one with '📕 Front cover' first (otherwise it stays white)."))
            w.setWordWrap(True)
            v.addWidget(w)
        if not heeft_achter:
            w = QLabel(L("Er is geen achterkant: die kant blijft wit.", "There is no back cover: that side stays white."))
            w.setObjectName("sub")
            v.addWidget(w)
        v.addStretch(1)
        kn = QHBoxLayout()
        kn.addStretch(1)
        ok = QPushButton(L("🖨  Maak de PDF's", "🖨  Make the PDFs"))
        ok.setObjectName("paars")
        ok.clicked.connect(self.accept)
        weg = QPushButton(L("Annuleren", "Cancel"))
        weg.clicked.connect(self.reject)
        kn.addWidget(weg)
        kn.addWidget(ok)
        v.addLayout(kn)
        for x in (self.formaat.currentIndexChanged, self.afloop.valueChanged, self.vel.valueChanged, self.aanvul.toggled):
            x.connect(self._info)
        self._kleur_knop()
        self._info()

    def _kies_rug(self):
        k = QColorDialog.getColor(QColor(self.rugkleur), self, "Rug" if self.nl else "Spine")
        if k.isValid():
            self.rugkleur = k.name()
            self._kleur_knop()

    def _kleur_knop(self):
        self.k_rug.setStyleSheet("border-bottom: 8px solid %s;" % self.rugkleur)

    def waarden(self):
        _, _, b, h = FORMATEN[self.formaat.currentIndex()]
        n = aangevuld(self.n) if self.aanvul.isChecked() else self.n
        return dict(breed=b, hoog=h, afloop=self.afloop.value(), vel=self.vel.value(), aanvul=self.aanvul.isChecked(),
                    tekens=self.tekens.isChecked(), rug=rug_mm(n, self.vel.value()), n=n, rugkleur=self.rugkleur,
                    rugtekst=self.titel if self.rugtekst_aan.isChecked() else "", formaat=self.formaat.currentIndex())

    def _info(self):
        w = self.waarden()
        nl = self.nl
        extra = w["n"] - self.n
        t = ("<b>Binnenwerk:</b> %d bladzijden%s<br><b>Rug:</b> %.1f mm<br><b>Kaft (met afloop):</b> %.1f x %.1f mm"
             if nl else "<b>Inside:</b> %d pages%s<br><b>Spine:</b> %.1f mm<br><b>Cover (with bleed):</b> %.1f x %.1f mm")
        plus = ((" (waarvan %d lege)" if nl else " (%d blank)") % extra) if extra else ""
        self.info.setText(t % (w["n"], plus, w["rug"], 2 * w["breed"] + w["rug"] + 2 * w["afloop"], w["hoog"] + 2 * w["afloop"]))
