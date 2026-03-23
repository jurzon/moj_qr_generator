import os
import math
import json
import sys
import pay_by_square
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import qrcode
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import colorama

# --- ANSI COLORS ---
ANSI_CYAN = "\033[96m"
ANSI_YELLOW = "\033[93m"
ANSI_BOLD = "\033[1m"
ANSI_BLUE = "\033[94m"
ANSI_RED = "\033[91m"
ANSI_GREEN = "\033[92m"
ANSI_END = "\033[0m"

# --- SETTINGS ---
MAX_AMOUNT_PER_QR = 1000.00
CONFIG_FILE = "config.json"
TEMP_DIR = "temp_qrs"

# --- CONFIGURATION FUNCTIONS ---

def load_partners_path():
    """Loads the last saved path to the partners file from config.json."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('partners_path')
    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Chyba pri čítaní {CONFIG_FILE}: {e}{ANSI_END}")
    return None

def save_partners_path(file_path):
    """Saves the path to the partners file into config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'partners_path': file_path}, f, indent=4)
    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Chyba pri ukladaní {CONFIG_FILE}: {e}{ANSI_END}")

# --- PARTNER PROCESSING FUNCTIONS ---

def load_partners_from_file(file_path):
    """
    Loads partners (name, IBAN) from a text file.
    Automatically tries multiple encodings.
    """
    partners = {}
    partner_id = 1
    encodings = ['utf-8', 'cp1250', 'iso-8859-2', 'utf-16']
    successful_encoding = None
    file_content = None

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                file_content = f.readlines()
            successful_encoding = encoding
            print(f"ℹ️ {ANSI_BLUE}Súbor úspešne načítaný s kódovaním: {encoding}{ANSI_END}")
            break
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            print(f"❌ {ANSI_RED}Chyba: Súbor '{file_path}' sa nenašiel.{ANSI_END}")
            return None
        except PermissionError:
            print(f"❌ {ANSI_RED}Chyba: Program nemá povolenie čítať súbor. Uistite sa, že zadávate cestu k SÚBORU.{ANSI_END}")
            return None
        except Exception as e:
            print(f"❌ {ANSI_RED}Chyba pri otváraní súboru: {e}{ANSI_END}")
            return None

    if not file_content:
        print(f"❌ {ANSI_RED}Chyba: Súbor sa nepodarilo prečítať so žiadnym z podporovaných kódovaní.{ANSI_END}")
        return None

    try:
        for line in file_content:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split(';')
            if len(parts) >= 2:
                name = parts[0].strip()
                iban = parts[1].strip().replace(" ", "")

                if iban and 15 <= len(iban) <= 34 and iban[:2].isalpha():
                    preferred_name = parts[3].strip() if len(parts) > 3 and parts[3].strip() else name
                    if preferred_name and iban:
                        partners[str(partner_id)] = {"name": preferred_name, "iban": iban}
                        partner_id += 1
                else:
                    print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok neobsahuje platný IBAN formát, preskakuje sa.{ANSI_END}")
            else:
                print(f"⚠️ {ANSI_YELLOW}Varovanie: Riadok nemá očakávaný formát (chýba ';'), preskakuje sa.{ANSI_END}")

    except Exception as e:
        print(f"❌ {ANSI_RED}Chyba pri spracovaní obsahu súboru: {e}{ANSI_END}")
        return None

    if not partners:
        print(f"❌ {ANSI_RED}V súbore sa nenašli žiadni platní partneri.{ANSI_END}")
        return None

    return partners

def prompt_and_load_partners():
    """Prompts the user for a file path, loads partners, and saves the path."""
    print(f"\n{ANSI_BLUE}Tip: Cestu k súboru získate najľahšie tak, že súbor {ANSI_BOLD}pretiahnete myšou{ANSI_END}{ANSI_BLUE} sem do okna.{ANSI_END}")
    print(f"{ANSI_YELLOW}   Súbor musí obsahovať riadky vo formáte: Názov ; IBAN ; ; Skrátený názov{ANSI_END}")

    while True:
        file_path = input(f"Zadajte cestu k súboru s partnermi (alebo '{ANSI_CYAN}q{ANSI_END}' pre ukončenie): ").strip()

        if file_path.startswith('"') and file_path.endswith('"'):
            file_path = file_path[1:-1]

        if file_path.lower() == 'q':
            return None, None

        partners = load_partners_from_file(file_path)
        if partners:
            save_partners_path(file_path)
            print(f"✅ {ANSI_GREEN}Partneri úspešne načítaní a cesta uložená.{ANSI_END}")
            return file_path, partners
        else:
            print(f"{ANSI_RED}Skúste zadať cestu znova.{ANSI_END}")

# --- PDF AND QR GENERATION FUNCTIONS ---

def generate_qr_code(payload, file_path):
    """Generates and saves a QR code image."""
    img = qrcode.make(payload)
    img.save(file_path)
    return file_path

def register_font(canvas_obj):
    """Registers the Arial font for PDF generation."""
    font_path = None
    font_registered = False
    font_name = 'Arial'
    fallback_font = 'Helvetica'

    try:
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            font_path = os.path.join(base_path, 'assets', 'arial.ttf')
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.abspath(os.path.join(script_dir, '..', 'assets', 'arial.ttf'))

        if font_path and os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                canvas_obj.setFont(font_name, 10)
                font_registered = True
            except Exception as e:
                print(f"⚠️ {ANSI_YELLOW}Chyba pri registrácii fontu: {e}. Použije sa {fallback_font}.{ANSI_END}")
        else:
            print(f"⚠️ {ANSI_YELLOW}Varovanie: Súbor fontu sa nenašiel. Použije sa {fallback_font}.{ANSI_END}")

    except Exception as e:
        print(f"⚠️ {ANSI_YELLOW}Neočekávaná chyba fontu: {e}. Použije sa {fallback_font}.{ANSI_END}")

    if not font_registered:
        canvas_obj.setFont(fallback_font, 10)

    return font_registered

def create_pdf_document(basic_info, payments_list):
    """Creates a PDF file with horizontal layout of QR codes and details."""
    output_file = f"QR_Platba_VS_{basic_info['vs']}.pdf"
    c = canvas.Canvas(output_file, pagesize=A4)
    width, height = A4

    block_height = 55 * mm
    top_margin = 20 * mm
    left_margin = 15 * mm
    right_margin = 15 * mm
    current_y = height - top_margin

    for payment in payments_list:
        if current_y < block_height + top_margin:
            c.showPage()
            current_y = height - top_margin

        block_top_y = current_y
        qr_size = 40 * mm
        qr_img = ImageReader(payment['qr_file'])
        qr_y_bottom = block_top_y - qr_size - (5*mm)
        c.drawImage(qr_img, left_margin, qr_y_bottom, width=qr_size, height=qr_size)

        has_arial = register_font(c)

        text_x = left_margin + qr_size + (10 * mm)
        text_y = block_top_y - (8 * mm)
        amount_text = f"{payment['amount']:.2f} EUR"
        
        texts = [
            f"Dodávateľ: {basic_info['recipient']}",
            f"IBAN: {basic_info['iban']}",
            f"VS: {basic_info['vs']}",
            f"KS: {basic_info['ks'] if basic_info['ks'] else '-'}",
            f"Suma: {amount_text}"
        ]
        
        if has_arial:
            c.setFont("Arial", 10)
        else:
            c.setFont("Helvetica", 10)

        for text in texts:
            c.drawString(text_x, text_y, text)
            text_y -= 5 * mm

        if has_arial:
            c.setFont("Arial", 24)
        else:
            c.setFont("Helvetica-Bold", 24)

        order_text = f"{payment['order']}/{payment['total_count']}"
        order_y = block_top_y - (block_height / 2) + (5*mm)
        c.drawRightString(width - right_margin, order_y, order_text)

        dash_y = block_top_y - block_height + (5 * mm)
        c.setDash(3, 3)
        c.line(left_margin, dash_y, width - right_margin, dash_y)
        c.setDash([], 0)

        current_y -= block_height

    c.save()
    print(f"\n{ANSI_BOLD}----------------------------------------------------{ANSI_END}")
    print(f"✅ {ANSI_GREEN}PDF súbor '{output_file}' bol úspešne vygenerovaný!{ANSI_END}")
    try:
        print(f"   Súbor: {os.path.abspath(output_file)}")
    except Exception:
        print(f"   Súbor: {output_file}")
    print(f"{ANSI_BOLD}----------------------------------------------------{ANSI_END}")

def cleanup_temp_dir():
    """Removes temporary QR code files and directory."""
    try:
        if os.path.exists(TEMP_DIR):
            for file in os.listdir(TEMP_DIR):
                try:
                    os.remove(os.path.join(TEMP_DIR, file))
                except Exception:
                    pass
            try:
                os.rmdir(TEMP_DIR)
            except Exception:
                pass
    except Exception:
        pass

# --- CORE LOGIC FUNCTIONS ---

def get_payment_details(partner_info):
    """Gets amount, VS, KS, and note from the user."""
    print(f"\n{ANSI_BOLD}--- Zadanie platby pre: {partner_info['name']} ({partner_info['iban']}) ---{ANSI_END}")
    print(f"(Pre zrušenie a návrat do menu zadajte '{ANSI_CYAN}q{ANSI_END}')")

    while True:
        try:
            amount_str = input(f"Zadajte CELKOVÚ sumu ({ANSI_YELLOW}napr. 5562.00{ANSI_END}): ").replace(',', '.')
            if amount_str.lower() == 'q': return None
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Suma musí byť kladné číslo.")
            break
        except ValueError as e:
            print(f"❌ {ANSI_RED}Neplatná suma. {e}{ANSI_END}")

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

    note = input(f"Zadajte {ANSI_YELLOW}poznámku pre príjemcu{ANSI_END} (nepovinné): ")
    if note.lower() == 'q': return None

    return {
        "recipient": partner_info['name'],
        "iban": partner_info['iban'].strip(),
        "total_amount": amount,
        "vs": vs,
        "ks": ks,
        "note": note
    }

def process_payment(payment_info):
    """Splits the payment, generates QR codes and creates PDF."""
    total_amount = payment_info["total_amount"]
    partial_amounts = []

    if total_amount > MAX_AMOUNT_PER_QR:
        full_payments_count = math.floor(total_amount / MAX_AMOUNT_PER_QR)
        remainder = round(total_amount - (full_payments_count * MAX_AMOUNT_PER_QR), 2)

        if abs(remainder) < 0.001:
            remainder = 0.0

        for _ in range(full_payments_count):
            partial_amounts.append(MAX_AMOUNT_PER_QR)
        if remainder > 0:
            partial_amounts.append(remainder)
        print(f"\n{ANSI_BLUE}INFO:{ANSI_END} Celková suma {ANSI_YELLOW}{total_amount:.2f} EUR{ANSI_END} bude rozdelená na {ANSI_YELLOW}{len(partial_amounts)} platieb{ANSI_END}.")
    else:
        partial_amounts.append(total_amount)

    generated_payments = []
    total_count = len(partial_amounts)

    try:
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR)
    except Exception as e:
         print(f"❌ {ANSI_RED}Nepodarilo sa vytvoriť dočasný priečinok: {e}{ANSI_END}")
         return

    try:
        for i, amount in enumerate(partial_amounts):
            order = i + 1
            current_note = payment_info['note']
            if total_count > 1:
                note_prefix = f"(Platba {order}/{total_count})"
                current_note = f"{note_prefix} {current_note}".strip()
                if len(current_note) > 60:
                    current_note = current_note[:57] + "..."

            payload = pay_by_square.generate(
                iban=payment_info['iban'],
                amount=round(amount, 2),
                variable_symbol=payment_info['vs'],
                constant_symbol=payment_info['ks'],
                note=current_note,
                beneficiary_name=payment_info['recipient']
            )
            
            qr_file_path = os.path.join(TEMP_DIR, f"temp_qr_{payment_info['vs']}_{order}_{i}.png")
            generate_qr_code(payload, qr_file_path)
            
            generated_payments.append({
                'amount': round(amount, 2),
                'qr_file': qr_file_path,
                'order': order,
                'total_count': total_count
            })

        if generated_payments:
            create_pdf_document(payment_info, generated_payments)

    except pay_by_square.exceptions.InvalidInput as e:
        print(f"❌ {ANSI_RED}Chyba pri generovaní dát: {e}{ANSI_END}")
    except Exception as e:
        print(f"❌ {ANSI_RED}Vyskytla sa chyba pri generovaní QR/PDF: {e}{ANSI_END}")

def select_partner_menu(partners, current_path):
    """Displays the menu for partner selection."""
    while True:
        print(f"\n{ANSI_BOLD}--- Hlavné Menu ---{ANSI_END}")
        if current_path:
            print(f"Aktuálny súbor partnerov: {ANSI_YELLOW}{current_path}{ANSI_END}")
        else:
            print(f"{ANSI_YELLOW}Zatiaľ nebol načítaný žiadny súbor partnerov.{ANSI_END}")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")
        print(f"[{ANSI_CYAN}0{ANSI_END}]: Načítať/zmeniť súbor partnerov")
        print(f"[{ANSI_CYAN}q{ANSI_END}]: Ukončiť program")
        print(f"{ANSI_BOLD}---------------------------------{ANSI_END}")

        if partners:
            print(f"{ANSI_BOLD}Komu chcete zaplatiť?{ANSI_END}")
            try:
                for key in sorted(partners.keys(), key=int):
                    value = partners.get(key)
                    if value:
                        print(f"  [{ANSI_CYAN}{key}{ANSI_END}]: {value.get('name', 'N/A')} ({value.get('iban', 'N/A')})")
                
                max_partner_num = max(int(k) for k in partners.keys()) if partners else 0
                prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0, q, alebo 1-{max_partner_num}{ANSI_END}): "
            except ValueError:
                print(f"❌ {ANSI_RED}Chyba formátu kľúčov v súbore.{ANSI_END}")
                prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0 alebo q{ANSI_END}): "
                partners = {}
        else:
             prompt_text = f"\nVyberte možnosť ({ANSI_CYAN}0 alebo q{ANSI_END}): "

        choice = input(prompt_text).lower().strip()

        if choice == 'q':
            return "EXIT", None
        if choice == '0':
            return "CHANGE_FILE", None
        if partners and choice in partners:
            return "PARTNER_SELECTED", partners[choice]
        else:
            print(f"❌ {ANSI_RED}Neplatný výber, skúste to znova.{ANSI_END}")

def main():
    """Main program loop."""
    colorama.init(autoreset=True)
    print(f"""
{ANSI_CYAN}{ANSI_BOLD}█████{ANSI_END} {ANSI_BOLD}PAY BY SQUARE QR GENERATOR (SEPA){ANSI_END}
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END} --- Automatické delenie platieb nad {MAX_AMOUNT_PER_QR:.2f}€ ---
{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_YELLOW}█{ANSI_CYAN}█{ANSI_END}
{ANSI_CYAN}{ANSI_BOLD}█████
""")
    
    cleanup_temp_dir()

    file_path = load_partners_path()
    partners = None

    if file_path and os.path.exists(file_path):
        print(f"Načítavam partnerov z uloženej cesty: {ANSI_YELLOW}{file_path}{ANSI_END}")
        partners = load_partners_from_file(file_path)
        if not partners:
            file_path = None

    if not partners:
        print(f"{ANSI_BOLD}Vitajte!{ANSI_END} Zadajte cestu k súboru s partnermi.")
        file_path, partners = prompt_and_load_partners()
        if not partners:
            return

    while True:
        action, data = select_partner_menu(partners, file_path)

        if action == "EXIT":
            break
        elif action == "CHANGE_FILE":
            new_path, new_partners = prompt_and_load_partners()
            if new_partners:
                file_path = new_path
                partners = new_partners
            continue
        elif action == "PARTNER_SELECTED":
            selected_partner = data
            payment_info = get_payment_details(selected_partner)

            if payment_info:
                process_payment(payment_info)
                print(f"\nStlačte {ANSI_CYAN}Enter{ANSI_END} pre návrat do hlavného menu...")
                input()
            else:
                print(f"{ANSI_YELLOW}Zadávanie platby zrušené.{ANSI_END}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{ANSI_YELLOW}Program ukončený používateľom (Ctrl+C).{ANSI_END}")
    except Exception as e:
        import traceback
        print(f"\n❌ {ANSI_RED}Kritická chyba: {e}{ANSI_END}")
        traceback.print_exc()
        input(f"Stlačte {ANSI_CYAN}Enter{ANSI_END} pre ukončenie.")
    finally:
        cleanup_temp_dir()