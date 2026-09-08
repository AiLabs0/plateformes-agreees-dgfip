# Plateformes agréées (PA, ex-PDP) pour la facturation électronique — registre DGFiP

Copie fidèle, en CSV, des deux listes publiées par la Direction générale des Finances publiques sur impots.gouv.fr, page « Je consulte la liste des plateformes agréées » : https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees

- **Relecture des fichiers officiels :** 7 septembre 2026 (date de modification affichée sur la page officielle ce jour-là).
- **Contenu :** 149 opérateurs satisfaisant à l'ensemble des conditions, tests d'interopérabilité compris (immatriculation définitive, datée), et 16 opérateurs ayant déposé un dossier complet et conforme, en attente de leur immatriculation définitive.
- **Colonnes :** liste (1 = immatriculation définitive, 2 = en attente), statut, nom commercial, date de délivrance du numéro d'immatriculation, adresse de l'établissement principal (voie, code postal, commune ou pays), site internet.
- **Ce qui n'est pas repris :** les courriels de contact du registre (plusieurs sont des adresses nominatives). Aucune donnée ajoutée, aucune note, aucun tarif.
- **Retouches d'affichage documentées :** casse de quelques communes, libellés postaux, une coquille, deux codes postaux ayant perdu leur zéro initial dans le tableur d'origine ; pour les sièges hors de France, la ville est reprise de la colonne « Voie » du fichier officiel.

## Fichiers

| Fichier | Rôle |
|---|---|
| `plateformes-agreees-dgfip-2026-09-07.csv` | Le registre, UTF-8 avec BOM, séparateur `;`, 165 lignes. |
| `registre-dgfip-2026-09-07-brut.txt` | Extraction brute des deux fichiers XLSX officiels, une ligne par plateforme, colonnes séparées par ` ¦ `. |
| `generer-donnees.py` | Script qui régénère les données structurées à partir de l'extraction brute (utilisé par l'annuaire ci-dessous). |

## Réutilisation

Ces données alimentent l'annuaire consultable, avec recherche, filtres et une fiche par plateforme (statut, date, siège, ce que l'agrément autorise), publié par FactureMatch, comparateur indépendant de logiciels de facturation électronique : https://facturematch.fr/plateformes-agreees

Un vérificateur gratuit indique en une seconde si un logiciel figure au registre, y compris le cas des « solutions compatibles » qui passent par une plateforme agréée tierce : https://facturematch.fr/outils/verifier-plateforme-agreee

## Licence et mise à jour

Données publiques de la DGFiP, republiées sous Licence Ouverte / Open Licence 2.0 (Etalab). Le registre officiel évolue à chaque nouvelle immatriculation : la date de relecture fait foi, et seule la page impots.gouv.fr fait autorité. Une nouvelle version du CSV est publiée à chaque relecture, avec la date dans le nom du fichier.

Contact : contact@facturematch.fr
