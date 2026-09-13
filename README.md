# Plateformes agréées (PA, ex-PDP) pour la facturation électronique — registre DGFiP

Copie fidèle, en CSV, des deux listes publiées par la Direction générale des Finances publiques sur impots.gouv.fr, page « Je consulte la liste des plateformes agréées » : https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees

- **Relevé en cours :** 13 septembre 2026 (page officielle « modifiée le 10/09/2026 »).
- **Contenu :** 148 opérateurs satisfaisant à l'ensemble des conditions, tests d'interopérabilité compris (immatriculation définitive, datée), et 14 opérateurs ayant déposé un dossier complet et conforme, en attente de leur immatriculation définitive, soit 162 plateformes.
- **Colonnes :** liste (1 = immatriculation définitive, 2 = en attente), statut, nom commercial, date de délivrance du numéro d'immatriculation, adresse de l'établissement principal (voie, code postal, commune ou pays), site internet.
- **Ce qui n'est pas repris :** les courriels de contact du registre (plusieurs sont des adresses nominatives). Aucune donnée ajoutée, aucune note, aucun tarif.
- **Retouches documentées :** deux codes postaux ayant perdu leur zéro initial dans le tableur d'origine (02100, 06200) sont complétés ; le code postal « / » des sièges sans code postal est laissé vide. Tout le reste (casse des communes, libellés postaux, coquilles) est reproduit tel quel.

## Fichiers

| Fichier | Rôle |
|---|---|
| `plateformes-agreees-dgfip-2026-09-13.csv` | Le registre au 13 septembre 2026, UTF-8 avec BOM, séparateur `;`, 162 lignes de données, triées par liste puis nom commercial. |
| `registre-dgfip-2026-09-13-brut.txt` | Extraction brute des deux PDF officiels, une ligne par plateforme dans l'ordre du registre, colonnes séparées par ` ¦ ` (liste, nom, voie, code postal, commune ou pays, site, courriel, date de délivrance telle qu'imprimée). |
| `plateformes-agreees-dgfip-2026-09-07.csv` | Le relevé précédent (7 septembre 2026, 165 lignes), conservé pour comparaison. |
| `registre-dgfip-2026-09-07-brut.txt` | Extraction brute des deux XLSX officiels du 7 septembre (date au format numéro de série du tableur). |
| `generer-donnees.py` | Script qui produit l'extraction brute et le CSV d'un relevé à partir des fichiers officiels. |

## Régénérer un relevé

Le script prend la date du relevé en paramètre et lit les deux PDF officiels, en les téléchargeant lui-même ou depuis des fichiers locaux. Les XLSX officiels et une extraction brute existante restent acceptés.

```bash
pip install pdfplumber            # openpyxl uniquement pour l'option --xlsx-*

# Depuis impots.gouv.fr (les PDF téléchargés sont conservés dans le dossier de sortie)
python3 generer-donnees.py --date 2026-09-13 --telecharger --effectifs 148,14

# Depuis des PDF déjà téléchargés
python3 generer-donnees.py --date 2026-09-13 --pdf-immatriculees liste_pa_attente_rapport_audit.pdf --pdf-attente liste_pa_attente_test_interop.pdf

# Depuis les XLSX officiels, ou depuis une extraction brute déjà produite
python3 generer-donnees.py --date 2026-09-07 --xlsx-immatriculees liste_pa_attente_rapport_audit.xlsx --xlsx-attente liste_pa_attente_test_interop.xlsx
python3 generer-donnees.py --date 2026-09-07 --brut registre-dgfip-2026-09-07-brut.txt
```

`--effectifs` fait échouer le script si les effectifs lus ne sont pas ceux attendus. `--ts chemin.ts` écrit en plus le module TypeScript utilisé par l'annuaire ci-dessous. Le CSV du 7 septembre est reproduit à l'octet près par le script à partir de son extraction brute comme à partir des XLSX officiels.

Relecture d'un relevé par rapport au précédent :

```bash
diff plateformes-agreees-dgfip-2026-09-07.csv plateformes-agreees-dgfip-2026-09-13.csv
```

## Historique des relevés

| Relevé | Page officielle | Immatriculées | En attente | Total | Mouvements |
|---|---|---|---|---|---|
| 7 septembre 2026 | modifiée le 07/09/2026 | 149 | 16 | 165 | Premier relevé publié. |
| 13 septembre 2026 | modifiée le 10/09/2026 | 148 | 14 | 162 | Trois sorties : YTEMS (immatriculée), YUMAN et ZEFYR (en attente). Aucune entrée, aucune ligne modifiée. |

Note sur le relevé du 13 septembre : seuls les PDF officiels reflétaient le registre à jour ; les XLSX et ODS publiés aux mêmes chemins contenaient encore les trois plateformes sorties. Les PDF ont fait foi. Le contrôle `diff` entre les deux CSV donne exactement trois lignes supprimées, zéro ajoutée, zéro modifiée. Dans l'extraction brute, seul le courriel de contact d'IAF change en plus (il n'est pas repris dans le CSV).

## Réutilisation

- Annuaire consultable, avec recherche, filtres et une fiche par plateforme (statut, date, siège, ce que l'agrément autorise), publié par FactureMatch, comparateur indépendant de logiciels de facturation électronique : https://facturematch.fr/plateformes-agreees
- Vérificateur gratuit qui indique en une seconde si un logiciel figure au registre, y compris le cas des « solutions compatibles » qui passent par une plateforme agréée tierce : https://facturematch.fr/outils/verifier-plateforme-agreee
- Jeu de données sur data.gouv.fr : https://www.data.gouv.fr/datasets/plateformes-agreees-pa-ex-pdp-pour-la-facturation-electronique-registre-dgfip-relu-le-7-septembre-2026

## Licence et mise à jour

Données publiques de la DGFiP, republiées sous Licence Ouverte / Open Licence 2.0 (Etalab). Le registre officiel évolue à chaque nouvelle immatriculation : la date de relevé fait foi, et seule la page impots.gouv.fr fait autorité. Une nouvelle version du CSV est publiée à chaque relevé, avec la date dans le nom du fichier ; les versions précédentes restent dans le dépôt.

Contact : contact@facturematch.fr
