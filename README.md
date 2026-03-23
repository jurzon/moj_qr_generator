# Generátor QR Kódov "Pay By Square" (SK)

Jednoduchý a pokročilý program na generovanie platobných QR kódov podľa slovenského štandardu "Pay By Square".

Program je navrhnutý primárne na zjednodušenie úhrad vysokých faktúr. Ak celková suma presiahne 1000 €, program ju **automaticky rozdelí na viacero čiastkových platieb** (napr. 5562 € sa rozdelí na 5x 1000 € a 1x 562 €) a vygeneruje pre každú platbu samostatný QR kód. Výsledkom je jeden PDF súbor, ktorý obsahuje všetky QR kódy pekne pod sebou.

## ✨ Kľúčové vlastnosti
* **Automatické delenie sumy:** Platby nad 1000 € sa automaticky rozdelia na viacero QR kódov.
* **Generovanie PDF:** Všetky QR kódy sa vygenerujú do jedného, prehľadného PDF súboru.
* **Čitateľné popisky:** Každý QR kód v PDF má pri sebe popis (Odberateľ, Suma, VS) a poradové číslo.
* **Štandard "Pay By Square":** Využíva oficiálny štandard pre slovenské bankové aplikácie.

---

## 📥 Stiahnutie a spustenie (Pre bežných používateľov)

Ak si chcete program iba spustiť a nechcete inštalovať programovacie prostredie, postupujte takto:

1. Na pravej strane tejto stránky nájdite sekciu **Releases**.
2. Kliknite na najnovšiu verziu (napr. `v1.1.9`).
3. V sekcii *Assets* (úplne dole) si stiahnite súbor **`moj_qr_generator.exe`**.
4. Stiahnutý súbor si presuňte do priečinka, kde ho chcete mať (napr. na Plochu) a jednoducho ho spustite dvojklikom.

---

## 📋 Nastavenie zoznamu platobných partnerov

Aby program vedel, komu idete platiť, musíte si pripraviť jednoduchý textový súbor s vašimi kontaktmi.

### 1. Vytvorenie súboru
Vytvorte si obyčajný textový súbor, napríklad `partneri.txt` (môžete použiť Poznámkový blok / Notepad).
Každého partnera alebo firmu uveďte na nový riadok presne v tomto formáte:
`Názov (oficiálny) ; IBAN ; ; Skrátený Názov`

**Príklad obsahu súboru:**
```text
# Toto je zoznam mojich platobných partnerov
Jozef Mrkvička ; SK9876543210987654321098 ; ; Jozef (skrátene)
Firma Alfa s.r.o. ; SK1122334455667788990011 ; ; Alfa sro
```

### 2. Vloženie cesty k súboru do programu
Pri prvom spustení programu sa vás čierne okno (konzola) opýta na **cestu k tomuto súboru**. 

Máte dve možnosti, ako ju tam zadať:
* **💡 Najjednoduchší spôsob:** Jednoducho chyťte váš vytvorený súbor `partneri.txt` myšou a presuňte (drag & drop) ho priamo do čierneho okna programu. Cesta sa tam sama vypíše a stačí stlačiť Enter.
* **Ručné zadanie cesty:** Skopírujte celú cestu k súboru. Na systéme Windows vyzerá takáto absolútna cesta napríklad takto:
  `C:\Users\MenoPouzivatela\Documents\partneri.txt`
  alebo
  `C:\Users\MenoPouzivatela\Desktop\Zmluvy\partneri.txt`

Program si túto cestu zapamätá a pri ďalšom spustení ju už od vás pýtať nebude.

---

## 💻 Pre vývojárov: Inštalácia zo zdrojového kódu

Ak si chcete kód upravovať alebo ho spúšťať priamo cez Python:

**1. Klonujte alebo stiahnite repozitár**
```bash
git clone [https://github.com/jurzon/moj_qr_generator.git](https://github.com/jurzon/moj_qr_generator.git)
cd moj_qr_generator
```

**2. Vytvorte a aktivujte virtuálne prostredie**
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

**3. Nainštalujte potrebné knižnice**
```bash
pip install -r requirements.txt
```

**4. Spustite program**
```bash
python src/main.py
```

---

## 📦 Pre vývojárov: Ako vydať novú verziu (Release)

Tento repozitár má nastavený automatizovaný proces (GitHub Actions Workflow). Keď upravíte kód a chcete používateľom ponúknuť nový `.exe` súbor na stiahnutie, postupujte takto:

**1. Uložte a odošlite úpravy kódu na GitHub:**
Týmto odošlete samotný kód do hlavnej vetvy repozitára.
```bash
git add .
git commit -m "Popis úprav (napr. oprava chýb, preklad UI)"
git push
```

**2. Vytvorte novú verziu (Tag) a odošlite ju:**
Na spúšťanie procesu zostavenia (buildu) používame sémantické verzovanie (napr. posun z `v1.1.9` na `v1.2.0`). Týmto krokom poviete GitHubu, aby vygeneroval novú aplikáciu.
```bash
git tag v1.2.0
git push origin v1.2.0
```

> *Hneď ako odošlete tag na GitHub (krok 2), server si ho všimne a na pozadí spustí skript `release.yml`. Automaticky nainštaluje Python, zabalí kód cez PyInstaller do `moj_qr_generator.exe` a vytvorí nový verejný Release vo vašom repozitári.*