from rest_framework import serializers


class FirebaseTokenVerifySerializer(serializers.Serializer):
    token = serializers.CharField(required=True, help_text="Firebase ID Token")
    role = serializers.ChoiceField(choices=["CITIZEN", "COLLECTOR", "ADMIN"], default="CITIZEN")
    name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True)


class FirebaseUserSyncSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.CharField(required=False, default="CITIZEN")
