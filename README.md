# Sviluppo Pellicole B/N

Calcolatore dei tempi di sviluppo per pellicole bianco e nero. L'utente sceglie
da menu a tendina pellicola → formato → rivelatore → diluizione → ISO esposto →
temperatura, e l'app restituisce la "ricetta": tempo, diluizione, temperatura di
riferimento e ritmo di agitazione, con timer integrato.

I tempi **non sono inventati**: sono trascritti dai **datasheet ufficiali** dei
produttori (Ilford/Harman, Kodak, Foma). Ogni ricetta mostra il link alla fonte.

## Cosa contiene la cartella

| File | Cosa è |
|---|---|
| `index.html` | L'app completa (HTML + CSS + JS in un unico file). |
| `data.js` | Il dataset generato (usato dall'app). **Non modificare a mano.** |
| `data.json` | Stesso dataset in JSON (comodo per altri usi). |
| `build_data.py` | La **fonte di verità**: le tabelle dei tempi. Genera `data.js` e `data.json`. |
| `README.md` | Questo file. |

## Provarla in locale

Basta aprire `index.html` con doppio clic nel browser: funziona anche da file,
perché i dati sono in `data.js` (nessun server necessario).

In alternativa, con un piccolo server locale:
```bash
cd sviluppo-pellicole
python3 -m http.server 8000
# poi apri http://localhost:8000
```

## Deploy su Vercel

È un sito **statico**: nessun build, nessuna configurazione.

**Opzione A — Vercel CLI (più veloce):**
```bash
npm i -g vercel
cd sviluppo-pellicole
vercel            # segui le domande; "framework preset" = Other
vercel --prod     # per pubblicare in produzione
```

**Opzione B — da GitHub:**
1. Carica la cartella in un repo GitHub.
2. Su vercel.com → *Add New Project* → importa il repo.
3. Framework Preset: **Other**. Lascia vuoti build/output. → *Deploy*.

## Chat (NLP locale) e come aggiungere un LLM dopo

L'app si apre sulla **Chat**: scrivi in linguaggio naturale (es. "HP5 a 800 in
Rodinal", "Tri-X in HC-110 a 22°", "negativi densi") e ottieni la ricetta con
timer. Il motore è **locale**: gratis, istantaneo, e non inventa mai i tempi
(risponde solo dai datasheet; altrimenti rimanda al Massive Dev Chart). Quando
manca un dato fa una domanda guidata (diluizione, ISO). C'è anche la scheda
**Tendine** per chi preferisce i menu.

Vuoi un LLM "vero" per le domande libere? È già predisposto:

1. In `index.html` c'è `var LLM_ENABLED = false` e la funzione `askLLM()`, che
   invia le frasi non capite a `/api/chat`.
2. Crea una **Vercel Function** `api/chat.js` che inoltra il messaggio a un
   servizio AI con piano gratuito (es. **Groq** o **Google Gemini** — NON ngrok,
   che non è un'AI), tenendo la API key in una **variabile d'ambiente** Vercel
   (`Settings → Environment Variables`), MAI nel codice del sito.
3. Metti `LLM_ENABLED = true`.

Regola d'oro: l'LLM risponde solo alle domande libere; i tempi di sviluppo li dà
sempre il motore locale dai datasheet, così non si inventa nulla.

## Strumenti (reciprocità + chimica)

Scheda **Strumenti**:

- **Reciprocità (pose lunghe):** dato il tempo misurato dall'esposimetro, calcola il
  tempo da impostare davvero. Usa le formule dei datasheet — legge di potenza
  Ilford/Kentmere (Ta = Tm^p), tabella Kodak (Tri-X, T-Max), fattore Schwarzschild
  Foma. Vale oltre ~1 s.
- **Diluizione:** dato il volume della tank e la diluizione (es. 1+50), dà i ml di
  rivelatore e acqua, con avviso sulla quantità minima per i concentrati.

## Consigli + Feedback in inbox (opzionale)

L'app include una sezione **Consigli** (diagnostica: negativi densi/chiari/contrastati →
cosa correggere) e un **form di feedback** che allega in automatico la ricetta scelta
(pellicola, rivelatore, diluizione, EI, temperatura, tempo).

Di default il pulsante "Invia feedback" apre l'app di posta del visitatore già compilata
verso `fde.llc2023@gmail.com`. Per riceverli **direttamente in inbox** (senza dipendere
dall'app di posta di chi scrive, e senza esporre la tua email nel sito):

1. Vai su <https://web3forms.com>, inserisci la tua email, copia l'**Access Key** (gratis,
   nessun account; piano free 250 invii/mese).
2. In `index.html`, in cima allo script, incolla la chiave:
   ```js
   var WEB3FORMS_KEY = "la-tua-access-key";
   ```
3. Salva → `git commit -m "feedback"` → `git push`. Vercel ri-pubblica e i feedback
   arrivano alla mail collegata alla chiave.

## Aggiungere o correggere una pellicola

Tutto vive in `build_data.py`. Esempio di una riga di tempi (a 20 °C):

```python
("rodinal","1+25",{400:"6:00", 800:"8:00"}),
#   ^dev      ^dil   ^EI:tempo (m:ss). Intervalli Foma: "9:00-10:00"
```

1. Modifica/aggiungi le righe nella lista `FILMS` (copia la struttura di una
   pellicola esistente). Gli sviluppatori validi sono nella lista `DEVELOPERS`.
2. Rigenera i dati:
   ```bash
   python3 build_data.py
   ```
3. Ricarica l'app (o ri-deploya). Fatto.

Scrivi sempre il tempo come `m:ss` (es. `7:30`), così `½ → :30`, `¼ → :15`,
`¾ → :45`. Metti il valore **solo se è sul datasheet**: se manca, lascialo fuori
— l'app rimanderà al Massive Dev Chart per quella combinazione.

## Pellicole incluse (14)

Ilford HP5 Plus · FP4 Plus · Delta 100 · Delta 400 · Delta 3200 · Pan F Plus ·
Kentmere Pan 100 · Kentmere Pan 400 · Kodak Tri-X 400 · T-Max 100 · T-Max 400 ·
Foma Fomapan 100 · 200 · 400.

Rivelatori coperti: Rodinal/R09, Kodak D-76, Ilford ID-11, XTOL, HC-110,
Ilfotec DD-X, Ilfosol 3, Ilfotec HC, Ilfotec LC29, Microphen, Perceptol,
T-Max / T-Max RS, Fomadon LQN/Excel/P.

## Limiti noti (onestà sui dati)

- **I tempi sono punti di partenza.** I produttori stessi dicono di tararli su
  agitazione, acqua e gusto personale.
- **Temperatura: esatta dove c'è il dato, altrimenti stima.** Per Delta 100/400/3200,
  T-Max 100/400 e Tri-X uso i tempi reali a 24 °C dei datasheet, interpolati tra 20 e
  24 °C (l'app scrive "da datasheet"). Per le altre combinazioni uso la stima
  `tempo × 0,90^(T−20)` (scritta "stima"), arrotondata a 15 s. Nota: la vecchia stima
  unica sbagliava parecchio sulle pellicole T-grain (anche ~2 min su Delta 400) — ora
  è corretta dove esiste il dato reale.
- **Buchi voluti.** Alcune combinazioni non sono sui datasheet (es. Tri-X in
  Rodinal, o i tempi push numerici di T-Max): non vengono mostrate per non
  inventare numeri — l'app apre quella ricerca sul Massive Dev Chart.
- **Foma** pubblica intervalli (es. 9–10 min): l'app mostra il range e il timer
  parte dal minimo.

## Fonti dei dati

Datasheet ufficiali: ilfordphoto.com (Ilford/Kentmere/Harman),
Kodak F-4016 / F-4017 (Kodak Alaris), foma.cz (Foma). I link puntuali sono in
`build_data.py` (sezione `SOURCES`) e compaiono in ogni ricetta nell'app.
