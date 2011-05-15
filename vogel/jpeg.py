import sys
import StringIO
import struct
import os


class JPEGError(Exception):
    """Base class for exception in the JPEG module"""


class Exif(object):
    START_MARKER = "\xff"
    SOI = START_MARKER + "\xd8"
    APP0 = START_MARKER + "\xe0"
    APP1 = START_MARKER + "\xe1"
    APP2 = START_MARKER + "\xe2"

    def __init__(self, image):
        if isinstance(image, basestring):
            self.image = StringIO.StringIO(image)
        else:
            self.image = image
        self._verify_jpeg()
        self._extract_app1_data()

    def _verify_jpeg(self):
        self.image.seek(0)
        if not self.image.read(2) == self.SOI:
            raise ValueError("Invalid JPEG image")

    def _extract_app1_data(self):
        offset = self._get_app1_offset()
        if offset < 0:
            raise ValueError("Invalid Exif image")
        self.app1_segment = APP1Segment(self.image, offset)

    def _get_app1_offset(self):
        # Assume strict std compliance
        offset = 2 # APP1 Should always follow SOI when Exif.
        self.image.seek(offset)
        marker = self.image.read(2)
        if marker == self.APP0: # Handle JFIF also wanting to be first...
            (app0_len,) = struct.unpack(">H", self.image.read(2))
            offset += 2 + app0_len # Compensate for marker + app0 segment
            self.image.seek(offset)
            marker = self.image.read(2)
        if not marker == self.APP1:
            # Not "pure" Exif or JFIF, Falling back to searching
            offset = self._find_app1_marker(offset)
        return offset

    def _find_app1_marker(self, offset):
        self.image.seek(offset)
        buf, loc = "", -1
        while loc < 0:
            chunk = self.image.read(1024)
            if not chunk:
                break
            buf += chunk
            loc = buf.find(self.APP1)
        return loc if loc < 0 else loc + offset

    def __getitem__(self, field_name):
        return self._entries[field_name]

    def get(self, field_name, default=None):
        try:
            return self.__getitem__(field_name)
        except KeyError:
            return default

    def __iter__(self):
        for field, value in self._entries.items():
            yield (field, value)

    def __len__(self):
        return len(self._entries)

    def __contains__(self, field_name):
        return field_name in self._entries

    @property
    def _entries(self):
        return self.app1_segment.exif_data.tiff_structure.ifd_entries


class APP1Segment(object):
    HEADER_LEN = 4

    def __init__(self, image, offset):
        self.image = image
        self.offset = offset
        self._extract_exif_data()

    def _extract_exif_data(self):
        offset = (self.offset + self.HEADER_LEN)
        self.exif_data = EXIFData(self.image, offset)


class EXIFData(object):
    ID_CODE = "Exif\x00"
    PADDING = "\x00"
    HEADER_LEN = 6

    def __init__(self, image, offset):
        self.image = image
        self.offset = offset
        self._verify_exif()
        self._extract_tiff_structure()

    def _verify_exif(self):
        self.image.seek(self.offset)
        header = self.image.read(self.HEADER_LEN)
        id_code, padding = struct.unpack("5sc", header)
        if not (id_code, padding) == (self.ID_CODE, self.PADDING):
            raise ValueError("Invalid Exif data")

    def _extract_tiff_structure(self):
        offset = self.offset + self.HEADER_LEN
        self.tiff_structure = TIFFStructure(self.image, offset)




class TIFFStructure(object):
    IFD_TYPES = {
        # Type: (fmt, size, name, parse_fn)
        1: ("B", 1, "BYTE", None),
        2: ("s", 1, "ASCII", lambda x: x[:-1]),
        3: ("H", 2, "SHORT", None),
        4: ("I", 4, "LONG", None), 
        5: ("II", 8, "RATIONAL", None),
        7: ("x", 1, "UNDEFINED", None),
        9: ("i", 4, "SLONG", None),
        10: ("ii", 8, "SRATIONAL", None),
    }
    RES = "RESERVED"
    OTHER = -1
    IFD_TAGS = {
        # Tag (DEC): (Name, Default, ValueMapping)
        
        # TIFF Tags
        # Tags relating to image data structure
        256: ("ImageWidth", None, {}),
        257: ("ImageLength", None, {}),
        258: ("BitsPerSample", (8,8,8), {}),
        259: ("Compression", None, {1: "uncompressed", 6: "JPEG", OTHER: RES}),
        262: ("PhotometricInterpretation", None, {2: "RGB", 6: "YCbCr",
              OTHER: RES}),
        274: ("Orientation", 1, {}), # TODO Interpret orientation value
        277: ("SamplesPerPixel", 3, {}),
        284: ("PlanarConfiguration", None, {1: "chunky", 2: "planar",
              OTHER: RES}),
        530: ("YCbCrSubSampling", None, {(2,1): "YCbCr4:2:2", 
              (2,2): "YCbCr4:2:0", OTHER: RES}),
        531: ("YCbCrPositioning", 1, {1: "centered", 2: "co-sited",
              OTHER: RES}),
        282: ("XResolution", (72,1), {}),
        283: ("YResolution", (72,1), {}),
        296: ("ResolutionUnit", 2, {2: "inches", 3: "centimeters", 
              OTHER: RES}),
    
        # Tags relating to recording offset
        273: ("StripOffsets", None, {}),
        278: ("RowsPerStrip", None, {}),
        279: ("StripByteCounts", None, {}),
        513: ("JPEGInterchangeFormat", None, {}),
        514: ("JPEGInterchangeFormatLength", None, {}),
    
        # Tags relating to image data characteristics
        301: ("TransferFunction", None, {}),
        318: ("WhitePoint", None, {}),
        319: ("PrimaryChromaticities", None, {}),
        529: ("YCbCrCoefficients", None, {}), # TODO: "see Annex D"
        532: ("ReferenceBlackWhite", None, {}), # TODO: Depends on other val
    
        # Other tags
        306: ("DateTime", None, {}),
        270: ("ImageDescription", None, {}),
        271: ("Make", None, {}),
        272: ("Model", None, {}),
        305: ("Software", None, {}),
        315: ("Artist", None, {}),
        33432: ("Copyright", None, {}),
    
        # EXIF_IFD_TAGS
        # Tags Relating to Version
        36864: ("ExifVersion", "0230", {}),
        40960: ("FlashpixVersion", "0100", {"0100": 
                "Flashpix Format Version 1.0", OTHER: RES}),
        # Tag Relating to Image Data Characteristics
        40961: ("ColorSpace", 1, {1: "sRGB", 0xFFFF: "Uncalibrated",
                OTHER: RES}),
        42240: ("Gamma", None, {}),
    
        # Tags Relating to Image Configuration
        37121: ("ComponentsConfiguration", "1230", {}), # TODO: Verify default
        37122: ("CompressedBitsPerPixel", None, {}),
        40962: ("PixelXDimension", None, {}),
        40963: ("PixelYDimension", None, {}),
    
        # Tags Relating to User Information
        37500: ("MakerNote", None, {}),
        37510: ("UserComment", None, {}),
    
        # Tag Relating to Related File Information
        40964: ("RelatedSoundFile", None, {}),
    
        # Tags Relating to Date and Time
        36867: ("DateTimeOriginal", None, {}),
        36868: ("DateTimeDigitized", None, {}),
        37520: ("SubSecTime", None, {}),
        37521: ("SubSecTimeOriginal", None, {}),
        37522: ("SubSecTimeDigitized", None, {}),
    
        # Tags Relating to Picture-Taking Conditions
        33434: ("ExposureTime", None, {}),
        33437: ("FNumber", None, {}),
        34850: ("ExposureProgram", 0, {0: "Not defined", 1: "Manual",
                2: "Normal program", 3: "Aperture priority",
                4: "Shutter priority",
                5: "Creative program (biased toward depth of field)",
                6: "Action program (biased toward fast shutter speed)",
                7: "Portrait mode (for closeup photos with the background out "
                   "of focus)",
                8: "Landscape mode (for landscape photos with the background "
                   "in focus)",
                OTHER: RES}),
        34852: ("SpectralSensitivity", None, {}),
        34855: ("PhotographicSensitivity", None, {}),
        34856: ("OECF", None, {}),
        34864: ("SensitivityType", None, {0: "Unknown",
                1: "SOS", 2: "REI", 3: "ISO Speed", 4: "SOS,REI",
                5: "SOS,ISO Speed", 6: "REI,ISO Speed", 7:"SOS,REI,ISO Speed",
                OTHER: RES}),
        34865: ("StandardOutputSensitivity", None, {}),
        34866: ("RecommendedExposureIndex", None, {}),
        34867: ("ISOSpeed", None, {}),
        34868: ("ISOSpeedLatitudeyyy", None, {}),
        34869: ("ISOSpeedLatitudezzz", None, {}),
        37377: ("ShutterSpeedValue", None, {}),
        37378: ("ApertureValue", None, {}),
        37379: ("BrightnessValue", None, {}),
        37380: ("ExposureBiasValue", None, {}),
        37381: ("MaxApertureValue", None, {}),
        37382: ("SubjectDistance", None, {}),
        37383: ("MeteringMode", 0, {0: "Unknown", 1: "Average",
                2: "CenterWeightedAverage", 3: "Spot", 4: "MultiSpot",
                5: "Pattern", 6: "Partial", 255: "Other", OTHER: RES}),
        37384: ("LightSource", 0, {0: "Unknown", 1: "Daylight",
                2: "Fluorescent", 3: "Tungsten", 4: "Flash", 9: "Fine weather",
                10: "Cloudy weather", 11: "Shade",
                12: "Daylight fluorescent (D 5700 - 7100K)",
                13: "Day white fluorescent (N 4600 - 5500K)",
                14: "Cool white fluorescent (W 3800 - 4500K)",
                15: "White fluorescent (WW 3250 - 3800K)",
                16: "Warm white fluorescent (L 2600 - 3250K)",
                17: "Standard light A", 18: "Standard light B",
                19: "Standard light C", 20: "D55", 21: "D65", 22: "D75",
                23: "D50", 24: "ISO studio tungsten", 255: "Other",
                OTHER: RES}),
        37385: ("Flash", None, {}),
        37386: ("FocalLength", None, {}),
        37396: ("SubjectArea", None, {}), # TODO SubjectArea
        41483: ("FlashEnergy", None, {}),
        41484: ("SpatialFrequencyResponse", None, {}),
        41486: ("FocalPlaneXResolution", None, {}),
        41487: ("FocalPlaneYResolution", None, {}),
        41488: ("FocalPlaneResolutionUnit", 2, {}),
        41492: ("SubjectLocation", None, {}),
        41493: ("ExposureIndex", None, {}),
        41495: ("SensingMethod", None, {1: "Not defined",
                2: "One-chip color area sensor",
                3: "Two-chip color area sensor",
                4: "Three-chip color area sensor",
                5: "Color sequential area sensor",
                7: "Trilinear sensor",
                8: "Color sequential linear sensor", OTHER: RES}),
        41728: ("FileSource", 3, {0: "Others",
                1: "Scanner of transparent type", 
                2: "Scanner of reflex type", 3: "DSC", OTHER: RES}),
        41729: ("SceneType", 1, {1: "A directly photographed image",
                OTHER: RES}),
        41730: ("CFAPattern", None, {}),
        41985: ("CustomRendered", 0, {0: "Normal Process", 1: "Custom Process",
                OTHER: RES}),
        41986: ("ExposureMode", None, {0: "Auto", 1: "Manual",
                2: "Auto bracket", OTHER: RES}),
        41987: ("WhiteBalance", None, {0: "Auto", 1: "Manual", OTHER: RES}),
        41988: ("DigitalZoomRatio", None, {}),
        41989: ("FocalLengthIn35mmFilm", None, {}),
        41990: ("SceneCaptureType", 0, {0: "Standard", 1: "Landscape",
                2: "Portrait", 3: "Night scene", OTHER: RES}),
        41991: ("GainControl", None, {0: "None", 1: "Low gain up",
                2: "High gain up", 3: "Low gain down", 4: "High gain down",
                OTHER: RES}),
        41992: ("Contrast", 0, {0: "Normal", 1: "Soft", 2: "Hard",
                OTHER: RES}),
        41993: ("Saturation", 0, {0: "Normal", 1: "Low saturation", 
                2: "High saturation", OTHER: RES}),
        41994: ("Sharpness", 0, {0: "Normal", 1: "Soft", 2: "Hard",
                OTHER: RES}),
        41995: ("DeviceSettingDescription", None, {}), # TODO
        41996: ("SubjectDistanceRange", None, {0: "Unknown", 1: "Macro",
                2: "Close view", 3: "Distant view", OTHER: RES}),
    
        # Other Tags
        42016: ("ImageUniqueID", None, {}),
        42032: ("CameraOwnerName", None, {}),
        42033: ("BodySerialNumber", None, {}),
        42034: ("LensSpecification", None, {}), # TODO
        42035: ("LensMake", None, {}),
        42036: ("LensModel", None, {}),
        42037: ("LensSerialNumber", None, {}),
    }
    EXIF_IFD = "ExifIFD",
    GPS_IFD = "GPSIFD"
    EXIF_IFD_TAGS = {
        34665: EXIF_IFD,
        34853: GPS_IFD,
    }
    BOM_LEN = 2
    BOM_BIG = "\x4d\x4d"
    BOM_LIT = "\x49\x49"
    MAGIC_NUMBER = 42
    MAGIC_LEN = 2
    IFD_OFFSET_LEN = 4
    IFD_COUNT_LEN = 2
    IFD_ENTRY_LEN = 12
    IFD_ENTRY_COUNT_LEN = 4

    def __init__(self, image, offset):
        self.image = image
        self.offset = offset
        self.bo = ">" # default to big endian
        self.ifd_entries = {}
        self._init_ifd_defaults()
        self._verify_tiff()
        self._decode_tiff_structure()

    def _init_ifd_defaults(self):
        for name, default, mapping in self.IFD_TAGS.values():
            got_default = default is not None
            if got_default:
                if mapping:
                    value = self._translate_ifd_value(mapping, default)
                else:
                    value = default
                self.ifd_entries[name] = value

    def _translate_ifd_value(self, mapping, value):
        return mapping.get(value, mapping.get(self.OTHER, value))

    def _verify_tiff(self):
        self.image.seek(self.offset)
        bom = self.image.read(self.BOM_LEN)
        if bom == self.BOM_BIG:
            self.bo = ">" # struct big endian marker
        elif bom == self.BOM_LIT:
            self.bo = "<" # struct little endian
        else:
            raise ValueError("Invalid TIFF Frame")
        magic_number = self.image.read(self.MAGIC_LEN)
        magic_number = self._unpack("H", magic_number)
        if not magic_number == self.MAGIC_NUMBER:
            raise ValueError("Invalid TIFF Frame")

    def _decode_tiff_header(self):
        self.image.seek(self.offset + self.BOM_LEN + self.MAGIC_LEN)
        ifd0_offset = self.image.read(self.IFD_OFFSET_LEN)
        ifd0_offset = self._unpack("I", ifd0_offset)
        return ifd0_offset

    def _decode_tiff_structure(self):
        ifd_offset = self._decode_tiff_header()
        self._decode_ifd(ifd_offset)

    def _decode_ifd(self, offset):
        # store file pos to make it re-entrant
        pos = self.image.tell()
        self.image.seek(self.offset + offset)
        count = self._unpack("H", self.image.read(self.IFD_COUNT_LEN))
        for i in xrange(count):
            self._decode_ifd_entry(self.image.read(self.IFD_ENTRY_LEN))
        next_offset = self.image.read(self.IFD_OFFSET_LEN)
        next_offset = self._unpack("I", next_offset)
        self.image.seek(pos)

    def _decode_ifd_entry(self, bytes):
        tag, typ, count = self._unpack("HHI", bytes[:8])
        value = self._decode_value(typ, bytes[8:], count)
        self._handle_ifd_entry(tag, typ, count, value)

    def _decode_value(self, typ, bytes, count):
        if typ == 7: # undefined
            return bytes
        fmt, size, _, parse_fn = self.IFD_TYPES[typ]
        byte_len = size * count
        if byte_len > self.IFD_ENTRY_COUNT_LEN:
            pos = self.image.tell()
            self.image.seek(self.offset + self._unpack("I", bytes))
            bytes = self.image.read(byte_len)
            self.image.seek(pos)
        if typ == 2: # ascii
            fmt = "%d%s" % (count, fmt)
        else:
            fmt = fmt * count
        value = self._unpack(fmt, bytes[:byte_len])
        if parse_fn:
            value = parse_fn(value)
        return value

    def _handle_ifd_entry(self, tag, typ, count, value):
        if tag in self.EXIF_IFD_TAGS:
            if tag == 34853:
                # print "skipping GPS"
                return
            self._decode_ifd(value)
        else:
            self._store_ifd_entry(tag, typ, count, value)

    def _store_ifd_entry(self, tag, typ, count, value):
        name, default, mapping = self.IFD_TAGS.get(tag, ("NA-0x%x" % tag,
                                                   None, {}))
        value = self._translate_ifd_value(mapping, value)
        self.ifd_entries[name] = value

    def _unpack(self, format, value):
        val = struct.unpack(self.bo + format, value)
        return val if len(val) > 1 else val[0] 


FIELDS = sorted([field for _, (field, _, _) in TIFFStructure.IFD_TAGS.items()])