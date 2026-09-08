import re, json, datetime, unicodedata

RAW = "/home/claude/pa/pa-raw.txt"
OUT = "/home/claude/pa/plateformes-agreees.ts"

COUNTRIES = {"Italie","Belgique","Suède","Espagne","Allemagne","Finlande","Pologne","Irlande","Danemark","Pays-Bas","Slovénie","Portugal","Chypre","Australie","Luxembourg"}

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

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+","-", s).strip("-").lower()
    return s

def excel_date(serial):
    return (datetime.date(1899,12,30) + datetime.timedelta(days=int(serial))).isoformat()

entries = []
seen = set()
for line in open(RAW, encoding="utf-8"):
    line = line.rstrip("\n")
    if not line.strip(): continue
    parts = [p.strip() for p in line.split(" ¦ ")]
    while len(parts) < 8: parts.append("")
    lst, name, voie, cp, commune, site, mail, dt = parts[:8]
    status = "definitive" if lst == "L1" else "pending"
    if commune in COUNTRIES or commune.endswith("(Finlande)"):
        country = "Finlande" if commune.endswith("(Finlande)") else commune
        city = FOREIGN_CITY[name]
    else:
        country = "France"
        city = FRENCH_CITY_FIX.get(commune, commune)
    sid = slug(name)
    if sid in seen: raise SystemExit("slug en double : "+sid)
    seen.add(sid)
    e = {"id": sid, "name": name, "status": status}
    if dt: e["registeredAt"] = excel_date(dt)
    e["address"] = voie
    if country == "France" and cp.isdigit() and len(cp) < 5:
        cp = cp.zfill(5)  # zéro initial perdu par le tableur (2100 -> 02100)
    if cp and cp != "/": e["postalCode"] = cp
    e["city"] = city
    e["country"] = country
    e["website"] = site
    if name in SOLUTION_BY_NAME: e["solutionId"] = SOLUTION_BY_NAME[name]
    entries.append(e)

assert len(entries) == 165, len(entries)
assert sum(e["status"]=="definitive" for e in entries) == 149
assert all("registeredAt" in e for e in entries if e["status"]=="definitive")
assert all("registeredAt" not in e for e in entries if e["status"]=="pending")

def ts(v):
    return json.dumps(v, ensure_ascii=False)

lines = []
for e in entries:
    fields = [f"id: {ts(e['id'])}", f"name: {ts(e['name'])}", f"status: {ts(e['status'])}"]
    if "registeredAt" in e: fields.append(f"registeredAt: {ts(e['registeredAt'])}")
    fields.append(f"address: {ts(e['address'])}")
    if "postalCode" in e: fields.append(f"postalCode: {ts(e['postalCode'])}")
    fields += [f"city: {ts(e['city'])}", f"country: {ts(e['country'])}", f"website: {ts(e['website'])}"]
    if "solutionId" in e: fields.append(f"solutionId: {ts(e['solutionId'])}")
    lines.append("  { " + ", ".join(fields) + " },")

header = '''import type { SolutionId } from "@/lib/solutions";

// Registre des plateformes agréées (PA, anciennement PDP) publié par la DGFiP.
// Source unique : https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees
// Les deux fichiers officiels (XLSX) ont été relus le 7 septembre 2026, jour de leur dernière
// modification annoncée sur la page. Chaque ligne reprend le nom commercial, l'adresse de
// l'établissement principal, le site internet et, pour la première liste, la date de délivrance
// du numéro d'immatriculation, tels qu'ils figurent dans le fichier de l'administration.
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
  publishedAt: "2026-09-07",
  /** Date de la relecture des fichiers officiels par FactureMatch. */
  checkedAt: "2026-09-07",
  checkedAtLabel: "7 septembre 2026",
} as const;

export const approvedPlatforms: ApprovedPlatform[] = [
'''

footer = '''];

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

open(OUT, "w", encoding="utf-8").write(header + "\n".join(lines) + "\n" + footer)
c = {"total":len(entries),"def":sum(e["status"]=="definitive" for e in entries),"fr":sum(e["country"]=="France" for e in entries)}
print(c)
print(sorted({e["country"] for e in entries}))
print(max(e.get("registeredAt","") for e in entries), min(e.get("registeredAt","9") for e in entries))
