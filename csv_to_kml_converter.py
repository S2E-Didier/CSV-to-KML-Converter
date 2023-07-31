import csv
import simplekml

def convert_csv_to_kml(csv_file, kml_file):
    # Create a KML object
    kml = simplekml.Kml()

    # Open the CSV file
    with open(csv_file, 'r') as file:
        reader = csv.reader(file)

        # Skip the header row
        next(reader)

        # Iterate over the remaining rows
        for row in reader:
            well_name = row[0]
            latitude = float(row[1])
            longitude = float(row[2])
            status = row[3]

            # Create a KML placemark for each well
            placemark = kml.newpoint(name=well_name, coords=[(longitude, latitude)])

            placemark.description = status

    # Save the KML file
    kml.save(kml_file)

# Provide the path to your CSV file and desired output KML file
csv_file = 'path/to/input.csv'
kml_file = 'path/to/output.kml'

convert_csv_to_kml(csv_file, kml_file)
