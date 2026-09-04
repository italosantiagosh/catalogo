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
      original. Tambem ganhou secoes de cookies/analytics (GA4 + Meta
      Pixel passaram a rodar no site depois desse texto ter sido
      escrito), compartilhamento de dados e direitos do titular --
      ainda vale revisao juridica antes de escalar trafego pago, mas o
      texto ja cobre o que realmente esta em uso no site hoje.
    - "Trocas e devolucao": reorganizada em accordion (<details>) por
      sugestao de auditoria externa -- separa claramente arrependimento
      (sem precisar de motivo, so as condicoes do produto) de defeito
      (precisa de foto/video), que antes apareciam meio misturados no
      mesmo paragrafo. Conteudo/prazos/condicoes sao os mesmos, so a
      organizacao mudou.
    - "Envio e prazo de entrega": reescrita como 3 etapas numeradas
      (producao -> postagem/rastreio -> entrega) pelo mesmo motivo --
      os prazos ja informados (5 dias producao, 7 dias rastreio, 2-20
      dias entrega) ficavam confusos sem deixar claro que sao etapas
      sequenciais, nao 3 prazos somados.

O corpo de cada pagina e HTML pronto (nao Markdown) -- marcado como
`| safe` no template porque e conteudo autoral nosso, nao entrada de
usuario.
"""

from __future__ import annotations

PAGINAS_ATENDIMENTO = {
    "envio-e-prazo-de-entrega": {
        "titulo": "Envio e Prazo de Entrega",
        "resumo": (
            "Produção de 5 a 10 dias úteis (conforme a quantidade do pedido) e entrega "
            "de 2 a 20 dias úteis após o envio, com código de rastreamento enviado em "
            "até 2 dias úteis após a produção ficar pronta."
        ),
        "corpo_html": """
            <p>São três etapas, nessa ordem:</p>
            <ol>
                <li><strong>Produção:</strong> de 5 a 10 dias úteis a partir da
                    confirmação do pagamento, conforme a quantidade total do pedido
                    (500+ peças: 7 dias úteis; 1000+ peças: 8 dias úteis; 2000+ peças:
                    10 dias úteis; abaixo disso, 5 dias úteis);</li>
                <li><strong>Postagem e rastreio:</strong> você recebe o código de
                    rastreamento no contato cadastrado no pedido em até 2 dias úteis
                    depois que a produção fica pronta;</li>
                <li><strong>Entrega:</strong> de 2 a 20 dias úteis a partir da postagem,
                    conforme o destino e a transportadora.</li>
            </ol>

            <p>Se o seu pedido estiver demorando além do prazo estipulado, consulte o
            código de rastreio primeiro -- se não tiver o código em mãos, fale com a
            gente pelo WhatsApp.</p>

            <p>Às vezes o produto fica um bom tempo parado num trajeto, principalmente
            no Mini Envios, que não tem rastreamento detalhado. Se o prazo estimado for
            ultrapassado, fale com a gente que acompanhamos a entrega junto à
            transportadora.</p>
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
            recebimento.</p>

            <details class="acordeao" open>
                <summary>Arrependimento (não gostei, mudei de ideia)</summary>
                <p>Você tem até 7 dias corridos após o recebimento pra desistir da
                compra, sem precisar justificar o motivo -- é o seu direito de
                arrependimento em compras feitas fora de loja física. Pra isso, o
                produto precisa:</p>
                <ol>
                    <li>Voltar na embalagem original;</li>
                    <li>Estar sem indícios de uso ou consumo, do jeito que foi
                        recebido;</li>
                    <li>Vir com etiquetas (ou protetores), manuais e todos os
                        acessórios que o acompanhem.</li>
                </ol>
            </details>

            <details class="acordeao">
                <summary>Produto com defeito</summary>
                <p>Se o produto chegou com defeito, envie também uma <strong>imagem
                ou vídeo que comprove o problema</strong> junto com o pedido de troca
                ou devolução -- isso agiliza a análise.</p>
            </details>

            <details class="acordeao">
                <summary>Como solicitar</summary>
                <p>Envie um e-mail para <strong>9djulho@gmail.com</strong> ou uma
                mensagem para <strong>(84) 98127-6650</strong> informando:</p>
                <ol>
                    <li>Nome do produto;</li>
                    <li>Número do pedido;</li>
                    <li>Contato cadastrado na compra;</li>
                    <li>Motivo da troca ou devolução;</li>
                    <li>Imagem ou vídeo do defeito, se for o caso.</li>
                </ol>
                <p>Confirmadas todas as questões, informamos o endereço para
                devolução do produto e ressarcimos o valor pago do produto e do
                frete.</p>
            </details>

            <details class="acordeao">
                <summary>Reembolso</summary>
                <ul>
                    <li><strong>Estorno no cartão de crédito:</strong> pode aparecer
                        em até duas faturas após a conclusão da devolução pelo
                        gateway de pagamento.</li>
                    <li><strong>TED:</strong> em até 10 dias úteis após a confirmação
                        da devolução, direto na conta do cliente (não pode ser feita
                        em conta de terceiros).</li>
                </ul>
            </details>

            <p><strong>Importante:</strong> não aceitamos devoluções caso as condições
            acima não sejam respeitadas.</p>
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

            <p>Por segurança, o pagamento é combinado <strong>somente pelos canais
            oficiais da Nove de Julho Artigos Ltda</strong> (CNPJ 39.390.354/0001-25) --
            WhatsApp (84) 98127-6650 ou e-mail 9djulho@gmail.com. Desconfie de qualquer
            cobrança fora desses canais.</p>
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

            <h2>Cookies e ferramentas de análise</h2>
            <p>Usamos cookies e ferramentas de análise (Google Analytics e Meta Pixel)
            para entender como o site é usado e melhorar a experiência de compra. Essas
            ferramentas podem registrar dados como páginas visitadas, tempo de navegação
            e origem do acesso. Você pode desativar cookies nas configurações do seu
            navegador, mas algumas funcionalidades do site podem parar de funcionar
            corretamente.</p>

            <h2>Compartilhamento de dados</h2>
            <p>Compartilhamos apenas os dados necessários para processar seu pedido com
            transportadoras (envio) e processadores de pagamento (Pix, cartão, boleto).
            Não vendemos nem alugamos seus dados pessoais para terceiros.</p>

            <h2>Seus direitos</h2>
            <p>Você pode solicitar a qualquer momento a confirmação, o acesso, a
            correção ou a exclusão dos seus dados pessoais, entrando em contato pelo
            e-mail <strong>9djulho@gmail.com</strong>.</p>

            <p>O uso do site da Nove de Julho pressupõe a aceitação deste termo.
            Podemos alterar este acordo sem aviso prévio — recomendamos consultar esta
            página com regularidade para se manter atualizado.</p>
        """,
    },
    "perguntas-frequentes": {
        "titulo": "Perguntas Frequentes",
        "resumo": (
            "Material de cada peça, cuidados no dia a dia, desconto de atacado, "
            "medalha personalizada, prazo de entrega e formas de pagamento."
        ),
        # versao texto-puro das mesmas perguntas do corpo_html abaixo, so pra
        # montar o schema.org FAQPage (ver app.py:pagina_atendimento) --
        # rich snippet no Google com a pergunta expansivel direto na busca.
        "faq_items": [
            (
                "De que material são feitas as peças?",
                "Medalha (1 lado): aço inoxidável, resinada. Chaveiro: liga de zinco, "
                "resinado. Entremeio (para terço): liga de zinco, resinado, nas "
                "colorações ouro velho ou prata antigo.",
            ),
            (
                "Como cuidar da peça no dia a dia?",
                "Vale para medalha, entremeio e chaveiro: pode molhar sem problema "
                "(banho, chuva, suor), só evite exposição exagerada e constante, tipo "
                "sol e praia todo dia. Evite passar produto químico ou perfume direto "
                "em cima da peça, e guarde longe de umidade excessiva quando não "
                "estiver usando.",
            ),
            (
                "Como funciona o desconto de atacado?",
                "Quanto mais peças você adiciona ao carrinho -- de qualquer santo, "
                "inclusive personalizada -- menor o preço por unidade, aplicado "
                "automaticamente, sem cupom. Medalhas e entremeios somam juntos pra "
                "faixa de desconto; chaveiros têm tabela própria.",
            ),
            (
                "Fazem medalha personalizada?",
                "Sim -- inclusive foi assim que a Nove de Julho começou: santos que a "
                "gente procurava e não encontrava prontos em lugar nenhum.",
            ),
            (
                "Qual o prazo de entrega?",
                "Produção de 5 a 10 dias úteis após a confirmação do pagamento "
                "(conforme a quantidade do pedido), mais o prazo de transporte (2 a "
                "20 dias úteis conforme o destino).",
            ),
            (
                "Quais as formas de pagamento?",
                "Os preços do catálogo são para pagamento à vista via Pix. Boleto "
                "(também à vista) e cartão (com taxas à parte) são combinados direto "
                "pelo WhatsApp.",
            ),
        ],
        "corpo_html": """
            <details class="acordeao" open>
                <summary>De que material são feitas as peças?</summary>
                <ul>
                    <li><strong>Medalha (1 lado):</strong> aço inoxidável, resinada.</li>
                    <li><strong>Chaveiro:</strong> liga de zinco, resinado.</li>
                    <li><strong>Entremeio (para terço):</strong> liga de zinco, resinado,
                        nas colorações <strong>ouro velho</strong> ou
                        <strong>prata antigo</strong>.</li>
                </ul>
            </details>

            <details class="acordeao">
                <summary>Como cuidar da peça no dia a dia?</summary>
                <p>Vale para medalha, entremeio e chaveiro:</p>
                <ul>
                    <li>Pode molhar sem problema (banho, chuva, suor) -- só evite
                        exposição exagerada e constante, tipo sol e praia todo dia;</li>
                    <li>Evite passar produto químico ou perfume direto em cima da
                        peça;</li>
                    <li>Guarde longe de umidade excessiva quando não estiver usando,
                        pra manter o brilho por mais tempo.</li>
                </ul>
            </details>

            <details class="acordeao">
                <summary>Como funciona o desconto de atacado?</summary>
                <p>Quanto mais peças você adiciona ao carrinho -- de qualquer santo,
                inclusive personalizada -- menor o preço por unidade, aplicado
                automaticamente, sem cupom. Medalhas e entremeios somam juntos pra
                faixa de desconto; chaveiros têm tabela própria. Veja o
                <a href="/kit-livraria-shalom">Kit Livraria Shalom</a> pra já começar
                com um sortimento pronto.</p>
            </details>

            <details class="acordeao">
                <summary>Fazem medalha personalizada?</summary>
                <p>Sim -- inclusive foi assim que a Nove de Julho começou: santos que a
                gente procurava e não encontrava prontos em lugar nenhum. Veja mais em
                <a href="/personalizada">Medalha Personalizada</a>.</p>
            </details>

            <details class="acordeao">
                <summary>Qual o prazo de entrega?</summary>
                <p>Produção de 5 a 10 dias úteis após a confirmação do pagamento
                (conforme a quantidade do pedido), mais o prazo de transporte. Detalhes
                completos em
                <a href="/atendimento/envio-e-prazo-de-entrega">Envio e Prazo de
                Entrega</a>.</p>
            </details>

            <details class="acordeao">
                <summary>Quais as formas de pagamento?</summary>
                <p>Os preços do catálogo são para pagamento à vista via Pix. Boleto
                (também à vista) e cartão (com taxas à parte) são combinados direto
                pelo WhatsApp. Veja mais em
                <a href="/atendimento/formas-de-pagamento">Formas de Pagamento</a>.</p>
            </details>
        """,
    },
}
