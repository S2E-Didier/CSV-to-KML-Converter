import os
import re
import threading
import logging
from datetime import datetime, timedelta
from tkinter import Tk, Label, Button, OptionMenu, StringVar, messagebox, W, Checkbutton, IntVar, Frame, Toplevel
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.ttk import Progressbar

import pandas as pd
import pytz
import simplekml

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    filename="csv_to_kml.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s"
)

VERSION = "0.8.2.3"


def detect_delimiter(csv_file: str) -> str:
    """
    Détecte le délimiteur du fichier CSV en lisant la première ligne.
    """
    with open(csv_file, 'r', encoding='utf-8') as file:
        first_line = file.readline()
    return ';' if ';' in first_line else ','


def convert_date_to_iso(date_str: str, date_format: str = "JJ/MM/AAAA") -> tuple[str | None, bool]:
    """
    Convertit une date au format ISO 8601.
    Retourne un tuple (date_iso, heure_supposée) où heure_supposée vaut True
    si l’heure est implicite (ex. une date sans heure).
    """
    date_str = re.sub(r'\s+', ' ', date_str.strip())

    if date_format == "JJ/MM/AAAA":
        primary_formats = [
            "%d/%m/%Y %H:%M:%S.%f %z", "%d/%m/%Y %H:%M:%S %z", "%d/%m/%Y %H:%M:%S.%f",
            "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y %H:%M:%S %z",
            "%d/%m/%y %H:%M:%S", "%d/%m/%y %H:%M", "%d/%m/%y",
            "%d-%m-%Y %H:%M:%S.%f %z", "%d-%m-%Y %H:%M:%S %z", "%d-%m-%Y %H:%M:%S.%f",
            "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y", "%d-%m-%y %H:%M:%S %z",
            "%d-%m-%y %H:%M:%S", "%d-%m-%y %H:%M", "%d-%m-%y"
        ]
    else:
        primary_formats = [
            "%m/%d/%Y %H:%M:%S.%f %z", "%m/%d/%Y %H:%M:%S %z", "%m/%d/%Y %H:%M:%S.%f",
            "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y", "%m/%d/%y %H:%M:%S %z",
            "%m/%d/%y %H:%M:%S", "%m/%d/%y %H:%M", "%m/%d/%y",
            "%m-%d-%Y %H:%M:%S.%f %z", "%m-%d-%Y %H:%M:%S %z", "%m-%d-%Y %H:%M:%S.%f",
            "%m-%d-%Y %H:%M:%S", "%m-%d-%Y %H:%M", "%m-%d-%Y", "%m-%d-%y %H:%M:%S %z",
            "%m-%d-%y %H:%M:%S", "%m-%d-%y %H:%M", "%m-%d-%y"
        ]

    generic_formats = [
        "%Y-%m-%d %H:%M:%S.%f %z", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S.%f %z",
        "%Y/%m/%d %H:%M:%S %z", "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M", "%Y/%m/%d"
    ]

    date_formats = primary_formats + generic_formats

    # Cas spécial : date avec indication UTC explicite (ex. "JJ/MM/AAAA HH:MM:SS UTC+2")
    utc_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}) UTC([+-]\d+)", date_str)
    if utc_match:
        date_part, utc_offset = utc_match.groups()
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            dt -= timedelta(hours=int(utc_offset))
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), False
        except ValueError:
            return None, False

    utc_paren_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\(UTC([+-]\d+)\)", date_str)
    if utc_paren_match:
        date_part, utc_offset = utc_paren_match.groups()
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            dt -= timedelta(hours=int(utc_offset))
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ"), False
        except ValueError:
            return None, False

    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            iso_format = "%Y-%m-%dT%H:%M:%S.%fZ" if "%f" in fmt else "%Y-%m-%dT%H:%M:%SZ"
            assumed_midnight = fmt in ["%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d-%m-%Y",
                                       "%Y/%m/%d"]
            return dt.astimezone(pytz.utc).strftime(iso_format), assumed_midnight
        except ValueError:
            continue
    return None, False


def dms_to_decimal(dms_str: str) -> float:
    """
    Convertit une chaîne au format DMS (degrés, minutes, secondes) en décimal.
    Exemple : "37°46'29.75\"N" -> 37.77493
    """
    dms_str = dms_str.strip()
    parts = re.split('[°\'"]', dms_str)
    if len(parts) < 4 or parts[3] not in ['N', 'S', 'E', 'W']:
        raise ValueError(f"Chaîne DMS invalide : {dms_str}")
    degrees, minutes, seconds, direction = parts[:4]
    if not (0 <= float(minutes) < 60) or not (0 <= float(seconds) < 60):
        raise ValueError(f"Minutes ou secondes invalides dans : {dms_str}")
    if direction in ['N', 'S'] and not (0 <= float(degrees) <= 90):
        raise ValueError(f"Latitude invalide dans : {dms_str}")
    if direction in ['E', 'W'] and not (0 <= float(degrees) <= 180):
        raise ValueError(f"Longitude invalide dans : {dms_str}")
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal


def convert_coord(coord_str: str) -> float:
    """
    Convertit une coordonnée sous forme de chaîne en décimal.
    Gère à la fois le format DMS et le format décimal (virgule ou point).
    """
    coord_str = coord_str.strip()
    if re.match(r'^\d+[°]\d+[\'"]\d+(\.\d+)?["]?[NSWE]$', coord_str):
        return dms_to_decimal(coord_str)
    elif ',' in coord_str:
        return float(coord_str.replace(',', '.'))
    return float(coord_str)


def convert_csv_to_kml(csv_file: str, kml_file: str, name_col: str | None,
                       lat_col: str, lon_col: str, timestamp_col: str | None,
                       desc_col: str | None, delimiter: str, connect_points: bool,
                       date_format: str, progress_label: Label,
                       progress_bar: Progressbar, mappings: dict) -> None:
    """
    Convertit un CSV en fichier KML.
    Traite le fichier par morceaux, met à jour l’interface périodiquement et
    écrit un fichier de log pour les points ignorés ou dont l’heure a été supposée.
    """
    kml = simplekml.Kml()
    ignored_rows = 0
    ignored_details = []
    assumed_midnight_dates = []
    coord_conversion_errors = []
    previous_coords = None
    start_time = datetime.now()
    update_interval = 100  # mise à jour de l'interface tous les 100 enregistrements

    try:
        # Comptage du nombre total de lignes (en ignorant l'en-tête)
        with open(csv_file, 'r', encoding='utf-8') as f:
            total_rows = sum(1 for _ in f) - 1
        processed_rows = 0
        progress_bar["maximum"] = total_rows
        progress_bar["value"] = 0

        chunk_size = 10000
        for chunk in pd.read_csv(csv_file, delimiter=delimiter, chunksize=chunk_size, encoding='utf-8'):
            if timestamp_col:
                conversion_results = chunk[timestamp_col].apply(lambda d: convert_date_to_iso(str(d), date_format))
                chunk[timestamp_col] = [result[0] for result in conversion_results]
                assumed_flags = [result[1] for result in conversion_results]
                ignored_count = sum(1 for date in chunk[timestamp_col] if date is None)
                ignored_rows += ignored_count
                ignored_details.extend(chunk[chunk[timestamp_col].isna()].to_dict('records'))
                chunk = chunk.dropna(subset=[timestamp_col])
                assumed_midnight_dates.extend(
                    [row for row, flag in zip(chunk.to_dict('records'), assumed_flags) if flag]
                )
                if connect_points:
                    chunk[timestamp_col] = pd.to_datetime(chunk[timestamp_col], errors='coerce')
                    chunk = chunk.sort_values(by=timestamp_col)
            for _, row in chunk.iterrows():
                processed_rows += 1
                if processed_rows % update_interval == 0 or processed_rows == total_rows:
                    progress_label.after(0, progress_label.config,
                                         {"text": f"Lignes traitées : {processed_rows}/{total_rows}"})
                    progress_bar.after(0, progress_bar.config, {"value": processed_rows})
                try:
                    well_name = row[name_col] if name_col else None
                    latitude = convert_coord(str(row[lat_col]))
                    longitude = convert_coord(str(row[lon_col]))
                    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                        raise ValueError(f"Coordonnées invalides : Latitude={latitude}, Longitude={longitude}")
                    timestamp = row[timestamp_col] if timestamp_col else None
                    description = row[desc_col] if desc_col else None
                    point = kml.newpoint(name=well_name, coords=[(longitude, latitude)])
                    point.description = f"Description: {description}" if description else None

                    # Traitement de la colonne d'icône (optionnelle)
                    if "icon_col" in mappings and mappings["icon_col"].get() != "Sélectionner une colonne":
                        icon_col_name = mappings["icon_col"].get()
                        icon_url = row[icon_col_name]
                        if pd.notnull(icon_url) and str(icon_url).strip() != "":
                            point.style.iconstyle.icon.href = icon_url

                    if connect_points and previous_coords:
                        linestring = kml.newlinestring()
                        linestring.coords = [previous_coords, (longitude, latitude)]
                        linestring.style.linestyle.color = simplekml.Color.red
                        linestring.style.linestyle.width = 4
                        if timestamp:
                            linestring.timespan = simplekml.TimeSpan(begin=timestamp.isoformat())
                    previous_coords = (longitude, latitude)
                except (ValueError, KeyError, TypeError) as e:
                    ignored_rows += 1
                    error_msg = f"Ligne ignorée en raison d'une erreur de conversion : {e}"
                    coord_conversion_errors.append(error_msg)
                    ignored_details.append(row.to_dict())
                    logging.warning(error_msg)
        kml.save(kml_file)
        end_time = datetime.now()
        log_file = os.path.splitext(kml_file)[0] + "_ignored_points.log"
        with open(log_file, 'w', encoding='utf-8') as log:
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
        if ignored_rows > 0 or assumed_midnight_dates or coord_conversion_errors:
            messagebox.showinfo("Attention",
                                f"Le fichier KML a été créé avec succès, mais {ignored_rows} point(s) ont été ignoré(s) et {len(assumed_midnight_dates)} point(s) ont eu leur heure supposée à minuit. Consultez le fichier de log : {log_file}")
        else:
            messagebox.showinfo("Succès", "Le fichier KML a été créé avec succès sans points ignorés.")
    except Exception as e:
        logging.error(f"Erreur lors de la conversion : {e}", exc_info=True)
        messagebox.showerror("Erreur", f"Le fichier KML n'a pas pu être créé en raison d'une erreur : {e}")


def load_csv_and_setup_ui(csv_file: str, root: Tk, mappings: dict, convert_button: Button,
                          connect_points_var: IntVar, dynamic_frame: Frame, progress_label: Label,
                          progress_bar: Progressbar) -> tuple[str, StringVar]:
    """
    Charge le CSV et crée dynamiquement l’interface de mapping des colonnes.
    """
    for widget in dynamic_frame.winfo_children():
        widget.destroy()
    convert_button.config(state="disabled")
    progress_label.config(text="Prêt à commencer")
    progress_bar["value"] = 0

    delimiter = detect_delimiter(csv_file)
    df = pd.read_csv(csv_file, delimiter=delimiter, encoding='utf-8')
    columns = df.columns.tolist()

    fields = [("Nom", "name_col"),
              ("Latitude *", "lat_col"),
              ("Longitude *", "lon_col"),
              ("Horodatage", "timestamp_col"),
              ("Description", "desc_col"),
              ("Icône (URL)", "icon_col")]  # Nouveau champ optionnel

    for idx, (label_text, var_name) in enumerate(fields):
        label_color = "red" if var_name in ["lat_col", "lon_col"] else "black"
        Label(dynamic_frame, text=label_text, fg=label_color).grid(row=idx, column=0, padx=10, pady=5, sticky='e')
        mappings[var_name] = StringVar(root)
        mappings[var_name].set("Sélectionner une colonne")
        OptionMenu(dynamic_frame, mappings[var_name], *columns).grid(row=idx, column=1, padx=10, pady=5, sticky='w')

    date_format_var = StringVar(root)
    date_format_var.set("JJ/MM/AAAA")
    Label(dynamic_frame, text="Format de date").grid(row=3, column=2, padx=10, pady=5, sticky='e')
    OptionMenu(dynamic_frame, date_format_var, "JJ/MM/AAAA", "MM/JJ/AAAA").grid(row=3, column=3, padx=10, pady=5,
                                                                                sticky='w')

    connect_points_checkbutton = Checkbutton(dynamic_frame, text="Relier les points (Trajet)",
                                             variable=connect_points_var)
    connect_points_checkbutton.grid(row=len(fields), column=0, columnspan=2, pady=10, sticky='w')

    def check_selection(*args):
        if mappings["lat_col"].get() != "Sélectionner une colonne" and mappings[
            "lon_col"].get() != "Sélectionner une colonne":
            convert_button.config(state="normal")
        else:
            convert_button.config(state="disabled")

    mappings["lat_col"].trace_add("write", check_selection)
    mappings["lon_col"].trace_add("write", check_selection)

    return delimiter, date_format_var


def show_icon_help():
    """
    Affiche une fenêtre d'aide listant les icônes par défaut de Google Earth avec un bouton pour copier l'URL dans le presse-papier.
    """
    help_window = Toplevel()
    help_window.title("Liste des icônes Google Earth")

    icons = {
        "Punaise jaune": "http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png",
        "Punaise rouge": "http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png",
        "Punaise bleue": "http://maps.google.com/mapfiles/kml/pushpin/blue-pushpin.png",
        "Punaise verte": "http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png",
        "Punaise violette": "http://maps.google.com/mapfiles/kml/pushpin/purple-pushpin.png"
    }

    row = 0
    for nom, url in icons.items():
        Label(help_window, text=f"{nom} :", anchor="w").grid(row=row, column=0, padx=10, pady=5, sticky='w')
        Label(help_window, text=url, fg="blue", anchor="w").grid(row=row, column=1, padx=10, pady=5, sticky='w')

        def copy_to_clipboard(u=url):
            help_window.clipboard_clear()
            help_window.clipboard_append(u)
            messagebox.showinfo("Copié", f"L'URL '{u}' a été copiée dans le presse-papier.")

        Button(help_window, text="Copier", command=copy_to_clipboard).grid(row=row, column=2, padx=10, pady=5)
        row += 1

    Button(help_window, text="Fermer", command=help_window.destroy).grid(row=row, column=0, columnspan=3, pady=10)


def start_conversion(csv_file: str, mappings: dict, delimiter: str, connect_points_var: IntVar,
                     date_format_var: StringVar, progress_label: Label, progress_bar: Progressbar) -> None:
    """
    Démarre la conversion dans un thread séparé pour ne pas bloquer l’interface.
    """

    def run_conversion():
        lat_col = mappings["lat_col"].get()
        lon_col = mappings["lon_col"].get()

        if lat_col == "Sélectionner une colonne" or lon_col == "Sélectionner une colonne":
            messagebox.showerror("Erreur", "Vous devez sélectionner les colonnes de Latitude et Longitude.")
            return

        name_col = mappings["name_col"].get() if mappings["name_col"].get() != "Sélectionner une colonne" else None
        timestamp_col = mappings["timestamp_col"].get() if mappings[
                                                               "timestamp_col"].get() != "Sélectionner une colonne" else None
        desc_col = mappings["desc_col"].get() if mappings["desc_col"].get() != "Sélectionner une colonne" else None

        kml_file = asksaveasfilename(title="Enregistrer le fichier KML", defaultextension=".kml",
                                     filetypes=[("Fichiers KML", "*.kml")])
        if kml_file:
            connect_points = (connect_points_var.get() == 1)
            date_format = date_format_var.get()
            convert_csv_to_kml(csv_file, kml_file, name_col, lat_col, lon_col, timestamp_col, desc_col,
                               delimiter, connect_points, date_format, progress_label, progress_bar, mappings)
        else:
            logging.info("Aucun fichier KML sélectionné. Sortie.")

    threading.Thread(target=run_conversion).start()


def open_csv_and_select_columns() -> None:
    """
    Interface principale permettant de sélectionner le CSV, de mapper les colonnes puis de lancer la conversion.
    """
    root = Tk()
    root.title(f"Convertisseur CSV vers KML v{VERSION}")
    root.minsize(600, 500)

    mappings = {}
    csv_file = None
    delimiter = None
    date_format_var = None

    main_frame = Frame(root)
    main_frame.grid(pady=20, padx=20)

    explanation_text = (
        "Bienvenue dans le convertisseur CSV vers KML.\n"
        "1. Sélectionnez un fichier CSV en cliquant sur le bouton ci-dessous.\n"
        "2. Mappez les colonnes de votre fichier CSV aux champs KML. Notez que les colonnes de Latitude et de Longitude sont obligatoires (marquées en rouge *).\n"
        "3. (Optionnel) Vous pouvez ajouter une colonne pour définir l’URL de l’icône à utiliser pour chaque point.\n"
        "4. Cliquez sur 'Convertir en KML' pour générer le fichier KML."
    )
    explanation_label = Label(main_frame, text=explanation_text, wraplength=480, justify="left")
    explanation_label.grid(row=0, columnspan=2, padx=10, pady=10, sticky=W)

    dynamic_frame = Frame(root)
    dynamic_frame.grid(row=1, column=0, padx=10, pady=5, sticky='w')

    def select_csv_file():
        nonlocal csv_file, delimiter, date_format_var
        csv_file = askopenfilename(title="Sélectionner un fichier CSV", filetypes=[("Fichiers CSV", "*.csv")])
        if csv_file:
            delimiter, date_format_var = load_csv_and_setup_ui(csv_file, root, mappings, convert_button,
                                                               connect_points_var, dynamic_frame, progress_label,
                                                               progress_bar)

    select_file_button = Button(main_frame, text="Sélectionner un fichier CSV", command=select_csv_file)
    select_file_button.grid(row=1, columnspan=2, pady=10)

    # Bouton d'aide pour les icônes Google Earth
    help_button = Button(main_frame, text="Aide - Icônes", command=show_icon_help)
    help_button.grid(row=2, columnspan=2, pady=5)

    connect_points_var = IntVar()
    convert_button = Button(main_frame, text="Convertir en KML",
                            command=lambda: start_conversion(csv_file, mappings, delimiter, connect_points_var,
                                                             date_format_var, progress_label, progress_bar),
                            state="disabled")
    convert_button.grid(row=8, columnspan=2, pady=10)

    progress_label = Label(main_frame, text="Prêt à commencer")
    progress_label.grid(row=9, columnspan=2, pady=10)

    progress_bar = Progressbar(main_frame, orient="horizontal", length=300, mode="determinate")
    progress_bar.grid(row=10, columnspan=2, pady=10)

    root.mainloop()


if __name__ == "__main__":
    open_csv_and_select_columns()
