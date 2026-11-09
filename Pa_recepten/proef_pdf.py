# -*- coding: utf-8 -*-
# Proef-PDF van "Pa's Hollandse pot" zonder venster (zelfde tekencode als DraveWriter).
import json, os, sys, zipfile
HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HIER))
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QPageLayout, QPageSize, QPainter, QPdfWriter
from PyQt6.QtCore import QMarginsF
app = QApplication(sys.argv)
import nevo
import pagina as pg

bron = os.path.join(HIER, "Hollandse pot.drecept")
boek = json.loads(zipfile.ZipFile(bron).read("boek.json").decode("utf-8"))
t = nevo.Tabel()
t.laad_map(os.path.join(os.path.dirname(HIER), "NEVO"))
fotos = pg.Fotos()
paginas = pg.bladzijden(boek, t, True)
uit = os.path.join(HIER, "Hollandse pot - proef.pdf")
w = QPdfWriter(uit)
w.setTitle(boek["titel"])
w.setCreator("DraveWriter - Dravenlock")
w.setResolution(200)
w.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait, QMarginsF(0, 0, 0, 0)))
p = QPainter(w)
s = w.width() / pg.PB
for i, pagina in enumerate(paginas):
    if i:
        w.newPage()
    pg.teken(p, pagina, s, boek, fotos, True)
p.end()
print("PAGINAS", len(paginas), [x["soort"] for x in paginas])
print("KLAAR", uit)
