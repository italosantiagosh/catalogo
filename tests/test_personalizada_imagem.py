from __future__ import annotations

from pathlib import Path

from PIL import Image

import app as app_module


def _salvar_jpg(tmp_path: Path, largura: int, altura: int) -> Path:
    caminho = tmp_path / "foto.jpg"
    Image.new("RGB", (largura, altura), (10, 20, 30)).save(caminho, quality=95)
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
    caminho = _salvar_jpg(tmp_path, 8000, 4000)  # maior lado = 8000, fator = 2400/8000 = 0.3
    box = (1000.0, 500.0, 5000.0, 4500.0)

    box_devolvido = app_module._reduzir_temp_se_grande_demais(caminho, box)

    with Image.open(caminho) as imagem:
        assert imagem.size == (2400, 1200)

    fator = 2400 / 8000
    assert box_devolvido == tuple(v * fator for v in box)


def test_box_none_continua_none_apos_reduzir(tmp_path):
    caminho = _salvar_jpg(tmp_path, 8000, 8000)
    assert app_module._reduzir_temp_se_grande_demais(caminho, None) is None
    with Image.open(caminho) as imagem:
        assert max(imagem.size) == 2400


def test_imagem_grande_sem_exif_preserva_orientacao(tmp_path):
    """Imagem retrato (altura > largura) reduzida continua com a mesma
    proporcao -- o lado MAIOR e´ que fica limitado a
    _FOTO_PERSONALIZADA_LADO_MAXIMO, nao os dois lados iguais."""
    caminho = _salvar_jpg(tmp_path, 3000, 9000)

    app_module._reduzir_temp_se_grande_demais(caminho, None)

    with Image.open(caminho) as imagem:
        assert imagem.size == (800, 2400)
