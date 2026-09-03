"""
Teste de fumaca do pipeline de composicao do gerador de medalha
personalizada -- portado sem alteracoes do repositorio `mockup`
(so o import mudou de absoluto para `services.gerador.*`).

Nao usa os assets reais: gera em memoria uma base e uma resina
SINTETICAS (formas simples desenhadas com Pillow, so para validar a
mecanica de alpha compositing, recorte 'cover' e mascara circular) e
uma foto de teste. Serve para provar que o pipeline roda de ponta a
ponta; nao substitui a calibracao visual com os arquivos reais
(base_medalha.png / efeito_resina.png).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from services.gerador.compositor import compose_medal, fit_cover_circle
from services.gerador.config import MEDAL_SPECS, MedalSpec, get_medal_spec


def _make_synthetic_base(path: Path, size=(800, 900), center=(400, 490), radius=310, thickness=45):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=(190, 190, 195, 255))
    inner = radius - thickness
    draw.ellipse((cx - inner, cy - inner, cx + inner, cy + inner), fill=(0, 0, 0, 0))
    # argola simples no topo
    draw.ellipse((cx - 40, cy - radius - 70, cx + 40, cy - radius + 10),
                  outline=(190, 190, 195, 255), width=18)
    img.save(path)
    return center, inner


def _make_synthetic_resina(path: Path, size=(800, 900), center=(400, 490), radius=265):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = center
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                 fill=(255, 255, 255, 40))
    draw.ellipse((cx - radius * 0.4, cy - radius * 0.6, cx + radius * 0.05, cy - radius * 0.1),
                 fill=(255, 255, 255, 90))
    img.save(path)


def _make_test_photo(path: Path, size=(1600, 1000)):
    img = Image.new("RGB", size, (30, 30, 30))
    draw = ImageDraw.Draw(img)
    for i in range(0, size[0], 40):
        draw.line((i, 0, i, size[1]), fill=(200, 40, 40))
    draw.rectangle((0, 0, 60, 60), fill=(0, 255, 0))  # marca no canto p/ checar crop
    img.save(path)


class TestCompositor(unittest.TestCase):
    def test_pipeline_ponta_a_ponta(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            base_path = tmp / "base_medalha.png"
            resina_path = tmp / "efeito_resina.png"
            foto_path = tmp / "foto.jpg"

            center, inner_radius = _make_synthetic_base(base_path)
            _make_synthetic_resina(resina_path)
            _make_test_photo(foto_path)

            spec = MedalSpec(
                id="sintetica_teste",
                nome="Fixture sintetica de teste",
                base_path=base_path,
                resina_path=resina_path,
                center_x=center[0],
                center_y=center[1],
                inner_radius=inner_radius,
                overlap_px=1.0,
            )

            resultado = compose_medal(spec, foto_path)

            with Image.open(base_path) as base_img:
                self.assertEqual(resultado.size, base_img.size)
            self.assertEqual(resultado.mode, "RGBA")

            # centro deve estar preenchido pela foto (nao branco, nao transparente)
            cx, cy = int(center[0]), int(center[1])
            r, g, b, a = resultado.getpixel((cx, cy))
            self.assertEqual(a, 255)
            self.assertFalse((r, g, b) == (255, 255, 255))

            # fora da medalha (canto do canvas) deve continuar branco
            r, g, b, a = resultado.getpixel((5, 5))
            self.assertEqual((r, g, b, a), (255, 255, 255, 255))

            # nao deve haver anel vazio: logo dentro do raio interno (a poucos
            # px da parede) o pixel deve estar opaco (foto ou resina), nao
            # branco/transparente
            edge_x = int(cx + inner_radius - 3)
            r, g, b, a = resultado.getpixel((edge_x, cy))
            self.assertEqual(a, 255)

    def test_fit_cover_circle_nao_deforma_e_cobre_totalmente(self):
        img = Image.new("RGB", (400, 100), (10, 20, 30))
        out = fit_cover_circle(img, 250)
        self.assertEqual(out.size, (250, 250))
        # centro do circulo tem que estar opaco (coberto), cantos tem que
        # estar transparentes (fora do circulo, mascara aplicada)
        self.assertEqual(out.getpixel((125, 125))[3], 255)
        self.assertEqual(out.getpixel((2, 2))[3], 0)


class TestMedalSpecsCadastradas(unittest.TestCase):
    """Roda o pipeline REAL (assets de verdade em services/gerador/assets/)
    pra cada base cadastrada em MEDAL_SPECS -- pega cedo se um asset for
    renomeado/removido ou se a geometria calibrada ficar fora dos limites
    da propria base (nao substitui conferencia visual, so evita quebra
    silenciosa)."""

    def test_todas_as_bases_cadastradas_compoem_sem_erro(self):
        with tempfile.TemporaryDirectory() as tmp:
            foto_path = Path(tmp) / "foto.jpg"
            _make_test_photo(foto_path, size=(600, 600))
            for medal_id in MEDAL_SPECS:
                spec = get_medal_spec(medal_id)
                resultado = compose_medal(spec, foto_path)
                with Image.open(spec.base_path) as base_img:
                    self.assertEqual(resultado.size, base_img.size, msg=medal_id)
                geo = spec.resolve(resultado.size)
                cx, cy = int(geo.center_x), int(geo.center_y)
                r, g, b, a = resultado.getpixel((cx, cy))
                self.assertEqual(a, 255, msg=f"{medal_id}: centro deveria estar opaco (foto)")

    def test_medalha_2lados_resina_maior_que_foto_meia_espessura_da_borda(self):
        """Pedido explicito do usuario: a foto encosta so no espaco branco,
        mas a resina avanca ate a metade da espessura da borda metalica --
        ver comentario de calibracao em services/gerador/config.py."""
        for medal_id in ("medalha_2lados_prata", "medalha_2lados_ouro_velho", "chaveiro_2lados"):
            spec = get_medal_spec(medal_id)
            self.assertIsNotNone(spec.resina_radius)
            self.assertGreater(spec.resina_radius, spec.inner_radius)


if __name__ == "__main__":
    unittest.main()
