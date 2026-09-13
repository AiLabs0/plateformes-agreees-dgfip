#!/usr/bin/env python3
"""Régénère les données du registre DGFiP des plateformes agréées pour un relevé daté.

Sources acceptées, au choix :
  - les deux PDF officiels (immatriculées, en attente) : --pdf-immatriculees / --pdf-attente,
    ou --telecharger pour les récupérer directement sur impots.gouv.fr ;
  - les deux XLSX officiels : --xlsx-immatriculees / --xlsx-attente (nécessite openpyxl) ;
  - une extraction brute déjà produite (fichier registre-dgfip-<date>-brut.txt) : --brut.

Sorties, dans le dossier courant (ou --sortie) :
  registre-dgfip-<date>-brut.txt        extraction brute, une ligne par plateforme, colonnes « ¦ »
  plateformes-agreees-dgfip-<date>.csv  le registre (UTF-8 avec BOM, séparateur « ; », CRLF)
  et, avec --ts, le module TypeScript utilisé par l'annuaire FactureMatch.

Exemple :
  python3 generer-donnees.py --date 2026-09-13 --telecharger --effectifs 148,14
"""
import argparse, csv, datetime, io, json, os, re, sys, unicodedata, urllib.request

URL_PAGE = "https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees"
URL_BASE = ("https://www.impots.gouv.fr/sites/default/files/media/1_metier/2_professionnel/EV/2_gestion/"
            "290_facturation_electronique/listes_plateformes_agreees/")
URL_PDF = {"L1": URL_BASE + "liste_pa_attente_rapport_audit.pdf", "L2": URL_BASE + "liste_pa_attente_test_interop.pdf"}

STATUT = {"L1": "immatriculation definitive", "L2": "dossier complet, en attente des tests d interoperabilite"}
COLONNES_CSV = ["liste", "statut", "nom_commercial", "date_delivrance_immatriculation",
                "adresse_voie", "code_postal", "commune_ou_pays", "site_internet"]

# ---------------------------------------------------------------- lecture des sources

def lire_pdf(chemin, liste):
    """Lit un PDF officiel : une ligne par plateforme, 7 colonnes (6 pour la liste d'attente).

    Le PDF est une impression du tableur : les textes trop longs débordent de leur cellule et les
    cellules de plusieurs lignes dépassent de leur rangée. On ne s'appuie donc pas sur le découpage
    en cellules de pdfplumber mais sur les chaînes de texte telles qu'elles sont dessinées, affectées
    à une colonne par leur abscisse de départ et à une rangée par le centre vertical du bloc de lignes
    (le tableur centre verticalement le contenu de chaque cellule).
    """
    import pdfplumber
    ncols = 7 if liste == "L1" else 6
    lignes = []
    with pdfplumber.open(chemin) as pdf:
        for page in pdf.pages:
            table = page.find_tables()[0]
            xs = sorted({round(c[0], 1) for c in table.cells}) + [max(c[2] for c in table.cells)]
            if len(xs) != ncols + 1:
                raise SystemExit(f"{chemin} : {len(xs) - 1} colonnes trouvées, {ncols} attendues")
            bandes = [(r.bbox[1], r.bbox[3]) for r in table.rows]
            # chaînes de texte (une par opérateur Tj du PDF, reconstituées caractère par caractère)
            runs, cur = [], None
            for c in page.chars:
                if cur and abs(c["top"] - cur["top"]) < 1 and abs(c["x0"] - cur["x1"]) < 1.5 and c["fontname"] == cur["fontname"]:
                    cur["text"] += c["text"]; cur["x1"] = c["x1"]
                else:
                    cur = {"text": c["text"], "x0": c["x0"], "x1": c["x1"], "top": c["top"], "bottom": c["bottom"], "fontname": c["fontname"]}
                    runs.append(cur)
            runs = [r for r in runs if r["text"].strip()]
            # rangées d'en-tête : celles qui contiennent les libellés officiels
            entetes = set()
            for r in runs:
                if r["text"].strip() in ("Nom commercial", "Voie", "Code postal", "Site internet"):
                    yc = (r["top"] + r["bottom"]) / 2
                    entetes.update(i for i, (a, b) in enumerate(bandes) if a <= yc < b)
            debut = max(entetes) + 1 if entetes else 0
            y_min = bandes[debut - 1][1] if debut else bandes[0][0]  # bas de la dernière rangée d'en-tête
            bandes = bandes[debut:]
            if not bandes:
                continue
            # lignes de texte par colonne (les chaînes d'une même ligne sont réunies)
            colonnes = [[] for _ in range(ncols)]
            for r in sorted(runs, key=lambda r: (round(r["top"]), r["x0"])):
                if (r["top"] + r["bottom"]) / 2 < y_min:
                    continue  # en-tête du tableau
                ci = next((i for i in range(ncols) if xs[i] <= r["x0"] < xs[i + 1]), None)
                if ci is None:
                    raise SystemExit(f"{chemin} : texte hors tableau « {r['text']} »")
                lig = colonnes[ci]
                if lig and abs(lig[-1]["top"] - r["top"]) < 1:
                    lig[-1]["text"] += " " + r["text"].strip(); lig[-1]["bottom"] = max(lig[-1]["bottom"], r["bottom"])
                else:
                    lig.append({"text": r["text"].strip(), "top": r["top"], "bottom": r["bottom"]})
            # affectation des lignes de texte aux rangées : bloc centré sur la rangée
            cellules = [["" for _ in range(ncols)] for _ in bandes]
            for ci, lig in enumerate(colonnes):
                i = 0
                for ri, (a, b) in enumerate(bandes):
                    centre = (a + b) / 2
                    meilleur, k_best = 4.0, 0
                    for k in range(1, 5):
                        if i + k > len(lig):
                            break
                        bloc_centre = (lig[i]["top"] + lig[i + k - 1]["bottom"]) / 2
                        if abs(bloc_centre - centre) < meilleur:
                            meilleur, k_best = abs(bloc_centre - centre), k
                    if k_best:
                        cellules[ri][ci] = " ".join(l["text"] for l in lig[i:i + k_best])
                        i += k_best
                if i != len(lig):
                    raise SystemExit(f"{chemin} : {len(lig) - i} ligne(s) de texte non affectée(s) en colonne {ci} : {lig[i]['text']!r}")
            for row in cellules:
                if row[0]:
                    lignes.append([liste] + row + ([""] if ncols == 6 else []))
    return lignes


def lire_xlsx(chemin, liste):
    import openpyxl
    ws = openpyxl.load_workbook(chemin, data_only=True).worksheets[0]
    lignes = []
    for r in ws.iter_rows(values_only=True):
        if r[0] is None or str(r[0]).strip() == "Nom commercial":
            continue
        cells = []
        for v in list(r[:7]) + [None] * (7 - len(r[:7])):
            if isinstance(v, datetime.datetime):
                v = str((v.date() - datetime.date(1899, 12, 30)).days)  # numéro de série du tableur
            cells.append("" if v is None else str(v).strip())
        lignes.append([liste] + cells[:6] + [cells[6] if liste == "L1" else ""])
    return lignes


def lire_brut(chemin):
    lignes = []
    for line in open(chemin, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = [p.strip() for p in line.rstrip(" ¦").split(" ¦ ")]
        while len(parts) < 8:
            parts.append("")
        lignes.append(parts[:8])
    return lignes


def telecharger(url, dest):
    with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest

# ---------------------------------------------------------------- normalisation

def date_iso(v):
    """Date du registre en ISO : numéro de série du tableur (46224) ou jj/mm/aa du PDF (21/07/26)."""
    v = v.strip()
    if not v:
        return ""
    if v.isdigit():
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))).isoformat()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{2}|\d{4})", v)
    if not m:
        raise SystemExit(f"date non reconnue : {v!r}")
    j, mo, a = m.groups()
    return f"{int(a) + 2000 if len(a) == 2 else int(a)}-{mo}-{j}"


COUNTRIES = {"Italie", "Belgique", "Suède", "Espagne", "Allemagne", "Finlande", "Pologne", "Irlande", "Danemark",
             "Pays-Bas", "Slovénie", "Portugal", "Chypre", "Australie", "Luxembourg"}


def est_en_france(commune):
    return not (commune in COUNTRIES or commune.endswith("(Finlande)"))


def code_postal_csv(cp, commune):
    if cp == "/":
        return ""
    if est_en_france(commune) and cp.isdigit() and len(cp) < 5:
        return cp.zfill(5)  # zéro initial perdu par le tableur (2100 -> 02100)
    return cp


def lignes_csv(brut):
    rows = []
    for lst, name, voie, cp, commune, site, _mail, dt in brut:
        rows.append(["1" if lst == "L1" else "2", STATUT[lst], name, date_iso(dt), voie, code_postal_csv(cp, commune), commune, site])
    rows.sort(key=lambda r: (r[0], r[2].lower()))
    return rows

# ---------------------------------------------------------------- module TypeScript (annuaire)

# Ville affichée pour les sièges hors de France (la colonne « Commune » du fichier officiel
# contient alors le pays ; la ville figure dans la colonne « Voie »).
FOREIGN_CITY = {
 "A-Cube":"Milan","ADEMICO SOFTWARE":"Louvain","Arratech":"Stockholm","Aruba S.p.A.":"Ponte San Pietro",
 "B2BRouter":"Barcelone","B4VALUE.NET":"Kaiserslautern","BASWARE":"Espoo","BILLIT":"Gand",
 "CBS Corporate Business Solutions":"Heidelberg","COMARCH SA":"Cracovie","DIGITAL TECHNOLOGIES":"Milan",
 "Docnova, MELASOFT GmbH":"Francfort","DOKAPI":"Malines","ecosio InterCom, a Vertex Company":"Munich",
 "EDICOM Group":"Valence (Paterna)","Fonoa Technologies Limited":"Dublin","GEP":"Espoo","GURUSOFT":"Madrid",
 "iEDI ApS":"Espergærde","INDICOM":"Milan","In.Te.S.A. spa":"Turin","INVOPOP":"Madrid",
 "Legalinvoice by Tinexta Infocert":"Rome","MAROSA":"Vigo","MySupply Aps":"Nørresundby",
 "NTT DATA Business Solutions":"Bautzen","ODOO":"Grand-Rosière","OPENTEXT":"Hoofddorp","PAGERO":"Göteborg",
 "SAP":"Walldorf","SEEBURGER":"Bretten","Shine":"Copenhague","SNI":"Ljubljana","SOLO":"Stockholm",
 "SOVOS":"Lisbonne","SPS COMMERCE":"Breukelen","STORECOVE":"Hilversum","TESISQUARE SPA":"Bra",
 "TRADESHIFT BABELWAY":"Ottignies-Louvain-la-Neuve","Transalis Limited":"Nicosie",
 "VOXEL, an Amadeus company":"Barcelone","WiseTech GLOBAL":"Alexandria (Sydney)",
 "BE FRESH S.à r.l.":"Kockelscheuer","EAGLESSOFT":"Zaventem","Insiders Technologies GmbH":"Kaiserslautern",
 "Taxilla Europe BV":"Bruxelles","YUMAN":"Bruxelles",
}

# Corrections d'affichage de la colonne « Commune » (casse et coquilles du fichier officiel).
FRENCH_CITY_FIX = {
 "LYON":"Lyon","MARSEILLE":"Marseille","SaintGermain-en-Laye":"Saint-Germain-en-Laye",
 "Lyon Cedex 09":"Lyon","Paris La Défense Cedex":"Paris La Défense","Saint Quentin":"Saint-Quentin",
 "Epagny Metz-Tessy":"Épagny Metz-Tessy",
}

SOLUTION_BY_NAME = {"INDY":"indy","PENNYLANE":"pennylane","QONTO":"qonto","TIIME PDP":"tiime","AXONAUT":"axonaut","ODOO":"odoo"}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()


def ecrire_ts(brut, date, chemin):
    entries, seen = [], set()
    for lst, name, voie, cp, commune, site, _mail, dt in brut:
        status = "definitive" if lst == "L1" else "pending"
        if est_en_france(commune):
            country, city = "France", FRENCH_CITY_FIX.get(commune, commune)
        else:
            country = "Finlande" if commune.endswith("(Finlande)") else commune
            city = FOREIGN_CITY[name]
        sid = slug(name)
        if sid in seen:
            raise SystemExit("slug en double : " + sid)
        seen.add(sid)
        e = {"id": sid, "name": name, "status": status}
        if dt:
            e["registeredAt"] = date_iso(dt)
        e["address"] = voie
        cp = code_postal_csv(cp, commune)
        if cp:
            e["postalCode"] = cp
        e.update(city=city, country=country, website=site)
        if name in SOLUTION_BY_NAME:
            e["solutionId"] = SOLUTION_BY_NAME[name]
        entries.append(e)
    assert all(("registeredAt" in e) == (e["status"] == "definitive") for e in entries)

    ts = lambda v: json.dumps(v, ensure_ascii=False)
    lines = []
    for e in entries:
        fields = [f"id: {ts(e['id'])}", f"name: {ts(e['name'])}", f"status: {ts(e['status'])}"]
        if "registeredAt" in e: fields.append(f"registeredAt: {ts(e['registeredAt'])}")
        fields.append(f"address: {ts(e['address'])}")
        if "postalCode" in e: fields.append(f"postalCode: {ts(e['postalCode'])}")
        fields += [f"city: {ts(e['city'])}", f"country: {ts(e['country'])}", f"website: {ts(e['website'])}"]
        if "solutionId" in e: fields.append(f"solutionId: {ts(e['solutionId'])}")
        lines.append("  { " + ", ".join(fields) + " },")
    d = datetime.date.fromisoformat(date)
    label = f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"
    header = TS_HEADER.replace("__DATE__", date).replace("__LABEL__", label)
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n" + TS_FOOTER)


TS_HEADER = '''import type { SolutionId } from "@/lib/solutions";

// Registre des plateformes agréées (PA, anciennement PDP) publié par la DGFiP.
// Source unique : https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees
// Les deux fichiers officiels ont été relus le __LABEL__. Chaque ligne reprend le nom commercial,
// l'adresse de l'établissement principal, le site internet et, pour la première liste, la date de
// délivrance du numéro d'immatriculation, tels qu'ils figurent dans le fichier de l'administration.
//
// Ce que ce fichier ne contient pas, volontairement :
// - les courriels de contact du registre (plusieurs sont des adresses nominatives) ;
// - toute note, tarif ou appréciation : l'annuaire reproduit le registre, il ne le complète pas.
//
// Seules retouches d'affichage, documentées ici : la casse de quelques communes (LYON, MARSEILLE),
// les libellés postaux (Cedex), une coquille (SaintGermain-en-Laye) et deux codes postaux dont le
// tableur avait perdu le zéro initial (02100, 06200) ; pour les sièges hors de
// France, la ville est reprise de la colonne « Voie » du fichier officiel, en français (Milan,
// Bruxelles…). L'adresse complète reste celle du registre, sans modification.

export type PlatformStatus = "definitive" | "pending";

export type ApprovedPlatform = {
  id: string;
  /** Nom commercial tel qu'il figure dans le registre. */
  name: string;
  /** definitive : immatriculation définitive délivrée ; pending : dossier complet, en attente des tests d'interopérabilité. */
  status: PlatformStatus;
  /** Date de délivrance du numéro d'immatriculation (ISO), uniquement pour les immatriculations définitives. */
  registeredAt?: string;
  address: string;
  postalCode?: string;
  city: string;
  country: string;
  website: string;
  /** Fiche FactureMatch lorsque la plateforme fait partie des solutions comparées. */
  solutionId?: SolutionId;
};

export const approvedPlatformsRegister = {
  publisher: "Direction générale des Finances publiques (DGFiP)",
  pageUrl: "https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees",
  definitiveListLabel: "Liste des opérateurs satisfaisant à l'ensemble des conditions, incluant les tests d'interopérabilité",
  pendingListLabel: "Liste des opérateurs ayant déposé un dossier complet et conforme et en attente de leur immatriculation définitive conditionnée à la réussite des tests d'interopérabilité",
  /** Date de modification affichée sur la page officielle lors de la relecture. */
  publishedAt: "__DATE__",
  /** Date de la relecture des fichiers officiels par FactureMatch. */
  checkedAt: "__DATE__",
  checkedAtLabel: "__LABEL__",
} as const;

export const approvedPlatforms: ApprovedPlatform[] = [
'''

TS_FOOTER = '''];

export const definitivePlatforms = approvedPlatforms.filter((platform) => platform.status === "definitive");
export const pendingPlatforms = approvedPlatforms.filter((platform) => platform.status === "pending");

export const approvedPlatformById = (id: string) => approvedPlatforms.find((platform) => platform.id === id);

export const approvedPlatformBySolutionId = (solutionId: SolutionId) =>
  approvedPlatforms.find((platform) => platform.solutionId === solutionId);

export function countApprovedPlatforms(platforms: ApprovedPlatform[] = approvedPlatforms) {
  return {
    total: platforms.length,
    definitive: platforms.filter((platform) => platform.status === "definitive").length,
    pending: platforms.filter((platform) => platform.status === "pending").length,
    france: platforms.filter((platform) => platform.country === "France").length,
    abroad: platforms.filter((platform) => platform.country !== "France").length,
  };
}

export function listPlatformCountries(platforms: ApprovedPlatform[] = approvedPlatforms) {
  return [...new Set(platforms.map((platform) => platform.country))].sort((a, b) => a.localeCompare(b, "fr"));
}

/** Dernière date de délivrance d'immatriculation présente dans le registre (ISO). */
export function latestRegistrationDate(platforms: ApprovedPlatform[] = approvedPlatforms) {
  const dates = platforms.map((platform) => platform.registeredAt ?? "").filter(Boolean).sort();
  return dates[dates.length - 1] ?? "";
}

const monthNames = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];

/** « 28 août 2026 » à partir d'une date ISO, sans dépendre du fuseau horaire du serveur. */
export function formatFrenchDate(isoDate: string) {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  return `${day === 1 ? "1er" : day} ${monthNames[month - 1]} ${year}`;
}

/** Nom lisible pour la recherche : sans accents ni ponctuation, en minuscules. */
export function normalizeForSearch(value: string) {
  return value.normalize("NFD").replace(/[\\u0300-\\u036f]/g, "").replace(/[^a-z0-9]+/gi, " ").trim().toLowerCase();
}
'''

# ---------------------------------------------------------------- programme

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", required=True, help="date du relevé, AAAA-MM-JJ (nom des fichiers produits)")
    src = ap.add_argument_group("source (une seule)")
    src.add_argument("--telecharger", action="store_true", help="télécharge les deux PDF officiels dans le dossier de sortie")
    src.add_argument("--pdf-immatriculees"); src.add_argument("--pdf-attente")
    src.add_argument("--xlsx-immatriculees"); src.add_argument("--xlsx-attente")
    src.add_argument("--brut", help="extraction brute existante (registre-dgfip-<date>-brut.txt)")
    ap.add_argument("--sortie", default=".", help="dossier de sortie (défaut : dossier courant)")
    ap.add_argument("--ts", help="écrit aussi le module TypeScript de l'annuaire à ce chemin")
    ap.add_argument("--effectifs", help="contrôle attendu « immatriculées,en attente », ex. 148,14")
    a = ap.parse_args()
    datetime.date.fromisoformat(a.date)
    os.makedirs(a.sortie, exist_ok=True)

    if a.telecharger:
        a.pdf_immatriculees = telecharger(URL_PDF["L1"], os.path.join(a.sortie, f"liste_pa_attente_rapport_audit-{a.date}.pdf"))
        a.pdf_attente = telecharger(URL_PDF["L2"], os.path.join(a.sortie, f"liste_pa_attente_test_interop-{a.date}.pdf"))
    if a.pdf_immatriculees and a.pdf_attente:
        brut = lire_pdf(a.pdf_immatriculees, "L1") + lire_pdf(a.pdf_attente, "L2")
    elif a.xlsx_immatriculees and a.xlsx_attente:
        brut = lire_xlsx(a.xlsx_immatriculees, "L1") + lire_xlsx(a.xlsx_attente, "L2")
    elif a.brut:
        brut = lire_brut(a.brut)
    else:
        ap.error("indiquer une source : --telecharger, --pdf-* (les deux), --xlsx-* (les deux) ou --brut")

    n1 = sum(l[0] == "L1" for l in brut); n2 = len(brut) - n1
    if a.effectifs:
        e1, e2 = (int(x) for x in a.effectifs.split(","))
        if (n1, n2) != (e1, e2):
            raise SystemExit(f"effectifs lus {n1} + {n2}, attendus {e1} + {e2}")
    if any(not l[7] for l in brut if l[0] == "L1") or any(l[7] for l in brut if l[0] == "L2"):
        raise SystemExit("date de délivrance manquante sur une immatriculée, ou présente sur une plateforme en attente")

    chemin_brut = os.path.join(a.sortie, f"registre-dgfip-{a.date}-brut.txt")
    if not (a.brut and os.path.abspath(a.brut) == os.path.abspath(chemin_brut)):
        with open(chemin_brut, "w", encoding="utf-8") as f:
            for l in brut:
                f.write(" ¦ ".join(l).rstrip(" ") + "\n")

    chemin_csv = os.path.join(a.sortie, f"plateformes-agreees-dgfip-{a.date}.csv")
    with open(chemin_csv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\r\n")
        w.writerow(COLONNES_CSV)
        w.writerows(lignes_csv(brut))

    if a.ts:
        ecrire_ts(brut, a.date, a.ts)
    print(f"{n1} immatriculées + {n2} en attente = {len(brut)} plateformes -> {chemin_csv}")


if __name__ == "__main__":
    main()
