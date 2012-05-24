# About

Simple JPEG Exif data reader in pure Python

```python
import vogel

with open("/Users/jacobk/lolwut.jpeg", "rb") as picture_file:
  exif = vogel.jpeg.Exif(picture_file)
  try:
    exif_time = exif["DateTimeDigitized"]
  except ValueError:
    print "Invalid EXIF data :("
  except KeyError:
    print "No DateTimeDigitized data :("
    
# Supported fields
print vogel.FIELDS
```

## License

vogel is release under the Apache License, Version 2.0
