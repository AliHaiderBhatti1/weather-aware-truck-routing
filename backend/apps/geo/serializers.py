from rest_framework import serializers


class GeocodeQuerySerializer(serializers.Serializer[dict[str, object]]):
    q = serializers.CharField(min_length=2, max_length=200, trim_whitespace=True)
    limit = serializers.IntegerField(min_value=1, max_value=10, default=5)


class PlaceSerializer(serializers.Serializer[dict[str, object]]):
    name = serializers.CharField()
    full_name = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    kind = serializers.CharField()
