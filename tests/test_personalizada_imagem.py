from __future__ import annotations

from pathlib import Path

import pytest
from PIL import ExifTags, Image

import app as app_module


def _salvar_jpg(tmp_path: Path, largura: int, altura: int) -> Path:
    caminho = tmp_path / "foto.jpg"
    Image.new("RGB", (largura, altura), (10, 20, 30)).save(caminho, quality=95)
    return caminho


def _salvar_jpg_com_orientacao(tmp_path: Path, largura: int, altura: int, orientacao: int) -> Path:
    """Mesma coisa que _salvar_jpg, mas com uma tag EXIF Orientation
    embutida -- `largura`/`altura` sao os pixels CRUS do arquivo (antes
    da rotacao), igual uma foto de celular sai da camera."""
    caminho = tmp_path / "foto_rotada.jpg"
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = orientacao
    Image.new("RGB", (largura, altura), (10, 20, 30)).save(caminho, quality=95, exif=exif)
    return caminho


def test_imagem_pequena_nao_e_mexida(tmp_path):
    """Sem isso, todo upload seria reprocessado/recomprimido a toa --
    so precisa reduzir quem realmente passa do limite (ver conversa,
    alerta real do Render de estouro de memoria)."""
    caminho = _salvar_jpg(tmp_path, 800, 600)
    box = (10.0, 20.0, 500.0, 510.0)

    box_devolvido = app_module._reduzir_temp_se_grande_demais(caminho, box)

    assert box_devolvido == box
    with Image.open(caminho) as imagem:
        assert imagem.size == (800, 600)


def test_imagem_grande_e_reduzida_e_box_escalado_junto(tmp_path):
    """O crop_box vem em pixels da imagem ORIGINAL (ver
    services/gerador/compositor.py:crop_to_box) -- precisa escalar na
    MESMA proporcao que a imagem encolheu, senao o recorte manual do
    cliente sai deslocado."""
    limite = app_module._FOTO_PERSONALIZADA_LADO_MAXIMO
    caminho = _salvar_jpg(tmp_path, 8000, 4000)  # maior lado = 8000
    box = (1000.0, 500.0, 5000.0, 4500.0)

    box_devolvido = app_module._reduzir_temp_se_grande_demais(caminho, box)

    fator = limite / 8000
    with Image.open(caminho) as imagem:
        assert imagem.size == (limite, round(4000 * fator))

    assert box_devolvido == tuple(v * fator for v in box)


def test_imagem_com_mais_de_80mp_e_rejeitada_antes_de_decodificar(tmp_path):
    """Foto absurdamente grande (modo especial de camera, nao o padrao
    de nenhum celular comum) e´ rejeitada com erro tratavel ANTES de
    tentar decodificar -- pra HEIC nao tem draft() disponivel (so
    ajuda JPEG), entao exif_transpose() decodificaria a foto inteira
    em memoria sem essa checagem (ver conversa: 2 quedas reais do
    Render no mesmo dia com pico quase vertical no grafico de
    memoria)."""
    caminho = tmp_path / "gigante.jpg"
    Image.new("RGB", (10000, 8500), (10, 20, 30)).save(caminho, quality=85)  # 85MP

    with pytest.raises(ValueError, match="grande demais"):
        app_module._reduzir_temp_se_grande_demais(caminho, None)


def test_box_none_continua_none_apos_reduzir(tmp_path):
    caminho = _salvar_jpg(tmp_path, 8000, 8000)
    assert app_module._reduzir_temp_se_grande_demais(caminho, None) is None
    with Image.open(caminho) as imagem:
        assert max(imagem.size) == app_module._FOTO_PERSONALIZADA_LADO_MAXIMO


def test_imagem_grande_sem_exif_preserva_orientacao(tmp_path):
    """Imagem retrato (altura > largura) reduzida continua com a mesma
    proporcao -- o lado MAIOR e´ que fica limitado a
    _FOTO_PERSONALIZADA_LADO_MAXIMO, nao os dois lados iguais."""
    limite = app_module._FOTO_PERSONALIZADA_LADO_MAXIMO
    caminho = _salvar_jpg(tmp_path, 3000, 9000)

    app_module._reduzir_temp_se_grande_demais(caminho, None)

    with Image.open(caminho) as imagem:
        assert imagem.size == (round(3000 * limite / 9000), limite)


def test_imagem_grande_com_exif_rotacionado_escala_box_no_lado_certo(tmp_path):
    """Foto de celular com EXIF Orientation=6 (rotaciona 90/270) tem
    largura/altura TROCADAS depois da correcao -- o arquivo cru e´
    paisagem (8000x4000) mas o resultado visual/corrigido e´ retrato
    (4000x8000). O `box` do cliente vem nesse referencial JA´ corrigido
    (mesmo que exif_transpose produz), entao o fator de escala e o
    tamanho final tem que usar 8000 (a altura CORRIGIDA) como maior
    lado, nao 8000 achando que e´ a largura crua -- e´ exatamente o que
    o draft() (que muda o `.size` aparente do arquivo pra decodificar
    mais rapido) podia bagunçar se lido na hora errada."""
    limite = app_module._FOTO_PERSONALIZADA_LADO_MAXIMO
    caminho = _salvar_jpg_com_orientacao(tmp_path, 8000, 4000, orientacao=6)
    box = (500.0, 1000.0, 3500.0, 7000.0)  # ja´ no referencial corrigido (4000x8000)

    box_devolvido = app_module._reduzir_temp_se_grande_demais(caminho, box)

    fator = limite / 8000  # maior lado CORRIGIDO e´ 8000 (a altura, depois de trocar)
    with Image.open(caminho) as imagem:
        assert imagem.size == (round(4000 * fator), limite)

    assert box_devolvido == tuple(v * fator for v in box)
