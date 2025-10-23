import os
import math
import json  # Potrebné pre prácu s config súborom
import sys   # Potrebné pre ukončenie programu a detekciu PyInstaller
import pay_by_square
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import colorama

# --- ANSI NASTAVENIA PRE SPRAVY ---
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_BOLD = "\033[1m"
ANSI_BLUE = "\033[94m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_END = "\033[0m"

# --- NASTAVENIA ---
MAX_SUMA_NA_QR = 1000.00
CONFIG_SUBOR = "config.json" # Súbor na uloženie cesty k partnerom
TEMP_DIR = "temp_qrs"        # Priečinok pre dočasné QR kódy

# --- FUNKCIE PRE PRÁCU S KONFIGURÁCIOU ---

def nacitaj_cestu_k_partnerom():
    """Načíta posledne uloženú cestu k súboru partnerov z config.json."""
    try:
        if os.path.exists(CONFIG_SUBOR):
            with open(CONFIG_SUBOR, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('cesta_partneri')
    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Chyba pri čítaní {CONFIG_SUBOR}: {e}{ANSI_END}")
    return None

def uloz_cestu_k_partnerom(cesta):
    """Uloží cestu k súboru partnerov do config.json."""
    try:
        with open(CONFIG_SUBOR, 'w', encoding='utf-8') as f:
            json.dump({'cesta_partneri': cesta}, f, indent=4)
    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Chyba pri ukladaní {CONFIG_SUBOR}: {e}{ANSI_END}")

# --- FUNKCIE PRE SPRACOVANIE PARTNEROV ---

def nacitaj_partnerov_zo_suboru(cesta_k_suboru):
    """
    Načíta partnerov (názov, IBAN) z textového súboru.
    Automaticky skúsi viacero kódovaní (utf-8, cp1250, atď.).
    Akceptuje rôzne SEPA IBAN formáty.
    """
    partneri = {}
    cislo_partnera = 1

    # Zoznam kódovaní, ktoré sa pokúsime použiť (cp1250 je bežné pre SK Windows)
    kodovania = ['utf-8', 'cp1250', 'iso-8859-2', 'utf-16']
    uspesne_kodovanie = None
    obsah_suboru = None

    for kodovanie in kodovania:
        try:
            with open(cesta_k_suboru, 'r', encoding=kodovanie) as f:
                obsah_suboru = f.readlines() # Načítame celý súbor
            uspesne_kodovanie = kodovanie
            print(f"ℹ️ {ANSI_BLUE}Súbor úspešne načítaný s kódovaním: {kodovanie}{ANSI_END}")
            break # Našli sme platné kódovanie, môžeme skončiť slučku
        except UnicodeDecodeError:
            # Toto kódovanie zlyhalo, skúsime ďalšie
            continue
        except FileNotFoundError:
            print(f"❌ {ANSI_RED}Chyba: Súbor '{cesta_k_suboru}' sa nenašiel.{ANSI_END}")
            return None
        except PermissionError:
            print(f"❌ {ANSI_RED}Chyba: Program nemá povolenie čítať súbor/priečinok.{ANSI_END}")
            print(f"   {ANSI_RED}Uistite sa, že zadávate cestu k SÚBORU (napr. partneri.txt), nie k priečinku.{ANSI_END}")
            return None
        except Exception as e:
            # Iná chyba
            print(f"❌ {ANSI_RED}Chyba pri otváraní súboru: {e}{ANSI_END}")
            return None

    if not obsah_suboru:
        print(f"❌ {ANSI_RED}Chyba: Súbor sa nepodarilo prečítať so žiadnym z podporovaných kódovaní ({', '.join(kodovania)}).{ANSI_END}")
        print(f"   {ANSI_RED}Skontrolujte, či súbor nie je poškodený alebo v inom kódovaní.{ANSI_END}")
        return None

    # Teraz spracujeme obsah_suboru, ktorý bol načítaný
    try:
        for riadok in obsah_suboru:
            riadok = riadok.strip()
            if not riadok:
                continue
            casti = riadok.split(';')
            if len(casti) >= 2:
                nazov = casti[0].strip()
                iban = casti[1].strip().replace(" ", "") # Odstránime aj medzery z IBANu

                # --- UPRAVENÁ KONTROLA ---
                # Základná kontrola - musí obsahovať aspoň niečo a dĺžka je v rozumnom rozsahu pre IBAN
                # Presnejšiu validáciu necháme na knižnicu pay_by_square
                if iban and 15 <= len(iban) <= 34 and iban[:2].isalpha(): # IBAN zvyčajne začína 2 písmenami kódu krajiny
                    preferovany_nazov = casti[3].strip() if len(casti) > 3 and casti[3].strip() else nazov
                    if preferovany_nazov and iban:
                        partneri[str(cislo_partnera)] = {"nazov": preferovany_nazov, "iban": iban}
                        cislo_partnera += 1
                else:
                    print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok '{riadok[:30]}...' neobsahuje platný IBAN formát (po odstránení medzier), preskakuje sa.{ANSI_END}")
                 # --- KONIEC UPRAVENEJ KONTROLY ---
            else:
                print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok '{riadok[:30]}...' nemá očakávaný formát (chýba ';'), preskakuje sa.{ANSI_END}")

    except Exception as e:
        print(f"❌ {ANSI_RED}Chyba pri spracovaní obsahu súboru (kódovanie {uspesne_kodovanie}): {e}{ANSI_END}")
        return None

    if not partneri:
        print(f"❌ {ANSI_RED}V súbore sa nenašli žiadni platní partneri.{ANSI_END}")
        return None

    return partneri

def pýtaj_a_nacitaj_partnerov_s_ulozenim():
    """
    Vyzve používateľa na zadanie cesty, načíta partnerov
    a úspešnú cestu uloží do configu.
    """
    print(f"\n{ANSI_BLUE}Tip: Cestu k súboru získate najľahšie tak, že súbor {ANSI_BOLD}pretiahnete myšou{ANSI_END}{ANSI_BLUE} sem do okna.{ANSI_END}")
    print(f"{ANSI_BLUE}   (Alebo použite 'Kopírovať ako cestu' a vložte ju sem){ANSI_END}")

    while True:
        cesta = input(f"Zadajte cestu k súboru s SEPA partnermi (alebo '{ANSI_CYAN}q{ANSI_END}' pre ukončenie): ").strip()

        # Očistenie cesty, ak ju používateľ vložil v úvodzovkách (z "Kopírovať ako cestu")
        if cesta.startswith('"') and cesta.endswith('"'):
            cesta = cesta[1:-1]

        if cesta.lower() == 'q':
            return None, None

        partneri = nacitaj_partnerov_zo_suboru(cesta)
        if partneri:
            uloz_cestu_k_partnerom(cesta)
            print(f"✅ {ANSI_GREEN}Partneri úspešne načítaní a cesta uložená.{ANSI_END}")
            return cesta, partneri
        else:
            print(f"{ANSI_RED}Skúste zadať cestu znova.{ANSI_END}")

# --- FUNKCIE PRE GENEROVANIE PDF A QR ---

def vygeneruj_qr_kod(payload, subor_qr):
    """Vygeneruje a uloží obrázok QR kódu."""
    img = qrcode.make(payload)
    img.save(subor_qr)
    return subor_qr

def registruj_font(c):
    """
    Pokúsi sa zaregistrovať Arial font pre PDF.
    Rozlišuje medzi spustením ako skript a ako PyInstaller bundle.
    """
    font_path = None
    font_registered = False
    font_name = 'Arial'
    fallback_font = 'Helvetica' # Záložný font, ak sa Arial nenájde/nezaregistruje

    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Program beží ako PyInstaller bundle (.exe)
            # sys._MEIPASS ukazuje na dočasný priečinok, kam PyInstaller rozbalil súbory
            base_path = sys._MEIPASS
            # Cesta k fontu zodpovedá cieľu v --add-data "assets/arial.ttf;assets"
            font_path = os.path.join(base_path, 'assets', 'arial.ttf')
            # print(f"DEBUG (Frozen): Hľadám font v: {font_path}") # Pre ladenie
        else:
            # Program beží ako normálny Python skript (.py)
            # Cesta sa počíta relatívne k aktuálnemu súboru (__file__)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Ideme o úroveň vyššie (z src do rootu projektu) a potom do assets
            font_path = os.path.abspath(os.path.join(script_dir, '..', 'assets', 'arial.ttf'))
            # print(f"DEBUG (Script): Hľadám font v: {font_path}") # Pre ladenie

        if font_path and os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                c.setFont(font_name, 10)
                font_registered = True
                # print(f"INFO: Font '{font_path}' úspešne zaregistrovaný.") # Pre ladenie
            except Exception as e:
                print(f"⚠️ {ANSI_YELLOW}Chyba pri registrácii fontu '{font_path}': {e}. Použije sa {fallback_font}.{ANSI_END}")
        else:
            if font_path:
                 print(f"⚠️ {ANSI_YELLOW}Varovanie: Súbor fontu '{font_path}' sa nenašiel. Použije sa {fallback_font}.{ANSI_END}")
            else:
                 print(f"⚠️ {ANSI_YELLOW}Varovanie: Nepodarilo sa určiť cestu k fontu. Použije sa {fallback_font}.{ANSI_END}")

    except Exception as general_e:
        print(f"⚠️ {ANSI_YELLOW}Neočekávaná chyba pri hľadaní/registrácii fontu: {general_e}. Použije sa {fallback_font}.{ANSI_END}")

    # Ak registrácia zlyhala, nastavíme záložný font
    if not font_registered:
        c.setFont(fallback_font, 10)

    return font_registered # Vráti True, ak sa podarilo použiť Arial, inak False


def vytvor_pdf_dokument(zakladne_info, zoznam_platieb):
    """
    Vytvorí PDF súbor s novým horizontálnym rozložením podľa predlohy.
    """
    vystupny_subor = f"QR_Platba_VS_{zakladne_info['vs']}.pdf"
    c = canvas.Canvas(vystupny_subor, pagesize=A4)
    sirka, vyska = A4

    vyska_bloku_platby = 55 * mm
    horny_okraj = 20 * mm
    lavy_okraj = 15 * mm
    pravy_okraj = 15 * mm
    pozicia_y = vyska - horny_okraj

    for platba in zoznam_platieb:
        # Ak sa blok nezmestí na aktuálnu stranu, začneme novú
        if pozicia_y < vyska_bloku_platby + horny_okraj: # Pridáme malú rezervu
            c.showPage()
            pozicia_y = vyska - horny_okraj

        vrch_bloku_y = pozicia_y
        velkost_qr = 40 * mm
        qr_obr = ImageReader(platba['subor_qr']) # ImageReader načíta cestu k súboru
        # Pozícia QR kódu (ľavý okraj, y súradnica spodku QR)
        qr_y_spodok = vrch_bloku_y - velkost_qr - (5*mm)
        c.drawImage(qr_obr, lavy_okraj, qr_y_spodok, width=velkost_qr, height=velkost_qr)

        # --- Text vedľa QR ---
        # Registrácia a nastavenie fontu pre každý blok (aj pre novú stranu)
        ma_arial = registruj_font(c) # Zaregistruje a nastaví 10pt

        text_x = lavy_okraj + velkost_qr + (10 * mm)
        text_y = vrch_bloku_y - (8 * mm) # Začíname trochu nižšie od vrchu bloku
        suma_text = f"{platba['suma']:.2f} EUR"
        texty = [
            f"Dodávateľ: {zakladne_info['prijemca']}",
            f"IBAN: {zakladne_info['iban']}",
            f"VS: {zakladne_info['vs']}",
            f"KS: {zakladne_info['ks'] if zakladne_info['ks'] else '-'}",
            f"Suma: {suma_text}"
        ]
        # Nastavenie fontu pre bežný text
        if ma_arial:
            c.setFont("Arial", 10)
        else:
            c.setFont("Helvetica", 10)

        for text in texty:
            c.drawString(text_x, text_y, text)
            text_y -= 5 * mm # Posun pre ďalší riadok

        # --- Poradové číslo (veľké, vpravo) ---
        if ma_arial:
            c.setFont("Arial", 24) # Väčší font pre poradové číslo
        else:
            c.setFont("Helvetica-Bold", 24) # Záložný väčší font

        poradove_cislo_text = f"{platba['poradie']}/{platba['celkovy_pocet']}"
        # Y pozícia približne v strede výšky bloku
        poradove_cislo_y = vrch_bloku_y - (vyska_bloku_platby / 2) + (5*mm) # Mierne vyššie
        c.drawRightString(sirka - pravy_okraj, poradove_cislo_y, poradove_cislo_text)

        # --- Čiarkovaná čiara pod blokom ---
        pozicia_ciary_y = vrch_bloku_y - vyska_bloku_platby + (5 * mm)
        c.setDash(3, 3) # Nastavenie prerušovanej čiary
        c.line(lavy_okraj, pozicia_ciary_y, sirka - pravy_okraj, pozicia_ciary_y)
        c.setDash([], 0) # Vrátenie na plnú čiaru pre prípadné ďalšie kreslenie

        # Posun pre ďalší blok
        pozicia_y -= vyska_bloku_platby

    c.save()
    print(f"\n{ANSI_BOLD}----------------------------------------------------{ANSI_END}")
    print(f"✅ {ANSI_GREEN}PDF súbor '{vystupny_subor}' bol úspešne vygenerovaný!{ANSI_END}")
    # Skúsime získať absolútnu cestu pre lepšiu informáciu
    try:
        abs_path = os.path.abspath(vystupny_subor)
        print(f"   Súbor: {abs_path}")
    except Exception:
        print(f"   Súbor: {vystupny_subor}") # Záložná možnosť
    print(f"{ANSI_BOLD}----------------------------------------------------{ANSI_END}")


def vycisti_temp_priecinok():
    """Odstráni dočasné QR kódy a priečinok."""
    try:
        if os.path.exists(TEMP_DIR):
            for subor in os.listdir(TEMP_DIR):
                try:
                    os.remove(os.path.join(TEMP_DIR, subor))
                except Exception as e_file:
                     print(f"⚠️ {ANSI_YELLOW}Nepodarilo sa odstrániť dočasný súbor {subor}: {e_file}{ANSI_END}")
            try:
                os.rmdir(TEMP_DIR)
            except Exception as e_dir:
                 print(f"⚠️ {ANSI_YELLOW}Nepodarilo sa odstrániť dočasný priečinok {TEMP_DIR}: {e_dir}{ANSI_END}")
    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Nepodarilo sa vyčistiť dočasný priečinok: {e}{ANSI_END}")

# --- HLAVNÉ FUNKCIE LOGIKY PROGRAMU ---

def ziskaj_detaily_platby(partner_info):
    """Získa od používateľa sumu, VS, KS, poznámku."""
    print(f"\n{ANSI_BOLD}--- Zadanie platby pre: {partner_info['nazov']} ({partner_info['iban']}) ---{ANSI_END}")
    print(f"(Pre zrušenie zadávania a návrat do menu zadajte '{ANSI_CYAN}q{ANSI_END}' kedykoľvek)")

    while True:
        try:
            suma_str = input(f"Zadajte CELKOVÚ sumu ({ANSI_YELLOW}napr. 5562.00{ANSI_END}): ").replace(',', '.')
            if suma_str.lower() == 'q': return None
            suma = float(suma_str)
            if suma <= 0:
                raise ValueError("Suma musí byť kladné číslo.")
            break
        except ValueError as e:
            print(f"❌ {ANSI_RED}Neplatná suma. Zadajte číslo (napr. 1234.50). {e}{ANSI_END}")

    while True:
        vs = input(f"Zadajte {ANSI_YELLOW}variabilný symbol{ANSI_END} (max 10 číslic): ")
        if vs.lower() == 'q': return None
        if vs.isdigit() and len(vs) <= 10:
            break
        print(f"❌ {ANSI_RED}Neplatný VS. Musí obsahovať iba číslice (max 10).{ANSI_END}")

    while True:
        ks = input(f"Zadajte {ANSI_YELLOW}konštantný symbol{ANSI_END} (nepovinné, max 4 číslice): ")
        if ks.lower() == 'q': return None
        if not ks or (ks.isdigit() and len(ks) <= 4):
            break
        print(f"❌ {ANSI_RED}Neplatný KS. Musí obsahovať iba číslice (max 4).{ANSI_END}")

    povodna_poznamka = input(f"Zadajte {ANSI_YELLOW}poznámku pre príjemcu{ANSI_END} (nepovinné): ")
    if povodna_poznamka.lower() == 'q': return None

    return {
        "prijemca": partner_info['nazov'],
        "iban": partner_info['iban'].strip(),
        "celkova_suma": suma,
        "vs": vs,
        "ks": ks,
        "povodna_poznamka": povodna_poznamka
    }

def spracuj_platbu(info_platby):
    """Rozdelí platbu, vygeneruje QR kódy a vytvorí PDF."""
    celkova_suma = info_platby["celkova_suma"]
    ciastocne_sumy = []

    if celkova_suma > MAX_SUMA_NA_QR:
        pocet_plnych_platieb = math.floor(celkova_suma / MAX_SUMA_NA_QR) # Použijeme floor pre istotu
        zostatok = round(celkova_suma - (pocet_plnych_platieb * MAX_SUMA_NA_QR), 2) # Presnejší výpočet zostatku

        # Kontrola zaokrúhlenia - ak je zostatok veľmi blízko nule, považujeme ho za nulu
        if abs(zostatok) < 0.001:
            zostatok = 0.0

        for _ in range(pocet_plnych_platieb):
            ciastocne_sumy.append(MAX_SUMA_NA_QR)
        if zostatok > 0:
            ciastocne_sumy.append(zostatok)
        print(f"\n{ANSI_BLUE}INFO:{ANSI_END} Celková suma {ANSI_YELLOW}{celkova_suma:.2f} EUR{ANSI_END} bude rozdelená na {ANSI_YELLOW}{len(ciastocne_sumy)} platieb{ANSI_END}.")
    else:
        ciastocne_sumy.append(celkova_suma)

    zoznam_vygenerovaných_platieb = []
    celkovy_pocet_platieb = len(ciastocne_sumy)

    # Vytvoríme TEMP_DIR až keď ho naozaj potrebujeme
    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
    except Exception as e:
         print(f"❌ {ANSI_RED}Nepodarilo sa vytvoriť dočasný priečinok '{TEMP_DIR}': {e}{ANSI_END}")
         return # Nemôžeme pokračovať bez dočasného priečinka

    try:
        for i, suma in enumerate(ciastocne_sumy):
            poradie = i + 1
            poznamka = info_platby['povodna_poznamka']
            if celkovy_pocet_platieb > 1:
                dodatok_poznamky = f"(Platba {poradie}/{celkovy_pocet_platieb})"
                # Pridáme dodatok na začiatok, aby bol vždy viditeľný
                poznamka = f"{dodatok_poznamky} {poznamka}".strip()
                # Skrátime poznámku, ak je príliš dlhá pre QR kód (limit je cca 60 znakov)
                if len(poznamka) > 60:
                    poznamka = poznamka[:57] + "..."


            payload = pay_by_square.generate(
                iban=info_platby['iban'],
                amount=round(suma, 2), # Zaokrúhlime sumu na 2 desatinné miesta pre istotu
                variable_symbol=info_platby['vs'],
                constant_symbol=info_platby['ks'],
                note=poznamka,
                beneficiary_name=info_platby['prijemca']
            )
            # Zabezpečíme unikátnosť názvu súboru aj v prípade rýchleho generovania
            subor_qr_cesta = os.path.join(TEMP_DIR, f"temp_qr_{info_platby['vs']}_{poradie}_{i}.png")
            vygeneruj_qr_kod(payload, subor_qr_cesta)
            zoznam_vygenerovaných_platieb.append({
                'suma': round(suma, 2), # Uložíme zaokrúhlenú sumu
                'subor_qr': subor_qr_cesta, # Uložíme cestu k súboru
                'poradie': poradie,
                'celkovy_pocet': celkovy_pocet_platieb
            })

        if zoznam_vygenerovaných_platieb:
            vytvor_pdf_dokument(info_platby, zoznam_vygenerovaných_platieb)

    except pay_by_square.exceptions.InvalidInput as e:
        print(f"❌ {ANSI_RED}Chyba pri generovaní PayBySquare dát: {e}{ANSI_END}")
        print(f"   {ANSI_RED}Skontrolujte zadané údaje, najmä IBAN, dĺžku poznámky alebo špeciálne znaky.{ANSI_END}") # Upravené hlásenie
    except Exception as e:
        print(f"❌ {ANSI_RED}Vyskytla sa chyba pri generovaní QR/PDF: {e}{ANSI_END}")
    # finally pre vyčistenie je v hlavnej funkcii

def vyber_partnera_menu(partneri, aktualna_cesta):
    """Zobrazí menu pre výber partnera a vráti voľbu."""
    while True:
        print(f"\n{ANSI_BOLD}--- Hlavné Menu ---{ANSI_END}")
        if aktualna_cesta:
            print(f"Aktuálny súbor partnerov: {ANSI_YELLOW}{aktualna_cesta}{ANSI_END}")
        else:
            print(f"{ANSI_YELLOW}Zatiaľ nebol načítaný žiadny súbor partnerov.{ANSI_END}")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")
        print(f"[{ANSI_CYAN}0{ANSI_END}]: Načítať/zmeniť súbor partnerov")
        print(f"[{ANSI_CYAN}q{ANSI_END}]: Ukončiť program")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")

        if partneri:
            print(f"{ANSI_BOLD}Komu chcete zaplatiť?{ANSI_END}")
            # Zoradíme partnerov podľa kľúča (čísla) pre konzistentné zobrazenie
            try:
                for key in sorted(partneri.keys(), key=int):
                    value = partneri.get(key) # Použijeme .get pre bezpečnosť
                    if value:
                        print(f"  [{ANSI_CYAN}{key}{ANSI_END}]: {value.get('nazov', 'N/A')} ({value.get('iban', 'N/A')})")
                    else:
                        print(f"  [{ANSI_CYAN}{key}{ANSI_END}]: {ANSI_RED}Chybné dáta partnera{ANSI_END}")
                max_partner_num = max(int(k) for k in partneri.keys()) if partneri else 0
                prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0, q, alebo 1-{max_partner_num}{ANSI_END}): "
            except ValueError:
                print(f"❌ {ANSI_RED}Chyba: Kľúče partnerov nie sú čísla. Skontrolujte formát súboru.{ANSI_END}")
                prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0 alebo q{ANSI_END}): "
                partneri = {} # Resetneme partnerov, aby sa vynútilo nové načítanie
        else:
             prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0 alebo q{ANSI_END}): "


        vyber = input(prompt_text).lower().strip()

        if vyber == 'q':
            return "UKONCIT", None
        if vyber == '0':
            return "ZMENIT_SUBOR", None
        if partneri and vyber in partneri:
            return "PARTNER_VYBRANY", partneri[vyber]
        else:
            print(f"❌ {ANSI_RED}Neplatný výber, skúste to znova.{ANSI_END}")

# --- HLAVNÁ ČASŤ PROGRAMU ---
def main():
    """Hlavná logika a slučka programu."""
    colorama.init(autoreset=True) # <-- INICIALIZÁCIA S AUTORESETOM
    # ANSI grafika pre spestrenie
    print(f"""
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END} {ANSI_BOLD}PAY BY SQUARE QR GENERATOR (SEPA){ANSI_END}
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END} --- Automatické delenie platieb nad {MAX_SUMA_NA_QR:.2f}€ ---
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END}
{ANSI_CYAN}{ANSI_BOLD}█████
""")
    #{ANSI_END}
    vycisti_temp_priecinok() # Vyčistíme prípadné zvyšky z minulého behu

    cesta_suboru = nacitaj_cestu_k_partnerom()
    partneri = None

    if cesta_suboru and os.path.exists(cesta_suboru):
        print(f"Načítavam partnerov z uloženej cesty: {ANSI_YELLOW}{cesta_suboru}{ANSI_END}")
        partneri = nacitaj_partnerov_zo_suboru(cesta_suboru)
        if not partneri:
            print(f"{ANSI_YELLOW}Nepodarilo sa načítať partnerov z uloženej cesty. Požiadam o novú cestu.{ANSI_END}")
            cesta_suboru = None # Resetujeme cestu, aby sa pýtala nová

    if not partneri:
        print(f"{ANSI_BOLD}Vitajte!{ANSI_END} Zdá sa, že spúšťate program prvýkrát, alebo uložený súbor partnerov nebol nájdený/načítaný.")
        cesta_suboru, partneri = pýtaj_a_nacitaj_partnerov_s_ulozenim()
        if not partneri:
            print(f"{ANSI_RED}Nepodarilo sa načítať partnerov. Program sa ukončí.{ANSI_END}")
            return # Ukončí funkciu main()

    # Hlavná slučka programu
    while True:
        akcia, data = vyber_partnera_menu(partneri, cesta_suboru)

        if akcia == "UKONCIT":
            break # Opustí hlavnú slučku

        elif akcia == "ZMENIT_SUBOR":
            nova_cesta, novi_partneri = pýtaj_a_nacitaj_partnerov_s_ulozenim()
            if novi_partneri:
                cesta_suboru = nova_cesta
                partneri = novi_partneri
            # Ak sa nepodarilo načítať nových, pokračujeme s pôvodnými (alebo žiadnymi, ak predtým zlyhalo načítanie)
            continue # Vráti sa na začiatok slučky a zobrazí menu znova

        elif akcia == "PARTNER_VYBRANY":
            vybrany_partner = data
            info_platby = ziskaj_detaily_platby(vybrany_partner)

            if info_platby:
                spracuj_platbu(info_platby)
                print(f"\nStlačte {ANSI_CYAN}Enter{ANSI_END} pre návrat do hlavného menu...")
                input() # Pauza, kým sa užívateľ nevráti do menu
            else:
                print(f"{ANSI_YELLOW}Zadávanie platby bolo zrušené, návrat do hlavného menu.{ANSI_END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ANSI_YELLOW}Program ukončený používateľom (Ctrl+C).{ANSI_END}")
    except Exception as e:
        import traceback
        print(f"\n❌ {ANSI_RED}Vyskytla sa neočakávaná kritická chyba: {e}{ANSI_END}")
        print(f"{ANSI_RED}--- Traceback ---{ANSI_END}")
        traceback.print_exc() # Vypíše detailný traceback chyby
        print(f"{ANSI_RED}--- Koniec Traceback ---{ANSI_END}")
        input(f"Stlačte {ANSI_CYAN}Enter{ANSI_END} pre ukončenie.")
    finally:
        vycisti_temp_priecinok()
        print(f"\n{ANSI_BLUE}Program bol ukončený.{ANSI_END}")