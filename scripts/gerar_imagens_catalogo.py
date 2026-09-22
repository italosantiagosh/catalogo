"""
Gera as 7 variantes de imagem de um modelo do catalogo (medalha, entremeio
prata/ouro velho, chaveiro, e as versoes "2 lados" de cada uma) a partir de
UMA imagem de arte fornecida -- usando exatamente o mesmo compose_medal()
que gera as previas de peca personalizada (ver services/gerador/compositor.py
e conversa 2026-09-22: as fotos do catalogo SEMPRE foram compostas assim,
nunca fotografadas prontas).

Uso:
    python -m scripts.gerar_imagens_catalogo <arte.jpg> <prefixo-arquivo> [--crop x1,y1,x2,y2]

Exemplo (Sagrado Coracao de Jesus, modelo 2):
    python -m scripts.gerar_imagens_catalogo \\
        data/IMG_6210.jpeg \\
        sagrado_coracao_de_jesus_modelo_2 \\
        --crop 0,20,720,740

Sem --crop, usa o recorte quadrado automatico centralizado (auto_cover_box),
igual ao que acontece quando o cliente nao mexe no editor de recorte.

Grava direto em static/img/produtos/<prefixo>_<sufixo>.jpg (JPEG, mesmo
formato dos arquivos existentes -- compose_medal devolve RGBA mas o canvas
ja nasce 100% opaco por baixo, entao converter pra RGB e seguro).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from services.gerador.compositor import compose_medal
from services.gerador.config import MEDAL_SPECS

BASE_DIR = Path(__file__).resolve().parent.parent
SAIDA_DIR = BASE_DIR / "static" / "img" / "produtos"

# spec_id -> sufixo do nome de arquivo, na mesma ordem/nomenclatura usada
# pelos campos de imagem em data/produtos.json.
VARIANTES: dict[str, str] = {
    "prata_16mm": "_medalha",
    "entremeio_prata": "_entremeio_prata",
    "entremeio_ouro_velho": "_entremeio_ouro_velho",
    "chaveiro": "_chaveiro",
    "medalha_2lados_prata": "_medalha_2lados_prata",
    "medalha_2lados_ouro_velho": "_medalha_2lados_ouro_velho",
    "chaveiro_2lados": "_chaveiro_2lados",
}


def gerar(arte_path: Path, prefixo: str, crop_box: tuple[float, float, float, float] | None) -> list[Path]:
    gerados = []
    for spec_id, sufixo in VARIANTES.items():
        spec = MEDAL_SPECS[spec_id]
        resultado = compose_medal(spec, arte_path, crop_box=crop_box)
        destino = SAIDA_DIR / f"{prefixo}{sufixo}.jpg"
        resultado.convert("RGB").save(destino, format="JPEG", quality=92)
        gerados.append(destino)
    return gerados


def _parse_crop(valor: str | None) -> tuple[float, float, float, float] | None:
    if not valor:
        return None
    partes = [float(p) for p in valor.split(",")]
    if len(partes) != 4:
        raise argparse.ArgumentTypeError("--crop precisa de 4 numeros: x1,y1,x2,y2")
    return tuple(partes)  # type: ignore[return-value]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arte", type=Path, help="Caminho da imagem de arte (ex: data/IMG_6210.jpeg)")
    parser.add_argument("prefixo", help="Prefixo do nome de arquivo (ex: sagrado_coracao_de_jesus_modelo_2)")
    parser.add_argument("--crop", type=str, default=None, help="x1,y1,x2,y2 em pixels da imagem original")
    args = parser.parse_args()

    crop_box = _parse_crop(args.crop)
    gerados = gerar(args.arte, args.prefixo, crop_box)
    for caminho in gerados:
        print(f"gerado: {caminho.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
