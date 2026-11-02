"""Fotos dos anúncios no Supabase Storage: o banco guarda só o link público."""
import logging
import uuid

import requests

from ..config import SUPABASE_BUCKET, SUPABASE_SERVICE_KEY, SUPABASE_URL
from ..erros import ErroArmazenamento, ErroValidacao

log = logging.getLogger(__name__)

MAX_FOTOS = 5
MAX_BYTES = 5 * 1024 * 1024
TEMPO_LIMITE = 30


def _tipo_imagem(conteudo):
    """Reconhece o tipo pelo conteúdo do arquivo, não pelo nome que o usuário enviou."""
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


def _cabecalhos():
    cabecalhos = {"apikey": SUPABASE_SERVICE_KEY}
    if SUPABASE_SERVICE_KEY.startswith("eyJ"):  # chaves antigas (JWT) também vão no Authorization
        cabecalhos["Authorization"] = f"Bearer {SUPABASE_SERVICE_KEY}"
    return cabecalhos


def _validar(arquivos):
    if len(arquivos) > MAX_FOTOS:
        raise ErroValidacao(f"Envie no máximo {MAX_FOTOS} fotos.")
    tipos = []
    for conteudo in arquivos:
        if len(conteudo) > MAX_BYTES:
            raise ErroValidacao("Cada foto pode ter no máximo 5 MB.")
        tipo = _tipo_imagem(conteudo)
        if tipo is None:
            raise ErroValidacao("As fotos precisam ser JPG, PNG ou WebP.")
        tipos.append(tipo)
    return tipos


def _descrever_falha(erro):
    """Resume a falha para o terminal: o código HTTP distingue chave errada de problema de rede."""
    if erro.response is not None:
        return f"HTTP {erro.response.status_code}: {erro.response.text[:200]}"
    return f"{type(erro).__name__}: {erro}"


def enviar_fotos(arquivos):
    """Envia os arquivos (bytes) e devolve os links públicos; se um falhar, apaga os já enviados."""
    tipos = _validar(arquivos)
    if not arquivos:
        return []
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ErroArmazenamento("O envio de fotos não está configurado. Publique sem fotos por enquanto.")

    urls = []
    try:
        for conteudo, (extensao, mime) in zip(arquivos, tipos):
            caminho = f"anuncios/{uuid.uuid4().hex}.{extensao}"
            resposta = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{caminho}",
                headers={**_cabecalhos(), "Content-Type": mime},
                data=conteudo,
                timeout=TEMPO_LIMITE,
            )
            resposta.raise_for_status()
            urls.append(f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{caminho}")
    except requests.RequestException as e:
        log.error("Falha ao enviar foto ao Supabase Storage: %s", _descrever_falha(e))
        remover_fotos(urls)
        raise ErroArmazenamento("Não foi possível enviar as fotos. Tente novamente.") from e
    return urls


def remover_fotos(urls):
    """Apaga do bucket as fotos que não são mais usadas; falhar aqui só deixa um arquivo sem uso."""
    prefixo = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/"
    urls = [u for u in urls if u.startswith(prefixo)]  # fotos antigas não estão no bucket
    if not urls or not SUPABASE_SERVICE_KEY:
        return
    try:
        requests.delete(
            f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}",
            headers=_cabecalhos(),
            json={"prefixes": [u.removeprefix(prefixo) for u in urls]},
            timeout=TEMPO_LIMITE,
        )
    except requests.RequestException:
        pass
