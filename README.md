# CSV-to-KML-Converter
Latitude (ins CSV) to KML Converter
---

# CSV to KML Converter

The CSV to KML Converter is a Python script that allows you to convert CSV (Comma-Separated Values) files containing geographical data to KML (Keyhole Markup Language) format, which is commonly used for visualizing geographic data in tools like Google Earth.

## Prerequisites

Before running the converter, ensure you have the following installed:

- Python (version 3.6 or higher)
- Required Python packages: `simplekml`, `csv`

## Installation

1. Clone or download this repository to your local machine.

2. Ensure you have Python installed. If not, you can download it from the official Python website (https://www.python.org/downloads/).

3. Open a terminal or command prompt and navigate to the project's directory.

4. Install the required Python packages by running the following command:
   ```
   pip install simplekml
   ```

## Usage

1. Place your CSV file with geographical data in the same directory as the Python script (`csv_to_kml_converter.py`).

2. Make sure your CSV file has the following columns: 'WELL NAME', 'Latitude', 'Longitude', and 'Status'. The 'WELL NAME' column should contain the name of each well, and 'Latitude'/'Longitude' should contain the corresponding coordinates. The 'Status' column can contain additional information about each well.

3. Run the Python script by executing the following command in the terminal:
   ```
   python csv_to_kml_converter.py
   ```

4. The script will prompt you to enter the name of the input CSV file (e.g., `input.csv`). Press Enter after providing the file name.

5. The converted KML file will be generated in the same directory with the name `output.kml`.

6. You can now open the `output.kml` file in tools like Google Earth to visualize the well locations and their statuses.

## Sample CSV Format

Here's an example of how your CSV file should be formatted:

```
WELL NAME,Latitude,Longitude,Status
ALBERTON-1,-38.6390335,146.6354826,Needs further investigation
... (add more wells as needed)
```

Make sure to remove this example from the README and use your actual well data in the CSV file.

## Troubleshooting

- If you encounter any issues while running the script, ensure that your CSV file is properly formatted and contains the required columns.
- Make sure you have installed the required Python packages mentioned in the "Prerequisites" section.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---
