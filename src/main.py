import os
import math
import json  # Potrebné pre prácu s config súborom
import sys   # Potrebné pre ukončenie programu
import pay_by_square
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
                iban = casti[1].strip()
                if iban.startswith("SK") and len(iban) == 24:
                    preferovany_nazov = casti[3].strip() if len(casti) > 3 and casti[3].strip() else nazov
                    if preferovany_nazov and iban:
                        partneri[str(cislo_partnera)] = {"nazov": preferovany_nazov, "iban": iban}
                        cislo_partnera += 1
                else:
                    print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok '{riadok[:30]}...' neobsahuje platný SK IBAN, preskakuje sa.{ANSI_END}")
            else:
                print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok '{riadok[:30]}...' nemá očakávaný formát, preskakuje sa.{ANSI_END}")
    
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
    """Pokúsi sa zaregistrovať Arial font pre PDF."""
    try:
        # Získanie absolútnej cesty k adresáru, kde sa nachádza tento skript (main.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Zostavenie cesty k fontu relatívne k adresáru skriptu
        # Ideme o úroveň vyššie (z src do moj_qr_generator) a potom do assets
        project_root = os.path.join(script_dir, "..")
        font_path = os.path.join(project_root, "assets", "arial.ttf")

        # Kontrola existencie súboru pomocou absolútnej cesty
        font_path = os.path.abspath(font_path) # Pre istotu prekonvertujeme na absolútnu cestu

        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial', font_path))
                c.setFont("Arial", 10)
                # print(f"INFO: Font '{font_path}' úspešne načítaný.") # Odkomentuj pre ladenie
                return True
            except Exception as e:
                print(f"⚠️ {ANSI_YELLOW}Nepodarilo sa načítať font '{font_path}': {e}. Použije sa Helvetica.{ANSI_END}")
        else:
            print(f"⚠️ {ANSI_YELLOW}Varovanie: Font '{font_path}' sa nenašiel. Použije sa predvolený Helvetica.{ANSI_END}")

    except NameError:
         # Ak __file__ nie je definované (napr. v interaktívnej konzole), skúsime starú metódu
         font_path_fallback = os.path.join("..", "assets", "arial.ttf")
         if os.path.exists(font_path_fallback):
             try:
                 pdfmetrics.registerFont(TTFont('Arial', font_path_fallback))
                 c.setFont("Arial", 10)
                 return True
             except Exception as e:
                 print(f"⚠️ {ANSI_YELLOW}Nepodarilo sa načítať font (fallback): {e}. Použije sa Helvetica.{ANSI_END}")
         else:
              print(f"⚠️ {ANSI_YELLOW}Varovanie: Font sa nenašiel ani cez fallback cestu. Použije sa predvolený Helvetica.{ANSI_END}")
    except Exception as general_e:
        print(f"⚠️ {ANSI_YELLOW}Neočekávaná chyba pri hľadaní fontu: {general_e}. Použije sa Helvetica.{ANSI_END}")


    c.setFont("Helvetica", 10)
    return False

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
        if pozicia_y < vyska_bloku_platby:
            c.showPage()
            pozicia_y = vyska - horny_okraj

        vrch_bloku_y = pozicia_y
        velkost_qr = 40 * mm
        qr_obr = ImageReader(platba['subor_qr']) # ImageReader načíta cestu k súboru
        c.drawImage(qr_obr, lavy_okraj, vrch_bloku_y - velkost_qr - (5*mm), width=velkost_qr, height=velkost_qr)

        # Registrácia a nastavenie fontu pre každý prípad (aj pre novú stranu)
        ma_arial = registruj_font(c)
        
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

        if ma_arial:
            c.setFont("Arial", 24)
        else:
            c.setFont("Helvetica-Bold", 24)

        poradove_cislo_text = f"{platba['poradie']}/{platba['celkovy_pocet']}"
        poradove_cislo_y = vrch_bloku_y - (vyska_bloku_platby / 2)
        c.drawRightString(sirka - pravy_okraj, poradove_cislo_y, poradove_cislo_text)

        pozicia_ciary_y = vrch_bloku_y - vyska_bloku_platby + (5 * mm)
        c.setDash(3, 3)
        c.line(lavy_okraj, pozicia_ciary_y, sirka - pravy_okraj, pozicia_ciary_y)
        c.setDash([], 0)

        pozicia_y -= vyska_bloku_platby

    c.save()
    print(f"\n{ANSI_BOLD}----------------------------------------------------{ANSI_END}")
    print(f"✅ {ANSI_GREEN}PDF súbor '{vystupny_subor}' bol úspešne vygenerovaný!{ANSI_END}")
    print(f"   Súbor: {os.path.abspath(vystupny_subor)}")
    print(f"{ANSI_BOLD}----------------------------------------------------{ANSI_END}")

def vycisti_temp_priecinok():
    """Odstráni dočasné QR kódy a priečinok."""
    try:
        if os.path.exists(TEMP_DIR):
            for subor in os.listdir(TEMP_DIR):
                os.remove(os.path.join(TEMP_DIR, subor))
            os.rmdir(TEMP_DIR)
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
            print(f"❌ {ANSI_RED}Neplatná suma. {e}{ANSI_END}")

    while True:
        vs = input(f"Zadajte {ANSI_YELLOW}variabilný symbol{ANSI_END} (max 10 číslic): ")
        if vs.lower() == 'q': return None
        if vs.isdigit() and len(vs) <= 10:
            break
        print(f"❌ {ANSI_RED}Neplatný VS. Musí obsahovať max 10 číslic.{ANSI_END}")

    while True:
        ks = input(f"Zadajte {ANSI_YELLOW}konštantný symbol{ANSI_END} (nepovinné, max 4 číslice): ")
        if ks.lower() == 'q': return None
        if not ks or (ks.isdigit() and len(ks) <= 4):
            break
        print(f"❌ {ANSI_RED}Neplatný KS. Musí obsahovať max 4 číslice.{ANSI_END}")

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
        pocet_plnych_platieb = int(celkova_suma / MAX_SUMA_NA_QR)
        zostatok = round(math.fmod(celkova_suma, MAX_SUMA_NA_QR), 2)
        for _ in range(pocet_plnych_platieb):
            ciastocne_sumy.append(MAX_SUMA_NA_QR)
        if zostatok > 0:
            ciastocne_sumy.append(zostatok)
        print(f"\n{ANSI_BLUE}INFO:{ANSI_END} Celková suma {ANSI_YELLOW}{celkova_suma:.2f} EUR{ANSI_END} bude rozdelená na {ANSI_YELLOW}{len(ciastocne_sumy)} platieb{ANSI_END}.")
    else:
        ciastocne_sumy.append(celkova_suma)

    zoznam_vygenerovaných_platieb = []
    celkovy_pocet_platieb = len(ciastocne_sumy)

    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    try:
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
            subor_qr_cesta = os.path.join(TEMP_DIR, f"temp_qr_{info_platby['vs']}_{poradie}.png")
            vygeneruj_qr_kod(payload, subor_qr_cesta)
            zoznam_vygenerovaných_platieb.append({
                'suma': suma,
                'subor_qr': subor_qr_cesta, # Uložíme cestu k súboru
                'poradie': poradie,
                'celkovy_pocet': celkovy_pocet_platieb
            })

        if zoznam_vygenerovaných_platieb:
            vytvor_pdf_dokument(info_platby, zoznam_vygenerovaných_platieb)

    except Exception as e:
        print(f"❌ {ANSI_RED}Vyskytla sa chyba pri generovaní PDF: {e}{ANSI_END}")
    # finally sa postará o vyčistenie temp súborov v hlavnej funkcii

def vyber_partnera_menu(partneri, aktualna_cesta):
    """Zobrazí menu pre výber partnera a vráti voľbu."""
    while True:
        print(f"\n{ANSI_BOLD}--- Hlavné Menu ---{ANSI_END}")
        print(f"Aktuálny súbor partnerov: {ANSI_YELLOW}{aktualna_cesta}{ANSI_END}")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")
        print(f"[{ANSI_CYAN}0{ANSI_END}]: Načítať nový súbor partnerov")
        print(f"[{ANSI_CYAN}q{ANSI_END}]: Ukončiť program")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")
        print(f"{ANSI_BOLD}Komu chcete zaplatiť?{ANSI_END}")
        
        # Zoradíme partnerov podľa kľúča (čísla) pre konzistentné zobrazenie
        for key in sorted(partneri.keys(), key=int):
            value = partneri[key]
            print(f"  [{ANSI_CYAN}{key}{ANSI_END}]: {value['nazov']} ({value['iban']})")

        vyber = input(f"\nVyberte možnosť ({ANSI_CYAN}0, q, alebo 1-{len(partneri)}{ANSI_END}): ").lower().strip()

        if vyber == 'q':
            return "UKONCIT", None
        if vyber == '0':
            return "ZMENIT_SUBOR", None
        if vyber in partneri:
            return "PARTNER_VYBRANY", partneri[vyber]
        else:
            print(f"❌ {ANSI_RED}Neplatný výber, skúste to znova.{ANSI_END}")

# --- HLAVNÁ ČASŤ PROGRAMU ---
def main():
    """Hlavná logika a slučka programu."""
    
    # ANSI grafika pre spestrenie
    print(f"""
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END} {ANSI_BOLD}PAY BY SQUARE QR GENERATOR (SK){ANSI_END}
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END} --- Automatické delenie platieb nad {MAX_SUMA_NA_QR:.2f}€ ---
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END}
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END}
""")
    
    vycisti_temp_priecinok() # Vyčistíme prípadné zvyšky z minulého behu

    cesta_suboru = nacitaj_cestu_k_partnerom()
    partneri = None

    if cesta_suboru and os.path.exists(cesta_suboru):
        print(f"Načítavam partnerov z uloženej cesty: {ANSI_YELLOW}{cesta_suboru}{ANSI_END}")
        partneri = nacitaj_partnerov_zo_suboru(cesta_suboru)
    
    if not partneri:
        print(f"{ANSI_BOLD}Vitajte!{ANSI_END} Zdá sa, že spúšťate program prvýkrát, alebo uložený súbor partnerov nebol nájdený.")
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
        print(f"\n❌ {ANSI_RED}Vyskytla sa neočakávaná kritická chyba: {e}{ANSI_END}")
        input(f"Stlačte {ANSI_CYAN}Enter{ANSI_END} pre ukončenie.")
    finally:
        vycisti_temp_priecinok()
        print(f"{ANSI_BLUE}Program bol ukončený.{ANSI_END}")