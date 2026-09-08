"""
Landing pages por publico/uso (/para/<slug>, ver app.py e
templates/landing.html) -- paginas de intencao, diferente do /blog
(narrativa sobre um santo) e do /atendimento (suporte/politicas): aqui
o objetivo e´ alguem que chega procurando "medalha pra casamento" ou
"medalha pra revender" achar rapido os produtos certos pro uso dela e
ir direto pro carrinho.

Mesmo espirito do services/blog.py (dict estatico, sem banco, corpo_html
pronto), mas cada pagina cita VARIOS produtos (nao um santo so) --
"produtos_destaque" e´ so pra validar nos testes que os ids citados no
corpo realmente existem no catalogo (ver tests/test_landing_paginas.py),
o link de verdade fica embutido no proprio corpo_html.

Escolha dos produtos citados: conferida contra data/produtos.json de
proposito (ex: NAO existe produto "Anjo da Guarda" no catalogo hoje,
entao nenhuma pagina promete um -- so cita o que realmente da pra
comprar).
"""

from __future__ import annotations

PAGINAS_LANDING = {
    "casamentos": {
        "titulo": "Medalhas para Casamento",
        "resumo": (
            "Lembrancinhas de casamento, presente para os noivos ou medalha "
            "personalizada do casal -- veja as opções e o desconto por quantidade."
        ),
        "corpo_html": """
            <p>Medalha católica é uma lembrancinha de casamento que foge do óbvio (sem
            perder o significado) e também um presente forte pros próprios noivos. Como o
            desconto de atacado entra sozinho a partir de certa quantidade, dá pra comprar
            uma peça só pro casal ou várias dezenas pra distribuir na cerimônia -- o preço
            por unidade cai conforme a quantidade total, sem cupom.</p>

            <h2>Pra lembrancinha dos convidados</h2>
            <p>A <a href="/produto/bodas-de-cana">medalha de Bodas de Caná</a> é a escolha
            mais direta pro tema: o primeiro milagre de Jesus foi justamente num casamento,
            a pedido de sua mãe. Uma opção que também funciona bem em quantidade, com
            significado ligado à união e à família.</p>

            <h2>Pros padroeiros do casamento</h2>
            <p>Os <a href="/produto/pais-de-teresinha">Pais de Santa Teresinha</a> (São Luís
            e Santa Zélia Martin) são um dos poucos casais canonizados JUNTOS, como casal, pela
            Igreja -- referência direta pra quem procura um padroeiro do matrimônio. A
            <a href="/produto/sagrada-familia">medalha da Sagrada Família</a> segue a mesma
            linha, pedindo proteção pro novo lar que está se formando.</p>

            <h2>Uma peça só do casal</h2>
            <p>Pra um presente mais pessoal (padrinhos, madrinhas, ou os próprios noivos),
            dá pra <a href="/personalizada">criar uma medalha personalizada</a> com a foto do
            casal, a data do casamento ou uma frase -- você vê a simulação antes de fechar o
            pedido.</p>

            <div class="cta-blog-produto">
              <p>Veja todas as opções e o desconto por quantidade</p>
              <a href="/catalogo" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
        "produtos_destaque": ["bodas-de-cana", "pais-de-teresinha", "sagrada-familia"],
    },
    "batizados": {
        "titulo": "Medalhas para Batizado",
        "resumo": (
            "Medalha personalizada com o nome do bebê ou medalha do santo escolhido "
            "-- lembrancinha e presente de batizado com desconto por quantidade."
        ),
        "corpo_html": """
            <p>Duas formas de escolher a medalha de batizado: pelo santo (o nome de
            batismo da criança, ou um santo de devoção da família) ou personalizada, com o
            nome e a data gravados na própria peça.</p>

            <h2>Pelo nome do santo</h2>
            <p>Se o bebê já tem nome de batismo definido, o jeito mais direto é buscar o
            santo correspondente direto no <a href="/catalogo">catálogo completo</a> (mais
            de 130 santos e devoções) -- é comum encontrar até mais de uma versão do mesmo
            santo, quando existem diferentes representações.</p>

            <h2>Opções que costumam ser escolhidas pra criança</h2>
            <p>Quando a família prefere uma devoção mais geral em vez do nome específico,
            <a href="/produto/nossa-senhora-toda-pequena">Nossa Senhora Toda Pequena</a> e
            <a href="/produto/santa-teresinha-crianca">Santa Teresinha Criança</a> retratam a
            santa ainda menina, e os <a href="/produto/santos-arcanjos">Santos Arcanjos</a>
            (Miguel, Gabriel e Rafael) são uma escolha tradicional de proteção.</p>

            <h2>Personalizada com o nome e a data</h2>
            <p>Pra uma lembrança mais única, dá pra <a href="/personalizada">criar uma
            medalha personalizada</a> com o nome do bebê, a data do batizado ou uma foto --
            uma peça que registra aquele dia específico, não só o santo escolhido.</p>

            <div class="cta-blog-produto">
              <p>Compre uma peça ou várias, o desconto entra sozinho por quantidade</p>
              <a href="/catalogo" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
        "produtos_destaque": ["nossa-senhora-toda-pequena", "santa-teresinha-crianca", "santos-arcanjos"],
    },
    "retiros-espirituais": {
        "titulo": "Medalhas para Retiro Espiritual",
        "resumo": (
            "Lembrancinha de retiro em quantidade: kit pronto ou medalhas avulsas "
            "de diferentes santos, com desconto automático por quantidade."
        ),
        "corpo_html": """
            <p>Retiro costuma reunir gente com devoções bem diferentes entre si -- por
            isso, em vez de fechar num santo só, muitos grupos preferem levar um
            <strong>sortimento</strong> de medalhas e deixar cada participante escolher a
            sua no final.</p>

            <h2>Kit pronto, sem precisar montar sozinho</h2>
            <p>O <a href="/kit-livraria-shalom">Kit Livraria Shalom</a> já vem com um
            sortimento dos santos que mais vendem, em quantidades editáveis -- é o jeito
            mais rápido de sair com uma leva variada pronta pra distribuir, sem escolher
            santo por santo.</p>

            <h2>Montando você mesmo</h2>
            <p>Se preferir escolher a dedo (por exemplo, seguindo o tema do retiro), o
            <a href="/catalogo">catálogo completo</a> tem busca por nome e filtro por
            categoria (Nossa Senhora, Santos, Santas, Devoções, Espírito Santo e mais) --
            o desconto de atacado soma a quantidade de TODOS os santos escolhidos juntos,
            não precisa comprar muito de um só pra cair de faixa de preço.</p>

            <div class="cta-blog-produto">
              <p>Monte seu sortimento ou comece pelo kit já pronto</p>
              <a href="/kit-livraria-shalom" class="botao-principal">Ver Kit Livraria Shalom →</a>
            </div>
        """,
        "produtos_destaque": [],
    },
    "paroquias-e-catequese": {
        "titulo": "Medalhas para Paróquia e Catequese",
        "resumo": (
            "Medalhas em quantidade para catequese, primeira comunhão, crisma e "
            "eventos paroquiais, com nota fiscal e desconto por quantidade."
        ),
        "corpo_html": """
            <p>Turma de catequese, primeira comunhão, crisma ou evento paroquial --
            comprar direto do fabricante em quantidade sai mais barato do que comprar peça
            por peça, e o desconto entra sozinho conforme o total do pedido cresce (soma
            todos os santos e formatos juntos, não precisa fechar num só).</p>

            <h2>Sortimento pronto</h2>
            <p>O <a href="/kit-livraria-shalom">Kit Livraria Shalom</a> é a forma mais
            rápida de sair com uma leva variada -- útil quando o grupo é grande e não dá
            pra escolher santo por santo com antecedência.</p>

            <h2>Devoções ligadas à formação na fé</h2>
            <p>Pra turmas de primeira comunhão, a <a href="/produto/sagrada-familia">Sagrada
            Família</a> e as devoções da categoria <a href="/categoria/jesus">Jesus</a>
            costumam fazer sentido com o momento -- mas o catálogo completo (mais de 130
            santos) cobre praticamente qualquer padroeiro que a paróquia queira destacar.</p>

            <h2>Nota fiscal e forma de pagamento</h2>
            <p>Emitimos nota fiscal para CPF ou CNPJ, e o pagamento pode ser combinado
            direto pelo WhatsApp pra pedidos grandes -- fala com a gente antes de fechar
            se precisar de um prazo ou condição específica pro evento.</p>

            <div class="cta-blog-produto">
              <p>Veja o catálogo completo ou comece pelo kit já pronto</p>
              <a href="/catalogo" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
        "produtos_destaque": ["sagrada-familia"],
    },
    "livrarias-e-revendedores": {
        "titulo": "Medalhas para Livrarias e Revendedores",
        "resumo": (
            "Fornecimento de medalhas, entremeios e chaveiros católicos para "
            "livrarias e revenda -- preço de atacado automático e nota fiscal."
        ),
        "corpo_html": """
            <p>Fornecemos medalhas, entremeios e chaveiros católicos direto de quem
            produz -- sem intermediário -- pra livrarias e quem revende peça religiosa.
            O preço de atacado entra sozinho conforme a quantidade total do pedido, sem
            precisar negociar cada compra.</p>

            <h2>Como funciona pra quem revende</h2>
            <ul>
                <li>Mais de 130 santos e devoções, com busca e filtro por categoria no
                    <a href="/catalogo">catálogo completo</a>;</li>
                <li>Desconto progressivo automático -- soma a quantidade de qualquer santo
                    e formato, não precisa concentrar tudo num item só;</li>
                <li>Nota fiscal para CNPJ;</li>
                <li><a href="/personalizada">Peças personalizadas</a> também disponíveis
                    pra quem quer oferecer um diferencial pros próprios clientes;</li>
                <li>Frete grátis acima de R$ 300 em produtos.</li>
            </ul>

            <h2>Sortimento pronto pra começar a vender</h2>
            <p>Quem está montando um mostruário do zero, o
            <a href="/kit-livraria-shalom">Kit Livraria Shalom</a> já vem com um
            sortimento dos santos que mais vendem, em quantidades editáveis.</p>

            <p>Pra negociar uma compra recorrente ou tirar dúvida antes de fechar o
            primeiro pedido, fala direto pelo WhatsApp.</p>

            <div class="cta-blog-produto">
              <p>Veja o catálogo completo ou comece pelo kit já pronto</p>
              <a href="/kit-livraria-shalom" class="botao-principal">Ver Kit Livraria Shalom →</a>
            </div>
        """,
        "produtos_destaque": [],
    },
}
