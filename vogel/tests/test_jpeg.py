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
        self.exif_photos = self.gather_photos("with_exif")
        self.noexif_photos = self.gather_photos("no_exif")
        self.non_jpeg = self.gather_photos("non_jpeg", pattern="*")

    def gather_photos(self, root, pattern="*.jp*g"):
        root = os.path.join(self.resource_dir, root)
        photos = []
        for root, dirs, files in os.walk(root):
            photos.extend(os.path.join(root, f) for f in files if
                          fnmatch.fnmatch(f, pattern))
        return photos

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

    def test_jpeg_without_exif_from_string(self):
        for picture_path in self.noexif_photos:
            with open(picture_path) as picture_file:
                picture_data = picture_file.read()
                self.assertRaises(ValueError, vogel.jpeg.Exif, picture_data)

    def test_jpeg_without_exif_from_file(self):
        for picture_path in self.noexif_photos:
            with open(picture_path) as picture_file:
                self.assertRaises(ValueError, vogel.jpeg.Exif, picture_file)

    def test_nonjpeg_string(self):
        for picture_path in self.non_jpeg:
            with open(picture_path) as picture_file:
                picture_data = picture_file.read()
                self.assertRaises(ValueError, vogel.jpeg.Exif, picture_data)


if __name__ == '__main__':
    unittest.main()