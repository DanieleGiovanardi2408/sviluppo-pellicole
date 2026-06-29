#!/usr/bin/env python3
"""
Genera data.js a partire da tabelle compatte trascritte dai datasheet UFFICIALI.

Fonte di verita': le tabelle qui sotto. Ogni tempo e' scritto come "m:ss"
(o "m:ss-m:ss" per gli intervalli Foma) esattamente come convertito dal
datasheet (1/2 -> :30, 1/4 -> :15, 3/4 -> :45). Nessun valore inventato.

Per aggiungere/correggere una pellicola: modifica FILMS e rilancia
`python3 build_data.py`. Rigenera data.js.
"""
import json, re, datetime

# --- Sviluppatori (lista canonica, ordine di visualizzazione) ---------------
DEVELOPERS = [
    ("rodinal",       "Rodinal / Adonal / R09"),
    ("d76",           "Kodak D-76"),
    ("id11",          "Ilford ID-11"),
    ("xtol",          "Kodak XTOL"),
    ("hc110",         "Kodak HC-110"),
    ("ddx",           "Ilford Ilfotec DD-X"),
    ("ilfosol3",      "Ilford Ilfosol 3"),
    ("ilfotec-hc",    "Ilford Ilfotec HC"),
    ("ilfotec-lc29",  "Ilford Ilfotec LC29"),
    ("microphen",     "Ilford Microphen"),
    ("perceptol",     "Ilford Perceptol"),
    ("tmax-dev",      "Kodak T-Max Developer"),
    ("tmax-rs",       "Kodak T-Max RS"),
    ("fomadon-lqn",   "Foma Fomadon LQN"),
    ("fomadon-excel", "Foma Fomadon Excel"),
    ("fomadon-p",     "Foma Fomadon P"),
]

# --- Note di agitazione (dal datasheet) -------------------------------------
AGI = {
    "ilford": ("Agitazione intermittente (spirale): capovolgi la tank 4 volte nei "
               "primi 10 s, poi 4 volte nei primi 10 s di ogni minuto successivo."),
    "kodak":  ("Agitazione iniziale: 5-7 inversioni in 5 s. Poi ripeti l'agitazione "
               "ogni 30 s per tutta la durata."),
    "foma":   ("Agitazione continua nei primi 30 s, poi nei primi 10 s di ogni minuto."),
}

# --- Fonti (datasheet ufficiali) --------------------------------------------
SOURCES = {
    "hp5":        ("ILFORD HP5 PLUS - Technical Information (HARMAN, Nov 2018)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1903/product/691/"),
    "fp4":        ("ILFORD FP4 PLUS - Technical Information (HARMAN, Nov 2018)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1919/product/690/"),
    "delta100":   ("ILFORD DELTA 100 PROFESSIONAL - Technical Information (HARMAN)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/3/product/679/"),
    "delta400":   ("ILFORD DELTA 400 PROFESSIONAL - Technical Information (HARMAN, Nov 2018)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1915/product/684/"),
    "delta3200":  ("ILFORD DELTA 3200 PROFESSIONAL - Technical Information (HARMAN)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1913/product/682/"),
    "panf":       ("ILFORD PAN F PLUS - Technical Information (HARMAN)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1905/product/699/"),
    "kentmere100":("KENTMERE PAN 100 - Technical Information (HARMAN)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1958/product/2131/"),
    "kentmere400":("KENTMERE PAN 400 - Technical Information (HARMAN)",
                   "https://www.ilfordphoto.com/amfile/file/download/file/1959/product/697/"),
    "trix":       ("KODAK PROFESSIONAL TRI-X 400 - F-4017 (Kodak Alaris, 2016)",
                   "https://business.kodakmoments.com/sites/default/files/files/resources/f4017_TriX.pdf"),
    "tmax":       ("KODAK PROFESSIONAL T-MAX 100/400 - F-4016 (Kodak)",
                   "https://www.freestylephoto.com/static/pdf/product_pdfs/kodak/Kodak_TMAX_Films.pdf"),
    "foma100":    ("FOMAPAN 100 CLASSIC - Datasheet (FOMA)",
                   "https://www.digitaltruth.com/products/foma_tech/Fomapan_100.pdf"),
    "foma200":    ("FOMAPAN 200 CREATIVE - Datasheet (FOMA)",
                   "https://www.digitaltruth.com/products/foma_tech/Fomapan_200.pdf"),
    "foma400":    ("FOMAPAN 400 ACTION - Datasheet (FOMA)",
                   "https://www.fomafoto.com/div/teknisk/film/F_pan_400_en.pdf"),
}

# --- Reciprocita' (pose lunghe). power: Ta=Tm^p (Ilford/Kentmere).
#     table: [Tm,Ta] secondi (Kodak). foma: [Tm, fattore] (Ta=Tm*fattore).
RECIP = {
    "ilford-hp5-plus":   {"type": "power", "p": 1.31},
    "ilford-fp4-plus":   {"type": "power", "p": 1.26},
    "ilford-delta-100":  {"type": "power", "p": 1.26},
    "ilford-delta-400":  {"type": "power", "p": 1.41},
    "ilford-delta-3200": {"type": "power", "p": 1.33},
    "ilford-pan-f-plus": {"type": "power", "p": 1.33},
    "kentmere-pan-100":  {"type": "power", "p": 1.26},
    "kentmere-pan-400":  {"type": "power", "p": 1.30},
    "kodak-tri-x-400":   {"type": "table", "points": [[1, 2], [10, 50], [100, 1200]]},
    "kodak-tmax-400":    {"type": "table", "points": [[1, 1.26], [10, 15], [100, 300]]},
    "kodak-tmax-100":    {"type": "table", "points": [[1, 1.26], [10, 15], [100, 200]]},
    "foma-fomapan-100":  {"type": "foma", "points": [[1, 2], [10, 8], [100, 16]]},
    "foma-fomapan-200":  {"type": "foma", "points": [[1, 3], [10, 9], [100, 18]]},
    "foma-fomapan-400":  {"type": "foma", "points": [[1, 1.5], [10, 6], [100, 8]]},
}

# --- Tempi reali a 24 C (dove il datasheet li fornisce). Stesso formato delle righe 20 C.
ROWS24 = {
 "ilford-delta-400": [
   ("ddx","1+4",{200:"4:30",400:"5:30",500:"7:00",800:"7:30",1600:"9:30",3200:"13:00"}),
   ("ilfosol3","1+9",{200:"4:30",400:"6:00",800:"10:30"}),
   ("ilfosol3","1+14",{200:"6:00",400:"8:30",800:"15:30"}),
   ("ilfotec-hc","1+15",{800:"4:30",1600:"5:30",3200:"8:00"}),
   ("ilfotec-hc","1+31",{200:"4:00",400:"5:00",800:"7:00",1600:"10:00"}),
   ("ilfotec-lc29","1+9",{800:"4:30",1600:"5:30",3200:"8:00"}),
   ("ilfotec-lc29","1+19",{200:"4:00",400:"5:00",800:"7:00",1600:"10:00"}),
   ("ilfotec-lc29","1+29",{200:"5:30",400:"7:30",800:"11:00",1600:"16:00"}),
   ("id11","stock",{200:"5:30",400:"8:00",800:"9:00",1600:"11:30",3200:"15:00"}),
   ("id11","1+1",{200:"8:00",400:"11:30",800:"14:00",1600:"18:00"}),
   ("id11","1+3",{200:"14:00",400:"19:30"}),
   ("microphen","stock",{200:"4:00",400:"5:00",500:"6:00",800:"6:30",1600:"7:30",3200:"10:00"}),
   ("microphen","1+1",{200:"7:00",400:"9:00",500:"11:00",800:"12:00",1600:"15:30"}),
   ("microphen","1+3",{200:"11:30",400:"16:00",500:"20:00"}),
   ("perceptol","stock",{200:"7:00",250:"9:00"}),
   ("perceptol","1+1",{200:"9:00",320:"11:30"}),
   ("perceptol","1+3",{200:"14:30",320:"17:30"}),
   ("rodinal","1+25",{200:"5:00",400:"7:00",800:"16:00"}),
   ("rodinal","1+50",{200:"9:30",400:"16:00"}),
   ("d76","stock",{200:"5:30",400:"8:00",800:"9:00",1600:"11:30",3200:"15:00"}),
   ("d76","1+1",{200:"8:00",400:"11:30",800:"14:00",1600:"18:00"}),
   ("d76","1+3",{200:"14:00",400:"19:30"}),
   ("hc110","A",{800:"4:30",1600:"5:30",3200:"8:00"}),
   ("hc110","B",{200:"4:00",400:"5:00",800:"7:00",1600:"10:00"}),
   ("tmax-dev","1+4",{200:"4:00",400:"5:00",500:"5:30",800:"7:00",1600:"8:30",3200:"11:00"}),
   ("xtol","stock",{200:"4:00",400:"4:30",500:"6:00",800:"7:30",1600:"9:30",3200:"12:00"}),
   ("xtol","1+1",{200:"6:30",400:"8:30",500:"9:30",800:"11:30",1600:"14:00",3200:"18:00"}),
 ],
 "kodak-tri-x-400": [
   ("tmax-dev","stock",{400:"4:45",800:"4:45",1600:"7:00"}),
   ("tmax-rs","stock",{400:"3:30",800:"3:30",1600:"6:00",3200:"7:30"}),
   ("hc110","B",{400:"2:30",800:"2:30",1600:"4:15"}),
   ("d76","stock",{400:"4:45",800:"4:45",1600:"6:30",3200:"7:30"}),
   ("d76","1+1",{400:"7:45",800:"7:45",1600:"10:45",3200:"12:45"}),
   ("xtol","stock",{400:"4:45",800:"4:45",1600:"6:45",3200:"8:00"}),
   ("xtol","1+1",{400:"7:15",800:"7:15",1600:"10:30",3200:"12:15"}),
 ],
 "kodak-tmax-400": [
   ("d76","stock",{400:"5:30"}),
   ("d76","1+1",{400:"9:00"}),
   ("xtol","stock",{400:"4:30"}),
   ("xtol","1+1",{400:"7:00"}),
   ("hc110","B",{400:"4:30"}),
   ("tmax-dev","1+4",{400:"6:00"}),
 ],
 "kodak-tmax-100": [
   ("d76","stock",{100:"4:15"}),
   ("d76","1+1",{100:"6:15"}),
   ("xtol","stock",{100:"5:00"}),
   ("xtol","1+1",{100:"6:30"}),
   ("hc110","B",{100:"4:00"}),
   ("tmax-dev","1+4",{100:"6:15"}),
 ],
 "ilford-delta-3200": [
   ("ddx","1+4",{800:"5:00",1600:"6:00",3200:"7:00",6400:"9:00",12500:"12:00"}),
   ("id11","stock",{400:"6:00",800:"7:00",1600:"8:00",3200:"9:00",6400:"11:00",12500:"13:30"}),
   ("microphen","stock",{800:"5:00",1600:"6:00",3200:"7:00",6400:"9:30",12500:"13:30"}),
   ("ilfosol3","1+9",{400:"5:30",800:"7:00",1600:"8:00",3200:"9:00",6400:"15:30"}),
 ],
}

# --- Pellicole + tabelle tempi (20 C). Tuple riga: (dev, dilution, {EI:"m:ss"})
#     opzionale 4o elemento = formati specifici per quella riga.
FILMS = [
 {"id":"ilford-hp5-plus","brand":"Ilford","model":"HP5 Plus","box":400,
  "formats":["35mm","120"],"agi":"ilford","src":"hp5","rows":[
   ("ddx","1+4",{400:"9:00",800:"10:00",1600:"13:00",3200:"20:00"}),
   ("ilfosol3","1+9",{200:"5:00",400:"6:30",800:"13:30"}),
   ("ilfosol3","1+14",{200:"7:00",400:"11:00",800:"19:30"}),
   ("ilfotec-hc","1+15",{400:"3:30",800:"5:00",1600:"7:30",3200:"11:00"}),
   ("ilfotec-hc","1+31",{400:"6:30",800:"9:30",1600:"14:00"}),
   ("ilfotec-lc29","1+9",{400:"3:30",800:"5:00",1600:"7:30",3200:"11:00"}),
   ("ilfotec-lc29","1+19",{400:"6:30",800:"9:30",1600:"14:00"}),
   ("ilfotec-lc29","1+29",{400:"9:00"}),
   ("id11","stock",{400:"7:30",800:"10:30",1600:"14:00"}),
   ("id11","1+1",{400:"13:00",800:"16:30"}),
   ("id11","1+3",{400:"20:00"}),
   ("microphen","stock",{400:"6:30",800:"8:00",1600:"11:00",3200:"16:00"}),
   ("microphen","1+1",{400:"12:00",800:"15:00"}),
   ("microphen","1+3",{400:"23:00"}),
   ("perceptol","stock",{250:"13:00"}),
   ("perceptol","1+1",{320:"18:00"}),
   ("perceptol","1+3",{320:"25:00"}),
   ("rodinal","1+25",{400:"6:00",800:"8:00"}),
   ("rodinal","1+50",{400:"11:00"}),
   ("d76","stock",{400:"7:30",800:"9:30",1600:"12:30"}),
   ("d76","1+1",{400:"11:00",800:"13:00"}),
   ("d76","1+3",{400:"22:00"}),
   ("hc110","A",{400:"2:30",800:"3:45",1600:"5:30",3200:"9:30"}),
   ("hc110","B",{400:"5:00",800:"7:30",1600:"11:00"}),
   ("tmax-dev","1+4",{400:"6:30",800:"8:00",1600:"9:30",3200:"11:30"}),
   ("xtol","stock",{400:"8:00",800:"11:00",1600:"14:00",3200:"19:00"}),
   ("xtol","1+1",{400:"12:00",800:"17:00"}),
  ]},

 {"id":"ilford-fp4-plus","brand":"Ilford","model":"FP4 Plus","box":125,
  "formats":["35mm","120"],"agi":"ilford","src":"fp4","rows":[
   ("ddx","1+4",{50:"8:00",125:"10:00",200:"12:00"}),
   ("ilfosol3","1+9",{125:"4:15"}),
   ("ilfosol3","1+14",{125:"7:30"}),
   ("ilfotec-hc","1+15",{125:"4:00",200:"5:00"}),
   ("ilfotec-hc","1+31",{50:"6:00",125:"8:00",200:"9:00"}),
   ("ilfotec-lc29","1+9",{125:"4:00",200:"5:00"}),
   ("ilfotec-lc29","1+19",{50:"6:00",125:"8:00",200:"9:00"}),
   ("ilfotec-lc29","1+29",{50:"8:00",125:"12:00"}),
   ("id11","stock",{50:"6:30",125:"8:30",200:"10:00"}),
   ("id11","1+1",{50:"8:00",125:"11:00",200:"15:00"}),
   ("id11","1+3",{50:"17:00",125:"20:00"}),
   ("microphen","stock",{125:"8:00",200:"9:00"}),
   ("microphen","1+1",{125:"10:00",200:"14:00"}),
   ("microphen","1+3",{125:"14:00",200:"18:00"}),
   ("perceptol","stock",{50:"9:00",125:"12:00"}),
   ("perceptol","1+1",{50:"13:00",125:"15:00"}),
   ("perceptol","1+3",{50:"17:00",125:"21:00"}),
   ("rodinal","1+25",{125:"9:00",200:"13:00"}),
   ("rodinal","1+50",{125:"15:00",200:"20:00"}),
   ("d76","stock",{50:"6:00",125:"8:00",200:"9:00"}),
   ("d76","1+1",{50:"9:00",125:"11:00",200:"15:00"}),
   ("d76","1+3",{50:"14:00",125:"16:00",200:"20:00"}),
   ("hc110","A",{125:"4:30",200:"6:00"}),
   ("hc110","B",{50:"6:00",125:"9:00",200:"12:00"}),
   ("tmax-dev","1+4",{125:"8:00",200:"9:00"}),
   ("xtol","stock",{125:"8:30",200:"10:00"}),
  ]},

 {"id":"ilford-delta-100","brand":"Ilford","model":"Delta 100 Professional","box":100,
  "formats":["35mm","120"],"agi":"ilford","src":"delta100","rows":[
   ("ddx","1+4",{50:"8:00",100:"10:30",200:"12:30"}),
   ("ilfosol3","1+9",{100:"5:00"}),
   ("ilfosol3","1+14",{100:"7:30"}),
   ("ilfotec-hc","1+31",{50:"5:00",100:"6:00",200:"8:00"}),
   ("ilfotec-lc29","1+19",{50:"5:00",100:"6:00",200:"8:00"}),
   ("ilfotec-lc29","1+29",{50:"5:30",100:"7:30",200:"10:00"}),
   ("id11","stock",{50:"7:00",100:"8:30",200:"10:30"}),
   ("id11","1+1",{50:"10:00",100:"11:00",200:"13:00"}),
   ("id11","1+3",{50:"15:00",100:"20:00"}),
   ("microphen","stock",{100:"6:30",200:"8:00"}),
   ("microphen","1+1",{100:"10:00",200:"14:00"}),
   ("microphen","1+3",{100:"14:00",200:"20:00"}),
   ("perceptol","stock",{50:"12:00",100:"15:00"}),
   ("perceptol","1+1",{50:"13:00",100:"17:00"}),
   ("perceptol","1+3",{50:"16:00",100:"22:00"}),
   ("rodinal","1+25",{50:"7:00",100:"9:00"}),
   ("rodinal","1+50",{50:"10:00",100:"14:00"}),
   ("d76","stock",{50:"7:00",100:"9:00",200:"11:00"}),
   ("d76","1+1",{50:"9:30",100:"12:00",200:"14:00"}),
   ("d76","1+3",{50:"14:00",100:"22:00"}),
   ("hc110","B",{50:"5:00",100:"6:00",200:"8:00"}),
   ("tmax-dev","1+4",{50:"6:00",100:"7:00",200:"8:00"}),
   ("xtol","stock",{50:"6:30",100:"7:30",200:"9:30"}),
  ]},

 {"id":"ilford-delta-400","brand":"Ilford","model":"Delta 400 Professional","box":400,
  "formats":["35mm","120"],"agi":"ilford","src":"delta400","rows":[
   ("ddx","1+4",{200:"6:00",400:"8:00",500:"9:30",800:"10:30",1600:"13:30",3200:"18:00"}),
   ("ilfosol3","1+9",{200:"5:30",400:"7:00",800:"14:00"}),
   ("ilfosol3","1+14",{200:"8:00",400:"12:00",800:"20:30"}),
   ("ilfotec-hc","1+15",{320:"4:00",800:"5:30",1600:"7:30",3200:"13:00"}),
   ("ilfotec-hc","1+31",{200:"5:00",400:"7:30",800:"10:00",1600:"13:30"}),
   ("ilfotec-lc29","1+9",{320:"4:00",800:"5:30",1600:"7:30",3200:"13:00"}),
   ("ilfotec-lc29","1+19",{200:"5:00",400:"7:30",800:"10:00",1600:"13:30"}),
   ("ilfotec-lc29","1+29",{200:"8:30",400:"11:30",800:"17:00"}),
   ("id11","stock",{200:"7:00",400:"9:30",800:"11:30",1600:"14:30",3200:"19:00"}),
   ("id11","1+1",{200:"10:00",400:"14:00",800:"17:30"}),
   ("id11","1+3",{200:"18:00"}),
   ("microphen","stock",{200:"5:00",400:"6:30",500:"7:30",800:"8:30",1600:"10:30",3200:"14:00"}),
   ("microphen","1+1",{200:"8:30",400:"11:30",500:"13:30",800:"15:30",1600:"19:00"}),
   ("microphen","1+3",{200:"16:00"}),
   ("perceptol","stock",{200:"10:00",250:"12:00"}),
   ("perceptol","1+1",{200:"12:30",320:"15:30"}),
   ("perceptol","1+3",{200:"18:30"}),
   ("rodinal","1+25",{200:"6:00",400:"9:00"}),
   ("rodinal","1+50",{200:"11:30",400:"20:00"}),
   ("d76","stock",{200:"7:00",400:"9:30",800:"11:30",1600:"14:30",3200:"19:00"}),
   ("d76","1+1",{200:"10:00",400:"14:00",800:"17:30"}),
   ("d76","1+3",{200:"18:00"}),
   ("hc110","A",{320:"4:00",800:"5:30",1600:"7:30",3200:"13:00"}),
   ("hc110","B",{200:"5:00",400:"7:30",800:"10:00",1600:"13:30"}),
   ("tmax-dev","1+4",{200:"5:00",400:"6:30",500:"7:00",800:"8:30",1600:"10:30",3200:"13:30"}),
   ("xtol","stock",{200:"6:00",400:"7:30",500:"8:30",800:"10:00",1600:"13:00",3200:"17:00"}),
   ("xtol","1+1",{200:"9:00",400:"11:30",500:"13:00",800:"15:30",1600:"20:00"}),
  ]},

 {"id":"ilford-delta-3200","brand":"Ilford","model":"Delta 3200 Professional","box":3200,
  "formats":["35mm","120"],"agi":"ilford","src":"delta3200",
  "note":"ISO reale ~1000; classificata 3200. Pellicola pensata per essere esposta a EI alti.","rows":[
   ("ddx","1+4",{400:"6:00",800:"7:00",1600:"8:00",3200:"9:30",6400:"12:30",12500:"17:00"}),
   ("ilfosol3","1+9",{400:"6:00",800:"7:30",1600:"10:00",3200:"11:00",6400:"18:00"}),
   ("ilfosol3","1+14",{400:"11:00",800:"13:00",1600:"15:30",3200:"17:00",6400:"23:00"}),
   ("ilfotec-hc","1+15",{1600:"5:00",3200:"8:00",6400:"13:00"}),
   ("ilfotec-hc","1+31",{400:"6:00",800:"7:30",1600:"9:00",3200:"14:30"}),
   ("ilfotec-lc29","1+9",{1600:"5:00",3200:"8:00",6400:"13:00"}),
   ("ilfotec-lc29","1+19",{400:"6:00",800:"7:30",1600:"9:00",3200:"14:30"}),
   ("id11","stock",{400:"7:00",800:"8:00",1600:"9:30",3200:"10:30",6400:"13:00",12500:"17:00"}),
   ("microphen","stock",{400:"6:00",800:"7:00",1600:"8:00",3200:"9:00",6400:"12:00",12500:"16:30"}),
   ("perceptol","stock",{400:"11:00",800:"13:00",1600:"15:00",3200:"18:00"}),
  ]},

 {"id":"ilford-pan-f-plus","brand":"Ilford","model":"Pan F Plus","box":50,
  "formats":["35mm","120"],"agi":"ilford","src":"panf","rows":[
   ("ddx","1+4",{25:"7:00",50:"8:00"}),
   ("ilfosol3","1+14",{50:"4:30"}),
   ("ilfotec-hc","1+31",{50:"4:00"}),
   ("ilfotec-lc29","1+19",{50:"4:00"}),
   ("ilfotec-lc29","1+29",{50:"5:30"}),
   ("id11","stock",{25:"4:30",50:"6:30"}),
   ("id11","1+1",{25:"6:00",50:"8:30"}),
   ("id11","1+3",{25:"12:30",50:"15:00"}),
   ("microphen","stock",{50:"4:30",64:"6:00"}),
   ("microphen","1+1",{50:"6:00",64:"9:00"}),
   ("microphen","1+3",{50:"11:00",64:"14:30"}),
   ("perceptol","stock",{25:"9:00",50:"14:00"}),
   ("perceptol","1+1",{25:"10:30",50:"15:00"}),
   ("perceptol","1+3",{25:"15:00",50:"17:00"}),
   ("rodinal","1+25",{50:"6:00"}),
   ("rodinal","1+50",{50:"11:00"}),
   ("d76","stock",{25:"4:30",50:"6:30"}),
   ("d76","1+1",{25:"6:00",50:"8:30"}),
   ("d76","1+3",{25:"12:30",50:"15:00"}),
   ("hc110","B",{50:"4:00"}),
   ("tmax-dev","1+4",{50:"4:00"}),
   ("xtol","stock",{25:"5:30",50:"6:45"}),
  ]},

 {"id":"kentmere-pan-100","brand":"Kentmere","model":"Pan 100","box":100,
  "formats":["35mm","120"],"agi":"ilford","src":"kentmere100","rows":[
   ("ddx","1+4",{50:"8:30",100:"10:30",200:"12:30"}),
   ("ilfosol3","1+9",{100:"5:00"}),
   ("ilfosol3","1+14",{100:"7:30"}),
   ("ilfotec-hc","1+15",{100:"4:00",200:"5:00"}),
   ("ilfotec-hc","1+31",{50:"5:00",100:"6:30",200:"8:00"}),
   ("ilfotec-lc29","1+9",{100:"4:00",200:"5:00"}),
   ("ilfotec-lc29","1+19",{50:"5:30",100:"7:00",200:"8:00"}),
   ("ilfotec-lc29","1+29",{50:"7:30",100:"11:00"}),
   ("id11","stock",{50:"7:00",100:"9:00",200:"11:00"}),
   ("id11","1+1",{50:"8:30",100:"11:30",200:"15:30"}),
   ("id11","1+3",{50:"17:30",100:"21:00"}),
   ("microphen","stock",{100:"8:30",200:"9:00"}),
   ("microphen","1+1",{100:"10:30",200:"14:00"}),
   ("microphen","1+3",{100:"14:30"}),
   ("perceptol","stock",{50:"9:30",100:"12:30"}),
   ("perceptol","1+1",{50:"13:30",100:"15:30"}),
   ("d76","stock",{50:"7:00",100:"9:00",200:"11:00"}),
   ("d76","1+1",{50:"8:30",100:"11:30",200:"15:30"}),
   ("d76","1+3",{50:"17:30",100:"21:00"}),
  ]},

 {"id":"kentmere-pan-400","brand":"Kentmere","model":"Pan 400","box":400,
  "formats":["35mm","120"],"agi":"ilford","src":"kentmere400","rows":[
   ("ddx","1+4",{400:"11:30",800:"13:00"}),
   ("ilfosol3","1+9",{400:"6:30",800:"15:00"}),
   ("ilfosol3","1+14",{400:"11:00",800:"25:00"}),
   ("ilfotec-hc","1+15",{400:"4:30",800:"6:30"}),
   ("ilfotec-hc","1+31",{400:"8:00",800:"12:30"}),
   ("ilfotec-lc29","1+9",{400:"4:30",800:"6:30"}),
   ("ilfotec-lc29","1+19",{400:"8:00",800:"12:30"}),
   ("ilfotec-lc29","1+29",{400:"11:00"}),
   ("id11","stock",{400:"9:30",800:"13:00"}),
   ("id11","1+1",{400:"16:30",800:"20:30"}),
   ("id11","1+3",{400:"25:30"}),
   ("microphen","stock",{400:"8:00",800:"10:00"}),
   ("microphen","1+1",{400:"15:00",800:"19:00"}),
   ("perceptol","1+1",{320:"23:00"}),
   ("d76","stock",{400:"9:30",800:"12:30"}),
   ("d76","1+1",{400:"14:00",800:"17:00"}),
   ("d76","1+3",{400:"28:00"}),
  ]},

 {"id":"kodak-tri-x-400","brand":"Kodak","model":"Tri-X 400 (400TX)","box":400,
  "formats":["35mm","120"],"agi":"kodak","src":"trix",
  "note":"Tempi small tank. EI 800 (1 stop): il datasheet indica di usare i tempi nominali.","rows":[
   ("tmax-dev","stock",{400:"6:00",800:"6:00",1600:"8:45"}),
   ("tmax-rs","stock",{400:"4:30",800:"4:30",1600:"7:45",3200:"9:30"}),
   ("hc110","B",{400:"3:45",800:"3:45",1600:"6:00"}),
   ("d76","stock",{400:"6:45",800:"6:45",1600:"9:30",3200:"11:00"}),
   ("d76","1+1",{400:"9:45",800:"9:45",1600:"13:15",3200:"16:00"}),
   ("xtol","stock",{400:"7:00",800:"7:00",1600:"9:45",3200:"11:30"}),
   ("xtol","1+1",{400:"9:00",800:"9:00",1600:"13:15",3200:"15:30"}),
  ]},

 {"id":"kodak-tmax-400","brand":"Kodak","model":"T-Max 400 (TMY)","box":400,
  "formats":["35mm","120"],"agi":"kodak","src":"tmax","rows":[
   ("tmax-dev","1+4",{400:"7:00"}),
   ("tmax-rs","stock",{400:"7:00"}),
   ("xtol","stock",{400:"6:30"}),
   ("xtol","1+1",{400:"8:45"},["35mm"]),
   ("xtol","1+1",{400:"9:15"},["120"]),
   ("d76","stock",{400:"8:00"}),
   ("d76","1+1",{400:"12:30"}),
   ("hc110","B",{400:"6:00"}),
  ]},

 {"id":"kodak-tmax-100","brand":"Kodak","model":"T-Max 100 (TMX)","box":100,
  "formats":["35mm","120"],"agi":"kodak","src":"tmax","rows":[
   ("tmax-dev","1+4",{100:"7:30"}),
   ("tmax-rs","stock",{100:"8:00"}),
   ("xtol","stock",{100:"7:30"}),
   ("xtol","1+1",{100:"9:30"}),
   ("d76","stock",{100:"6:30"}),
   ("d76","1+1",{100:"9:30"}),
   ("hc110","B",{100:"6:00"}),
  ]},

 {"id":"foma-fomapan-100","brand":"Foma","model":"Fomapan 100 Classic","box":100,
  "formats":["35mm","120","sheet"],"agi":"foma","src":"foma100",
  "note":"Foma indica intervalli di tempo, non valori secchi.","rows":[
   ("fomadon-lqn","1+10",{100:"7:00-8:00"}),
   ("rodinal","1+40",{100:"6:00-7:00"}),
   ("fomadon-p","stock",{100:"7:00-8:00"}),
   ("fomadon-excel","stock",{100:"5:00-6:00"}),
   ("xtol","stock",{100:"5:00-6:00"}),
   ("microphen","stock",{100:"5:00-7:00"}),
   ("perceptol","stock",{100:"8:00"}),
   ("d76","stock",{100:"6:00-7:00"}),
   ("id11","stock",{100:"6:00-7:00"}),
  ]},

 {"id":"foma-fomapan-200","brand":"Foma","model":"Fomapan 200 Creative","box":200,
  "formats":["35mm","120","sheet"],"agi":"foma","src":"foma200",
  "note":"Foma indica intervalli di tempo, non valori secchi.","rows":[
   ("fomadon-lqn","1+10",{200:"5:00-6:00"}),
   ("rodinal","1+40",{200:"8:00-9:00"}),
   ("fomadon-p","stock",{200:"5:00-6:00"}),
   ("fomadon-excel","stock",{200:"6:00"}),
   ("xtol","stock",{200:"6:00"}),
   ("microphen","stock",{200:"5:00-6:00"}),
   ("perceptol","stock",{200:"5:00-6:00"}),
   ("d76","stock",{200:"5:00-6:00"}),
   ("id11","stock",{200:"5:00-6:00"}),
  ]},

 {"id":"foma-fomapan-400","brand":"Foma","model":"Fomapan 400 Action","box":400,
  "formats":["35mm","120","sheet"],"agi":"foma","src":"foma400",
  "note":"Foma indica intervalli di tempo, non valori secchi.","rows":[
   ("fomadon-lqn","1+10",{400:"9:00-10:00"}),
   ("rodinal","1+40",{400:"9:00-10:00"}),
   ("fomadon-p","stock",{400:"10:00-11:00"}),
   ("fomadon-excel","stock",{400:"7:00"}),
   ("xtol","stock",{400:"7:00"}),
   ("microphen","stock",{400:"8:00-9:00"}),
   ("perceptol","stock",{400:"9:00-10:00"}),
   ("d76","stock",{400:"7:00-8:00"}),
   ("id11","stock",{400:"7:00-8:00"}),
  ]},
]

# --- Parsing -----------------------------------------------------------------
def to_sec(tok):
    m = re.match(r"^(\d+):([0-5]\d)$", tok)
    if not m:
        raise ValueError("formato tempo non valido: %r" % tok)
    return int(m.group(1)) * 60 + int(m.group(2))

def parse_time(tok):
    if "-" in tok:
        a, b = tok.split("-")
        return to_sec(a), to_sec(b)
    return to_sec(tok), None

def main():
    dev_ids = {d[0] for d in DEVELOPERS}
    dict24 = {}
    for fid, rows in ROWS24.items():
        for row in rows:
            dev24, dil24, times24 = row[0], row[1], row[2]
            for ei24, tok24 in times24.items():
                dict24[(fid, dev24, dil24, ei24)] = parse_time(tok24)[0]
    recipes = []
    rid = 0
    n24 = 0
    for f in FILMS:
        for row in f["rows"]:
            dev, dil, times = row[0], row[1], row[2]
            row_formats = row[3] if len(row) > 3 else f["formats"]
            if dev not in dev_ids:
                raise ValueError("developer sconosciuto %r in %s" % (dev, f["id"]))
            for ei, tok in times.items():
                lo, hi = parse_time(tok)
                rec = {
                    "id": rid, "film": f["id"], "dev": dev, "dilution": dil,
                    "formats": row_formats, "ei": ei,
                    "sec": lo, "secMax": hi, "agi": f["agi"], "src": f["src"],
                }
                s24 = dict24.get((f["id"], dev, dil, ei))
                if s24 is not None:
                    rec["sec24"] = s24
                    n24 += 1
                recipes.append(rec)
                rid += 1
    films_out = [{"id":f["id"],"brand":f["brand"],"model":f["model"],
                  "box":f["box"],"formats":f["formats"],
                  "note":f.get("note",""),"recip":RECIP.get(f["id"])} for f in FILMS]
    db = {
        "meta": {
            "version": 1,
            "generated": datetime.date.today().isoformat(),
            "tempCoeff": 0.90,     # tempo *= coeff^(T-20); validato su datasheet Kodak/Ilford
            "tempMin": 18, "tempMax": 24, "roundSec": 15,
            "filmCount": len(films_out), "recipeCount": len(recipes),
        },
        "films": films_out,
        "developers": [{"id":i,"name":n} for i,n in DEVELOPERS],
        "agitation": AGI,
        "sources": {k:{"title":t,"url":u} for k,(t,u) in SOURCES.items()},
        "recipes": recipes,
    }
    js = "// GENERATO da build_data.py - NON modificare a mano.\n"
    js += "// Tempi trascritti dai datasheet ufficiali (vedi 'sources').\n"
    js += "window.DB = " + json.dumps(db, ensure_ascii=False, indent=1) + ";\n"
    with open("data.js", "w", encoding="utf-8") as fh:
        fh.write(js)
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1)
    print("OK: %d pellicole, %d ricette, %d sviluppatori, %d con tempo 24C"
          % (len(films_out), len(recipes), len(DEVELOPERS), n24))

if __name__ == "__main__":
    main()
