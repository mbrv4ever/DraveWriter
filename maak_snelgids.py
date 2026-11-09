# Maakt DraveWriter-Snelgids.pdf (grote letters). Copyright (C) 2026 Dravenlock (Roger & Claudio). GPL-3.0.
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import os
for n, f in (("D", "DejaVuSans.ttf"), ("DB", "DejaVuSans-Bold.ttf")):
    for m in ("/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/"):
        if os.path.exists(m + f):
            pdfmetrics.registerFont(TTFont(n, m + f)); break
P = HexColor("#3b2f6b")
t = ParagraphStyle("t", fontName="DB", fontSize=28, leading=34, textColor=P)
h = ParagraphStyle("h", fontName="DB", fontSize=19, leading=24, textColor=P, spaceBefore=14, spaceAfter=6, keepWithNext=1)
b = ParagraphStyle("b", fontName="D", fontSize=14, leading=21, spaceAfter=6)
li = ParagraphStyle("li", parent=b, leftIndent=18, bulletIndent=4)
E_ = []
H = lambda x: E_.append(Paragraph(x, h))
B = lambda x: E_.append(Paragraph(x, b))
L = lambda xs: [E_.append(Paragraph(x, li, bulletText="•")) for x in xs]
E_.append(Image("assets/icon.png", 3 * cm, 3 * cm, hAlign="LEFT"))
E_.append(Paragraph("DraveWriter — snelgids", t))
B("Maak je eigen receptenboek of een gewoon boek. Gratis (donationware) · GNU GPL v3.0 · Dravenlock (Roger &amp; Claudio)")
H("1. Beginnen")
L(["Klik op <b>📄 Nieuw</b> en kies <b>Een receptenboek</b> of <b>Een gewoon boek</b> (verhaal, roman, herinneringen). Een gewoon boek staat in hoofdstuk 8.",
   "Links staan je <b>recepten</b>. <b>+ Recept</b> zet er een bij, <b>− Weg</b> haalt het gekozen recept weg, <b>▲ ▼</b> verandert de volgorde in het boek.",
   "In het midden vul je het recept in. Rechts zie je meteen hoe de bladzijde in het boek eruitziet."])
H("2. Het recept")
L(["<b>Naam</b>, <b>soort gerecht</b> (ontbijt, soep, hoofdgerecht, nagerecht, gebak…), <b>voor hoeveel personen</b> en de <b>tijden</b>.",
   "<b>Korte zin erboven</b>: bijvoorbeeld 'Hartig en klaar in een half uur'. Mag leeg blijven.",
   "<b>📷 Foto kiezen…</b> zet een foto boven het recept. De eerste foto wordt ook de foto op de voorkant (dat kun je veranderen).",
   "<b>Bereiding</b>: schrijf <b>één stap per regel</b>. Druk op Enter voor de volgende stap. In het boek krijgen de stappen vanzelf een nummer.",
   "<b>Tip of eigen verhaal</b>: komt in een geel vakje onderaan."])
H("3. Ingrediënten")
L(["<b>+ Ingrediënt</b> zet een nieuwe regel erbij. Vul in: <b>Hoeveel</b> (bijv. 250, 1,5 of ½), de <b>eenheid</b> (g, ml, el, tl, stuk, teen, snufje, naar smaak…) en <b>wat</b> het is.",
   "Achter elk ingrediënt staat een knop: <b>waar de voedingswaarde uit komt</b>. DraveWriter kiest zelf de beste gok uit de NEVO-tabel (✓).",
   "Klopt de gok niet? Klik op de knop en kies zelf. Je kunt zoeken, bijvoorbeeld 'kaas goudse jong'.",
   "Bij <b>stuks</b> vraagt DraveWriter hoeveel gram één stuk is (een ei is ongeveer 55 gram). Je kunt ook het totaal in gram invullen.",
   "Staat het er niet in? Vul dan zelf de waarden per 100 gram in, die staan op de verpakking. Die komen als <b>eigen waarden</b> in het boek.",
   "Een ⚠ betekent: dit ingrediënt telt nog niet mee. Klik op de knop en kies wat het is."])
H("4. Voedingswaarden")
L(["DraveWriter rekent zelf uit hoeveel <b>energie, eiwit, vet, koolhydraten, suikers, vezels en zout</b> er in één portie zit.",
   "Weet je het beter? Vul rechts je <b>eigen waarde</b> in. In het boek staat er dan een sterretje (*) achter.",
   "De waarden komen uit de <b>NEVO-tabel van het RIVM</b> (NEVO-online versie 2025/9.0). Die staat in de map <b>NEVO</b> naast de app en werkt zonder internet. De tabel zelf wordt nooit veranderd.",
   "Het zijn <b>schattingen</b>: hoe je kookt, bakt en afweegt maakt verschil."])
H("5. Meer of minder personen")
L(["Rechts boven het voorbeeld staat <b>Bekijk voor … personen</b>. De hoeveelheden rekenen mee en worden <b>netjes afgerond</b>: 1 ei, niet 1,3 ei; 220 g, niet 223 g.",
   "<b>Alleen dit recept als PDF</b> maakt een PDF voor dat aantal personen. Handig om in de keuken te gebruiken.",
   "Wil je het recept zelf omzetten? Klik op <b>📐 Zet het recept om naar dit aantal</b>."])
H("6. Boek en kaft")
L(["<b>📘 Boek en kaft</b>: de titel, een ondertitel, 'gemaakt door', de foto en de kleur van de kaft, en een tekst voor de achterkant.",
   "De <b>inhoudsopgave</b> en de <b>bladzijdenummers</b> komen vanzelf. Je kunt de inhoud per soort gerecht laten indelen.",
   "Past een recept niet op één bladzijde, dan gaat het vanzelf verder op de volgende ('vervolg')."])
H("7. Delen en drukken")
L(["<b>📕 PDF</b> zet het hele boek in één PDF op A4: om te printen, te mailen of te delen.",
   "<b>🖨 Drukker</b> maakt twee PDF's voor een drukker of print-on-demand: het <b>binnenwerk</b> en de <b>kaft</b> (achterkant + rug + voorkant). De rug rekent DraveWriter zelf uit.",
   "Kies het formaat (A4, B5 of A5) en lees even de <i>aanleverspecificaties</i> van je drukker (afloop, snijtekens, veelvoud van 4)."])
H("8. Een gewoon boek")
L(["Links staan je <b>hoofdstukken</b>. <b>+ Hoofdstuk</b> zet er een bij, <b>▲ ▼</b> verandert de volgorde.",
   "Geef het hoofdstuk een <b>titel</b> en typ gewoon door. <b>Enter</b> begint een nieuwe alinea. De bladzijden, de inhoudsopgave en de bladzijdenummers maakt DraveWriter zelf.",
   "Onder de tekst zie je hoeveel <b>woorden</b> en <b>alinea's</b> het hoofdstuk heeft.",
   "<b>📷 Plaatje erbij…</b> zet een foto of tekening in het hoofdstuk, na de alinea waar je cursor staat. Bij <b>Na alinea</b> kun je dat veranderen (0 = helemaal bovenaan). Een <b>onderschrift</b> mag erbij.",
   "Past een plaatje niet meer op de bladzijde, dan gaat de tekst gewoon door en komt het plaatje bovenaan de volgende bladzijde.",
   "De tekst staat netjes uitgevuld, zonder losse regels boven- of onderaan een bladzijde."])
H("9. Ongedaan maken")
L(["<b>↶ Ongedaan</b> (Ctrl + Z) zet de laatste verandering terug. <b>↷ Opnieuw</b> (Ctrl + Y) doet hem weer. Dat kan tot 100 stappen terug."])
H("10. Opslaan")
L(["<b>💾 Opslaan</b> bewaart het hele boek in één bestand (.drecept), met de foto's erin. Standaard in de map DraveWriter-data\\Mijn boeken naast de app.",
   "<b>📂 Openen</b> opent een boek weer. <b>A− / A+</b> maakt de letters in de app kleiner of groter."])
H("11. Toetsen")
tb = Table([["Ctrl + Z", "Ongedaan maken"], ["Ctrl + Y", "Opnieuw"], ["Ctrl + S", "Opslaan"], ["Ctrl + O", "Openen"], ["Enter (bij Bereiding)", "Volgende stap"], ["Enter (bij Tekst)", "Nieuwe alinea"], ["A− / A+", "Tekst in de app kleiner / groter"]],
           colWidths=[5 * cm, 10.5 * cm])
tb.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "D", 14), ("FONT", (0, 0), (0, -1), "DB", 14),
                        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#b9b2d6")), ("BACKGROUND", (0, 0), (0, -1), HexColor("#efeafd")),
                        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
E_.append(tb)
E_.append(Spacer(1, 12))
B("Voedingswaarden: gebaseerd op gegevens van NEVO-online versie 2025/9.0, RIVM, Bilthoven. Eigen waarden zijn gemarkeerd met *.")
B("Vragen of ideeën? service@dravenlock.nl · dravenlock.nl")
SimpleDocTemplate("DraveWriter-Snelgids.pdf", pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                  bottomMargin=1.8 * cm, title="DraveWriter snelgids", author="Dravenlock (Roger & Claudio)").build(E_)
print("snelgids klaar")
