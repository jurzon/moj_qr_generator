import os
import math
import pay_by_square
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
from dotenv import load_dotenv

load_dotenv()

# --- ANSI NASTAVENIA PRE SPRAVY ---
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_BOLD = "\033[1m"
ANSI_BLUE = "\033[94m"    # <-- DOPLNENÉ
ANSI_RED = "\033[91m"     # <-- DOPLNENÉ
ANSI_GREEN = "\033[92m"   # <-- DOPLNENÉ
ANSI_END = "\033[0m"

# --- NASTAVENIA ---
# Dáta sa teraz načítajú z .env súboru, nie sú v kóde
PREDEFINOVANE_FIRMY = {
    "1": {"nazov": os.getenv("FIRMA_1_NAZOV"), "iban": os.getenv("FIRMA_1_IBAN")},
    "2": {"nazov": os.getenv("FIRMA_2_NAZOV"), "iban": os.getenv("FIRMA_2_IBAN")},
    "3": {"nazov": os.getenv("FIRMA_3_NAZOV"), "iban": os.getenv("FIRMA_3_IBAN")},
}
# Vyčistíme firmy, ktoré sa nenačítali (ak by .env chýbal)
PREDEFINOVANE_FIRMY = {k: v for k, v in PREDEFINOVANE_FIRMY.items() if v['iban']}
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
        # Ak by si chcel použiť logo, musíš ho najprv prekonvertovať na vhodný formát (napr. PNG) a použiť ImageReader, zatiaľ bez loga.
        # qr_obr = ImageReader(platba['subor_qr']) 
        qr_obr = platba['subor_qr']
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
    print(f"\n{ANSI_BOLD}----------------------------------------------------{ANSI_END}")
    print(f"✅ {ANSI_GREEN}PDF súbor '{vystupny_subor}' bol úspešne vygenerovaný!{ANSI_END}")
    print(f"   Súbor: {os.path.abspath(vystupny_subor)}")
    print(f"{ANSI_BOLD}----------------------------------------------------{ANSI_END}")


def ziskaj_vstup_od_uzivatela():
    """Získa všetky potrebné údaje od používateľa."""
    print(f"\n{ANSI_BOLD}Prosím, vyberte firmu, ktorej chcete zaplatiť:{ANSI_END}")
    for key, value in PREDEFINOVANE_FIRMY.items():
        print(f"  [{ANSI_CYAN}{key}{ANSI_END}]: {value['nazov']} ({value['iban']})")
    
    while True:
        vyber = input(f"Zadajte číslo ({ANSI_CYAN}1-{len(PREDEFINOVANE_FIRMY)}{ANSI_END}): ")
        if vyber in PREDEFINOVANE_FIRMY:
            firma = PREDEFINOVANE_FIRMY[vyber]
            break
        else:
            print(f"❌ {ANSI_RED}Neplatný výber, skúste to znova.{ANSI_END}")

    while True:
        try:
            suma_str = input(f"Zadajte CELKOVÚ sumu na úhradu ({ANSI_YELLOW}napr. 5562.00{ANSI_END}): ").replace(',', '.')
            suma = float(suma_str)
            if suma <= 0:
                raise ValueError("Suma musí byť kladné číslo.")
            break
        except ValueError as e:
            print(f"❌ {ANSI_RED}Neplatná suma. {e}{ANSI_END}")

    vs = input(f"Zadajte {ANSI_YELLOW}variabilný symbol{ANSI_END} (max 10 číslic): ")
    ks = input(f"Zadajte {ANSI_YELLOW}konštantný symbol{ANSI_END} (nepovinné, max 4 číslice): ")
    povodna_poznamka = input(f"Zadajte {ANSI_YELLOW}poznámku pre príjemcu{ANSI_END} (nepovinné): ")
    
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
    
    # ANSI grafika pre spestrenie
    print(f"""
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END} {ANSI_BOLD}PAY BY SQUARE QR GENERATOR (SK){ANSI_END}
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END} --- Automatické delenie platieb nad {MAX_SUMA_NA_QR:.2f}€ ---
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END}
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END}
""")
    
    info_platby = ziskaj_vstup_od_uzivatela()
    celkova_suma = info_platby["celkova_suma"]

    ciastocne_sumy = []
    if celkova_suma > MAX_SUMA_NA_QR:
        pocet_plnych_platieb = int(celkova_suma / MAX_SUMA_NA_QR)
        # Použitie math.fmod pre presnejší zvyšok pre float
        zostatok = round(math.fmod(celkova_suma, MAX_SUMA_NA_QR), 2)
        
        for _ in range(pocet_plnych_platieb):
            ciastocne_sumy.append(MAX_SUMA_NA_QR)
        
        if zostatok > 0:
            ciastocne_sumy.append(zostatok)
        
        print(f"\n{ANSI_BLUE}INFO:{ANSI_END} Celková suma {ANSI_YELLOW}{celkova_suma:.2f} EUR{ANSI_END} bude rozdelená na {ANSI_YELLOW}{len(ciastocne_sumy)} platieb{ANSI_END}.")
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

        # Generovanie Pay By Square dátového reťazca
        payload = pay_by_square.generate(
            iban=info_platby['iban'],
            amount=suma,
            variable_symbol=info_platby['vs'],
            constant_symbol=info_platby['ks'],
            note=poznamka,
            beneficiary_name=info_platby['prijemca']
        )
        
        # Dočasné uloženie QR kódu ako súboru
        subor_qr = f"temp_qr_vs{info_platby['vs']}_{poradie}.png"
        vygeneruj_qr_kod(payload, subor_qr)
        
        zoznam_vygenerovanych_platieb.append({
            'suma': suma,
            # Poznámka: reportlab preferuje ImageReader, tak si ho pripravíme vopred
            'subor_qr': ImageReader(subor_qr),
            'poradie': poradie,
            'celkovy_pocet': celkovy_pocet_platieb,
            'docasny_subor': subor_qr # Uchováme pre neskoršie zmazanie
        })

    if zoznam_vygenerovanych_platieb:
        vytvor_pdf_dokument(info_platby, zoznam_vygenerovanych_platieb)

        # Vyčistenie dočasných QR kódov (PNG súbory)
        for platba in zoznam_vygenerovanych_platieb:
            try:
                os.remove(platba['docasny_subor'])
            except OSError as e:
                print(f"{ANSI_RED}Upozornenie: Nepodarilo sa zmazať dočasný súbor {platba['docasny_subor']}. {e}{ANSI_END}")