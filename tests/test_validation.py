from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from app.utils.validators import validate_image, valid_coordinates, validate_password


def test_coordinates_validation():
    assert valid_coordinates('18.52', '73.85')
    assert not valid_coordinates('999', '73.85')
    assert not valid_coordinates('x', '73.85')


def test_password_validation():
    assert validate_password('abcdefgh')[0]
    assert not validate_password('short')[0]


def test_image_extension_mime_validation():
    good = SimpleNamespace(filename='test.jpg', mimetype='image/jpeg')
    bad_ext = SimpleNamespace(filename='test.exe', mimetype='application/octet-stream')
    assert validate_image(good)[0]
    assert not validate_image(bad_ext)[0]
