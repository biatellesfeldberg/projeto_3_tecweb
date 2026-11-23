from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseStorage(Storage):
    """Storage do Django que guarda os arquivos no banco (modelo StoredFile).

    Ativada com DJANGO_MEDIA_STORAGE=database (veja config/settings.py).
    Os arquivos não têm URL pública: as fotos de perfil são entregues pelo
    endpoint autenticado GET /api/auth/me/photo/.
    """

    def _model(self):
        # Importação tardia: o storage é criado antes dos apps carregarem.
        from .models import StoredFile

        return StoredFile

    def _open(self, name, mode="rb"):
        stored = self._model().objects.filter(name=name).first()
        if stored is None:
            raise FileNotFoundError(name)
        return ContentFile(bytes(stored.content), name=name)

    def _save(self, name, content):
        if hasattr(content, "seek"):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()

        self._model().objects.update_or_create(
            name=name,
            defaults={"content": data, "size": len(data)},
        )
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        stored = self._model().objects.filter(name=name).only("size").first()
        if stored is None:
            raise FileNotFoundError(name)
        return stored.size

    def url(self, name):
        raise NotImplementedError(
            "Arquivos no banco não têm URL pública; use o endpoint da API."
        )
