import os
import math
import pay_by_square
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode

# --- NASTAVENIA ---
# TODO: Upravte si zoznam firiem a ich IBAN účty podľa potreby
PREDEFINOVANE_FIRMY = {
    "1": {"nazov": "***REMOVED***", "iban": "***REMOVED***"},
    "2": {"nazov": "***REMOVED***", "iban": "***REMOVED***"},
    "3": {"nazov": "***REMOVED***", "iban": "***REMOVED***"},
}
MAX_SUMA_NA_QR = 1000.00

# --- FUNKCIE ---

def vygeneruj_qr_kod(payload, subor_qr):
    """Vygeneruje a uloží obrázok QR kódu."""
    img = qrcode.make(payload)
    img.save(subor_qr)
    return subor_qr

def vytvor_pdf_dokument(zakladne_info, zoznam_platieb):
    """
    Vytvorí PDF súbor s novým horizontálnym rozložením podľa predlohy.
    """
    vystupny_subor = f"QR_Platba_VS_{zakladne_info['vs']}.pdf"
    c = canvas.Canvas(vystupny_subor, pagesize=A4)
    sirka, vyska = A4

    # === NOVÉ NASTAVENIA PRE ROZLOŽENIE ===
    vyska_bloku_platby = 55 * mm
    horny_okraj = 20 * mm
    lavy_okraj = 15 * mm
    pravy_okraj = 15 * mm
    pozicia_y = vyska - horny_okraj

    for platba in zoznam_platieb:
        # Ak sa blok nezmestí na aktuálnu stranu, vytvor novú
        if pozicia_y < vyska_bloku_platby:
            c.showPage()
            pozicia_y = vyska - horny_okraj

        # Súradnica vrchu aktuálneho bloku
        vrch_bloku_y = pozicia_y

        # 1. Kreslenie QR kódu (vľavo)
        velkost_qr = 40 * mm
        qr_obr = ImageReader(platba['subor_qr'])
        c.drawImage(qr_obr, lavy_okraj, vrch_bloku_y - velkost_qr - (5*mm), width=velkost_qr, height=velkost_qr)

        # 2. Kreslenie textových informácií (v strede)
        c.setFont("Helvetica", 10)
        text_x = lavy_okraj + velkost_qr + (10 * mm)
        text_y = vrch_bloku_y - (8 * mm)
        
        suma_text = f"{platba['suma']:.2f} EUR"
        texty = [
            f"Dodávateľ: {zakladne_info['prijemca']}",
            f"IBAN: {zakladne_info['iban']}",
            f"VS: {zakladne_info['vs']}",
            f"KS: {zakladne_info['ks'] if zakladne_info['ks'] else '-'}",
            f"Suma: {suma_text}"
        ]
        for text in texty:
            c.drawString(text_x, text_y, text)
            text_y -= 5 * mm

        # 3. Kreslenie poradového čísla (vpravo)
        c.setFont("Helvetica-Bold", 24)
        poradove_cislo_text = f"{platba['poradie']}/{platba['celkovy_pocet']}"
        # Vertikálne centrovanie poradového čísla v bloku
        poradove_cislo_y = vrch_bloku_y - (vyska_bloku_platby / 2)
        c.drawRightString(sirka - pravy_okraj, poradove_cislo_y, poradove_cislo_text)

        # 4. Kreslenie bodkovanej čiary na odstrihnutie
        pozicia_ciary_y = vrch_bloku_y - vyska_bloku_platby + (5 * mm)
        c.setDash(3, 3) # Nastavenie štýlu čiary na bodkovanú
        c.line(lavy_okraj, pozicia_ciary_y, sirka - pravy_okraj, pozicia_ciary_y)
        c.setDash([], 0) # Vrátenie štýlu čiary na plnú

        # Posun na pozíciu pre ďalší platobný blok
        pozicia_y -= vyska_bloku_platby

    c.save()
    print("\n----------------------------------------------------")
    print(f"✅ PDF súbor '{vystupny_subor}' bol úspešne vygenerovaný!")
    print(f"   Súbor: {os.path.abspath(vystupny_subor)}")
    print("----------------------------------------------------")


def ziskaj_vstup_od_uzivatela():
    """Získa všetky potrebné údaje od používateľa."""
    print("Prosím, vyberte firmu, ktorej chcete zaplatiť:")
    for key, value in PREDEFINOVANE_FIRMY.items():
        print(f"  [{key}]: {value['nazov']} ({value['iban']})")
    
    while True:
        vyber = input(f"Zadajte číslo (1-{len(PREDEFINOVANE_FIRMY)}): ")
        if vyber in PREDEFINOVANE_FIRMY:
            firma = PREDEFINOVANE_FIRMY[vyber]
            break
        else:
            print("❌ Neplatný výber, skúste to znova.")

    while True:
        try:
            suma_str = input("Zadajte CELKOVÚ sumu na úhradu (napr. 5562.00): ").replace(',', '.')
            suma = float(suma_str)
            if suma <= 0:
                raise ValueError("Suma musí byť kladné číslo.")
            break
        except ValueError as e:
            print(f"❌ Neplatná suma. {e}")

    vs = input("Zadajte variabilný symbol (max 10 číslic): ")
    ks = input("Zadajte konštantný symbol (nepovinné, max 4 číslice): ")
    povodna_poznamka = input("Zadajte poznámku pre príjemcu (nepovinné): ")
    
    return {
        "prijemca": firma['nazov'],
        "iban": firma['iban'].strip(),
        "celkova_suma": suma,
        "vs": vs,
        "ks": ks,
        "povodna_poznamka": povodna_poznamka
    }

# --- HLAVNÁ ČASŤ PROGRAMU ---
if __name__ == "__main__":
    print("--- Generátor Pay BY Square QR kódu do PDF (s delením platby) ---")
    
    info_platby = ziskaj_vstup_od_uzivatela()
    celkova_suma = info_platby["celkova_suma"]

    ciastocne_sumy = []
    if celkova_suma > MAX_SUMA_NA_QR:
        pocet_plnych_platieb = int(celkova_suma / MAX_SUMA_NA_QR)
        zostatok = round(celkova_suma % MAX_SUMA_NA_QR, 2)
        
        for _ in range(pocet_plnych_platieb):
            ciastocne_sumy.append(MAX_SUMA_NA_QR)
        
        if zostatok > 0:
            ciastocne_sumy.append(zostatok)
        
        print(f"\nINFO: Celková suma {celkova_suma:.2f} EUR bude rozdelená na {len(ciastocne_sumy)} platieb.")
    else:
        ciastocne_sumy.append(celkova_suma)

    zoznam_vygenerovanych_platieb = []
    celkovy_pocet_platieb = len(ciastocne_sumy)

    for i, suma in enumerate(ciastocne_sumy):
        poradie = i + 1
        
        poznamka = info_platby['povodna_poznamka']
        if celkovy_pocet_platieb > 1:
            dodatok_poznamky = f"(Platba {poradie}/{celkovy_pocet_platieb})"
            poznamka = f"{dodatok_poznamky} {poznamka}".strip()

        payload = pay_by_square.generate(
            iban=info_platby['iban'],
            amount=suma,
            variable_symbol=info_platby['vs'],
            constant_symbol=info_platby['ks'],
            note=poznamka,
            beneficiary_name=info_platby['prijemca']
        )
        
        subor_qr = f"temp_qr_{poradie}.png"
        vygeneruj_qr_kod(payload, subor_qr)
        
        zoznam_vygenerovanych_platieb.append({
            'suma': suma,
            'subor_qr': subor_qr,
            'poradie': poradie,
            'celkovy_pocet': celkovy_pocet_platieb
        })

    if zoznam_vygenerovanych_platieb:
        vytvor_pdf_dokument(info_platby, zoznam_vygenerovanych_platieb)

        for platba in zoznam_vygenerovanych_platieb:
            os.remove(platba['subor_qr'])