


![image](https://github.com/user-attachments/assets/76ff31b1-9cc6-44d0-becf-12b7d4777c97)












## EVO Projekt – README

Az EVO (Enhanced Vision Operative) egy nyílt forráskódú, moduláris animatronikus szem prototípus, amely ötvözi a szemmozgás-követést, hangvezérlést és mesterséges intelligenciát a felhasználói interakciók új szintre emeléséhez. A projekt célja egy költséghatékony, testre szabható platform létrehozása, amely orvosi, ipari vagy oktatási alkalmazásokban is hasznosítható.

---

## Főbb Jellemzők

- **Valós idejű szemmozgás-felismerés**: Kameraalapú követés MediaPipe és TensorFlow Lite segítségével, helyi feldolgozással (Raspberry Pi 4-en).
- **Hibrid vezérlés**: Szem- és hangvezérlés kombinációja (pl. „Nézz balra!” parancsra a szemek elfordulnak).
- **Moduláris hardver**: Könnyen bővíthető új szenzorokkal (pl. LIDAR, hőmérséklet-érzékelő) vagy aktorokkal (pl. robotkar).
- **Költséghatékonyság**: Jelentősen olcsóbb a piaci alternatíváknál, alacsony karbantartási költségek, DIY alkatrészekkel javítható.
- **Nyílt forráskód**: Python és TensorFlow kódok teljes hozzáféréssel, szabadon testre szabható.

---

## Hardverkövetelmények

- **Mikrokontroller**: Raspberry Pi x
- **Szervomotorok**: 6× MG996R (szemmozgás szimulációhoz)
- **Vezérlő**: PCA9685 szervóvezérlő
- **Kamera**: USB vagy Raspberry Pi kompatibilis kamera
- **Mozgásérzékelő**: Ultrahangos szenzor (opcionális)
- **Mikrofonmodul**: Hangvezérléshez

---

## Szoftverkövetelmények

- **Python 3.x**
- **TensorFlow Lite**
- **MediaPipe**
- **OpenCV**
- **GPIO könyvtárak (Raspberry Pi esetén)**

---

## Telepítés

1. Klónozd a repót:
   ```bash
   git clone https://github.com//EVO.git
   ```
2. Telepítsd a szükséges Python csomagokat:
   ```bash
   pip install -r requirements.txt
   ```
3. Csatlakoztasd a hardverelemeket a dokumentáció szerint.
4. Indítsd el a vezérlő szkriptet:
   ```bash
   python main.py
   ```

---

## Fejlesztési ütemterv (részlet)

- **1. hónap**: Alapkutatás, rendszerterv, hardver kiválasztása, szoftverterv kidolgozása
- **2. hónap**: Hardver- és szoftverprototípus fejlesztése, AI-modulok integrálása
- **3. hónap**: Interaktív funkciók, gépi tanulás, adaptív válaszok fejlesztése
- **4. hónap**: Felhasználói tesztelés, dokumentáció, további fejlesztési irányok meghatározása

---

## Felhasználási területek

- Orvosi segédeszközök (pl. mozgáskorlátozottak interakciója)
- Ipari automatizálás (figyelem-követés, hibacsökkentés)
- Oktatás (interaktív tanulási platformok)
- Human-computer interaction (HCI) kutatás

---

## Hozzájárulás

Szívesen várjuk a közösségi hozzájárulásokat! Hibákat, ötleteket vagy új modulokat pull request formájában lehet beküldeni.

---

## Licenc

Ez a projekt nyílt forráskódú, a licenc részletei a LICENSE fájlban találhatók.

---

## Kapcsolat

Készítők: Dek Hunor, Tóth Miklós Milán, Zsigó Zsolt  
Kérdés vagy észrevétel: [deakhunor14@gmail.com]

---

> „Az emberek nem azt hiszik, amit látnak, hanem azt látják, amit hisznek.”
