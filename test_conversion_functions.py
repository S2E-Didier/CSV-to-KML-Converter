import unittest
from csv_to_kml_converter import convert_date_to_iso, dms_to_decimal, convert_coord

class TestConversionFunctions(unittest.TestCase):

    def test_convert_date_to_iso(self):
        # Tests pour le format JJ/MM/AAAA
        self.assertEqual(convert_date_to_iso("01/01/2020 12:30:45 +0200", "JJ/MM/AAAA")[0], "2020-01-01T10:30:45Z")
        self.assertEqual(convert_date_to_iso("31/12/2019 23:59:59 +0100", "JJ/MM/AAAA")[0], "2019-12-31T22:59:59Z")
        self.assertEqual(convert_date_to_iso("01/01/2020", "JJ/MM/AAAA")[0], "2020-01-01T00:00:00Z")

        # Tests pour le format MM/JJ/AAAA
        self.assertEqual(convert_date_to_iso("12/31/2019 23:59:59 +0100", "MM/JJ/AAAA")[0], "2019-12-31T22:59:59Z")
        self.assertEqual(convert_date_to_iso("01/01/2020", "MM/JJ/AAAA")[0], "2020-01-01T00:00:00Z")

        # Tests pour le format personnalisé 03/07/2021 13:15:25(UTC+2)
        self.assertEqual(convert_date_to_iso("03/07/2021 13:15:25(UTC+2)", "JJ/MM/AAAA")[0], "2021-07-03T11:15:25Z")
        self.assertEqual(convert_date_to_iso("07/03/2021 13:15:25(UTC+2)", "MM/JJ/AAAA")[0], "2021-03-07T11:15:25Z")

        # Test pour une date sans heure (devrait retourner minuit)
        self.assertEqual(convert_date_to_iso("01-01-2020", "JJ/MM/AAAA")[0], "2020-01-01T00:00:00Z")
        self.assertEqual(convert_date_to_iso("01-01-2020", "MM/JJ/AAAA")[0], "2020-01-01T00:00:00Z")

        # Tests pour les formats de date valides incluant UTC
        self.assertEqual(convert_date_to_iso("01/01/2020 12:30:45 UTC+2", "JJ/MM/AAAA")[0], "2020-01-01T10:30:45Z")
        self.assertEqual(convert_date_to_iso("01/01/2020 12:30:45 UTC+2", "MM/JJ/AAAA")[0], "2020-01-01T10:30:45Z")

        # Test pour un format de date invalide
        self.assertIsNone(convert_date_to_iso("Invalid date format")[0])

    def test_dms_to_decimal(self):
        # Tests pour des coordonnées DMS valides
        self.assertAlmostEqual(dms_to_decimal("37°46'29.75\"N"), 37.77493, places=5)
        self.assertAlmostEqual(dms_to_decimal("122°25'9.24\"W"), -122.41923, places=5)
        self.assertAlmostEqual(dms_to_decimal("37°46'29.75\"S"), -37.77493, places=5)
        self.assertAlmostEqual(dms_to_decimal("122°25'9.24\"E"), 122.41923, places=5)
        
        # Tests pour des cas limites (0°0'0")
        self.assertAlmostEqual(dms_to_decimal("0°0'0\"N"), 0.0, places=5)
        self.assertAlmostEqual(dms_to_decimal("0°0'0\"E"), 0.0, places=5)

        # Test pour une chaîne invalide
        with self.assertRaises(ValueError):
            dms_to_decimal("Invalid DMS string")
        
        # Test pour une direction invalide (manque N/S/E/W)
        with self.assertRaises(ValueError):
            dms_to_decimal("37°46'29.75\"")

    def test_convert_coord(self):
        # Tests pour des coordonnées DMS
        self.assertAlmostEqual(convert_coord("37°46'29.75\"N"), 37.77493, places=5)
        self.assertAlmostEqual(convert_coord("122°25'9.24\"W"), -122.41923, places=5)

        # Tests pour des coordonnées décimales avec des virgules
        self.assertEqual(convert_coord("37,77493"), 37.77493)
        self.assertEqual(convert_coord("-122,41923"), -122.41923)

        # Tests pour des coordonnées décimales avec des points
        self.assertEqual(convert_coord("37.77493"), 37.77493)
        self.assertEqual(convert_coord("-122.41923"), -122.41923)

        # Tests pour des coordonnées invalides
        with self.assertRaises(ValueError):
            convert_coord("Invalid coordinate string")

        # Test pour des coordonnées DMS sans direction (doit échouer)
        with self.assertRaises(ValueError):
            convert_coord("37°46'29.75\"")

        # Test pour des coordonnées DMS avec des valeurs invalides
        with self.assertRaises(ValueError):
            convert_coord("181°0'0\"N")  # Latitude ne peut pas être > 90
        with self.assertRaises(ValueError):
            convert_coord("122°60'0\"W")  # Minutes ne peuvent pas être >= 60
        with self.assertRaises(ValueError):
            convert_coord("122°0'60\"W")  # Secondes ne peuvent pas être >= 60

if __name__ == '__main__':
    unittest.main()
