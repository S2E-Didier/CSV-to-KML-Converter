import csv
import simplekml
import os
import pandas as pd
from tkinter import Tk, Label, Button, OptionMenu, StringVar, messagebox, W, Checkbutton, IntVar, Frame
from tkinter.filedialog import askopenfilename, asksaveasfilename
from datetime import datetime, timedelta
import pytz
import re

def detect_delimiter(csv_file):
    with open(csv_file, 'r') as file:
        first_line = file.readline()
        return ';' if ';' in first_line else ','

def convert_date_to_iso(date_str):
    date_formats = [
        "%d/%m/%Y %H:%M:%S %z", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S %z",
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p %z", "%m/%d/%Y %I:%M:%S %p",
        "%d-%m-%Y %H:%M %z", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M:%S %z",
        "%Y/%m/%d %H:%M:%S", "%d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S"
    ]
    
    custom_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\(UTC([+-]\d{1,2})\)", date_str)
    if custom_match:
        date_part, utc_offset = custom_match.groups()
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            dt -= timedelta(hours=int(utc_offset))
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            return None
    
    tz_match = re.match(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}) (\w+)", date_str)
    if tz_match:
        date_part, tz_abbr = tz_match.groups()
        try:
            dt = datetime.strptime(date_part, "%d/%m/%Y %H:%M:%S")
            timezone = pytz.timezone(pytz.country_timezones['FR'][0])
            dt = timezone.localize(dt).astimezone(pytz.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, pytz.UnknownTimeZoneError):
            return None
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    
    return None

def dms_to_decimal(dms_str):
    """
    Convertit une chaîne de caractères DMS (Degrés, Minutes, Secondes) en décimal.
    Exemple : "37°46'29.75\"N" devient 37.77493
    """
    dms_str = dms_str.strip()
    degrees, minutes, seconds, direction = re.split('[°\'"]', dms_str)[:4]
    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if direction in ['S', 'W']:
        decimal = -decimal
    return decimal

def convert_coord(coord_str):
    """
    Convertit une chaîne de caractères de coordonnées qui peut être soit en DMS ou en décimal avec une virgule.
    """
    # Convertir en chaîne de caractères au cas où ce serait un float
    coord_str = str(coord_str).strip()
    
    # Vérifier si c'est du DMS
    if re.match(r'^\d+[°]\d+[\'"]\d+(\.\d+)?["]?[NSWE]?$', coord_str):
        return dms_to_decimal(coord_str)
    
    # Vérifier si c'est du décimal avec une virgule
    elif ',' in coord_str:
        coord_str = coord_str.replace(',', '.')
        return float(coord_str)
    
    # Sinon, considérer que c'est un décimal avec un point
    return float(coord_str)

def convert_csv_to_kml(csv_file, kml_file, name_col, lat_col, lon_col, timestamp_col, desc_col, delimiter, connect_points):
    kml = simplekml.Kml()
    df = pd.read_csv(csv_file, delimiter=delimiter)

    ignored_rows = 0  # Compteur pour les points ignorés
    ignored_details = []  # Liste pour stocker les détails des lignes ignorées

    # Uniformiser le format de la colonne d'horodatage
    if timestamp_col:
        df[timestamp_col] = df[timestamp_col].apply(convert_date_to_iso)
        ignored_rows += df[timestamp_col].isna().sum()  # Compter les lignes ignorées en raison de l'horodatage
        ignored_details.extend(df[df[timestamp_col].isna()].to_dict('records'))  # Enregistrer les lignes ignorées
        df = df.dropna(subset=[timestamp_col])  # Supprimer les lignes avec un horodatage non valide

    # Si les points doivent être reliés et qu'il y a une colonne d'horodatage valide, trier par horodatage
    if connect_points and timestamp_col:
        df[timestamp_col] = pd.to_datetime(df[timestamp_col], errors='coerce')
        df = df.sort_values(by=timestamp_col)

    if df.empty:
        messagebox.showerror("Erreur", "Aucun point valide n'a été trouvé pour créer le fichier KML.")
        return

    previous_coords = None

    try:
        for _, row in df.iterrows():
            try:
                well_name = row[name_col] if name_col else None
                latitude = convert_coord(row[lat_col])
                longitude = convert_coord(row[lon_col])

                # Vérifier les coordonnées de latitude et de longitude
                if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
                    raise ValueError(f"Coordonnées invalides : Latitude={latitude}, Longitude={longitude}")

                timestamp = row[timestamp_col] if timestamp_col else None
                description = row[desc_col] if desc_col else None

                # Ajouter le point avec le nom et la description
                point = kml.newpoint(name=well_name, coords=[(longitude, latitude)])
                point.description = f"Description: {description}" if description else None

                # Si les points doivent être reliés, ajouter un segment entre les points
                if connect_points and previous_coords:
                    linestring = kml.newlinestring()
                    linestring.coords = [previous_coords, (longitude, latitude)]
                    
                    # Appliquer le style rouge directement au segment
                    linestring.style.linestyle.color = simplekml.Color.red  # Ligne rouge
                    linestring.style.linestyle.width = 4  # Largeur de la ligne

                    # Ajouter le TimeSpan pour le segment
                    if timestamp:
                        timespan = simplekml.TimeSpan(begin=timestamp.isoformat())
                        linestring.timespan = timespan

                previous_coords = (longitude, latitude)

            except (IndexError, ValueError) as e:
                ignored_rows += 1
                ignored_details.append(dict(row))
                print(f"Skipping row due to error: {e}")

        kml.save(kml_file)

        # Si des points ont été ignorés, générer un fichier de log
        if ignored_rows > 0:
            log_file = os.path.splitext(kml_file)[0] + "_ignored_points.log"
            with open(log_file, 'w') as log:
                log.write(f"{ignored_rows} point(s) ont été ignoré(s) en raison d'un horodatage ou de coordonnées invalides.\n")
                log.write("Détails des points ignorés :\n")
                for record in ignored_details:
                    log.write(f"{record}\n")
            messagebox.showinfo("Attention", f"Le fichier KML a été créé avec succès, mais {ignored_rows} point(s) ont été ignoré(s). Consultez le fichier de log : {log_file}")
        else:
            messagebox.showinfo("Succès", "Le fichier KML a été créé avec succès sans points ignorés.")
    
    except Exception as e:
        messagebox.showerror("Erreur", f"Le fichier KML n'a pas pu être créé en raison d'une erreur : {e}")



def load_csv_and_setup_ui(csv_file, root, mappings, convert_button, connect_points_var):
    delimiter = detect_delimiter(csv_file)
    df = pd.read_csv(csv_file, delimiter=delimiter)
    columns = df.columns.tolist()

    # Mise à jour des champs avec indication que Latitude et Longitude sont obligatoires
    fields = [("Nom", "name_col"), 
              ("Latitude *", "lat_col"), 
              ("Longitude *", "lon_col"),
              ("Horodatage", "timestamp_col"), 
              ("Description", "desc_col")]

    for idx, (label_text, var_name) in enumerate(fields):
        label_color = "red" if var_name in ["lat_col", "lon_col"] else "black"
        Label(root, text=label_text, fg=label_color).grid(row=idx+2, column=0, padx=10, pady=5, sticky='e')
        mappings[var_name] = StringVar(root)
        mappings[var_name].set("Sélectionner une colonne")
        OptionMenu(root, mappings[var_name], *columns).grid(row=idx+2, column=1, padx=10, pady=5, sticky='w')

    # Placer la case à cocher pour relier les points en dessous des sélections de colonnes
    connect_points_checkbutton = Checkbutton(root, text="Relier les points (Trajet)", variable=connect_points_var)
    connect_points_checkbutton.grid(row=len(fields) + 2, columnspan=2, pady=10)

    def check_selection(*args):
        if mappings["lat_col"].get() != "Sélectionner une colonne" and mappings["lon_col"].get() != "Sélectionner une colonne":
            convert_button.config(state="normal")
        else:
            convert_button.config(state="disabled")

    mappings["lat_col"].trace_add("write", check_selection)
    mappings["lon_col"].trace_add("write", check_selection)

    return delimiter

def start_conversion(csv_file, mappings, delimiter, connect_points_var):
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
        convert_csv_to_kml(csv_file, kml_file, name_col, lat_col, lon_col, timestamp_col, desc_col, delimiter, connect_points)
        messagebox.showinfo("Succès", "Le fichier KML a été créé avec succès.")
    else:
        print("Aucun fichier KML sélectionné. Sortie.")

def open_csv_and_select_columns():
    root = Tk()
    root.title("Convertisseur CSV vers KML")

    # Fixer une taille minimum pour la fenêtre
    root.minsize(500, 400)

    mappings = {}
    csv_file = None
    delimiter = None

    # Cadre principal pour organiser les éléments
    main_frame = Frame(root)
    main_frame.pack(pady=20, padx=20)

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
        nonlocal csv_file, delimiter
        csv_file = askopenfilename(title="Sélectionner un fichier CSV", filetypes=[("Fichiers CSV", "*.csv")])
        if csv_file:
            delimiter = load_csv_and_setup_ui(csv_file, main_frame, mappings, convert_button, connect_points_var)

    select_file_button = Button(main_frame, text="Sélectionner un fichier CSV", command=select_csv_file)
    select_file_button.grid(row=1, columnspan=2, pady=10)

    # Déclarer la variable pour la case à cocher ici pour pouvoir l'utiliser plus tard
    connect_points_var = IntVar()

    convert_button = Button(main_frame, text="Convertir en KML", command=lambda: start_conversion(csv_file, mappings, delimiter, connect_points_var), state="disabled")
    convert_button.grid(row=8, columnspan=2, pady=10)

    root.mainloop()

if __name__ == "__main__":
    open_csv_and_select_columns()
