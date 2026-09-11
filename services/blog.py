"""
Conteudo do blog (/blog, /blog/<slug>, ver app.py e conversa "vamos
fazer esse conteudo/blog") -- textos sobre os santos e devocoes do
catalogo, pensados pra aparecer em buscas de quem ainda nao sabe qual
produto quer (topo de funil), diferente das paginas de produto (que ja
assumem que a pessoa sabe o santo e quer comprar).

Escritos com base em tradicao/hagiografia catolica de dominio publico
-- nao e´ texto enviado pelo usuario (MESMO padrao de
services/paginas_institucionais.py: dict fixo, sem banco de dados, so
muda por deploy). Cada artigo linka pro produto correspondente
(`produto_relacionado_id`, precisa existir em data/produtos.json) como
CTA principal -- e´ esse link que conecta o conteudo de busca a uma
venda de verdade.
"""

from __future__ import annotations

ARTIGOS_BLOG = {
    "sao-judas-tadeu-santo-das-causas-impossiveis": {
        "titulo": "São Judas Tadeu: por que ele é o santo das causas impossíveis",
        "resumo": (
            "Apóstolo de Jesus e primo do Senhor, São Judas Tadeu se tornou o santo mais "
            "invocado nos momentos mais difíceis. Entenda a origem dessa devoção tão forte "
            "no Brasil."
        ),
        "produto_relacionado_id": "sao-judas-tadeu",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>São Judas Tadeu foi um dos doze apóstolos escolhidos por Jesus -- segundo a
            tradição, primo do Senhor, da mesma família de José. É autor de uma das cartas
            do Novo Testamento, a Epístola de Judas, endereçada a cristãos que enfrentavam
            perseguição e precisavam de firmeza na fé. Depois da Ressurreição, teria pregado
            o Evangelho na Mesopotâmia, Síria e Armênia, onde foi martirizado.</p>

            <h2>Por que "santo das causas impossíveis"?</h2>
            <p>A explicação mais aceita é também a mais simples: seu nome. Por soar
            parecido com Judas Iscariotes, o apóstolo que traiu Jesus, poucos cristãos ao
            longo da história recorriam a ele em oração -- ninguém queria "confundir" os
            dois nomes. O resultado é que São Judas Tadeu ficou conhecido como o santo a
            quem se recorre só quando nenhuma outra ajuda parece possível: exatamente por
            ser "esquecido" nos pedidos fáceis, tornou-se o intercessor das causas mais
            difíceis, urgentes e, aparentemente, sem saída.</p>

            <h2>Uma devoção muito forte no Brasil</h2>
            <p>A devoção a São Judas Tadeu é especialmente popular no Brasil, com destaque
            para a tradicional novena realizada na Igreja de Santa Cecília e na Igreja de
            Santa Cruz, em São Paulo, que reúne milhares de fiéis todos os meses. Sua festa
            é celebrada em 28 de outubro, mas quem tem uma causa urgente não costuma
            esperar a data -- carrega a medalha no dia a dia como lembrete de que nenhuma
            situação está além da esperança.</p>

            <div class="cta-blog-produto">
              <p>Quer ter São Judas Tadeu sempre com você?</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São Judas Tadeu →</a>
            </div>
        """,
    },
    "nossa-senhora-aparecida-historia": {
        "titulo": "A história de Nossa Senhora Aparecida, padroeira do Brasil",
        "resumo": (
            "Uma pequena imagem encontrada por pescadores num rio, em 1717, deu origem à "
            "maior devoção mariana do Brasil. Conheça a história por trás da padroeira."
        ),
        "produto_relacionado_id": "nossa-senhora-aparecida",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>Em outubro de 1717, três pescadores -- Domingos Garcia, João Alves e Felipe
            Pedroso -- lançavam redes no Rio Paraíba do Sul, perto da cidade de Guaratinguetá
            (SP), sem sorte alguma. Na esperança de conseguir pelo menos algo, jogaram a
            rede mais uma vez e recolheram, primeiro, o corpo de uma pequena imagem de
            barro escurecido de Nossa Senhora da Conceição -- e, logo em seguida, na mesma
            rede, a cabeça da mesma imagem. Diz a tradição que, a partir daquele lance, a
            pesca no rio se tornou tão farta que a canoa quase afundava com o peso dos
            peixes.</p>

            <h2>De uma capelinha simples à padroeira do Brasil</h2>
            <p>A imagem, de pouco mais de 30 centímetros e escurecida pelo tempo dentro
            d'água, passou a ser venerada primeiro em casas de família e depois numa
            pequena capela. A devoção cresceu tanto que, ao longo dos séculos seguintes,
            deu origem à cidade de Aparecida (SP) e à Basílica de Nossa Senhora Aparecida,
            um dos maiores santuários marianos do mundo. Em 1930, o Papa Pio XI proclamou
            oficialmente Nossa Senhora Aparecida como padroeira do Brasil.</p>

            <h2>Por que a imagem é escura?</h2>
            <p>A cor escura da imagem, um dos traços mais reconhecíveis da devoção, vem do
            tempo em que ficou submersa nas águas barrentas do rio e do próprio material
            usado -- terracota, que escurece com a ação da água e do tempo. Para muitos
            devotos, essa característica reforça o símbolo de uma santa "do povo", achada
            por gente simples, num rio brasileiro.</p>

            <p>Sua festa é celebrada em 12 de outubro, feriado nacional e um dos dias de
            maior movimento de peregrinos em todo o país.</p>

            <div class="cta-blog-produto">
              <p>Leve Nossa Senhora Aparecida com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Nossa Senhora Aparecida →</a>
            </div>
        """,
    },
    "sao-bento-medalha-significado": {
        "titulo": "O que significa a medalha de São Bento e por que ela protege",
        "resumo": (
            "Cheia de siglas e cruzes, a medalha de São Bento é uma das mais usadas do "
            "mundo católico. Entenda o significado de cada símbolo e a origem da devoção."
        ),
        "produto_relacionado_id": "sao-bento",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>São Bento de Núrsia viveu entre os séculos V e VI, na Itália, numa época de
            grande instabilidade após a queda do Império Romano. Ainda jovem, deixou os
            estudos em Roma para viver em oração e penitência numa gruta em Subiaco, e mais
            tarde fundou o mosteiro de Monte Cassino, onde escreveu a "Regra de São Bento" --
            um conjunto de orientações para a vida monástica organizada em torno do lema
            <em>ora et labora</em> ("reza e trabalha"). É considerado o fundador do
            monaquismo ocidental e, por sua influência na formação cultural da Europa, foi
            declarado padroeiro do continente pelo Papa Paulo VI em 1964.</p>

            <h2>O que significam as letras na medalha</h2>
            <p>A medalha de São Bento é reconhecida pelas letras que cercam a cruz -- na
            verdade, as iniciais de uma oração latina de proteção contra o mal:</p>
            <ul>
                <li><strong>C S P B</strong> -- <em>Crux Sancti Patris Benedicti</em> (Cruz
                    do Santo Padre Bento);</li>
                <li><strong>C S S M L</strong> -- <em>Crux Sacra Sit Mihi Lux</em> (Que a
                    Santa Cruz seja minha luz);</li>
                <li><strong>N D S M D</strong> -- <em>Non Draco Sit Mihi Dux</em> (Que o
                    dragão nunca seja meu guia);</li>
                <li><strong>V R S</strong> -- <em>Vade Retro Satana</em> (Afasta-te, Satanás);</li>
                <li><strong>S M Q L</strong> -- <em>Sunt Mala Quae Libas</em> (São más as
                    coisas que ofereces);</li>
                <li><strong>I V B</strong> -- <em>Ipse Venena Bibas</em> (Bebe tu mesmo teu
                    veneno).</li>
            </ul>
            <p>Junto às letras, aparece também o "PAX" (paz, lema beneditino) e a data
            "1880", ano em que a medalha ganhou o formato atualmente mais difundido, cunhada
            pelos monges de Monte Cassino para celebrar os 1.400 anos do nascimento do
            santo.</p>

            <h2>Uma medalha de proteção espiritual</h2>
            <p>Por causa dessa oração de exorcismo embutida no próprio desenho, a medalha
            de São Bento é uma das mais usadas por quem busca proteção espiritual no dia a
            dia -- seja no pescoço, na carteira, no carro ou na entrada de casa. Sua festa é
            celebrada em 11 de julho.</p>

            <div class="cta-blog-produto">
              <p>Proteção que você carrega com fé</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São Bento →</a>
            </div>
        """,
    },
    "nossa-senhora-desatadora-dos-nos-oracao": {
        "titulo": "Nossa Senhora Desatadora dos Nós: a origem da devoção e como rezar",
        "resumo": (
            "Popularizada no Brasil e na Argentina, a devoção a Nossa Senhora Desatadora "
            "dos Nós nasceu de um quadro alemão do século XVIII. Conheça a história."
        ),
        "produto_relacionado_id": "nossa-senhora-desatadora-dos-nos",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>A devoção a Nossa Senhora Desatadora dos Nós tem origem num quadro pintado
            por volta de 1700 pelo artista alemão Johann Georg Melchior Schmidtner, hoje
            conservado na igreja de São Pedro em Perlach, na cidade de Augsburgo, Alemanha.
            Na pintura, Maria aparece desatando, com as próprias mãos, uma fita cheia de
            nós -- enquanto anjos levam a ela a fita ainda emaranhada e recolhem, do outro
            lado, a fita já livre.</p>

            <h2>Como a devoção chegou à América Latina</h2>
            <p>A imagem permaneceu relativamente pouco conhecida fora da Alemanha até o
            fim do século XX, quando um jovem padre argentino, Jorge Mario Bergoglio,
            viu o quadro durante uma viagem de estudos e ficou impressionado com o
            simbolismo. Ele trouxe uma reprodução da pintura para Buenos Aires em 1996,
            onde a devoção se espalhou rapidamente. Anos depois, aquele mesmo padre se
            tornaria o Papa Francisco -- o que ajudou a levar essa devoção a praticamente
            todo o mundo católico, com destaque especial para o Brasil.</p>

            <h2>O que significam os "nós"</h2>
            <p>Os nós da fita representam as dificuldades, os problemas e os enganos que se
            acumulam ao longo da vida -- relações desgastadas, decisões difíceis, situações
            que parecem sem solução. A imagem de Maria desatando cada nó, um de cada vez,
            com paciência, é um convite à confiança: entregar as próprias dificuldades a
            ela e confiar que, com tempo e fé, também podem ser desatadas.</p>

            <p>Não existe uma data fixa de festa universal para essa devoção específica,
            mas ela costuma ser celebrada junto com as festas marianas locais de cada
            comunidade, e sua novena (rezada geralmente ao longo de nove dias seguidos) é
            uma das mais praticadas atualmente no Brasil.</p>

            <div class="cta-blog-produto">
              <p>Carregue essa confiança com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Nossa Senhora Desatadora dos Nós →</a>
            </div>
        """,
    },
    "santa-rita-de-cassia-santa-dos-impossiveis": {
        "titulo": "Santa Rita de Cássia: a santa dos impossíveis",
        "resumo": (
            "Esposa, mãe, viúva e depois freira, Santa Rita de Cássia atravessou perdas "
            "profundas antes de se tornar uma das santas mais queridas da Igreja."
        ),
        "produto_relacionado_id": "santa-rita-de-cassia",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>Rita nasceu por volta de 1381, em Roccaporena, uma pequena vila na região
            da Úmbria, na Itália. Ainda jovem, contra sua própria vontade de seguir a vida
            religiosa, foi dada em casamento pelos pais a um homem de temperamento
            violento, com quem teve dois filhos. Ao longo de quase vinte anos de casamento
            difícil, é lembrada por sua paciência e por rezar insistentemente pela
            conversão do marido -- que, segundo a tradição, de fato mudou de vida pouco
            antes de ser assassinado numa disputa local.</p>

            <h2>Perdas profundas, uma depois da outra</h2>
            <p>Viúva, Rita viu seus dois filhos jurarem vingar a morte do pai -- e rezou
            para que Deus os levasse antes de cometerem esse pecado a permitir que
            morressem em estado de graça, o que de fato aconteceu, ambos por doença, ainda
            jovens. Sozinha depois de perder marido e filhos, tentou por três vezes entrar
            no mosteiro agostiniano de Cássia, sendo recusada por não ser mais viúva "de
            paz" segundo as regras da época. Só foi aceita depois de reconciliar as
            famílias envolvidas na morte do marido.</p>

            <h2>O espinho na testa</h2>
            <p>Já freira, dedicada a uma vida de oração e penitência, Rita teria recebido,
            após meditar diante de um crucifixo, uma ferida na testa -- como se um espinho
            da coroa de Cristo a tivesse atingido. A marca, dolorosa e com odor
            desagradável segundo os relatos da época, permaneceu com ela até sua morte, em
            1457, e é um dos traços mais reconhecíveis em suas imagens e medalhas.</p>

            <h2>Por que "santa dos impossíveis"</h2>
            <p>Depois de uma vida marcada por perdas que pareciam insuportáveis e por
            portas que se fechavam repetidamente, Santa Rita se tornou símbolo de
            esperança para quem enfrenta situações aparentemente sem saída -- ao lado de
            São Judas Tadeu, é uma das santas mais invocadas nas causas impossíveis,
            especialmente em casamentos difíceis e situações familiares delicadas. Sua
            festa é celebrada em 22 de maio.</p>

            <div class="cta-blog-produto">
              <p>Uma companhia pra quando tudo parece difícil</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santa Rita de Cássia →</a>
            </div>
        """,
    },
    "sao-cristovao-padroeiro-dos-viajantes": {
        "titulo": "São Cristóvão: por que ele é o padroeiro dos viajantes e motoristas",
        "resumo": (
            "A lenda de um homem forte que carregou o menino Jesus para atravessar um "
            "rio deu origem a uma das devoções mais usadas dentro dos carros do Brasil."
        ),
        "produto_relacionado_id": "sao-cristovao",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>Segundo a tradição, Cristóvão era um homem de estatura e força enormes que
            decidiu colocar sua força a serviço do bem, ajudando viajantes a atravessar um
            rio perigoso, sem ponte, carregando-os nos ombros de uma margem à outra. Uma
            noite, atravessou uma criança que parecia cada vez mais pesada a cada passo --
            tão pesada que Cristóvão temeu não conseguir chegar à outra margem. Ao final da
            travessia, a criança revelou ser o próprio Jesus, e explicou que carregava não
            só o peso de um menino, mas o peso do mundo inteiro sobre os ombros.</p>

            <h2>O que significa o nome "Cristóvão"</h2>
            <p>É justamente dessa lenda que vem o nome pelo qual ficou conhecido:
            "Cristóvão" (do grego <em>Christophoros</em>) significa literalmente "aquele
            que carrega Cristo". A devoção não afirma que esse tenha sido seu nome de
            nascença, mas sim o título que passou a carregar depois do episódio da
            travessia.</p>

            <h2>Um mártir dos primeiros séculos</h2>
            <p>Historicamente, sabe-se pouco com certeza sobre Cristóvão além de que
            provavelmente foi um mártir cristão dos primeiros séculos da Igreja, na região
            da atual Turquia. Boa parte do que se conhece hoje vem de relatos e lendas
            transmitidas ao longo da Idade Média, quando sua devoção já era amplamente
            difundida por toda a Europa.</p>

            <h2>Por que aparece tanto em carros e estradas</h2>
            <p>A imagem de alguém que carrega em segurança quem está sob sua proteção,
            atravessando um percurso perigoso, tornou Cristóvão o padroeiro natural de
            viajantes -- e, com o tempo, especialmente de motoristas e caminhoneiros. É
            comum encontrar sua medalha ou imagem pendurada no retrovisor ou no painel de
            veículos por todo o Brasil, como um pedido de proteção nas estradas. Sua festa
            é celebrada em 25 de julho.</p>

            <div class="cta-blog-produto">
              <p>Proteção pra quem está sempre na estrada</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São Cristóvão →</a>
            </div>
        """,
    },
    "sao-jose-pai-adotivo-de-jesus": {
        "titulo": "São José: o silêncio e a fé do pai adotivo de Jesus",
        "resumo": (
            "Nenhuma palavra de São José foi registrada nos Evangelhos -- mas seus atos "
            "de obediência e cuidado fizeram dele padroeiro dos trabalhadores e da Igreja."
        ),
        "produto_relacionado_id": "sao-jose",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>José era um carpinteiro (ou, mais amplamente, um artesão que trabalhava com
            madeira e outros materiais) da cidade de Nazaré, prometido em casamento a
            Maria quando recebeu a notícia, por meio de um anjo em sonho, de que ela estava
            grávida por obra do Espírito Santo. Apesar do choque compreensível dessa
            situação, José escolheu não a abandonar, assumindo publicamente Maria como
            esposa e Jesus como filho -- um ato de coragem e fé que os Evangelhos registram
            com respeito, ainda que sem nenhuma palavra sua transcrita diretamente.</p>

            <h2>Um pai de poucas palavras, muitos atos</h2>
            <p>Esse é um dos traços mais marcantes de José: em nenhuma passagem bíblica
            aparece uma fala sua registrada. Tudo o que se sabe sobre ele vem de suas
            ações -- aceitar Maria, fugir para o Egito para proteger o menino Jesus de
            Herodes, voltar a Nazaré, criar e sustentar a família com seu trabalho manual.
            Por essa combinação de obediência silenciosa e cuidado prático, José é
            frequentemente descrito como modelo de fé que se expressa mais em atitude do
            que em discurso.</p>

            <h2>Padroeiro dos trabalhadores e da Igreja</h2>
            <p>Por seu ofício de artesão/carpinteiro, São José é o padroeiro dos
            trabalhadores -- sua segunda festa, em 1º de maio (São José Operário), foi
            instituída pelo Papa Pio XII justamente para unir a espiritualidade católica ao
            Dia do Trabalho. Já é padroeiro da Igreja Universal desde 1870, título
            reafirmado por diversos papas ao longo do século XX. Sua festa principal é
            celebrada em 19 de março, e em 2020-2021 o Papa Francisco dedicou um Ano
            Especial a São José, destacando seu papel como pai adotivo, sustento e
            protetor da Sagrada Família.</p>

            <div class="cta-blog-produto">
              <p>Um pai de fé pra sua casa</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São José →</a>
            </div>
        """,
    },
    "sagrado-coracao-de-jesus-significado": {
        "titulo": "O que significa a devoção ao Sagrado Coração de Jesus",
        "resumo": (
            "Nascida de revelações a uma freira francesa no século XVII, a devoção ao "
            "Sagrado Coração simboliza o amor de Cristo por toda a humanidade."
        ),
        "produto_relacionado_id": "sagrado-coracao-de-jesus",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>A devoção ao Sagrado Coração de Jesus, embora com raízes que remontam à
            Idade Média, ganhou a forma como é conhecida hoje a partir das revelações
            relatadas por Santa Margarida Maria Alacoque, uma freira francesa da Ordem da
            Visitação, entre 1673 e 1675, no convento de Paray-le-Monial. Segundo seu
            relato, Jesus lhe teria aparecido mostrando o próprio coração, cercado de
            espinhos e em chamas, pedindo que essa imagem do seu amor por toda a
            humanidade fosse mais conhecida e venerada.</p>

            <h2>O que representam os símbolos</h2>
            <p>Nas imagens tradicionais, o Sagrado Coração aparece com alguns elementos
            fixos, cada um com um significado: as <strong>chamas</strong> representam o
            amor ardente de Cristo; a <strong>coroa de espinhos</strong> enrolada ao redor
            do coração lembra o sofrimento da Paixão; e a própria ferida no coração remete
            ao momento em que o lado de Jesus foi perfurado na cruz. Juntos, esses
            elementos formam uma síntese visual de um amor que sofre, mas continua
            ardendo.</p>

            <h2>Uma devoção de proteção e consagração</h2>
            <p>É comum que famílias façam a "consagração ao Sagrado Coração de Jesus",
            colocando a casa e seus membros sob a proteção desse amor. O mês de junho é
            tradicionalmente dedicado a essa devoção na Igreja Católica, com destaque para
            a Solenidade do Sagrado Coração, celebrada numa sexta-feira móvel após o
            Corpo de Cristo. É uma das imagens mais presentes em lares e igrejas
            católicas em todo o mundo, símbolo direto e visual de que o amor de Deus não
            tem condição nem limite.</p>

            <div class="cta-blog-produto">
              <p>O amor de Cristo, sempre com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro do Sagrado Coração de Jesus →</a>
            </div>
        """,
    },
    "sao-miguel-arcanjo-oracao-de-protecao": {
        "titulo": "São Miguel Arcanjo: o guerreiro celestial e sua oração de proteção",
        "resumo": (
            "Líder dos exércitos celestiais contra o mal, São Miguel Arcanjo é hoje o "
            "padroeiro da proteção espiritual, de policiais e militares."
        ),
        "produto_relacionado_id": "sao-miguel",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>Miguel é um dos três arcanjos citados pelo nome na Bíblia (ao lado de
            Gabriel e Rafael) e o único chamado explicitamente de "arcanjo" no Novo
            Testamento. Seu nome, em hebraico, significa "Quem é como Deus?" -- uma
            pergunta retórica que também funciona como grito de guerra contra qualquer
            criatura que se coloque no lugar do Criador. No livro do Apocalipse, é descrito
            liderando os anjos fiéis na batalha celestial contra o dragão (Satanás) e seus
            seguidores, expulsando-os do céu.</p>

            <h2>Um arcanjo, três papéis</h2>
            <p>Ao longo da tradição cristã, Miguel acumulou três funções principais:
            <strong>guerreiro</strong>, liderando a luta contra o mal; <strong>protetor</strong>,
            defendendo o povo de Deus (e, por extensão, cada fiel individualmente); e
            <strong>psicopompo</strong>, aquele que conduz as almas dos falecidos à
            presença de Deus no momento do juízo, com uma balança na mão em muitas
            representações artísticas.</p>

            <h2>A oração de proteção mais conhecida</h2>
            <p>A "Oração a São Miguel Arcanjo", composta pelo Papa Leão XIII no fim do
            século XIX depois de uma visão que teria tido sobre os ataques do mal contra a
            Igreja, é uma das orações de proteção mais rezadas até hoje: <em>"São Miguel
            Arcanjo, defendei-nos no combate..."</em>. Por essa associação direta com
            proteção e combate ao mal, Miguel é o padroeiro natural de policiais,
            militares, bombeiros e de qualquer profissão que exija coragem diante do
            perigo. Sua festa, junto com os arcanjos Gabriel e Rafael, é celebrada em 29 de
            setembro.</p>

            <div class="cta-blog-produto">
              <p>Proteção espiritual pra todo dia</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São Miguel Arcanjo →</a>
            </div>
        """,
    },
    "santa-teresinha-caminho-da-infancia-espiritual": {
        "titulo": "Santa Teresinha e o caminho da infância espiritual",
        "resumo": (
            "Morta aos 24 anos, Santa Teresinha do Menino Jesus se tornou uma das santas "
            "mais amadas ao ensinar que a santidade está nas pequenas coisas do dia a dia."
        ),
        "produto_relacionado_id": "santa-teresinha",
        "publicado_em": "2026-09-08",
        "corpo_html": """
            <p>Teresa Martin nasceu em 1873, em Alençon, na França, e entrou ainda muito
            jovem -- aos 15 anos, com uma permissão especial -- no Carmelo de Lisieux, onde
            viveu como freira de clausura até sua morte, em 1897, vítima de tuberculose,
            aos 24 anos. Apesar da vida curta e vivida quase inteiramente dentro dos muros
            de um convento, sem grandes feitos visíveis, tornou-se uma das santas mais
            populares e influentes da Igreja Católica moderna.</p>

            <h2>A "pequena via" da santidade</h2>
            <p>O legado de Santa Teresinha está principalmente em seu livro autobiográfico
            <em>História de uma Alma</em>, onde descreve o que chamou de "caminhozinho" ou
            "pequena via": a ideia de que não é preciso realizar grandes feitos para
            alcançar a santidade -- basta fazer as pequenas coisas do cotidiano com muito
            amor e total confiança em Deus, como uma criança confia nos braços do pai. Essa
            simplicidade tocou profundamente fiéis ao redor do mundo, e em 1997 ela foi
            declarada Doutora da Igreja pelo Papa João Paulo II, um dos títulos mais altos
            que a Igreja concede.</p>

            <h2>A promessa das rosas</h2>
            <p>Antes de morrer, Teresinha teria dito: "Passarei meu céu fazendo o bem na
            terra" e prometido "deixar cair uma chuva de rosas" sobre quem pedisse sua
            intercessão. Por causa dessa promessa, é comum que devotos peçam a ela um
            "sinal" na forma de uma rosa -- física ou simbólica -- como confirmação de que
            uma oração foi ouvida. Sua festa é celebrada em 1º de outubro.</p>

            <div class="cta-blog-produto">
              <p>A força das pequenas coisas feitas com amor</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santa Teresinha →</a>
            </div>
        """,
    },
    "jovens-santos-e-beatos": {
        "titulo": "Jovens santos e beatos: quando a santidade não espera envelhecer",
        "resumo": (
            "Carlo Acutis, Pier Giorgio Frassati e Chiara Luce Badano mostram que não é "
            "preciso viver muitos anos pra deixar um exemplo de fé que atravessa gerações."
        ),
        "produto_relacionado_id": "carlo-acutis",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>É comum imaginar a santidade como fruto de uma vida longa, dedicada
            inteiramente à religião. Mas a Igreja também reconhece, cada vez com mais
            força, jovens que viveram poucos anos e, ainda assim, deixaram um testemunho
            de fé tão intenso quanto o de qualquer santo adulto.</p>

            <h2>Carlo Acutis, o "influencer de Deus"</h2>
            <p>Carlo Acutis nasceu em Londres em 1991 e morreu em Monza, na Itália, em
            2006, aos 15 anos, vítima de uma leucemia fulminante. Apaixonado por
            informática desde criança, usou justamente essa habilidade para catalogar, num
            site que ele mesmo programou, milagres eucarísticos reconhecidos pela Igreja ao
            redor do mundo -- um trabalho que continua disponível on-line até hoje. Beatificado
            em 2020, foi <strong>canonizado em 7 de setembro de 2025</strong> pelo Papa Leão
            XIV, tornando-se um dos primeiros santos "millennial" da Igreja Católica e
            padroeiro da internet.</p>

            <h2>Pier Giorgio Frassati, alpinista e servidor dos pobres</h2>
            <p>Quase um século antes, outro jovem italiano já apontava nessa mesma direção:
            <a href="/produto/sao-pier-giorgio-frassati">Pier Giorgio Frassati</a> (1901-1925)
            vinha de uma família rica e influente de Turim, mas dedicava boa parte do tempo
            livre a visitar e ajudar famílias pobres da cidade, muitas vezes escondendo
            isso até dos próprios pais. Também era um alpinista apaixonado, e é justamente
            numa dessas escaladas que aparece um de seus ditos mais conhecidos: "Verso
            l'alto" ("Rumo ao alto"). Morreu aos 24 anos, de poliomielite, contraída
            provavelmente ao cuidar de doentes. Beatificado em 1990 pelo Papa João Paulo
            II, que o chamou de "homem das oito bem-aventuranças", foi canonizado no
            mesmo dia que Carlo Acutis, em setembro de 2025.</p>

            <h2>Chiara Luce Badano, o sorriso na dor</h2>
            <p><a href="/produto/chiara-luce">Chiara Luce Badano</a> (1971-1990) era uma
            adolescente italiana ligada ao Movimento dos Focolares quando, aos 17 anos, foi
            diagnosticada com um tipo raro e agressivo de câncer ósseo. Ao longo do
            tratamento, chamou a atenção de quem a cercava por manter um semblante sereno e
            alegre mesmo diante da dor -- foi aí que ganhou o sobrenome espiritual "Luce"
            (luz, em italiano). Morreu aos 18 anos, em 1990, e foi beatificada em 2010 pelo
            Papa Bento XVI, sendo a primeira beata do Movimento dos Focolares.</p>

            <p>Três histórias diferentes, uma mesma mensagem: não é preciso esperar
            envelhecer para viver com profundidade a própria fé.</p>

            <div class="cta-blog-produto">
              <p>Um exemplo de fé jovem pra carregar com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Carlo Acutis →</a>
            </div>
        """,
    },
    "santos-carmelitas-espiritualidade-do-carmelo": {
        "titulo": "Santos carmelitas: a espiritualidade do Monte Carmelo",
        "resumo": (
            "Santa Teresa d'Ávila, São João da Cruz, Santa Teresinha e Edith Stein "
            "carregam o mesmo hábito e uma busca em comum: a união íntima com Deus."
        ),
        "produto_relacionado_id": "teresas-do-carmelo",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>A Ordem do Carmelo nasceu no século XII, quando um grupo de eremitas
            cristãos passou a viver em oração e silêncio no Monte Carmelo, na atual Israel
            -- o mesmo monte onde, segundo a tradição, o profeta Elias enfrentou os
            profetas de Baal. Ao longo dos séculos seguintes, a espiritualidade carmelita se
            espalhou pela Europa e formou alguns dos místicos mais influentes da história da
            Igreja.</p>

            <h2>Santa Teresa d'Ávila, a reformadora</h2>
            <p><a href="/produto/santa-teresa-davila">Santa Teresa d'Ávila</a> (1515-1582)
            entrou para o Carmelo ainda jovem, na Espanha, mas percebeu com o tempo que a
            vida da ordem havia se afastado do rigor e do silêncio original. Liderou então
            uma reforma que deu origem aos Carmelitas Descalços, e escreveu obras
            fundamentais sobre oração e vida interior, como <em>Castelo Interior</em>. Foi
            declarada Doutora da Igreja em 1970 -- a primeira mulher a receber esse
            título.</p>

            <h2>São João da Cruz, o poeta da noite escura</h2>
            <p><a href="/produto/sao-joao-da-cruz">São João da Cruz</a> (1542-1591) foi
            companheiro de Teresa d'Ávila na reforma carmelita, e por isso mesmo chegou a
            ser preso e maltratado por religiosos que se opunham às mudanças. Foi durante
            esse cativeiro que escreveu parte de sua poesia mística mais conhecida,
            incluindo o conceito de "noite escura da alma" -- o período de aridez espiritual
            que, segundo ele, precede uma união mais profunda com Deus. Também é Doutor da
            Igreja.</p>

            <h2>Santa Teresinha, a pequena via</h2>
            <p>Três séculos depois, Santa Teresinha do Menino Jesus levou essa mesma
            tradição carmelita a um caminho mais simples -- a "pequena via" das pequenas
            coisas feitas com amor, que já contamos em detalhe <a href="/blog/santa-teresinha-caminho-da-infancia-espiritual">num
            outro artigo aqui do blog</a>.</p>

            <h2>Edith Stein, a filósofa que virou carmelita</h2>
            <p><a href="/produto/edith-stein">Edith Stein</a> (1891-1942) teve uma
            trajetória bem diferente das demais: nascida numa família judia na Alemanha,
            tornou-se uma respeitada filósofa antes de se converter ao catolicismo e entrar
            para o Carmelo, adotando o nome de Teresa Benedita da Cruz. Presa pelos nazistas
            justamente por sua origem judaica, morreu no campo de concentração de Auschwitz
            em 1942. Foi canonizada em 1998 e declarada copadroeira da Europa em 1999.</p>

            <div class="cta-blog-produto">
              <p>A força espiritual do Carmelo, numa peça só</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver Teresas do Carmelo (medalha, entremeio e chaveiro) →</a>
            </div>
        """,
    },
    "titulos-de-sao-jose": {
        "titulo": "Os vários títulos de São José: um só santo, muitas invocações",
        "resumo": (
            "Terror dos Demônios, Castíssimo Coração, São José Dormindo -- entenda por "
            "que um mesmo santo aparece em tantas invocações diferentes."
        ),
        "produto_relacionado_id": "sao-jose",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>Já contamos aqui a <a href="/blog/sao-jose-pai-adotivo-de-jesus">história de
            São José</a>, pai adotivo de Jesus. Mas quem visita uma livraria católica ou
            navega por um catálogo de medalhas costuma se deparar com títulos diferentes
            para o mesmo santo -- "São José Operário", "Castíssimo Coração de São José",
            "São José Dormindo", "São José Terror dos Demônios". Não são santos diferentes:
            são invocações, formas da Igreja destacar um aspecto específico da vida ou da
            proteção de São José, conforme a necessidade de quem reza.</p>

            <h2>Castíssimo Coração de São José</h2>
            <p><a href="/produto/castissimo-coracao-de-sao-jose">O Castíssimo Coração de
            São José</a> segue o mesmo modelo de devoção do Sagrado Coração de Jesus e do
            Imaculado Coração de Maria -- só que aqui destacando a pureza e a fidelidade de
            José em seu papel de esposo e pai, sem nenhum vínculo carnal com Maria segundo a
            tradição católica. É uma devoção que reforça o amor casto e a entrega total à
            vontade de Deus.</p>

            <h2>São José Dormindo</h2>
            <p>A imagem de <a href="/produto/sao-jose-dormindo">São José dormindo</a> vem
            direto dos Evangelhos: foi enquanto dormia que José recebeu, por três vezes, a
            visita de um anjo em sonho -- avisando sobre a gravidez de Maria, sobre a fuga
            para o Egito e sobre o momento seguro de voltar para Nazaré. A devoção ganhou
            força recente com o Papa Francisco, que mantinha sobre sua própria escrivaninha
            uma imagem de São José dormindo e o hábito de colocar embaixo dela pedidos de
            oração escritos à mão, confiando-os ao santo enquanto "dormia" sobre eles.</p>

            <h2>São José Terror dos Demônios</h2>
            <p>Esse título vem direto da Litania de São José, oração tradicional aprovada
            pela Igreja em 1909, que o invoca como <em>"Terror daemonum"</em> -- terror dos
            demônios. A ideia por trás da invocação é simples: se José teve força e
            coragem suficientes para proteger a Sagrada Família de perigos reais (como a
            perseguição de Herodes), pode também proteger espiritualmente quem recorre a
            ele contra qualquer forma de mal.</p>

            <p>São invocações diferentes, mas sempre do mesmo José -- carpinteiro, esposo,
            pai e protetor.</p>

            <div class="cta-blog-produto">
              <p>Escolha a invocação de São José que mais fala com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São José →</a>
            </div>
        """,
    },
    "santa-faustina-e-jesus-misericordioso": {
        "titulo": "Santa Faustina e Jesus Misericordioso: a origem da Divina Misericórdia",
        "resumo": (
            "Uma freira polonesa simples deu origem a uma das devoções que mais cresceram "
            "no mundo católico no último século. Conheça a história por trás da imagem "
            "\"Jesus, eu confio em Vós\"."
        ),
        "produto_relacionado_id": "santa-faustina",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>Faustina Kowalska nasceu em 1905, numa família humilde de agricultores da
            Polônia, e entrou ainda jovem para a Congregação das Irmãs de Nossa Senhora da
            Misericórdia. Foi lá, a partir de 1931, que começou a registrar em seu diário
            uma série de experiências místicas: visões e diálogos com Jesus, que lhe pedia
            que espalhasse a mensagem da sua misericórdia infinita por todo o mundo.</p>

            <h2>A imagem de Jesus Misericordioso</h2>
            <p>Numa dessas visões, Faustina viu Jesus com a mão direita levantada em sinal
            de bênção e a esquerda tocando o peito, de onde saíam dois raios -- um pálido
            e outro vermelho, representando a água e o sangue derramados na cruz. Segundo o
            pedido que ela relatou ter recebido, a imagem deveria trazer a inscrição
            <strong>"Jesus, eu confio em Vós"</strong> -- e é exatamente assim que a
            <a href="/produto/jesus-misericordioso">imagem de Jesus Misericordioso</a> é
            retratada até hoje.</p>

            <h2>A Coroazinha e o Domingo da Misericórdia</h2>
            <p>Além da imagem, Faustina também recebeu -- segundo seu relato -- uma oração
            específica para pedir a misericórdia de Deus para si e para o mundo: a
            Coroazinha da Divina Misericórdia, rezada com um terço comum, mas com orações
            próprias. A devoção cresceu de forma tão significativa ao longo do século XX
            que o Papa João Paulo II, também polonês e grande devoto da causa, instituiu
            oficialmente o <strong>Domingo da Divina Misericórdia</strong> em 2000 --
            celebrado sempre no domingo seguinte à Páscoa -- no mesmo dia em que canonizou
            Santa Faustina.</p>

            <p>De uma freira simples, quase desconhecida em vida, nasceu uma das devoções
            que mais rapidamente se espalhou pelo mundo católico nas últimas décadas.</p>

            <div class="cta-blog-produto">
              <p>A confiança que atravessa qualquer dificuldade</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santa Faustina →</a>
            </div>
        """,
    },
    "arcanjos-miguel-gabriel-rafael": {
        "titulo": "Miguel, Gabriel e Rafael: os três arcanjos citados pela Bíblia",
        "resumo": (
            "Guerreiro, mensageiro e curador -- os três únicos arcanjos chamados pelo "
            "nome na Bíblia têm papéis bem diferentes entre si. Conheça cada um."
        ),
        "produto_relacionado_id": "santos-arcanjos",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>Entre todos os anjos mencionados na tradição cristã, apenas três são
            chamados pelo próprio nome nos textos bíblicos reconhecidos pela Igreja
            Católica: Miguel, Gabriel e Rafael. Não por acaso, a Igreja celebra os três
            juntos, no mesmo dia -- 29 de setembro -- reconhecendo que, apesar de papéis
            bem diferentes, formam um só grupo de mensageiros a serviço de Deus.</p>

            <h2>Miguel, o guerreiro</h2>
            <p>Já contamos em detalhe a <a href="/blog/sao-miguel-arcanjo-oracao-de-protecao">história
            de São Miguel Arcanjo</a> aqui no blog -- líder dos exércitos celestiais contra
            o mal, seu nome significa "Quem é como Deus?".</p>

            <h2>Gabriel, o mensageiro</h2>
            <p><a href="/produto/sao-gabriel">Gabriel</a> é o arcanjo dos grandes anúncios:
            foi ele quem apareceu ao sacerdote Zacarias para anunciar o nascimento de João
            Batista, e é ele também quem aparece a Maria, em Nazaré, para anunciar que ela
            seria a mãe de Jesus -- a Anunciação, um dos momentos mais retratados de toda a
            arte cristã. Seu nome significa "força de Deus" ou "Deus é minha força".</p>

            <h2>Rafael, o curador</h2>
            <p><a href="/produto/sao-rafael">Rafael</a> aparece apenas no Livro de Tobias,
            onde se disfarça de companheiro de viagem do jovem Tobias, protegendo-o ao
            longo do caminho, ajudando-o a encontrar sua futura esposa, Sara, e por fim
            curando a cegueira de seu pai, Tobit. Seu nome significa "Deus cura", e por
            causa dessa história é considerado padroeiro dos viajantes, dos médicos e
            também das relações e encontros que dão certo.</p>

            <p>Guerra, anúncio e cura -- três formas bem diferentes de servir, todas
            reunidas nesses três mensageiros de Deus.</p>

            <div class="cta-blog-produto">
              <p>Os três arcanjos protegendo você ao mesmo tempo</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver Santos Arcanjos (medalha, entremeio e chaveiro) →</a>
            </div>
        """,
    },
    "familia-martin-pais-de-santa-teresinha": {
        "titulo": "Louis e Zélie Martin: os pais de Santa Teresinha, canonizados juntos",
        "resumo": (
            "Um relojoeiro e uma rendeira franceses criaram cinco filhas que se tornaram "
            "freiras -- e foram os primeiros esposos canonizados juntos na mesma cerimônia."
        ),
        "produto_relacionado_id": "familia-martin",
        "publicado_em": "2026-09-09",
        "corpo_html": """
            <p>Quando se fala da <a href="/blog/santa-teresinha-caminho-da-infancia-espiritual">Santa
            Teresinha do Menino Jesus</a>, é comum esquecer que ela cresceu numa casa com
            outras quatro irmãs -- e que todas as cinco, sem exceção, escolheram a vida
            religiosa. Por trás dessa família tão incomum estavam Louis e Zélie Martin, um
            casal francês do século XIX hoje reconhecido pela Igreja como modelo de
            santidade vivida dentro do casamento e da vida familiar comum.</p>

            <h2>Um relojoeiro e uma rendeira</h2>
            <p>Louis Martin trabalhava como relojoeiro e joalheiro em Alençon, na França, e
            Zélie Guérin era uma habilidosa fabricante de rendas, dona do próprio pequeno
            negócio -- uma independência pouco comum para mulheres da época. Casaram-se em
            1858 e tiveram nove filhos, dos quais quatro morreram ainda bebês -- uma
            realidade dura, mas frequente naquele período. As cinco filhas que sobreviveram
            até a vida adulta entraram todas para conventos.</p>

            <h2>Uma vida marcada por perda e fé</h2>
            <p>Zélie foi diagnosticada com câncer de mama e morreu em 1877, quando
            Teresinha, a caçula, tinha apenas quatro anos. Louis criou sozinho as cinco
            filhas a partir daí, sustentando com dedicação a fé e a educação de todas elas
            -- inclusive apoiando o pedido pouco comum de Teresinha para entrar no convento
            ainda adolescente, aos 15 anos.</p>

            <h2>Os primeiros esposos canonizados juntos</h2>
            <p>Louis e Zélie foram beatificados juntos em 2008 e canonizados juntos pelo
            Papa Francisco em 2015 -- tornando-se o primeiro casal de esposos da história
            moderna da Igreja canonizado na mesma cerimônia. O reconhecimento reforça uma
            mensagem cada vez mais valorizada: a santidade não pertence só a padres, freiras
            e religiosos -- também pode florescer dentro de um casamento comum, criando
            filhos, sustentando uma casa, enfrentando perdas.</p>

            <div class="cta-blog-produto">
              <p>Uma família inteira de fé, numa só peça</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver Família Martin (medalha, entremeio e chaveiro) →</a>
            </div>
        """,
    },
    "santos-martires-de-cunhau-e-uruacu": {
        "titulo": "Santos Mártires de Cunhaú e Uruaçu: a fé que resistiu no Rio Grande do Norte",
        "resumo": (
            "Em 1645, dois massacres no litoral potiguar deram origem aos primeiros "
            "santos nascidos em solo brasileiro. Uma história que começa bem perto daqui."
        ),
        "produto_relacionado_id": "santos-martires-do-rn",
        "publicado_em": "2026-09-10",
        "corpo_html": """
            <p>Nem toda devoção do nosso catálogo nasceu do outro lado do mundo -- essa
            começou bem perto daqui. Em 1645, o Brasil holandês vivia um período de forte
            perseguição religiosa movida por tropas calvinistas contra a população
            católica do litoral do que hoje é o Rio Grande do Norte.</p>

            <h2>Dois massacres, poucos meses de diferença</h2>
            <p>No dia 16 de julho de 1645, um grupo de fiéis participava de uma missa na
            Capela de Nossa Senhora das Candeias, em Cunhaú (hoje Canguaretama-RN), quando
            tropas calvinistas trancaram as portas da igreja e assassinaram todos que
            estavam dentro. Meses depois, em 3 de outubro do mesmo ano, um ataque
            semelhante aconteceu em Uruaçu, no atual município de São Gonçalo do
            Amarante -- entre as vítimas estava o padre Ambrósio Francisco Ferro e o leigo
            Mateus Moreira. Ao todo, cerca de trinta pessoas -- vinte e cinco homens e
            cinco mulheres -- morreram nos dois episódios, reunidas simplesmente por
            praticar sua fé.</p>

            <h2>De beatos a santos, quase quatro séculos depois</h2>
            <p>Os mártires de Cunhaú e Uruaçu foram beatificados em 5 de março de 2000
            pelo Papa João Paulo II, e canonizados em 15 de outubro de 2017 pelo Papa
            Francisco -- tornando-se os primeiros santos nascidos e martirizados em solo
            brasileiro. A cerimônia de canonização, em Roma, reuniu cerca de 35 mil
            pessoas, incluindo mais de 400 potiguares que viajaram até lá especialmente
            para acompanhar o momento.</p>

            <h2>Uma devoção que se pode visitar</h2>
            <p>Diferente de muitas devoções que só existem em livros e imagens, essa dá
            pra visitar de perto: a Capela dos Mártires, em São Gonçalo do Amarante, o
            Santuário dos Mártires, no bairro Nossa Senhora de Nazaré, em Natal, e a
            capela original de Nossa Senhora das Candeias, no antigo engenho de Cunhaú, em
            Canguaretama, seguem recebendo romarias todos os anos -- uma fé que resistiu há
            quase 400 anos, na mesma terra de onde saem nossas medalhas.</p>

            <div class="cta-blog-produto">
              <p>Uma devoção nascida bem perto daqui</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro dos Santos Mártires do RN →</a>
            </div>
        """,
    },
    "beata-nha-chica-baependi": {
        "titulo": "Beata Nhá Chica: a ex-escravizada que virou mãe dos pobres de Baependi",
        "resumo": (
            "Analfabeta, nascida escravizada, Francisca de Paula de Jesus se tornou a "
            "primeira mulher negra leiga beatificada pela Igreja no Brasil."
        ),
        "produto_relacionado_id": "beata-nha-xica",
        "publicado_em": "2026-09-10",
        "corpo_html": """
            <p>Francisca de Paula de Jesus, mais conhecida pelo apelido carinhoso de
            <strong>Nhá Chica</strong> (também escrito "Nhá Xica"), nasceu em 1810 em Minas
            Gerais e passou a maior parte da vida em Baependi, pequena cidade no sul do
            estado. Nascida em condição de escravidão, teve uma vida marcada pela pobreza e
            pelo trabalho duro desde cedo -- e, ainda assim, tornou-se uma das figuras
            espirituais mais queridas da região.</p>

            <h2>Uma vida simples, dedicada aos outros</h2>
            <p>Sem nunca ter aprendido a ler ou escrever, Nhá Chica viveu de forma humilde,
            mas dedicou boa parte do que tinha -- tempo, atenção, os poucos recursos que
            possuía -- a ajudar quem precisava em Baependi, o que lhe rendeu o apelido
            popular de "mãe dos pobres". Morreu em 1895, e sua devoção, sempre viva entre
            os moradores da cidade, cresceu de forma constante ao longo do século
            seguinte.</p>

            <h2>Primeira mulher negra leiga beatificada no Brasil</h2>
            <p>O processo de beatificação reconheceu, em 2011, suas virtudes heroicas, e em
            2013 o Papa Bento XVI aprovou o milagre necessário para sua beatificação: a
            cura de uma professora de uma cidade vizinha, que se recuperou de um problema
            cardíaco congênito sem cirurgia, atribuída à intercessão de Nhá Chica. Com a
            beatificação, em 4 de maio de 2013, ela se tornou a primeira mulher negra leiga
            (ou seja, sem ser freira) beatificada pela Igreja no Brasil.</p>

            <p>Uma história que mostra que a santidade não exige nem estudo, nem riqueza,
            nem poder -- só uma vida inteira dedicada a cuidar de quem está por perto.</p>

            <div class="cta-blog-produto">
              <p>A força de uma vida simples e dedicada</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro da Beata Nhá Chica →</a>
            </div>
        """,
    },
    "padre-cicero-e-frei-damiao-devocao-nordestina": {
        "titulo": "Padre Cícero e Frei Damião: duas devoções que marcaram o Nordeste",
        "resumo": (
            "Nenhum dos dois foi oficialmente beatificado até hoje -- mas poucas figuras "
            "marcaram tanto a fé popular do Nordeste brasileiro quanto esses dois padres."
        ),
        "produto_relacionado_id": "padre-cicero",
        "publicado_em": "2026-09-10",
        "corpo_html": """
            <p>Nem toda devoção presente no nosso catálogo já recebeu um título oficial da
            Igreja -- e é importante ser honesto sobre isso. Padre Cícero e Frei Damião
            estão entre as figuras religiosas mais amadas e visitadas do Nordeste
            brasileiro, mas nenhum dos dois foi, até hoje, oficialmente beatificado.
            Mesmo assim, a fé popular que os cerca é grande demais pra ser ignorada.</p>

            <h2><a href="/produto/padre-cicero">Padre Cícero</a>, o padrinho de Juazeiro</h2>
            <p>Cícero Romão Batista (1844-1934) foi pároco em Juazeiro do Norte, no Ceará,
            cidade que se transformou, em boa parte graças a ele, num dos maiores polos de
            romaria católica do Brasil. Sua relação com a hierarquia da Igreja foi
            historicamente conturbada -- chegou a ser suspenso de exercer funções
            sacerdotais em 1894, após controvérsias envolvendo um episódio atribuído a
            milagre, e só teve sua situação parcialmente normalizada anos depois. Apesar
            disso, seu processo de causa de beatificação avança: a fase realizada na
            Diocese de Crato (CE) foi concluída em 2025, e o caso segue agora em análise no
            Vaticano, ainda sem data prevista para uma eventual beatificação. Enquanto isso,
            é tratado por milhões de devotos, sobretudo no Ceará, como "Padim Ciço".</p>

            <h2>Frei Damião, o missionário do Nordeste</h2>
            <p><a href="/produto/frei-damiao">Frei Damião de Bozzano</a> (1898-1997)
            nasceu Pio Giannotti, na Itália, e chegou ao Brasil em 1931 como frade
            capuchinho. Dedicou 66 anos de vida a percorrer cidades do Norte e Nordeste
            pregando o Evangelho, quase sempre a pé ou em meios de transporte simples,
            tornando-se uma figura extremamente familiar e querida em centenas de
            comunidades ao longo desse período. Foi declarado <strong>Venerável</strong>
            pelo Papa Francisco em 2019, um passo formal a caminho da beatificação, que
            ainda depende do reconhecimento oficial de um milagre.</p>

            <p>Duas trajetórias diferentes, unidas pelo mesmo carinho popular -- a prova de
            que, no Nordeste, a devoção muitas vezes anda alguns passos à frente dos
            processos formais da Igreja.</p>

            <div class="cta-blog-produto">
              <p>A fé popular do Nordeste, numa medalha</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro do Padre Cícero →</a>
            </div>
        """,
    },
    "francisco-e-jacinta-pastorinhos-de-fatima": {
        "titulo": "Francisco e Jacinta: os pastorinhos que viram Nossa Senhora em Fátima",
        "resumo": (
            "Duas crianças portuguesas, mortas ainda na infância, se tornaram os santos "
            "não-mártires mais jovens da história da Igreja Católica."
        ),
        "produto_relacionado_id": "francisco-de-fatima",
        "publicado_em": "2026-09-10",
        "corpo_html": """
            <p>Já contamos aqui <a href="/blog/nossa-senhora-aparecida-historia">a história
            de Nossa Senhora Aparecida</a>, mas o Brasil não é o único país com uma
            aparição mariana que marcou profundamente a fé católica. Em 1917, em Fátima,
            Portugal, três crianças pastoras -- os irmãos <a href="/produto/francisco-de-fatima">Francisco</a>
            e Jacinta Marto, e a prima deles, Lúcia dos Santos -- afirmaram ter visto Nossa
            Senhora em seis aparições sucessivas, entre maio e outubro daquele ano.</p>

            <h2>Duas crianças, uma missão de oração</h2>
            <p>Segundo o relato dos três pastorinhos, Nossa Senhora pediu que rezassem o
            terço todos os dias pela paz do mundo e fizessem sacrifícios pelos pecadores --
            um pedido que as crianças levaram a sério com uma seriedade impressionante para
            a idade que tinham (Francisco tinha 9 anos; Jacinta, 7). Pouco tempo depois,
            ambos contraíram a gripe espanhola, pandemia que matou milhões de pessoas ao
            redor do mundo entre 1918 e 1920. Francisco morreu em 1919, aos 10 anos; Jacinta,
            em 1920, aos 9.</p>

            <h2>Os santos mais jovens não-mártires da história</h2>
            <p>Em 2017, no mesmo ano do centenário das aparições, o Papa Francisco
            canonizou Francisco e Jacinta -- tornando-os os santos não-mártires mais jovens
            já reconhecidos pela Igreja Católica (crianças que morreram mártires, matadas
            por causa da fé, já haviam sido canonizadas antes, mas nenhuma que tenha
            morrido de causas naturais tão jovem). Lúcia, a prima mais velha, viveu muito
            mais tempo -- tornou-se freira carmelita e faleceu em 2005, aos 97 anos; seu
            processo de beatificação segue em andamento.</p>

            <p>Uma pequena aparição num campo de Portugal, sustentada pela fé simples de
            duas crianças, que se tornou uma das devoções marianas mais fortes do mundo
            católico.</p>

            <div class="cta-blog-produto">
              <p>A fé simples de uma criança</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Francisco de Fátima →</a>
            </div>
        """,
    },
    "espirito-santo-pentecostes-santissima-trindade": {
        "titulo": "Espírito Santo, Pentecostes e Santíssima Trindade: entendendo as três devoções",
        "resumo": (
            "Três imagens diferentes, um só mistério de fé -- entenda a diferença entre "
            "essas devoções que aparecem juntas com frequência."
        ),
        "produto_relacionado_id": "espirito-santo",
        "publicado_em": "2026-09-10",
        "corpo_html": """
            <p>Entre as devoções do catálogo, três aparecem com frequência lado a lado e
            geram dúvida sobre a diferença entre elas: Espírito Santo, Pentecostes e
            Santíssima Trindade. Não são a mesma coisa -- mas estão profundamente
            conectadas.</p>

            <h2>Espírito Santo</h2>
            <p>Na fé católica, Deus é <strong>um só</strong>, mas existe em três pessoas
            distintas: Pai, Filho (Jesus) e Espírito Santo. O Espírito Santo é
            tradicionalmente representado na forma de uma pomba branca, imagem que vem do
            relato do batismo de Jesus no rio Jordão, quando o Espírito teria descido sobre
            ele "como uma pomba". É invocado como fonte de sabedoria, força e inspiração
            para viver a fé no dia a dia.</p>

            <h2>Pentecostes</h2>
            <p>O <a href="/produto/pentecostes">Pentecostes</a> é o EVENTO bíblico
            específico em que o Espírito Santo desceu sobre os apóstolos, cinquenta dias
            depois da Páscoa, na forma de "línguas de fogo" -- dando a eles a coragem e a
            capacidade de pregar o Evangelho em várias línguas para os povos reunidos em
            Jerusalém naquele dia. É considerado o marco do nascimento oficial da Igreja
            Católica como comunidade organizada de fiéis, e é celebrado todos os anos, dez
            dias após a Ascensão de Jesus.</p>

            <h2>Santíssima Trindade</h2>
            <p>Já a <a href="/produto/santissima-trindade">Santíssima Trindade</a> não é um
            evento nem uma pessoa isolada -- é o próprio mistério central da fé católica: a
            crença de que Deus é Pai, Filho e Espírito Santo ao mesmo tempo, três pessoas
            distintas e, ainda assim, um único Deus. É um dos conceitos mais difíceis de
            explicar racionalmente dentro da teologia católica, por isso costuma ser
            representado visualmente -- muitas vezes como três figuras reunidas numa só
            imagem -- em vez de apenas descrito em palavras.</p>

            <p>Três devoções, um só fio condutor: a presença constante de Deus, seja
            guiando (Espírito Santo), agindo na história (Pentecostes) ou existindo em sua
            plenitude (Trindade).</p>

            <div class="cta-blog-produto">
              <p>A presença do Espírito Santo com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro do Espírito Santo →</a>
            </div>
        """,
    },
    "nossa-senhora-titulos-e-aparicoes": {
        "titulo": "Nossa Senhora: por que ela aparece de tantas formas diferentes?",
        "resumo": (
            "Lourdes, Guadalupe, Carmo, Perpétuo Socorro -- dezenas de nomes para a "
            "mesma Maria. Entenda a diferença entre uma aparição e um título."
        ),
        "produto_relacionado_id": "nossa-senhora-imaculada-conceicao",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Quem já visitou uma livraria católica ou olhou o catálogo de uma loja de
            medalhas provavelmente notou algo curioso: Nossa Senhora aparece sob dezenas de
            nomes diferentes -- Aparecida, Lourdes, Guadalupe, Fátima, Carmo, e por aí vai.
            Não são "Marias diferentes": é sempre a mesma mãe de Jesus, mas cada título
            representa ou uma aparição específica em um lugar e época, ou um aspecto
            particular de sua fé e sua história.</p>

            <h2>Nossa Senhora de Lourdes</h2>
            <p>Em 1858, na cidade francesa de Lourdes, uma jovem camponesa chamada
            Bernadette Soubirous relatou dezoito aparições de uma "senhora" numa gruta às
            margens do rio Gave. Na última delas, a aparição teria se identificado dizendo
            "Eu sou a Imaculada Conceição" -- confirmando, segundo os fiéis, o dogma que a
            Igreja havia proclamado apenas quatro anos antes. Lourdes se tornou um dos
            maiores destinos de peregrinação do mundo, especialmente por doentes em busca
            de cura na água da fonte que brotou no local. Veja a
            <a href="/produto/nossa-senhora-de-lourdes">medalha, entremeio e chaveiro de Nossa Senhora de Lourdes</a>.</p>

            <h2>Nossa Senhora de Guadalupe</h2>
            <p>Em 1531, no México, Maria teria aparecido ao indígena Juan Diego no monte
            Tepeyac, deixando impressa em seu manto (tilma) uma imagem que, segundo os
            devotos, permanece preservada até hoje na Basílica de Guadalupe, na Cidade do
            México -- um dos santuários marianos mais visitados do planeta. É a padroeira
            oficial de todo o continente americano. Veja a
            <a href="/produto/nossa-senhora-de-guadalupe">medalha, entremeio e chaveiro de Nossa Senhora de Guadalupe</a>.</p>

            <h2>Nossa Senhora do Perpétuo Socorro</h2>
            <p>Diferente das duas anteriores, essa devoção não vem de uma aparição, mas de
            um ícone: uma pintura bizantina antiga, de autoria desconhecida, que retrata
            Maria com o Menino Jesus enquanto dois anjos mostram a ele os instrumentos da
            Paixão. O quadro está guardado em Roma desde o século XIX, sob os cuidados dos
            padres Redentoristas, e se tornou uma das imagens marianas mais reproduzidas do
            mundo católico. Veja a
            <a href="/produto/nossa-senhora-do-perpetuo-socorro">medalha, entremeio e chaveiro de Nossa Senhora do Perpétuo Socorro</a>.</p>

            <h2>Nossa Senhora do Carmo</h2>
            <p>Ligada à Ordem do Carmelo (a mesma dos <a href="/blog/santos-carmelitas-espiritualidade-do-carmelo">santos
            carmelitas</a> que já contamos aqui), Nossa Senhora do Carmo é associada
            tradicionalmente ao escapulário -- um pequeno tecido bento usado como sinal de
            consagração e proteção mariana, que a tradição afirma ter sido entregue por
            Maria a São Simão Stock, no século XIII. Veja a
            <a href="/produto/nossa-senhora-do-carmo">medalha, entremeio e chaveiro de Nossa Senhora do Carmo</a>.</p>

            <h2>Imaculada Conceição</h2>
            <p>Diferente das anteriores, essa não é uma aparição nem um objeto -- é um
            <strong>dogma</strong>, uma verdade de fé definida oficialmente pela Igreja em
            1854: a crença de que Maria foi concebida sem o pecado original, desde o
            primeiro instante de sua existência. É uma das quatro grandes definições
            marianas da Igreja Católica, e é justamente essa verdade que a aparição de
            Lourdes teria vindo confirmar, quatro anos depois.</p>

            <p>Aparições, ícones, dogmas -- caminhos diferentes que levam sempre ao mesmo
            lugar: a mesma Maria, mãe de Jesus, olhada por ângulos diferentes ao longo da
            história da fé.</p>

            <div class="cta-blog-produto">
              <p>Escolha o título de Nossa Senhora que mais fala com você</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro da Imaculada Conceição →</a>
            </div>
        """,
    },
    "santo-antonio-de-padua-santo-casamenteiro": {
        "titulo": "Santo Antônio de Pádua: por que ele é o santo casamenteiro",
        "resumo": (
            "Pregador, professor e um dos santos mais populares do Brasil -- entenda a "
            "origem da tradição de pedir a Santo Antônio ajuda para casar."
        ),
        "produto_relacionado_id": "santo-antonio",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Fernando Martins de Bulhões nasceu em Lisboa, Portugal, em 1195, numa
            família nobre, e entrou ainda jovem para a vida religiosa -- primeiro como
            cônego agostiniano, depois como frade franciscano, quando adotou o nome de
            Antônio. Conhecido por sua eloquência e profundo conhecimento das Escrituras,
            tornou-se um dos maiores pregadores de sua época, viajando por Portugal, Itália
            e França para evangelizar. Morreu ainda jovem, aos 35 anos, em Pádua, na
            Itália -- cidade que hoje carrega seu nome mais conhecido.</p>

            <h2>Por que "casamenteiro"?</h2>
            <p>A fama de Santo Antônio como intercessor para encontrar um bom casamento
            vem, principalmente, de uma tradição popular portuguesa que remonta a séculos:
            a de que ele ajudaria moças a encontrar um marido, prática que incluía até
            rituais caseiros (como "afogar" uma imagem do santo até o pedido ser atendido --
            algo que a Igreja nunca recomendou oficialmente, mas que se popularizou de
            forma folclórica). O 13 de junho, dia de sua festa, é tradicionalmente marcado
            por bênçãos de noivos e casais em igrejas por todo o Brasil e Portugal.</p>

            <h2>O santo das coisas perdidas</h2>
            <p>Outra devoção fortíssima ligada a Santo Antônio é a de recuperar objetos
            perdidos -- tradição que remonta a um episódio contado sobre sua própria vida,
            em que teria recuperado um livro de salmos roubado após rezar por sua
            devolução. Até hoje, é comum ouvir alguém pedir "Santo Antônio, ajuda a
            achar..." diante de uma chave sumida ou um documento extraviado.</p>

            <h2>Parte da festa junina brasileira</h2>
            <p>No Brasil, o dia de Santo Antônio (13 de junho) abre o tradicional trio de
            festas juninas do mês, seguido por São João Batista (24 de junho) e São Pedro
            (29 de junho) -- fazendo dele, além de um dos santos mais queridos em devoção
            pessoal, também parte de uma das maiores tradições culturais e religiosas do
            calendário brasileiro.</p>

            <div class="cta-blog-produto">
              <p>Um santo pra pedir ajuda em qualquer busca</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santo Antônio →</a>
            </div>
        """,
    },
    "sao-jorge-cavaleiro-e-martir": {
        "titulo": "São Jorge: a lenda do dragão e a história por trás do cavaleiro",
        "resumo": (
            "Soldado romano martirizado no século III, São Jorge é hoje um dos santos "
            "mais populares do Brasil. Conheça a lenda e a história real por trás dela."
        ),
        "produto_relacionado_id": "sao-jorge",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Jorge foi, segundo a tradição, um soldado romano de origem grega que
            serviu no exército do imperador Diocleciano, no fim do século III, numa época
            de intensa perseguição aos cristãos. Recusando-se a abandonar sua fé mesmo sob
            ordem direta do imperador, foi torturado e decapitado por volta do ano 303,
            tornando-se um dos mártires mais venerados dos primeiros séculos da Igreja.</p>

            <h2>A lenda do dragão</h2>
            <p>A história mais conhecida sobre São Jorge, porém, não é histórica, e sim
            uma lenda medieval que só surgiu séculos depois de sua morte: a de que ele
            teria salvo uma cidade (geralmente identificada como Selene, na Líbia) de um
            dragão que aterrorizava a população, exigindo sacrifícios humanos regulares. No
            dia em que a vítima escolhida era a própria filha do rei, Jorge apareceu,
            enfrentou e derrotou o dragão, salvando a princesa e convertendo toda a cidade
            ao cristianismo. A imagem do cavaleiro montado, lança em riste contra o dragão,
            é uma das mais reproduzidas de toda a arte religiosa.</p>

            <h2>Padroeiro de soldados e de cidades inteiras</h2>
            <p>Por seu histórico como soldado corajoso e fiel até a morte, São Jorge se
            tornou padroeiro de exércitos, de cavaleiros e de nações inteiras -- é o santo
            padroeiro da Inglaterra, da Geórgia (país que leva seu nome) e também do Rio de
            Janeiro, onde sua festa, em 23 de abril, é feriado municipal e reúne
            multidões nas ruas todos os anos.</p>

            <p>Entre a história do soldado mártir e a lenda do cavaleiro contra o dragão,
            São Jorge segue sendo um símbolo de coragem para enfrentar qualquer "dragão" --
            literal ou simbólico -- que apareça pelo caminho.</p>

            <div class="cta-blog-produto">
              <p>Coragem pra enfrentar qualquer desafio</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São Jorge →</a>
            </div>
        """,
    },
    "santo-expedito-santo-das-causas-urgentes": {
        "titulo": "Santo Expedito: a origem do santo das causas urgentes",
        "resumo": (
            "Um grito de \"hoje!\" contra um corvo que gritava \"amanhã\" -- essa é a "
            "lenda por trás de um dos santos mais procurados em momentos de urgência."
        ),
        "produto_relacionado_id": "santo-expedito",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Diferente da maioria dos santos deste catálogo, é importante começar sendo
            direto: a história de Santo Expedito tem pouquíssimo lastro documental
            histórico. Estudiosos da própria Igreja -- os bolandistas, responsáveis por
            avaliar criticamente a vida dos santos -- levantam a hipótese de que seu nome
            possa até ter surgido de uma leitura equivocada da palavra "Elpidius" (outro
            nome próprio) em documentos antigos. Ainda assim, a devoção popular a Santo
            Expedito é imensa, especialmente no Brasil.</p>

            <h2>Um soldado romano na Armênia</h2>
            <p>Segundo a tradição mais difundida, Expedito teria sido comandante de uma
            legião romana baseada na Armênia, no fim do século III, e teria se convertido
            ao cristianismo -- decisão que lhe custou a vida durante a perseguição movida
            pelo imperador Diocleciano, sendo martirizado junto de seus soldados.</p>

            <h2>A lenda do corvo: "amanhã" contra "hoje"</h2>
            <p>A história mais contada sobre ele, no entanto, é simbólica: no momento de
            sua conversão, o próprio mal teria aparecido a Expedito na forma de um corvo,
            gritando repetidamente "cras, cras, cras" -- "amanhã", em latim -- tentando
            convencê-lo a adiar a decisão de mudar de vida. Expedito, segundo a lenda,
            pisou sobre o corvo e respondeu "hodie" -- "hoje". Dessa cena nasceu tanto seu
            título de "santo das causas urgentes" quanto a inscrição "HOJE", que aparece
            até hoje estampada em suas imagens e medalhas.</p>

            <h2>Uma devoção sobre não adiar</h2>
            <p>Seja qual for a base histórica real por trás da figura, a mensagem que
            sustenta essa devoção há séculos continua atual: diante de uma necessidade
            urgente, não vale a pena adiar para amanhã o que precisa de resposta hoje --
            nem a oração, nem a atitude diante do problema.</p>

            <div class="cta-blog-produto">
              <p>Pra quando a resposta não pode esperar</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santo Expedito →</a>
            </div>
        """,
    },
    "santa-dulce-dos-pobres-primeira-santa-brasileira": {
        "titulo": "Santa Dulce dos Pobres: a primeira santa nascida no Brasil",
        "resumo": (
            "Ainda adolescente, transformou a casa dos pais num abrigo pra mendigos e "
            "doentes -- décadas depois, se tornou a primeira santa nascida em solo brasileiro."
        ),
        "produto_relacionado_id": "santa-dulce",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Maria Rita de Souza Brito Lopes Pontes nasceu em Salvador, Bahia, em 1914.
            Ainda aos 13 anos, já demonstrava a vocação que marcaria toda sua vida:
            transformou a própria casa da família num abrigo informal para mendigos e
            doentes que não tinham pra onde ir -- iniciativa que ficou conhecida na
            vizinhança como "A Portaria de São Francisco".</p>

            <h2>De um posto médico a um hospital de referência</h2>
            <p>Já como freira, com o nome religioso de Irmã Dulce, continuou expandindo
            esse trabalho de forma organizada: fundou em 1936 a primeira organização
            católica de assistência a operários da Bahia, e dois anos depois abriu uma
            escola gratuita para trabalhadores e seus filhos. Esse conjunto de iniciativas
            deu origem, com o tempo, às Obras Sociais Irmã Dulce (OSID), hoje um dos
            maiores complexos hospitalares filantrópicos do Brasil, ainda em atividade em
            Salvador.</p>

            <h2>Reconhecimento em vida e depois da morte</h2>
            <p>Irmã Dulce morreu em 1992, aos 77 anos, já reconhecida nacionalmente por seu
            trabalho -- havia sido inclusive indicada ao Prêmio Nobel da Paz em 1988. Foi
            beatificada em 2011, numa cerimônia em Salvador que reuniu mais de 70 mil
            pessoas, e canonizada pelo Papa Francisco em 13 de outubro de 2019, tornando-se
            a <strong>primeira santa nascida em solo brasileiro</strong> -- uma canonização
            que levou apenas 27 anos após sua morte, uma das mais rápidas da história
            recente da Igreja.</p>

            <p>De uma menina de 13 anos abrindo as portas da própria casa a uma santa
            reconhecida mundialmente: a trajetória de Santa Dulce mostra que cuidar de quem
            precisa pode começar em qualquer idade, com qualquer recurso disponível.</p>

            <div class="cta-blog-produto">
              <p>O cuidado que vira exemplo pro mundo inteiro</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de Santa Dulce →</a>
            </div>
        """,
    },
    "sao-joao-paulo-ii-o-papa-viajante": {
        "titulo": "São João Paulo II: o papa que ajudou a mudar a história da Europa",
        "resumo": (
            "Primeiro papa não-italiano em mais de 450 anos, sobrevivente de um atentado, "
            "João Paulo II se tornou um dos líderes religiosos mais influentes do século XX."
        ),
        "produto_relacionado_id": "sao-joao-paulo-ii",
        "publicado_em": "2026-09-11",
        "corpo_html": """
            <p>Karol Józef Wojtyła nasceu em 1920, na Polônia, e viveu a juventude sob duas
            das maiores tragédias do século XX: a ocupação nazista, durante a qual chegou a
            trabalhar em fábricas e pedreiras para escapar da deportação, e depois o regime
            comunista que dominou o país no pós-guerra. Ordenado padre em 1946, seguiu uma
            trajetória acadêmica e pastoral na Igreja polonesa até ser eleito Papa em 1978
            -- tornando-se o primeiro pontífice não-italiano em mais de 450 anos, adotando
            o nome de João Paulo II.</p>

            <h2>Um papa que sobreviveu a um atentado</h2>
            <p>Em 13 de maio de 1981, João Paulo II foi baleado na Praça de São Pedro, em
            Roma, por um atirador turco, e sobreviveu por pouco a ferimentos graves. Anos
            depois, atribuiu sua sobrevivência à intercessão de Nossa Senhora de Fátima --
            justamente no aniversário da primeira aparição -- e fez questão de visitar
            pessoalmente, na prisão, o homem que tentara matá-lo, perdoando-o
                publicamente.</p>

            <h2>Papel na queda do comunismo</h2>
            <p>Historiadores e líderes políticos da época reconhecem amplamente o papel de
            João Paulo II no enfraquecimento dos regimes comunistas do Leste Europeu,
            especialmente em sua Polônia natal -- suas visitas ao país e seu apoio moral ao
            movimento sindical Solidariedade são frequentemente citados como fatores que
            contribuíram para a queda do Muro de Berlim, em 1989, e o fim da Guerra Fria
            que se seguiu.</p>

            <h2>O papa viajante</h2>
            <p>Ao longo de quase 27 anos de pontificado -- um dos mais longos da história
            -- visitou mais de 120 países, um número sem precedentes até então, o que lhe
            rendeu o apelido de "papa viajante". Morreu em 2005, foi beatificado em 2011
            pelo Papa Bento XVI e canonizado em 2014 pelo Papa Francisco, na mesma
            cerimônia que canonizou o Papa João XXIII.</p>

            <div class="cta-blog-produto">
              <p>A força de um papa que marcou o século XX</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver medalha, entremeio e chaveiro de São João Paulo II →</a>
            </div>
        """,
    },
    "a-historia-da-nove-de-julho": {
        "titulo": "A história da Nove de Julho: de uma medalha pra ele mesmo a milhares pelo Brasil",
        "resumo": (
            "Começou sem impressora, sem máquina de corte e sem apoio -- 7 meses só de "
            "prejuízo. Essa é a história de como uma dificuldade pessoal virou a Nove de Julho."
        ),
        "produto_relacionado_id": None,
        "cta_endpoint": "personalizada",
        "imagem_manual": "img/banner-hero.jpg",
        "publicado_em": "2026-09-12",
        "corpo_html": """
            <blockquote>"Não espere o momento ideal e os planos perfeitos, apenas
            comece..."</blockquote>

            <p>É assim que Ítalo, fundador da Nove de Julho, costuma resumir os últimos
            anos da própria história. Consagrado da Comunidade Católica Shalom, ele tinha
            planos bem diferentes para a vida antes de ir em missão. Quando voltou, em
            2020, tudo começou a mudar -- a partir de um desejo simples: fazer uma medalha
            pra si mesmo.</p>

            <h2>Uma dor pessoal que era de muita gente</h2>
            <p>A dificuldade era concreta: encontrar medalhas de santos e devoções menos
            conhecidos -- como Santa Gianna ou Edith Stein -- praticamente não existia no
            mercado. Some a isso o desejo de conseguir uma renda extra durante a
            faculdade, e nasceu a ideia. Ítalo deu o primeiro passo, ainda de forma bem
            simples, no dia <strong>28 de abril de 2020</strong>, completamente sem apoio,
            bem no início da pandemia.</p>

            <h2>Sete meses só de prejuízo</h2>
            <p>Não deu certo de primeira. Durante sete meses, foi só prejuízo: material
            ruim, forma de preparo inadequada, nenhum cliente. Foi só no dia
            <strong>1º de outubro daquele ano</strong>, confiando especialmente à
            intercessão de São José, Santa Teresinha e São Josemaria Escrivá, que as coisas
            começaram a tomar corpo de verdade e as vendas passaram a alavancar.</p>

            <h2>Decisões difíceis pra apostar no sonho</h2>
            <p>Conforme a confiança e o apoio de amigos foram crescendo, vieram também as
            decisões mais difíceis: desistir do curso superior numa universidade federal e
            de um emprego que havia acabado de conseguir, pra apostar de vez no projeto que
            ainda parecia arriscado demais aos olhos de fora.</p>

            <h2>Começou sem quase nada</h2>
            <p>Talvez a parte mais reveladora dessa história esteja nos detalhes pequenos.
            Ítalo começou <strong>sem impressora</strong>, indo de bicicleta até a gráfica
            toda vez que precisava imprimir algo. Começou <strong>sem máquina de
            recorte</strong>, cortando cada peça na tesoura e pedindo ajuda de amigos.
            Começou <strong>sem aparelhos industriais</strong>, evitando trabalhar em dias
            de chuva por causa da umidade e colocando sal grosso ao redor do material pra
            absorver o excesso de água do ar. Usou a <strong>resina errada</strong> no
            início, que exalava um cheiro forte e não secava direito, e o
            <strong>adesivo errado</strong>, que só rendia dor de cabeça. Usou
            <strong>argolas de ferro</strong> por um tempo, porque ainda não sabia onde
            encontrar argolas de aço inox de verdade. Chegou a enviar pedidos <strong>em
            papel comum, como se fosse carta</strong>, sem saber que aquele não era o jeito
            certo de proteger a peça no correio.</p>

            <h2>De uma bicicleta a todos os estados do Brasil</h2>
            <p>Anos de aprendizado depois -- e, como o próprio Ítalo costuma dizer, ainda
            serão muitos outros --, a Nove de Julho hoje já enviou peças para todos os
            estados do Brasil e também para fora do país. São medalhas presentes em
            batizados, casamentos, retiros espirituais e momentos de fé de famílias
            inteiras -- e não é raro que, viajando por aí, ele encontre alguém usando uma
            peça que saiu das próprias mãos.</p>

            <p>Uma medalha pensada pra resolver uma dificuldade pessoal se tornou, aos
            poucos, parte da história de fé de milhares de pessoas -- prova de que o passo
            mais importante, quase sempre, é simplesmente começar.</p>

            <div class="cta-blog-produto">
              <p>Continue essa história com a sua própria medalha</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Simular minha medalha personalizada →</a>
            </div>
        """,
    },
    "por-que-personalizar-uma-medalha": {
        "titulo": "Por que personalizar uma medalha? A dor que descobri que era de muita gente",
        "resumo": (
            "Tudo começou querendo uma medalha só pra mim. Depois entendi que essa "
            "vontade de carregar algo único, com a própria fé, é de muito mais gente do que imaginei."
        ),
        "produto_relacionado_id": None,
        "cta_endpoint": "personalizada",
        "imagem_manual": "img/banner-personalizada.jpg",
        "publicado_em": "2026-09-12",
        "corpo_html": """
            <p>A <a href="/blog/a-historia-da-nove-de-julho">Nove de Julho nasceu</a> de
            uma dor pessoal bem específica: a dificuldade de achar uma medalha de um santo
            menos conhecido. Com o tempo, ficou claro que essa vontade -- de carregar algo
            que representasse exatamente aquilo que importa pra você, e não só o que já
            vem pronto numa prateleira -- não era só nossa. Era de muita gente.</p>

            <h2>Uma foto no lugar de um santo -- ou os dois juntos</h2>
            <p>A grande diferença de uma peça personalizada é simples de explicar e
            profunda de sentir: em vez de um santo do catálogo, você escolhe QUALQUER foto
            pra estampar numa medalha, entremeio ou chaveiro -- e, nos formatos de 2 lados,
            dá pra combinar um santo de devoção de um lado com uma foto pessoal do outro.
            Fé e memória, na mesma peça.</p>

            <h2>Guardar quem já não está mais aqui</h2>
            <p>Um dos motivos mais comuns -- e mais emocionantes de receber -- é a saudade.
            Levar consigo o rosto de um avô, uma mãe, um filho que já partiu é uma forma de
            manter essa pessoa fisicamente perto, todos os dias, em algo que se pode segurar
            ou vestir.</p>

            <h2>Batismos, primeira comunhão e outros marcos de fé</h2>
            <p>Muita gente personaliza pra guardar um marco espiritual específico -- a foto
            do dia do batismo, da primeira comunhão, da crisma -- transformando um registro
            que normalmente ficaria só numa foto guardada em algo que a criança (ou quem
            recebeu o sacramento) pode carregar fisicamente pelo resto da vida.</p>

            <h2>Bichos de estimação, também</h2>
            <p>Não é só gente: pedidos com foto de cães, gatos e outros bichos de estimação
            que já se foram ou que ainda estão por perto são um dos pedidos mais frequentes
            -- porque quem ama um animal sabe que ele também é família.</p>

            <h2>Namoro, casamento e quem mora longe</h2>
            <p>Casais pedem peças com a foto um do outro, ou da data do casamento. Quem
            mora longe da família -- morando fora do país, ou só numa cidade distante --
            também encontra na medalha personalizada uma forma de carregar quem ama mesmo à
            distância.</p>

            <h2>O simulador tira a dúvida antes de você decidir</h2>
            <p>Uma das maiores travas de comprar algo personalizado pela internet é a
            insegurança: "e se não ficar bom?". Por isso, antes de fechar o pedido, você
            vê no simulador uma prévia de como a peça vai ficar de verdade, já recortada e
            posicionada dentro do formato escolhido -- sem depender de imaginar como vai
            sair.</p>

            <p>Foi assim que resolvemos nossa própria dor -- e ficamos felizes toda vez que
            uma peça personalizada ajuda alguém a resolver a dela também.</p>

            <div class="cta-blog-produto">
              <p>Crie a sua peça e veja o resultado antes de decidir</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Simular minha medalha personalizada →</a>
            </div>
        """,
    },
    "nove-de-julho-e-confiavel": {
        "titulo": "A Nove de Julho é confiável? Veja como funciona cada etapa da compra",
        "resumo": (
            "CNPJ, endereço, pagamento processado por instituições conhecidas, nota "
            "fiscal, acompanhamento do pedido -- reunimos aqui tudo que comprova que a "
            "compra é segura."
        ),
        "produto_relacionado_id": None,
        "cta_endpoint": "catalogo_completo",
        "imagem_manual": "img/logo-icone.png",
        "publicado_em": "2026-09-13",
        "corpo_html": """
            <p>É uma pergunta natural antes de comprar de uma loja nova, e a resposta
            curta é sim: a Nove de Julho é uma empresa registrada, com CNPJ ativo, endereço
            físico, pagamento processado por instituições financeiras conhecidas e um
            histórico real de vendas desde 2020. Abaixo, detalhamos cada ponto pra você
            conferir com os próprios olhos.</p>

            <h2>Quem está por trás da loja</h2>
            <p>A Nove de Julho é operada pela empresa <strong>Nove de Julho Artigos
            Ltda</strong>, CNPJ <strong>39.390.354/0001-25</strong> -- número que qualquer
            pessoa pode consultar gratuitamente no site da Receita Federal pra confirmar
            que a empresa está ativa e regular. Tem endereço físico em
            <strong>Rua Furnas, 4835, Neópolis, Natal/RN</strong> (retirada de pedidos só
            mediante agendamento prévio) e foi fundada por Ítalo, cuja
            <a href="/blog/a-historia-da-nove-de-julho">história real está contada aqui no
            blog</a> -- não é uma loja anônima nem recém-criada só pra rodar uma campanha de
            anúncios.</p>

            <h2>O pagamento não passa direto pela loja</h2>
            <p>Pix e cartão de crédito são processados pela <strong>InfinitePay</strong>,
            e o boleto bancário é emitido diretamente pelo <strong>Banco Inter</strong> --
            duas instituições financeiras homologadas e amplamente usadas por milhares de
            outros negócios no Brasil. Isso significa que seus dados de pagamento nunca
            ficam armazenados nos nossos servidores: quem processa a transação é a
            instituição financeira, não a loja.</p>

            <h2>Nota fiscal em todo pedido</h2>
            <p>Toda venda emite nota fiscal, seja pra CPF (pessoa física) ou CNPJ (pessoa
            jurídica) -- outro ponto que diferencia uma operação regular de um perfil
            informal de rede social vendendo sem nenhum registro fiscal.</p>

            <h2>Você acompanha o pedido do início ao fim</h2>
            <p>Assim que o pagamento é confirmado, você recebe um link de acompanhamento
            exclusivo do seu pedido, que mostra o status em tempo real -- produção, código
            de rastreio dos Correios assim que é postado, e confirmação de entrega. Não é
            preciso ficar perguntando "cadê meu pedido": a informação fica disponível pra
            você consultar quando quiser.</p>

            <h2>Avaliações reais, com moderação</h2>
            <p>As avaliações que aparecem na página de cada santo são enviadas por quem
            realmente comprou, muitas com foto da peça recebida, e passam por um filtro de
            moderação antes de ficarem públicas -- exatamente pra evitar spam ou avaliação
            falsa, pra cima ou pra baixo. Já são mais de <strong>125 mil medalhas
            vendidas</strong> desde o início da operação.</p>

            <h2>Direito de arrependimento garantido por lei</h2>
            <p>Como toda compra feita fora de loja física, você tem até
            <a href="/atendimento/trocas-e-devolucao">7 dias corridos após o recebimento
            para desistir da compra</a>, sem precisar justificar o motivo -- direito
            garantido pelo Código de Defesa do Consumidor em qualquer compra on-line no
            Brasil, e que a Nove de Julho cumpre integralmente.</p>

            <h2>Atendimento direto, sem robô</h2>
            <p>Qualquer dúvida antes, durante ou depois da compra pode ser tirada
            diretamente pelo WhatsApp, com uma pessoa de verdade respondendo -- não um chat
            automatizado sem saída.</p>

            <p>Nenhuma loja precisa ser perfeita pra ser confiável -- precisa ser
            transparente. É exatamente isso que tentamos garantir em cada etapa da
            compra.</p>

            <div class="cta-blog-produto">
              <p>Agora que você já conhece cada etapa, dá uma olhada no catálogo</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
    },
    "medalha-entremeio-ou-chaveiro-qual-escolher": {
        "titulo": "Medalha, entremeio ou chaveiro: qual formato escolher?",
        "resumo": (
            "Mesma imagem do santo, três formatos diferentes -- medalha, entremeio e "
            "chaveiro. Entenda a diferença de cada um antes de decidir."
        ),
        "produto_relacionado_id": None,
        "cta_endpoint": "catalogo_completo",
        "imagem_manual": "img/guia-tamanhos.jpg",
        "publicado_em": "2026-09-14",
        "corpo_html": """
            <p>Todo santo do catálogo sai em três formatos -- a diferença não é o santo,
            é o USO que a peça vai ter no dia a dia. Vale a pena entender as diferenças
            antes de escolher, principalmente quando o pedido é pra revenda ou lembrancinha
            em quantidade.</p>

            <h2>Medalha: pra usar no corpo</h2>
            <p>A medalha (1,2 cm ou 1,6 cm) vem com uma argola só, pensada pra colar ou
            pulseira -- é o formato mais tradicional, o que a maioria das pessoas imagina
            quando pensa em "medalha de santo". Em aço inoxidável, aguenta bem o uso diário
            (banho, chuva, suor).</p>

            <h2>Entremeio: pra montar um terço ou rosário</h2>
            <p>O entremeio tem DUAS argolas (uma de cada lado), porque ele é feito pra
            passar no cordão de um terço ou rosário -- não é pra usar sozinho no pescoço. Em
            liga de zinco, nas cores prata ou ouro velho, é a peça certa pra quem monta ou
            personaliza terços artesanais. Também combina com a
            <a href="/cruz-para-terco">Cruz para Terço</a> na mesma cor, pra fechar o
            conjunto.</p>

            <h2>Chaveiro: o maior formato, pra levar junto</h2>
            <p>Com 3 cm de diâmetro interno, o chaveiro é o maior formato do catálogo --
            pensado pra ir na bolsa, mochila ou molho de chaves, não pra usar no corpo. É
            uma escolha comum de lembrancinha, já que também funciona como objeto de
            decoração/devoção sobre uma mesa.</p>

            <h2>E se eu não souber qual escolher?</h2>
            <p>Pra lembrancinha de evento (casamento, batizado, retiro), o mais comum é
            variar: uma parte do pedido em medalha, outra em chaveiro. Como o desconto de
            atacado soma a quantidade de medalhas e entremeios juntos (chaveiro tem tabela
            própria), misturar formatos não atrapalha o preço por peça.</p>

            <div class="cta-blog-produto">
              <p>Veja os três formatos disponíveis em cada santo</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
    },
    "como-escolher-a-medalha-certa-para-o-batizado": {
        "titulo": "Como escolher a medalha certa para o batizado",
        "resumo": (
            "Pelo nome do santo, por uma devoção da família ou personalizada com o nome "
            "do bebê -- veja os caminhos mais comuns pra escolher a medalha de batizado."
        ),
        "produto_relacionado_id": None,
        "cta_endpoint": "catalogo_completo",
        "imagem_manual": "img/produtos/nossa_senhora_toda_pequena_modelo_1_medalha.jpg",
        "publicado_em": "2026-09-15",
        "corpo_html": """
            <p>Não existe uma única forma "certa" de escolher a medalha de batizado -- mas
            alguns caminhos são bem mais comuns que outros, e ajudam quem está decidindo
            agora.</p>

            <h2>Caminho 1: pelo nome de batismo</h2>
            <p>O mais tradicional é buscar o santo que dá nome à criança -- se o nome de
            batismo já está definido, é só procurar esse santo direto no
            <a href="/catalogo">catálogo completo</a> (mais de 130 santos e devoções). É
            comum encontrar até mais de uma representação do mesmo santo.</p>

            <h2>Caminho 2: por uma devoção da família</h2>
            <p>Quando o nome não corresponde a um santo específico (ou a família prefere
            outra devoção), o comum é escolher pela proteção que se deseja pra criança.
            <a href="/produto/nossa-senhora-toda-pequena">Nossa Senhora Toda Pequena</a> e
            <a href="/produto/santa-teresinha-crianca">Santa Teresinha Criança</a> retratam
            a santa ainda menina -- uma escolha frequente justamente por isso -- e os
            <a href="/produto/santos-arcanjos">Santos Arcanjos</a> (Miguel, Gabriel e
            Rafael) são a opção mais tradicional de proteção espiritual.</p>

            <h2>Caminho 3: personalizada, com o nome e a data</h2>
            <p>Pra quem quer uma lembrança mais única do dia, dá pra
            <a href="/personalizada">criar uma medalha personalizada</a> com o nome do
            bebê, a data do batizado ou até uma foto -- você vê a simulação antes de fechar
            o pedido, sem depender de imaginar como vai ficar.</p>

            <h2>Formato: medalha, entremeio ou os dois?</h2>
            <p>Pra usar no corpo do bebê (ou guardar), a medalha é o formato mais comum.
            Famílias que já têm o costume de rezar terço às vezes preferem o entremeio, pra
            montar uma peça em memória do batizado. <a
            href="/blog/medalha-entremeio-ou-chaveiro-qual-escolher">Veja a diferença entre
            os formatos</a> antes de decidir.</p>

            <div class="cta-blog-produto">
              <p>Veja todas as opções e o desconto por quantidade</p>
              <a href="__URL_PRODUTO__" class="botao-principal">Ver catálogo completo →</a>
            </div>
        """,
    },
}


def artigo_por_produto_id(produto_id: str) -> tuple[str, dict] | None:
    """Achado inverso -- pra pagina de produto linkar de volta pro
    artigo do blog quando existir um (ver app.py:produto). Devolve
    (slug, artigo) ou None."""
    for slug, artigo in ARTIGOS_BLOG.items():
        if artigo["produto_relacionado_id"] == produto_id:
            return slug, artigo
    return None
