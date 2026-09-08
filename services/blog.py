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
}


def artigo_por_produto_id(produto_id: str) -> tuple[str, dict] | None:
    """Achado inverso -- pra pagina de produto linkar de volta pro
    artigo do blog quando existir um (ver app.py:produto). Devolve
    (slug, artigo) ou None."""
    for slug, artigo in ARTIGOS_BLOG.items():
        if artigo["produto_relacionado_id"] == produto_id:
            return slug, artigo
    return None
