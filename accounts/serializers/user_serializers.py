from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class PenggunaSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'nama_lengkap', 'telepon', 'peran', 'status']

class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'nama_lengkap', 'telepon', 
            'alamat', 'no_ktp', 'jenis_kelamin', 'kota_kab', 
            'password', 'peran'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'id': {'read_only': True},
            'email': {
                'error_messages': {
                    'unique': 'Gagal: Email ini sudah digunakan oleh akun lain.'
                }
            },
            'username': {
                'error_messages': {
                    'unique': 'Gagal: Username ini sudah terdaftar.'
                }
            }
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance