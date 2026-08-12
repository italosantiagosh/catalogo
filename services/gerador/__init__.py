# Gerador de mockups de medalha, portado sem alteracoes do repositorio
# `mockup` (ja em producao em gerador-medalhas.onrender.com). A unica
# mudanca em relacao ao original e o import relativo em compositor.py
# (era `from config import ...`, agora `from .config import ...`) para
# funcionar como pacote dentro deste projeto -- a logica de composicao
# em si (compositor.py) e a geometria calibrada (config.py) sao identicas.
