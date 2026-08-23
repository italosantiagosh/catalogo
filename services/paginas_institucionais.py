"""
Paginas de atendimento/institucionais (/atendimento/<slug>, ver app.py e
templates/pagina_atendimento.html) -- conteudo enviado pelo usuario
(texto real ja usado no site oficial, Yampi), com pequenos ajustes:

    - "Quem somos": idade do fundador atualizada pra 32 anos (pedido
      explicito do usuario).
    - "Termos e privacidade": o texto original citava a lei de PROTECAO
      DE DADOS DE PORTUGAL (Lei n.o 67/98, de 26/10/1998) -- claramente
      um texto-modelo nao adaptado, ja que o resto do site e uma loja
      brasileira (Correios, CPF/CNPJ, R$). Trocado pela LGPD (Lei
      13.709/2018), mantendo a mesma estrutura/intencao do texto
      original.

O corpo de cada pagina e HTML pronto (nao Markdown) -- marcado como
`| safe` no template porque e conteudo autoral nosso, nao entrada de
usuario.
"""

from __future__ import annotations

PAGINAS_ATENDIMENTO = {
    "envio-e-prazo-de-entrega": {
        "titulo": "Envio e Prazo de Entrega",
        "resumo": (
            "Produção em até 5 dias úteis e entrega de 2 a 20 dias úteis após o envio, "
            "com código de rastreamento enviado em até 7 dias úteis."
        ),
        "corpo_html": """
            <p>A produção é de até <strong>5 dias úteis</strong>. Depois do envio da
            mercadoria, o prazo de entrega varia de <strong>2 a 20 dias úteis</strong>,
            conforme o destino.</p>

            <p>Você recebe o código de rastreamento no contato cadastrado no pedido em
            até <strong>7 dias úteis</strong> após o processamento. Se o seu pedido
            estiver demorando além do prazo estipulado, consulte o código de rastreio
            primeiro -- se não tiver o código em mãos, fale com a gente pelo
            WhatsApp.</p>

            <p>Às vezes o produto fica um bom tempo parado num trajeto, principalmente
            no Mini Envios, que não tem rastreamento detalhado. Não se preocupe: o
            produto chega até você.</p>
        """,
    },
    "trocas-e-devolucao": {
        "titulo": "Política de Devolução e Reembolso",
        "resumo": (
            "Troca ou devolução em até 7 dias corridos após o recebimento, seguindo as "
            "condições do produto -- veja como solicitar e as formas de ressarcimento."
        ),
        "corpo_html": """
            <p>A equipe Nove de Julho está constantemente investindo em políticas para
            que nossos clientes sempre saiam satisfeitos. Você pode solicitar a troca ou
            devolução de um produto em até <strong>7 dias corridos</strong> após o
            recebimento. Precisam ser observadas as seguintes condições:</p>

            <ol>
                <li>O produto deve ser devolvido em sua embalagem original;</li>
                <li>O produto deve ser devolvido sem indícios de uso ou consumo, isto é,
                    da forma que foi recebido;</li>
                <li>O produto deve ser devolvido com etiquetas (ou protetores) afixados,
                    manuais e todos os acessórios que o acompanhem.</li>
            </ol>

            <p><strong>Importante:</strong> não aceitamos devoluções caso as condições
            acima não sejam respeitadas.</p>

            <h2>O que fazer para solicitar troca ou devolução</h2>
            <p>Envie um e-mail para <strong>9djulho@gmail.com</strong> ou uma mensagem
            para <strong>(84) 98127-6650</strong> informando:</p>
            <ol>
                <li>Nome do produto;</li>
                <li>Número do pedido;</li>
                <li>Contato cadastrado na compra;</li>
                <li>Motivo da troca ou devolução;</li>
                <li>Imagem ou vídeo que comprove o defeito, caso haja.</li>
            </ol>

            <p>Confirmadas todas as questões sobre a devolução, informamos o endereço
            para devolução do produto e ressarcimos o valor pago do produto e do
            frete.</p>

            <h2>Formas de ressarcimento</h2>
            <ul>
                <li><strong>Estorno no cartão de crédito:</strong> pode aparecer em até
                    duas faturas após a conclusão da devolução pelo gateway de
                    pagamento.</li>
                <li><strong>TED:</strong> transferência para a conta do cliente,
                    realizada em até 10 dias úteis após a confirmação da devolução. A
                    transferência não pode ser feita em conta de terceiros.</li>
            </ul>
        """,
    },
    "formas-de-pagamento": {
        "titulo": "Formas de Pagamento",
        "resumo": (
            "Pagamento combinado pelo WhatsApp: Pix à vista (preço do catálogo), "
            "link seguro de cartão/Pix ou boleto sob consulta. Nota fiscal emitida "
            "antes do envio."
        ),
        "corpo_html": """
            <p>O pagamento é combinado direto pelo WhatsApp depois de você finalizar o
            pedido no catálogo. Os valores mostrados aqui são para pagamento à vista via
            <strong>Pix</strong> (a chave é passada na conversa).</p>

            <p>Também aceitamos pagamento por <strong>link seguro</strong> de cartão ou
            Pix, ou por <strong>boleto</strong> -- nesses casos os dados são informados
            durante o atendimento. Boleto é sempre à vista (não parcelado/faturado);
            pagamento no cartão está sujeito a taxas adicionais.</p>

            <p>Emitimos <strong>nota fiscal</strong> para CNPJ ou CPF antes do envio do
            seu pedido.</p>
        """,
    },
    "quem-somos": {
        "titulo": "Quem Somos",
        "resumo": (
            "A história da Nove de Julho, contada por Ítalo, seu fundador -- fé, "
            "devoção e o desejo de levar medalhas de santos a todo o Brasil."
        ),
        "corpo_html": """
            <p>Meu nome é Ítalo, tenho 32 anos, sou Consagrado da Comunidade Católica
            Shalom e fundador da Nove de Julho.</p>

            <p>Tudo começou com uma dor: a dificuldade de encontrar medalhas de santos
            mais raros ou personalizados — como Santa Gianna ou Edith Stein. Essa
            necessidade, que parecia apenas minha, era partilhada por muitos.</p>

            <p>Dei o primeiro passo no dia 28 de abril de 2020, ainda de forma simples.
            Mas foi no dia 1º de outubro, confiando especialmente à intercessão de São
            José, Santa Teresinha e São Josemaria Escrivá, que tudo começou a tomar
            corpo de verdade e as vendas começaram a alavancar.</p>

            <p>Mesmo sem apoio inicial, decidi investir e aprender a produzir
            artesanalmente medalhas resinadas em material inox de qualidade. Hoje, posso
            dizer com alegria que encontrei nesse projeto uma missão de vida.</p>

            <p>A Nove de Julho nasceu do desejo de evangelizar por meio da beleza, da
            devoção e da tradição da Igreja. Nossa missão é ajudar pessoas que, como eu,
            buscavam representações de fé que não encontravam com facilidade — e, com
            isso, espalhar o amor e a intercessão dos santos, conhecidos e desconhecidos,
            por todo o Brasil.</p>

            <p>Sinto uma profunda gratidão ao ver nossos produtos chegando a tantos
            cantos do país — e até fora dele. É uma alegria imensa receber testemunhos e
            fotos das nossas medalhas sendo usadas em momentos tão especiais:
            nascimentos, batizados, retiros, festividades de paróquias e comunidades,
            casamentos, e missas de consagração e discipulado.</p>

            <p>Cada medalha é feita com zelo, carinho e fé. Que ela seja mais do que um
            objeto: que seja um sinal da presença de Deus e da intercessão dos santos em
            sua vida.</p>

            <p>Rezo por cada cliente. E se você chegou até aqui, conto também com sua
            oração.</p>

            <p><em>São José, Santa Teresinha e São Josemaria Escrivá, rogai por nós e
            providenciai!</em></p>
        """,
    },
    "termos-e-privacidade": {
        "titulo": "Termos de Uso e Política de Privacidade",
        "resumo": (
            "Como tratamos seus dados pessoais na Nove de Julho, em conformidade com "
            "a LGPD (Lei nº 13.709/2018)."
        ),
        "corpo_html": """
            <p>Todas as informações pessoais que coletamos são usadas para tornar sua
            visita ao nosso site o mais produtiva e agradável possível. A
            confidencialidade dos seus dados pessoais é importante para a Nove de Julho.
            Tratamos todas as informações pessoais de clientes e visitantes em
            conformidade com a <strong>Lei Geral de Proteção de Dados Pessoais (LGPD —
            Lei nº 13.709/2018)</strong>.</p>

            <p>As informações pessoais coletadas podem incluir seu nome, e-mail,
            telefone/WhatsApp, endereço e outros dados necessários para processar seu
            pedido, calcular o frete e emitir a nota fiscal.</p>

            <p>O uso do site da Nove de Julho pressupõe a aceitação deste termo.
            Podemos alterar este acordo sem aviso prévio — recomendamos consultar esta
            página com regularidade para se manter atualizado.</p>
        """,
    },
}
