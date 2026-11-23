from django.db import models


class StoredFile(models.Model):
    """Arquivo enviado (ex.: foto de perfil) guardado no banco de dados.

    Usado em produção pela DatabaseStorage (core/storage.py): no plano
    gratuito do Render o disco do servidor é apagado a cada reinício, então
    os arquivos ficam no PostgreSQL junto com o resto dos dados.
    """

    name = models.CharField("nome", max_length=255, unique=True)
    content = models.BinaryField("conteúdo")
    size = models.PositiveIntegerField("tamanho (bytes)")
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "arquivo armazenado"
        verbose_name_plural = "arquivos armazenados"

    def __str__(self):
        return self.name
