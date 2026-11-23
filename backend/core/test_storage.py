import io

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.models import StoredFile
from core.storage import DatabaseStorage


User = get_user_model()

DATABASE_STORAGES = {
    "default": {"BACKEND": "core.storage.DatabaseStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}


def png_bytes(color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, format="PNG")
    return buffer.getvalue()


class DatabaseStorageTests(TestCase):
    def setUp(self):
        self.storage = DatabaseStorage()

    def test_salvar_ler_e_apagar(self):
        name = self.storage.save("fotos/a.txt", ContentFile(b"conteudo"))

        self.assertTrue(self.storage.exists(name))
        self.assertEqual(self.storage.size(name), 8)
        with self.storage.open(name) as file:
            self.assertEqual(file.read(), b"conteudo")

        self.storage.delete(name)
        self.assertFalse(self.storage.exists(name))

    def test_nome_repetido_ganha_nome_novo(self):
        first = self.storage.save("fotos/a.txt", ContentFile(b"1"))
        second = self.storage.save("fotos/a.txt", ContentFile(b"2"))

        self.assertNotEqual(first, second)
        self.assertEqual(StoredFile.objects.count(), 2)

    def test_arquivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            self.storage.open("nao/existe.png")


@override_settings(STORAGES=DATABASE_STORAGES)
class ProfilePhotoInDatabaseTests(APITestCase):
    """O fluxo da foto de perfil funciona com os arquivos guardados no banco."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Viagem!2026Segura",
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def upload(self, color):
        return self.client.patch(
            "/api/auth/me/photo/",
            {
                "photo": SimpleUploadedFile(
                    "foto.png", png_bytes(color), content_type="image/png"
                )
            },
            format="multipart",
        )

    def test_enviar_consultar_trocar_e_remover_foto(self):
        response = self.upload("red")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StoredFile.objects.count(), 1)

        response = self.client.get("/api/auth/me/photo/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertEqual(b"".join(response.streaming_content)[:4], b"\x89PNG")

        # Trocar a foto apaga a anterior.
        self.upload("blue")
        self.assertEqual(StoredFile.objects.count(), 1)

        response = self.client.delete("/api/auth/me/photo/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StoredFile.objects.exists())
        self.assertEqual(self.client.get("/api/auth/me/photo/").status_code, 404)
