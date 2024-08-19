import csv
import simplekml
import os
import pandas as pd
from tkinter import Tk, Label, Button, OptionMenu, StringVar, messagebox, W, Checkbutton, IntVar, Frame
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.ttk import Progressbar
from datetime import datetime, timedelta
import threading
import pytz
import re

# Définir le numéro de version de l'application
VERSION = "0.8.1"

# Fonction pour détecter le délimiteur du fichier CSV (virgule ou point-virgule)
def detect_delimiter(csv_file):
    with open(csv_file, 'r') as file:
        first_line = file.readline()
        # On détecte le délimiteur en vérifiant s'il y a une virgule ou un point-virgule dans la première ligne du fichier CSV
        return ';' if ';' in first_line else ','

# Fonction pour convertir une date en format ISO 8601
def convert_date_to_iso(date_str, date_format="JJ/MM/AAAA"):
    # Supprimer les espaces multiples dans la chaîne de date
    date_str = re.sub(r'\s+', ' ', date_str.strip())
    
    # Définir les formats de date en fonction du format choisi par l'utilisateur
    if date_format == "JJ/MM/AAAA":
        primary_formats = [
        # Formats de date pour JJ/MM/AAAA
            "%d/%m/%Y %H:%M:%S.%f %z", "%d/%m/%Y %H:%M:%S %z", "%d/%m/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y %H:%M:%S %z",
            "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M", "%d/%m/%y",
            "%d-%m-%Y %H:%M:%S.%f %z", "%d-%m-%Y %H:%M:%S %z", "%d-%m-%Y %H:%M:%S.%f",
            "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d-%m-%y %H:%M:%S %z",
            "%d-%m-%y %H:%M:%S", "%d-%m-%y %H:%M", "%d-%m-%y"
        ]
    else:
        primary_formats = [
        # Formats de date pour MM/JJ/AAAA
            "%m/%d/%Y %H:%M:%S.%f %z", "%m/%d/%Y %H:%M:%S %z", "%m/%d/%Y %H:%M:%S.%f",
            "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%m/%d/%y %H:%M:%S %z",
            "%m/%d/%y %H:%M:%S", "%m/%d/%y %H:%M", "%m/%d/%y",
            "%m-%d-%Y %H:%M:%S.%f %z", "%m-%d-%Y %H:%M:%S %z", "%m-%d-%Y %H:%M:%S.%f",
            "%m-%d-%Y %H:%M:%S", "%m-%d-%Y %H:%M", "%m-%d-%Y", "%m-%d-%y %H:%M:%S %z",
            "%m-%d-%y %H:%M:%S", "%m-%d-%y %H:%M", "%m-%d-%y"
        ]
    
    # Formats de date génériques acceptés indépendamment du format choisi
    generic_formats = [
        "%Y-%m-%d %H:%M:%S.%f %z", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S.%f %z",
        "%Y/%m/%d %H:%M:%S %z", "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M", "%Y/%m/%d"
    ]
    
    # Combinaison des formats spécifiques et génériques
    date_formats = primary_formats + generic_formats
    
    # Cas spécial pour les dates avec fuseau horaire explicite (UTC+2, par exemple)
    utc_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}) UTC([+-]\d+)", date_str)
    if utc_match:
        date_part, utc_offset = utc_match.groups()
        utc_offset_hours = int(utc_offset)
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            dt -= timedelta(hours=utc_offset_hours)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), False
        except ValueError:
            return None, False
    
    # Cas spécial pour UTC avec parenthèses
    utc_paren_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\(UTC([+-]\d+)\)", date_str)
    if utc_paren_match:
        date_part, utc_offset = utc_paren_match.groups()
        utc_offset_hours = int(utc_offset)
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            dt -= timedelta(hours=utc_offset_hours)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), False
        except ValueError:
            return None, False
    
    # Essayer de parser la date avec les formats définis
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            iso_format = "%Y-%m-%dT%H:%M:%S.%fZ" if "%f" in fmt else "%Y-%m-%dT%H:%M:%SZ"
            # Identifier si une date sans heure a été supposée à minuit
            elements_supposed = fmt in ["%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
            return dt.astimezone(pytz.utc).strftime(iso_format), elements_supposed
        except ValueError:
            continue
    
    return None, False

# Convertir les coordonnées en format décimal (latitude/longitude)
def dms_to_decimal(dms_str):
    """
    Convertit une chaîne de caractères DMS (Degrés, Minutes, Secondes) en décimal.
    Exemple : "37°46'29.75\"N" devient 37.77493
    """
    dms_str = dms_str.strip()
    parts = re.split('[°\'"]', dms_str)
    
    # Validation du format DMS
    if len(parts) < 4 or parts[3] not in ['N', 'S', 'E', 'W']:
        raise ValueError(f"Chaîne DMS invalide : {dms_str}")
    
    degrees, minutes, seconds, direction = parts[:4]
    
    # Vérifier les bornes des valeurs pour minutes et secondes
    if not (0 <= float(minutes) < 60) or not (0 <= float(seconds) < 60):
        raise ValueError(f"Minutes ou secondes invalides dans : {dms_str}")
    
    # Vérifier la validité des latitudes et longitudes
    if direction in ['N', 'S'] and not (0 <= float(degrees) <= 90):
        raise ValueError(f"Latitude invalide dans : {dms_str}")
    
    if direction in ['E', 'W'] and not (0 <= float(degrees) <= 180):
        raise ValueError(f"Longitude invalide dans : {dms_str}")
    
    # Conversion des degrés, minutes, secondes en décimal
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

# Convertir les coordonnées à partir de différents formats en décimal
def convert_coord(coord_str):
    coord_str = str(coord_str).strip()
    
    # Vérifier si les coordonnées sont en format DMS
    if re.match(r'^\d+[°]\d+[\'"]\d+(\.\d+)?["]?[NSWE]?$', coord_str):
        return dms_to_decimal(coord_str)
    
    # Si les coordonnées sont en format décimal avec des virgules, remplacer par des points
    elif ',' in coord_str:
        coord_str = coord_str.replace(',', '.')
        return float(coord_str)
    
    # Si les coordonnées sont déjà en format décimal avec des points
    return float(coord_str)

# Fonction principale pour convertir un fichier CSV en fichier KML
def convert_csv_to_kml(csv_file, kml_file, name_col, lat_col, lon_col, timestamp_col, desc_col, delimiter, connect_points, date_format, progress_label, progress_bar):
    kml = simplekml.Kml()

    # Initialisation des compteurs et des listes pour les erreurs
    ignored_rows = 0  # Nombre de lignes ignorées
    ignored_details = []  # Détails des lignes ignorées
    assumed_midnight_dates = []  # Dates pour lesquelles l'heure est supposée à minuit
    coord_conversion_errors = []  # Erreurs de conversion des coordonnées

    previous_coords = None  # Coordonnées précédentes pour le traçage de lignes
    start_time = datetime.now()  # Enregistrement du début du traitement

    try:
        # Lire la totalité du CSV pour calculer le nombre total de lignes
        total_rows = sum(1 for _ in open(csv_file)) - 1  # Soustraction de l'en-tête
        processed_rows = 0

        # Initialisation de la barre de progression
        progress_bar["maximum"] = total_rows
        progress_bar["value"] = 0

        chunk_size = 10000  # Taille des morceaux de lecture du CSV
        for chunk in pd.read_csv(csv_file, delimiter=delimiter, chunksize=chunk_size):
            if timestamp_col:
                # Conversion des dates en utilisant le format sélectionné
                chunk[timestamp_col], assumed_midnight = zip(*chunk[timestamp_col].apply(lambda date: convert_date_to_iso(date, date_format)))
                ignored_rows += chunk[timestamp_col].isna().sum()
                ignored_details.extend(chunk[chunk[timestamp_col].isna()].to_dict('records'))
                chunk = chunk.dropna(subset=[timestamp_col])

                assumed_midnight_dates.extend([row for row, midnight in zip(chunk.to_dict('records'), assumed_midnight) if midnight])

            if connect_points and timestamp_col:
                chunk[timestamp_col] = pd.to_datetime(chunk[timestamp_col], errors='coerce')
                chunk = chunk.sort_values(by=timestamp_col)

            for _, row in chunk.iterrows():
                processed_rows += 1

                # Utiliser after pour mettre à jour l'interface dans le thread principal
                progress_label.after(0, progress_label.config, {"text": f"Lignes traitées : {processed_rows}/{total_rows}"})
                progress_label.after(0, progress_bar.config, {"value": processed_rows})
                progress_label.after(0, progress_label.update_idletasks)

                try:
                    well_name = row[name_col] if name_col else None
                    latitude = convert_coord(row[lat_col])
                    longitude = convert_coord(row[lon_col])

                    # Vérification des limites des coordonnées
                    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                        raise ValueError(f"Coordonnées invalides : Latitude={latitude}, Longitude={longitude}")

                    timestamp = row[timestamp_col] if timestamp_col else None
                    description = row[desc_col] if desc_col else None

                    # Créer un nouveau point KML
                    point = kml.newpoint(name=well_name, coords=[(longitude, latitude)])
                    point.description = f"Description: {description}" if description else None

                    # Créer une ligne pour relier les points si nécessaire
                    if connect_points and previous_coords:
                        linestring = kml.newlinestring()
                        linestring.coords = [previous_coords, (longitude, latitude)]
                        linestring.style.linestyle.color = simplekml.Color.red
                        linestring.style.linestyle.width = 4

                        if timestamp:
                            timespan = simplekml.TimeSpan(begin=timestamp.isoformat())
                            linestring.timespan = timespan

                    previous_coords = (longitude, latitude)

                except (IndexError, ValueError) as e:
                    ignored_rows += 1
                    coord_conversion_errors.append(f"Ligne ignorée en raison d'une erreur de conversion : {e}")
                    ignored_details.append(dict(row))

        # Sauvegarder le fichier KML généré
        kml.save(kml_file)
        end_time = datetime.now()  # Enregistrement de la fin du traitement

        # Générer le fichier de log pour les points ignorés
        log_file = os.path.splitext(kml_file)[0] + "_ignored_points.log"
        with open(log_file, 'w') as log:
            log.write(f"Version de l'application : {VERSION}\n")
            log.write(f"Traitement commencé à : {start_time}\n")
            log.write(f"Traitement terminé à : {end_time}\n")
            log.write(f"Temps total de traitement : {end_time - start_time}\n\n")

            if ignored_rows > 0:
                log.write(f"{ignored_rows} point(s) ont été ignoré(s).\n")
                log.write("Détails des points ignorés :\n")
                for record in ignored_details:
                    log.write(f"{record}\n")

            if assumed_midnight_dates:
                log.write(f"\n{len(assumed_midnight_dates)} point(s) ont eu leur heure supposée à minuit (00:00:00).\n")
                log.write("Détails des points concernés :\n")
                for record in assumed_midnight_dates:
                    log.write(f"{record}\n")

            if coord_conversion_errors:
                log.write("\nErreurs de conversion de coordonnées :\n")
                for error in coord_conversion_errors:
                    log.write(f"{error}\n")

        # Avertir l'utilisateur si des points ont été ignorés
        if ignored_rows > 0 or assumed_midnight_dates ou coord_conversion_errors:
            messagebox.showinfo("Attention", f"Le fichier KML a été créé avec succès, mais {ignored_rows} point(s) ont été ignoré(s) et {len(assumed_midnight_dates)} point(s) ont été supposés à minuit. Consultez le fichier de log : {log_file}")
        else:
            messagebox.showinfo("Succès", "Le fichier KML a été créé avec succès sans points ignorés.")

    except Exception as e:
        messagebox.showerror("Erreur", f"Le fichier KML n'a pas pu être créé en raison d'une erreur : {e}")

# Charger le CSV et configurer l'interface utilisateur pour la sélection des colonnes
def load_csv_and_setup_ui(csv_file, root, mappings, convert_button, connect_points_var):
    # Détection du délimiteur du fichier CSV
    delimiter = detect_delimiter(csv_file)
    df = pd.read_csv(csv_file, delimiter=delimiter)
    columns = df.columns.tolist()

    # Créer un cadre pour les options de mapping des colonnes
    mapping_frame = Frame(root)
    mapping_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')

    # Mise à jour des champs avec indication que Latitude et Longitude sont obligatoires
    fields = [("Nom", "name_col"), 
              ("Latitude *", "lat_col"), 
              ("Longitude *", "lon_col"),
              ("Horodatage", "timestamp_col"), 
              ("Description", "desc_col")]

    for idx, (label_text, var_name) in enumerate(fields):
        label_color = "red" if var_name in ["lat_col", "lon_col"] else "black"
        Label(mapping_frame, text=label_text, fg=label_color).grid(row=idx, column=0, padx=10, pady=5, sticky='e')
        mappings[var_name] = StringVar(root)
        mappings[var_name].set("Sélectionner une colonne")
        OptionMenu(mapping_frame, mappings[var_name], *columns).grid(row=idx, column=1, padx=10, pady=5, sticky='w')

    # Ajout du menu déroulant pour la sélection du format de date juste après le champ Horodatage
    date_format_var = StringVar(root)
    date_format_var.set("JJ/MM/AAAA")  # Valeur par défaut
    Label(mapping_frame, text="Format de date").grid(row=3, column=2, padx=10, pady=5, sticky='e')
    OptionMenu(mapping_frame, date_format_var, "JJ/MM/AAAA", "MM/JJ/AAAA").grid(row=3, column=3, padx=10, pady=5, sticky='w')

    # Créer un cadre pour les options supplémentaires
    options_frame = Frame(root)
    options_frame.grid(row=2, column=0, padx=10, pady=5, sticky='w')

    # Placer la case à cocher pour relier les points
    connect_points_checkbutton = Checkbutton(options_frame, text="Relier les points (Trajet)", variable=connect_points_var)
    connect_points_checkbutton.grid(row=0, column=0, pady=10, sticky='w')

    # Ajuster la taille minimale de la fenêtre pour que tout soit visible
    root.minsize(600, 500)

    # Activer ou désactiver le bouton "Convertir" en fonction des sélections
    def check_selection(*args):
        if mappings["lat_col"].get() != "Sélectionner une colonne" and mappings["lon_col"].get() != "Sélectionner une colonne":
            convert_button.config(state="normal")
        else:
            convert_button.config(state="disabled")

    mappings["lat_col"].trace_add("write", check_selection)
    mappings["lon_col"].trace_add("write", check_selection)

    return delimiter, date_format_var

# Démarrer la conversion du CSV vers KML
def start_conversion(csv_file, mappings, delimiter, connect_points_var, date_format_var, progress_label, progress_bar):
    def run_conversion():
        lat_col = mappings["lat_col"].get()
        lon_col = mappings["lon_col"].get()

        if lat_col == "Sélectionner une colonne" or lon_col == "Sélectionner une colonne":
            messagebox.showerror("Erreur", "Vous devez sélectionner les colonnes de Latitude et Longitude.")
            return

        name_col = mappings["name_col"].get() if mappings["name_col"].get() != "Sélectionner une colonne" else None
        timestamp_col = mappings["timestamp_col"].get() if mappings["timestamp_col"].get() != "Sélectionner une colonne" else None
        desc_col = mappings["desc_col"].get() if mappings["desc_col"].get() != "Sélectionner une colonne" else None

        kml_file = asksaveasfilename(title="Enregistrer le fichier KML", defaultextension=".kml", filetypes=[("Fichiers KML", "*.kml")])
        if kml_file:
            connect_points = connect_points_var.get() == 1
            date_format = date_format_var.get()  # Récupérer le format de date sélectionné
            convert_csv_to_kml(csv_file, kml_file, name_col, lat_col, lon_col, timestamp_col, desc_col, delimiter, connect_points, date_format, progress_label, progress_bar)
        else:
            print("Aucun fichier KML sélectionné. Sortie.")

    # Lancer la conversion dans un thread séparé
    threading.Thread(target=run_conversion).start()

# Ouvrir l'interface utilisateur principale pour sélectionner le fichier CSV et configurer les options
def open_csv_and_select_columns():
    root = Tk()
    root.title(f"Convertisseur CSV vers KML v{VERSION}")

    # Fixer une taille minimum pour la fenêtre
    root.minsize(600, 500)

    mappings = {}
    csv_file = None
    delimiter = None
    date_format_var = None

    # Cadre principal pour organiser les éléments
    main_frame = Frame(root)
    main_frame.grid(pady=20, padx=20)

    # Mettre à jour les explications en haut de la fenêtre avec un Label
    explanation_text = (
        "Bienvenue dans le convertisseur CSV vers KML.\n"
        "1. Sélectionnez un fichier CSV en cliquant sur le bouton ci-dessous.\n"
        "2. Mappez les colonnes de votre fichier CSV aux champs KML. Notez que les colonnes de Latitude et de Longitude sont obligatoires (marquées en rouge *).\n"
        "3. Cliquez sur 'Convertir en KML' pour générer le fichier KML."
    )
    explanation_label = Label(main_frame, text=explanation_text, wraplength=480, justify="left")
    explanation_label.grid(row=0, columnspan=2, padx=10, pady=10, sticky=W)

    def select_csv_file():
        nonlocal csv_file, delimiter, date_format_var
        csv_file = askopenfilename(title="Sélectionner un fichier CSV", filetypes=[("Fichiers CSV", "*.csv")])
        if csv_file:
            delimiter, date_format_var = load_csv_and_setup_ui(csv_file, root, mappings, convert_button, connect_points_var)

    select_file_button = Button(main_frame, text="Sélectionner un fichier CSV", command=select_csv_file)
    select_file_button.grid(row=1, columnspan=2, pady=10)

    # Déclarer la variable pour la case à cocher ici pour pouvoir l'utiliser plus tard
    connect_points_var = IntVar()

    convert_button = Button(main_frame, text="Convertir en KML", command=lambda: start_conversion(csv_file, mappings, delimiter, connect_points_var, date_format_var, progress_label, progress_bar), state="disabled")
    convert_button.grid(row=8, columnspan=2, pady=10)

    # Ajouter un label pour afficher l'avancement
    progress_label = Label(main_frame, text="Prêt à commencer")
    progress_label.grid(row=9, columnspan=2, pady=10)

    # Ajouter une barre de progression
    progress_bar = Progressbar(main_frame, orient="horizontal", length=300, mode="determinate")
    progress_bar.grid(row=10, columnspan=2, pady=10)

    root.mainloop()

if __name__ == "__main__":
    open_csv_and_select_columns()
