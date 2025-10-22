# Generátor QR Kódov "Pay By Square" (SK)

Pokročilý Python skript na generovanie platobných QR kódov podľa slovenského štandardu "Pay By Square".

Program je navrhnutý na zjednodušenie úhrad vysokých faktúr. Ak celková suma presiahne 1000 €, program ju **automaticky rozdelí na viacero čiastkových platieb** (napr. 5562 € sa rozdelí na 5x 1000 € a 1x 562 €) a vygeneruje pre každú platbu samostatný QR kód.

Výsledkom je jeden PDF súbor, ktorý obsahuje všetky QR kódy pekne pod sebou, vrátane čitateľného popisu ku každému z nich.

## Kľúčové vlastnosti

  * **Automatické delenie sumy:** Platby nad 1000 € sa automaticky rozdelia na viacero QR kódov, aby sa predišlo limitom v bankových aplikáciách.
  * **Generovanie PDF:** Všetky QR kódy sa vygenerujú do jedného, prehľadného PDF súboru, pripraveného na tlač alebo digitálne použitie.
  * **Čitateľné popisky:** Každý QR kód v PDF má pri sebe popis (Odberateľ, Suma, VS) a poradové číslo (napr. "Platba 1/6").
  * **Štandard "Pay By Square":** Využíva knižnicu `bysquare` na korektné vytvorenie dátového reťazca (LZMA kompresia, Base32hex, CRC32).
  * **Assety:** Využíva vlastný font (`arial.ttf`) pre konzistentný vzhľad textu.

## Požiadavky

  * Python 3.x
  * Knižnice uvedené v `requirements.txt` (primárne `bysquare`, `qrcode`, `pillow`, `reportlab`)

*(Poznámka: Ak generujete PDF, pravdepodobne používate knižnicu ako `reportlab`. Ak áno, nezabudnite ju pridať do `requirements.txt`\!)*

## Inštalácia a spustenie

Postupujte podľa týchto krokov na spustenie programu vo vašom lokálnom prostredí.

**1. Klonujte alebo stiahnite repozitár**

```bash
# Ak máte Git
git clone https://github.com/VASE-MENO/moj_qr_generator.git
cd moj_qr_generator
```

*(Ak Git nemáte, jednoducho stiahnite projekt ako ZIP a rozbaľte ho.)*

**2. Vytvorte a aktivujte virtuálne prostredie**

Je silne odporúčané používať virtuálne prostredie (`.venv`), aby sa knižnice neinštalovali globálne.

```bash
# Vytvorenie .venv (Windows)
python -m venv .venv

# Aktivácia .venv (Windows)
.\.venv\Scripts\activate
```

**3. Nainštalujte potrebné knižnice**

Pomocou súboru `requirements.txt` nainštalujete všetky potrebné závislosti naraz.

```bash
pip install -r requirements.txt
```

**4. Spustite program**

Program sa spustí vykonaním skriptu `main.py` v priečinku `src/`.

```bash
python src/main.py
```

## Ako program funguje

Po spustení skript `src/main.py` automaticky vykoná nasledujúce kroky:

1.  **Získa vstup:** Opýta sa používateľa na údaje o platbe (IBAN, Celková suma, VS, Poznámka).
2.  **Rozdelí sumu:** Skontroluje, či je celková suma vyššia ako 1000 €. Ak áno, vytvorí zoznam čiastkových súm (napr. `[1000, 1000, 562.00]`). Ak nie, zoznam bude obsahovať len jednu položku (napr. `[150.00]`).
3.  **Generuje QR kódy:** Prejde týmto zoznamom súm a pre každú jednu vygeneruje platný "Pay By Square" reťazec a z neho QR kód.
4.  **Pridá poradie:** K poznámke pre každú platbu pripojí poradové číslo (napr. "Faktúra X (Platba 1/3)").
5.  **Vytvorí PDF:** Vytvorí PDF dokument, kam postupne vykreslí každý QR kód spolu s jeho popisom (Suma, VS, Odberateľ).
6.  **Uloží súbor:** Finálny dokument uloží (napr. ako `vystupna_faktura.pdf`) a otvorí ho.