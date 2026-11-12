from django.test import TestCase

# Create your tests here.
import io
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


User = get_user_model()


class ProfileTests(APITestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)

        settings_override = override_settings(
            MEDIA_ROOT=self.media.name,
        )
        settings_override.enable()
        self.addCleanup(settings_override.disable)

        self.user = User.objects.create_user(
            username="bia",
            email="bia@example.com",
            password="Viagem!2026Segura",
            first_name="Bia",
        )

        self.other_user = User.objects.create_user(
            username="ana",
            email="ana@example.com",
            password="Outra!Senha2026Segura",
            first_name="Ana",
        )

        token = Token.objects.create(user=self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {token.key}",
        )

    def test_consultar_perfil(self):
        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["interests"], [])
        self.assertNotIn("password", response.data)

    def test_atualizar_apenas_o_proprio_perfil(self):
        response = self.client.patch(
            "/api/auth/me/",
            {
                "first_name": "Beatriz",
                "interests": ["culture", "gastronomy"],
                "style": "intermediate",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.other_user.refresh_from_db()

        self.assertEqual(self.user.first_name, "Beatriz")
        self.assertEqual(self.other_user.first_name, "Ana")
        self.assertEqual(
            self.user.interests,
            ["culture", "gastronomy"],
        )

    def test_atualizacao_parcial_preserva_outros_dados(self):
        self.user.interests = ["beach"]
        self.user.save()

        response = self.client.patch(
            "/api/auth/me/",
            {"home_city": "Santos"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(self.user.home_city, "Santos")
        self.assertEqual(self.user.interests, ["beach"])

    def test_rejeitar_preferencia_invalida(self):
        response = self.client.patch(
            "/api/auth/me/",
            {"style": "opcao_inexistente"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejeitar_alteracao_de_campo_protegido(self):
        response = self.client.patch(
            "/api/auth/me/",
            {"is_staff": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.user.refresh_from_db()

        self.assertFalse(self.user.is_staff)

    def test_exigir_autenticacao(self):
        self.client.credentials()

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 401)

    def test_enviar_e_remover_foto(self):
        buffer = io.BytesIO()

        Image.new(
            "RGB",
            (20, 20),
            color="blue",
        ).save(buffer, format="PNG")

        photo = SimpleUploadedFile(
            "foto.png",
            buffer.getvalue(),
            content_type="image/png",
        )

        response = self.client.patch(
            "/api/auth/me/photo/",
            {"photo": photo},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        filename = self.user.photo.name
        storage = self.user.photo.storage

        self.assertTrue(storage.exists(filename))

        response = self.client.delete("/api/auth/me/photo/")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["photo"])
        self.assertFalse(storage.exists(filename))