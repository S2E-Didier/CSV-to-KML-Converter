
# Convertisseur CSV vers KML

## Description

L'application "Convertisseur CSV vers KML" est un outil simple et efficace pour transformer des fichiers CSV contenant des coordonnées géographiques en fichiers KML, prêts à être utilisés dans des applications de cartographie telles que Google Earth. Ce programme offre plusieurs fonctionnalités utiles, notamment la gestion des horodatages, la prise en charge des différents formats de coordonnées, ainsi que la possibilité de relier les points pour visualiser des trajets.

## Fonctionnalités

- **Conversion CSV vers KML** : Transforme un fichier CSV contenant des informations géographiques en un fichier KML utilisable dans Google Earth.
- **Relier les points** : Permet de relier les points entre eux pour former un trajet dans le fichier KML.
- **Gestion des horodatages** : Les points peuvent être affichés chronologiquement en fonction des horodatages fournis dans le CSV.
- **Formats de coordonnées supportés** : Prise en charge des coordonnées en format DMS (Degrés, Minutes, Secondes) et en format décimal (avec points ou virgules comme séparateurs décimaux).
- **Gestion des fuseaux horaires (UTC)** : Prend en charge les horodatages incluant des informations de fuseau horaire (UTC).
- **Fichier de log** : Génère un fichier de log pour les points ignorés en raison d'erreurs (horodatages ou coordonnées invalides).

## Prérequis

- Python 3.x
- Les bibliothèques Python suivantes :
  - `csv`
  - `simplekml`
  - `os`
  - `pandas`
  - `tkinter`
  - `datetime`
  - `pytz`
  - `re`

## Installation

1. **Clonez le dépôt** :

   ```bash
   git clone https://github.com/votre_nom_utilisateur/convertisseur-csv-vers-kml.git
   cd convertisseur-csv-vers-kml
   ```

2. **Installez les dépendances** :

   Assurez-vous que les bibliothèques nécessaires sont installées :

   ```bash
   pip install pandas simplekml pytz
   ```

3. **Exécutez l'application** :

   ```bash
   python csv_to_kml_converter.py
   ```

## Utilisation

1. **Lancez l'application** : Une interface graphique s'ouvrira.
2. **Sélectionnez un fichier CSV** : Cliquez sur le bouton pour choisir le fichier CSV à convertir.
3. **Mappez les colonnes** : Associez les colonnes du CSV aux champs KML. Les colonnes de Latitude et Longitude sont obligatoires.
4. **Options supplémentaires** : Cochez la case "Relier les points" si vous souhaitez visualiser un trajet dans le fichier KML.
5. **Convertir en KML** : Cliquez sur "Convertir en KML". Un fichier KML sera généré et un message de confirmation s'affichera.
6. **Vérifiez les logs** : Si des points ont été ignorés, un fichier de log sera créé avec les détails.

## Formats de date supportés

L'application supporte plusieurs formats de date pour les horodatages, y compris ceux avec des informations de fuseau horaire (UTC). Voici quelques exemples :

- `"%d/%m/%Y %H:%M:%S %z"` – Exemple : `03/07/2021 13:15:00 +0200`
- `"%d/%m/%Y %H:%M:%S"` – Exemple : `03/07/2021 13:15:00`
- `"%Y-%m-%d %H:%M:%S %z"` – Exemple : `2021-07-03 13:15:00 +0000`
- `"%Y-%m-%d %H:%M:%S"` – Exemple : `2021-07-03 13:15:00`
- `"%m/%d/%Y %I:%M:%S %p %z"` – Exemple : `07/03/2021 01:15:00 PM -0500`
- `"%m/%d/%Y %I:%M:%S %p"` – Exemple : `07/03/2021 01:15:00 PM`
- `"%d-%m-%Y %H:%M %z"` – Exemple : `03-07-2021 13:15 +0200`
- `"%d-%m-%Y %H:%M"` – Exemple : `03-07-2021 13:15`
- `"%Y/%m/%d %H:%M:%S %z"` – Exemple : `2021/07/03 13:15:00 +0000`
- `"%Y/%m/%d %H:%M:%S"` – Exemple : `2021/07/03 13:15:00`
- `"%d %b %Y %H:%M:%S %z"` – Exemple : `03 Jul 2021 13:15:00 +0200`
- `"%d %b %Y %H:%M:%S"` – Exemple : `03 Jul 2021 13:15:00`
- **`"%d/%m/%Y %H:%M:%S(UTC±H)`** – Exemple : `03/07/2021 13:15:25(UTC+2)`

## Gestion des erreurs

- **Sélection des colonnes** : Les colonnes de Latitude et Longitude doivent être sélectionnées pour permettre la conversion.
- **Validation des coordonnées** : Les coordonnées invalides (latitude hors de [-90, 90] et longitude hors de [-180, 180]) sont ignorées et consignées dans le fichier de log.
- **Validation des horodatages** : Les horodatages invalides ou manquants sont ignorés, et les détails sont enregistrés dans le fichier de log.
- **Fichier de log** : En cas d'erreurs (coordonnées ou horodatages invalides), un fichier de log est généré pour répertorier les points ignorés.

## Contribution

Les contributions sont les bienvenues ! Veuillez soumettre une pull request avec des modifications ou ouvrir une issue pour discuter des changements que vous souhaitez apporter.

## License

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
