from rest_framework import serializers

from .catalog import normalize_district, normalize_taluk, place_label


def clean_place_text(value, label, max_length):
    text = ' '.join(str(value or '').split())
    if not text:
        raise serializers.ValidationError(f'{label} is required.')
    if len(text) > max_length:
        raise serializers.ValidationError(f'{label} must be {max_length} characters or fewer.')
    return text


def official_district(value):
    text = clean_place_text(value, 'District', 100)
    official = normalize_district(text)
    if not official:
        raise serializers.ValidationError('Choose an official Karnataka or Maharashtra district.')
    return official


def official_taluk(district, value, required=False):
    text = ' '.join(str(value or '').split())
    if not text:
        if required:
            raise serializers.ValidationError('Choose an official taluk for that district.')
        return ''
    if len(text) > 120:
        raise serializers.ValidationError('Taluk must be 120 characters or fewer.')
    official = normalize_taluk(district, text)
    if not official:
        raise serializers.ValidationError('Choose an official taluk for that district.')
    return official


def official_locality(value):
    return clean_place_text(value, 'Locality', 120)


def display_place(locality, taluk, district):
    return place_label(locality, taluk, district)
