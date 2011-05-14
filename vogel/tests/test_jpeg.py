import fnmatch
import glob
import os
import unittest

import vogel.jpeg


class ExifTest(unittest.TestCase):
    MANDATORY_0IFD_TIFF_TAGS = ("XResolution", "YResolution", 
        "ResolutionUnit", "YCbCrPositioning")
    MANDATORY_0IFD_EXIF_TAGS = ("ExifVersion", "ComponentsConfiguration",
        "FlashpixVersion", "ColorSpace", "PixelXDimension", "PixelYDimension")
    # TBD.
    # MANDATORY_0IFD_GPS_TAGS = ()
    # MANDATORY_1IFD_TIFF_TAGS = ()
    MANDATORY_TAGS = MANDATORY_0IFD_TIFF_TAGS + MANDATORY_0IFD_EXIF_TAGS
    
    def setUp(self):
        self.resource_dir = os.path.join(os.path.dirname(__file__),
                                         "resources")
        self.exif_photos_dir = os.path.join(self.resource_dir, "with_exif")
        self.gather_exif_photos()

    def gather_exif_photos(self):
        self.exif_photos = []
        for root, dirs, files in os.walk(self.exif_photos_dir):
            self.exif_photos.extend(os.path.join(root, f) for f in files if
                                    fnmatch.fnmatch(f, "*.jp*g"))

    def verify_correct_meta(self, exif, filepath=None):
        for t in self.MANDATORY_TAGS:
            self.assertTrue(t in exif, "%s not in %s" % (t, filepath))

    def test_extract_mandatory_metadata_from_string(self):
        for picture_path in self.exif_photos:
            with open(picture_path, "rb") as picture_file:
                picture_data = picture_file.read()
                exif = vogel.jpeg.Exif(picture_data)
                self.verify_correct_meta(exif, filepath=picture_path)

    def test_extract_mandatory_metadata_from_file(self):
        for picture_path in self.exif_photos:
            with open(picture_path, "rb") as picture_file:
                exif = vogel.jpeg.Exif(picture_file)
                self.verify_correct_meta(exif, filepath=picture_path)


if __name__ == '__main__':
    unittest.main()