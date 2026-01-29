#!/usr/bin/env python3
"""
Script para importar o Decreto 6.759/2009 (Regulamento Aduaneiro) diretamente no SQLite.

Este script importa o texto fornecido diretamente, sem tentar baixar da URL.
"""
import sys
from pathlib import Path

# Adicionar raiz do projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.legislacao_service import LegislacaoService
from db_manager import init_db

# Texto completo do Decreto 6.759/2009 fornecido pelo usuário
TEXTO_DECRETO_6759 = """Presidência da República
Casa Civil
Subchefia para Assuntos Jurídicos

DECRETO Nº 6.759, DE 5 DE FEVEREIRO DE 2009.

 
Regulamenta a administração das atividades aduaneiras, e a fiscalização, o controle e a tributação das operações de comércio exterior.

O PRESIDENTE DA REPÚBLICA, no uso da atribuição que lhe confere o art. 84, inciso IV, da Constituição, 

DECRETA:

Art. 1o  A administração das atividades aduaneiras, e a fiscalização, o controle e a tributação das operações de comércio exterior serão exercidos em conformidade com o disposto neste Decreto. 

LIVRO I

DA JURISDIÇÃO ADUANEIRA E DO CONTROLE ADUANEIRO DE VEÍCULOS 

TÍTULO I

DA JURISDIÇÃO ADUANEIRA 

CAPÍTULO I

DO TERRITÓRIO ADUANEIRO 

Art. 2o  O território aduaneiro compreende todo o território nacional. 

Art. 3o  A jurisdição dos serviços aduaneiros estende-se por todo o território aduaneiro e abrange (Decreto-Lei no 37, de 18 de novembro de 1966, art. 33, caput):

I - a zona primária, constituída pelas seguintes áreas demarcadas pela autoridade aduaneira local:

a) a área terrestre ou aquática, contínua ou descontínua, nos portos alfandegados;

b) a área terrestre, nos aeroportos alfandegados; e

c) a área terrestre, que compreende os pontos de fronteira alfandegados; e

II - a zona secundária, que compreende a parte restante do território aduaneiro, nela incluídas as águas territoriais e o espaço aéreo. 

§ 1o  Para efeito de controle aduaneiro, as zonas de processamento de exportação, referidas no art. 534, constituem zona primária (Lei no 11.508, de 20 de julho de 2007, art. 1o, parágrafo único). 

§ 2o  Para a demarcação da zona primária, deverá ser ouvido o órgão ou empresa a que esteja afeta a administração do local a ser alfandegado. 

§ 3o  A autoridade aduaneira poderá exigir que a zona primária, ou parte dela, seja protegida por obstáculos que impeçam o acesso indiscriminado de veículos, pessoas ou animais. 

§ 4o  A autoridade aduaneira poderá estabelecer, em locais e recintos alfandegados, restrições à entrada de pessoas que ali não exerçam atividades profissionais, e a veículos não utilizados em serviço. 

§ 5o  A jurisdição dos serviços aduaneiros estende-se ainda às Áreas de Controle Integrado criadas em regiões limítrofes dos países integrantes do Mercosul com o Brasil (Acordo de Alcance Parcial para a Facilitação do Comércio no 5 - Acordo de Recife, aprovado pelo Decreto Legislativo no 66, de 16 de novembro de 1981, e promulgado pelo Decreto no 1.280, de 14 de outubro de 1994; e Segundo Protocolo Adicional ao Acordo de Recife, Anexo - Acordo de Alcance Parcial de Promoção do Comércio no 5 para a Facilitação do Comércio, art. 3o, alínea "a", internalizado pelo Decreto no 3.761, de 5 de março de 2001). 

Art. 4o  O Ministro de Estado da Fazenda poderá demarcar, na orla marítima ou na faixa de fronteira, zonas de vigilância aduaneira, nas quais a permanência de mercadorias ou a sua circulação e a de veículos, pessoas ou animais ficarão sujeitas às exigências fiscais, proibições e restrições que forem estabelecidas (Decreto-Lei nº 37, de 1966, art. 33, parágrafo único). 

§ 1o  O ato que demarcar a zona de vigilância aduaneira poderá:

I - ser geral em relação à orla marítima ou à faixa de fronteira, ou específico em relação a determinados segmentos delas;

II - estabelecer medidas específicas para determinado local; e

III - ter vigência temporária. 

§ 2o  Na orla marítima, a demarcação da zona de vigilância aduaneira levará em conta, além de outras circunstâncias de interesse fiscal, a existência de portos ou ancoradouros naturais, propícios à realização de operações clandestinas de carga e descarga de mercadorias. 

§ 3o  Compreende-se na zona de vigilância aduaneira a totalidade do Município atravessado pela linha de demarcação, ainda que parte dele fique fora da área demarcada. 

CAPÍTULO II

DOS PORTOS, AEROPORTOS E PONTOS DE FRONTEIRA ALFANDEGADOS 

Art. 5o  Os portos, aeroportos e pontos de fronteira serão alfandegados por ato declaratório da autoridade aduaneira competente, para que neles possam, sob controle aduaneiro:

I - estacionar ou transitar veículos procedentes do exterior ou a ele destinados;

II - ser efetuadas operações de carga, descarga, armazenagem ou passagem de mercadorias procedentes do exterior ou a ele destinadas; e

III - embarcar, desembarcar ou transitar viajantes procedentes do exterior ou a ele destinados. 

Art. 6o  O alfandegamento de portos, aeroportos ou pontos de fronteira será precedido da respectiva habilitação ao tráfego internacional pelas autoridades competentes em matéria de transporte. 

Parágrafo único.  Ao iniciar o processo de habilitação de que trata o caput, a autoridade competente notificará a Secretaria da Receita Federal do Brasil. 

Art. 7o  O ato que declarar o alfandegamento estabelecerá as operações aduaneiras autorizadas e os termos, limites e condições para sua execução. 

Art. 8o  Somente nos portos, aeroportos e pontos de fronteira alfandegados poderá efetuar-se a entrada ou a saída de mercadorias procedentes do exterior ou a ele destinadas (Decreto-Lei nº 37, de 1966, art. 34, incisos II e III). 

Parágrafo único.  O disposto no caput não se aplica à importação e à exportação de mercadorias conduzidas por linhas de transmissão ou por dutos, ligados ao exterior, observadas as regras de controle estabelecidas pela Secretaria da Receita Federal do Brasil. 

Parágrafo único. O disposto no caput não se aplica:                       (Redação dada pelo Decreto nº 8.010, de 2013)

I - à importação e à exportação de mercadorias conduzidas por linhas de transmissão ou por dutos, ligados ao exterior, observadas as regras de controle estabelecidas pela Secretaria da Receita Federal do Brasil; e  (Redação dada pelo Decreto nº 8.010, de 2013)

II - a outros casos estabelecidos em ato normativo da Secretaria da Receita Federal do Brasil.                  (Redação dada pelo Decreto nº 8.010, de 2013)

CAPÍTULO III

DOS RECINTOS ALFANDEGADOS 

Seção I

Das Disposições Preliminares 

Art. 9o  Os recintos alfandegados serão assim declarados pela autoridade aduaneira competente, na zona primária ou na zona secundária, a fim de que neles possam ocorrer, sob controle aduaneiro, movimentação, armazenagem e despacho aduaneiro de:

I - mercadorias procedentes do exterior, ou a ele destinadas, inclusive sob regime aduaneiro especial;

II - bagagem de viajantes procedentes do exterior, ou a ele destinados; e

III - remessas postais internacionais. 

Parágrafo único.  Poderão ainda ser alfandegados, em zona primária, recintos destinados à instalação de lojas francas. 

Art. 10.  A Secretaria da Receita Federal do Brasil poderá, no âmbito de sua competência, editar atos normativos para a implementação do disposto neste Capítulo. 

Seção II

Dos Portos Secos 

Art. 11.  Portos secos são recintos alfandegados de uso público nos quais são executadas operações de movimentação, armazenagem e despacho aduaneiro de mercadorias e de bagagem, sob controle aduaneiro. 

§ 1o  Os portos secos não poderão ser instalados na zona primária de portos e aeroportos alfandegados. 

§ 2o  Os portos secos poderão ser autorizados a operar com carga de importação, de exportação ou ambas, tendo em vista as necessidades e condições locais. 

Art. 12.  As operações de movimentação e armazenagem de mercadorias sob controle aduaneiro, bem como a prestação de serviços conexos, em porto seco, sujeitam-se ao regime de concessão ou de permissão (Lei no 9.074, de 7 de julho de 1995, art. 1o, inciso VI). 

Parágrafo único.  A execução das operações e a prestação dos serviços referidos no caput serão efetivadas mediante o regime de permissão, salvo quando os serviços devam ser prestados em porto seco instalado em imóvel pertencente à União, caso em que será adotado o regime de concessão precedida da execução de obra pública. 

CAPÍTULO IV

DO ALFANDEGAMENTO 

Art. 13.  O alfandegamento de portos, aeroportos e pontos de fronteira somente poderá ser efetivado:

I - depois de atendidas as condições de instalação do órgão de fiscalização aduaneira e de infra-estrutura indispensável à segurança fiscal;

II - se atestada a regularidade fiscal do interessado;

III - se houver disponibilidade de recursos humanos e materiais;

IV - se o interessado assumir a condição de fiel depositário da mercadoria sob sua guarda. 

§ 1o  O disposto no caput aplica-se, no que couber, ao alfandegamento de recintos de zona primária e de zona secundária. 

§ 2o  Em se tratando de permissão ou concessão de serviços públicos, o alfandegamento poderá ser efetivado somente após a conclusão do devido procedimento licitatório pelo órgão competente, e o cumprimento das condições fixadas em contrato. 

§ 3o  O alfandegamento poderá abranger a totalidade ou parte da área dos portos e dos aeroportos. 

§ 4o  Poderão, ainda, ser alfandegados silos ou tanques, para armazenamento de produtos a granel, localizados em áreas contíguas a porto organizado ou instalações portuárias, ligados a estes por tubulações, esteiras rolantes ou similares, instaladas em caráter permanente. 

§ 5o  O alfandegamento de que trata o § 4o é subordinado à comprovação do direito de construção e de uso das tubulações, esteiras rolantes ou similares, e ao cumprimento do disposto no caput. 

§ 6o  Compete à Secretaria da Receita Federal do Brasil declarar o alfandegamento a que se refere este artigo e editar, no âmbito de sua competência, atos normativos para a implementação do disposto neste Capítulo. 

Art. 13-A.  Compete à Secretaria da Receita Federal do Brasil definir os requisitos técnicos e operacionais para o alfandegamento dos locais e recintos onde ocorram, sob controle aduaneiro, movimentação, armazenagem e despacho aduaneiro de mercadorias procedentes do exterior, ou a ele destinadas, inclusive sob regime aduaneiro especial, bagagem de viajantes procedentes do exterior, ou a ele destinados, e remessas postais internacionais (Lei nº 12.350, de 20 de dezembro de 2010, art. 34, caput).                       (Incluído pelo Decreto nº 8.010, de 2013)

§ 1º  Na definição dos requisitos técnicos e operacionais de que trata o caput, a Secretaria da Receita Federal do Brasil deverá estabelecer (Lei nº 12.350, de 2010, art. 34, § 1º):                    (Incluído pelo Decreto nº 8.010, de 2013)

I - segregação e proteção física da área do local ou recinto, inclusive entre as áreas de armazenagem de mercadorias ou bens para exportação, para importação ou para regime aduaneiro especial;                         (Incluído pelo Decreto nº 8.010, de 2013)

II - disponibilização de edifícios e instalações, aparelhos de informática, mobiliário e materiais para o exercício de suas atividades e, quando necessário, de outros órgãos ou agências da administração pública federal;                    (Incluído pelo Decreto nº 8.010, de 2013)

III - disponibilização e manutenção de balanças e outros instrumentos necessários à fiscalização e ao controle aduaneiros;                      (Incluído pelo Decreto nº 8.010, de 2013)

IV - disponibilização e manutenção de instrumentos e aparelhos de inspeção não invasiva de cargas e veículos, como os aparelhos de raios X ou gama;                        (Incluído pelo Decreto nº 8.010, de 2013)

V - disponibilização de edifícios e instalações, equipamentos, instrumentos e aparelhos especiais para a verificação de mercadorias frigorificadas, apresentadas em tanques ou recipientes que não devam ser abertos durante o transporte, produtos químicos, tóxicos e outras mercadorias que exijam cuidados especiais para seu transporte, manipulação ou armazenagem; e                          (Incluído pelo Decreto nº 8.010, de 2013)

VI - disponibilização de sistemas, com acesso remoto pela fiscalização aduaneira, para:                    (Incluído pelo Decreto nº 8.010, de 2013)

a) vigilância eletrônica do recinto; e                        (Incluído pelo Decreto nº 8.010, de 2013)

b) registro e controle:                       (Incluído pelo Decreto nº 8.010, de 2013)

1. de acesso de pessoas e veículos; e                         (Incluído pelo Decreto nº 8.010, de 2013)

2. das operações realizadas com mercadorias, inclusive seus estoques.                               (Incluído pelo Decreto nº 8.010, de 2013)

§ 2º  A utilização dos sistemas referidos no inciso VI do § 1º deverá ser supervisionada por Auditor-Fiscal da Receita Federal do Brasil e acompanhada por ele por ocasião da realização da conferência aduaneira (Lei nº 12.350, de 2010, art. 34, § 2º).                       (Incluído pelo Decreto nº 8.010, de 2013)

§ 3º  A Secretaria da Receita Federal do Brasil poderá dispensar a implementação de requisito previsto no § 1º, considerando as características específicas do local ou recinto (Lei nº 12.350, de 2010, art. 34, § 3º).            (Incluído pelo Decreto nº 8.010, de 2013)

Art. 13-B.  A pessoa jurídica responsável pela administração do local ou recinto alfandegado, referido no art. 13-A, fica obrigada a observar os requisitos técnicos e operacionais definidos pela Secretaria da Receita Federal do Brasil (Lei nº 12.350, de 2010, art. 35).                           (Incluído pelo Decreto nº 8.010, de 2013)

Art. 13-C.  O disposto nos arts. 13-A e 13-B aplica-se também aos responsáveis que já exerciam a administração de locais e recintos alfandegados em 21 de dezembro de 2010 (Lei nº 12.350, de 2010, art. 36, caput).      (Incluído pelo Decreto nº 8.010, de 2013)

Art. 13-D.  A Secretaria da Receita Federal do Brasil, no âmbito de sua competência, disciplinará a aplicação do disposto nos arts. 13-A, 13-B, 13-C e 735-C (Lei nº 12.350, de 2010, art. 39).                      (Incluído pelo Decreto nº 8.010, de 2013)

Art. 14.  Nas cidades fronteiriças, poderão ser alfandegados pontos de fronteira para o tráfego local e exclusivo de veículos matriculados nessas cidades. 

§ 1o  Os pontos de fronteira de que trata o caput serão alfandegados pela autoridade aduaneira regional, que poderá fixar as restrições que julgar convenientes. 

§ 2o  As autoridades aduaneiras locais com jurisdição sobre as cidades fronteiriças poderão instituir, no interesse do controle aduaneiro, cadastros de pessoas que habitualmente cruzam a fronteira (Decreto-Lei nº 37, de 1966, art. 34, inciso I). 

CAPÍTULO V

DA ADMINISTRAÇÃO ADUANEIRA 

Art. 15.  O exercício da administração aduaneira compreende a fiscalização e o controle sobre o comércio exterior, essenciais à defesa dos interesses fazendários nacionais, em todo o território aduaneiro (Constituição, art. 237). 

Parágrafo único.  As atividades de fiscalização de tributos incidentes sobre as operações de comércio exterior serão supervisionadas e executadas por Auditor-Fiscal da Receita Federal do Brasil (Lei no 5.172, de 1966, arts. 142, 194 e 196; Lei no 4.502, de 1964, art. 93; Lei no 10.593, de 6 de dezembro de 2002, art. 6o, com a redação dada pela Lei no 11.457, de 16 de março de 2007, art. 9o).                        (Incluído pelo Decreto nº 7.213, de 2010).

Art. 16.  A fiscalização aduaneira poderá ser ininterrupta, em horários determinados, ou eventual, nos portos, aeroportos, pontos de fronteira e recintos alfandegados (Decreto-Lei nº 37, de 1966, art. 36, caput, com a redação dada pela Lei no 10.833, de 29 de dezembro de 2003, art. 77). 

§ 1o  A administração aduaneira determinará os horários e as condições de realização dos serviços aduaneiros, nos locais referidos no caput (Decreto-Lei nº 37, de 1966, art. 36, § 1º, com a redação dada pela Lei nº 10.833, de 2003, art. 77). 

§ 2o  O atendimento em dias e horas fora do expediente normal da unidade aduaneira é considerado serviço extraordinário, devendo os interessados, na forma estabelecida em ato normativo da Secretaria da Receita Federal do Brasil, ressarcir a administração das despesas decorrentes dos serviços a eles efetivamente prestados (Decreto-Lei nº 37, de 1966, art. 36, § 2º, com a redação dada pelo Decreto-Lei no 2.472, de 1o de setembro de 1988, art. 1o). 

Art. 17.  Nas áreas de portos, aeroportos, pontos de fronteira e recintos alfandegados, bem como em outras áreas nas quais se autorize carga e descarga de mercadorias, ou embarque e desembarque de viajante, procedentes do exterior ou a ele destinados, a administração aduaneira tem precedência sobre os demais órgãos que ali exerçam suas atribuições (Decreto-Lei nº 37, de 1966, art. 35). 

Art. 17.  Nas áreas de portos, aeroportos, pontos de fronteira e recintos alfandegados, bem como em outras áreas nas quais se autorize carga e descarga de mercadorias, ou embarque e desembarque de viajante, procedentes do exterior ou a ele destinados, a autoridade aduaneira tem precedência sobre as demais que ali exerçam suas atribuições (Decreto-Lei nº 37, de 1966, art. 35).                       (Redação dada pelo Decreto nº 7.213, de 2010).

§ 1o  A precedência de que trata o caput implica:

I - a obrigação, por parte dos demais órgãos, de prestar auxílio imediato, sempre que requisitado pela administração aduaneira, disponibilizando pessoas, equipamentos ou instalações necessários à ação fiscal; e

I - a obrigação, por parte das demais autoridades, de prestar auxílio imediato, sempre que requisitado pela autoridade aduaneira, disponibilizando pessoas, equipamentos ou instalações necessários à ação fiscal; e                   (Redação dada pelo Decreto nº 7.213, de 2010).

II - a competência da administração aduaneira, sem prejuízo das atribuições de outros órgãos, para disciplinar a entrada, a permanência, a movimentação e a saída de pessoas, veículos, unidades de carga e mercadorias nos locais referidos no caput, no que interessar à Fazenda Nacional. 

II - a competência da autoridade aduaneira, sem prejuízo das atribuições de outras autoridades, para disciplinar a entrada, a permanência, a movimentação e a saída de pessoas, veículos, unidades de carga e mercadorias nos locais referidos no caput, no que interessar à Fazenda Nacional.                          (Redação dada pelo Decreto nº 7.213, de 2010).

§ 2o  O disposto neste artigo aplica-se igualmente à zona de vigilância aduaneira, devendo os demais órgãos prestar à administração aduaneira a colaboração que for solicitada. 

§ 2o  O disposto neste artigo aplica-se igualmente à zona de vigilância aduaneira, devendo as demais autoridades prestar à autoridade aduaneira a colaboração que for solicitada.                    (Redação dada pelo Decreto nº 7.213, de 2010).

Art. 18.  O importador, o exportador ou o adquirente de mercadoria importada por sua conta e ordem têm a obrigação de manter, em boa guarda e ordem, os documentos relativos às transações que realizarem, pelo prazo decadencial estabelecido na legislação tributária a que estão submetidos, e de apresentá-los à fiscalização aduaneira quando exigidos (Lei nº 10.833, de 2003, art. 70, caput):

§ 1o  Os documentos de que trata o caput compreendem os documentos de instrução das declarações aduaneiras, a correspondência comercial, incluídos os documentos de negociação e cotação de preços, os instrumentos de contrato comercial, financeiro e cambial, de transporte e seguro das mercadorias, os registros contábeis e os correspondentes documentos fiscais, bem como outros que a Secretaria da Receita Federal do Brasil venha a exigir em ato normativo (Lei no 10.833, de 2003, art. 70, § 1o). 

§ 2o  Nas hipóteses de incêndio, furto, roubo, extravio ou qualquer outro sinistro que provoque a perda ou deterioração dos documentos a que se refere o caput, deverá ser feita comunicação, por escrito, no prazo de quarenta e oito horas do sinistro, à unidade de fiscalização aduaneira da Secretaria da Receita Federal do Brasil que jurisdicione o domicílio matriz do sujeito passivo, instruída com os documentos que comprovem o registro da ocorrência junto à autoridade competente para apurar o fato (Lei nº 10.833, de 2003, art. 70, §§ 2º e 4º). 

§ 3o  No caso de encerramento das atividades da pessoa jurídica, a guarda dos documentos referidos no caput será atribuída à pessoa responsável pela guarda dos demais documentos fiscais, nos termos da legislação específica (Lei nº 10.833, de 2003, art. 70, § 5º). 

§ 4o  O descumprimento de obrigação referida no caput implicará o não-reconhecimento de tratamento mais benéfico de natureza tarifária, tributária ou aduaneira eventualmente concedido, com efeitos retroativos à data da ocorrência do fato gerador, caso não sejam apresentadas provas do regular cumprimento das condições previstas na legislação específica para obtê-lo (Lei nº 10.833, de 2003, art. 70, inciso I, alínea "b"). 

§ 5o  O disposto no caput aplica-se também ao despachante aduaneiro, ao transportador, ao agente de carga, ao depositário e aos demais intervenientes em operação de comércio exterior quanto aos documentos e registros relativos às transações em que intervierem, na forma e nos prazos estabelecidos pela Secretaria da Receita Federal do Brasil (Lei nº 10.833, de 2003, art. 71). 

Art. 19.  As pessoas físicas ou jurídicas exibirão aos Auditores-Fiscais da Receita Federal do Brasil, sempre que exigidos, as mercadorias, livros das escritas fiscal e geral, documentos mantidos em arquivos magnéticos ou assemelhados, e todos os documentos, em uso ou já arquivados, que forem julgados necessários à fiscalização, e lhes franquearão os seus estabelecimentos, depósitos e dependências, bem assim veículos, cofres e outros móveis, a qualquer hora do dia, ou da noite, se à noite os estabelecimentos estiverem funcionando (Lei no 4.502, de 30 de novembro de 1964, art. 94 e parágrafo único; e Lei no 9.430, de 27 de dezembro de 1996, art. 34). 

§ 1o  As pessoas físicas ou jurídicas, usuárias de sistema de processamento de dados, deverão manter documentação técnica completa e atualizada do sistema, suficiente para possibilitar a sua auditoria, facultada a manutenção em meio magnético, sem prejuízo da sua emissão gráfica, quando solicitada (Lei nº 9.430, de 1996, art. 38). 

§ 2o  As pessoas jurídicas que utilizarem sistemas de processamento eletrônico de dados para registrar negócios e atividades econômicas ou financeiras, escriturar livros ou elaborar documentos de natureza contábil ou fiscal ficam obrigadas a manter, à disposição da Secretaria da Receita Federal do Brasil, os respectivos arquivos digitais e sistemas, pelo prazo decadencial previsto na legislação tributária (Lei no 8.218, de 29 de agosto de 1991, art. 11, caput, com a redação dada pela Medida Provisória no 2.158-35, de 24 de agosto de 2001, art. 72). 

§ 3o  Na hipótese a que se refere o § 2o, a Secretaria da Receita Federal do Brasil:

I - poderá estabelecer prazo inferior ao ali previsto, que poderá ser diferenciado segundo o porte da pessoa jurídica (Lei nº 8.218, de 1991, art. 11, § 1º, com a redação dada pela Medida Provisória nº 2.158-35, de 2001, art. 72); e

II - expedirá ou designará a autoridade competente para expedir os atos necessários ao estabelecimento da forma e do prazo em que os arquivos digitais e sistemas deverão ser apresentados (Lei nº 8.218, de 1991, art. 11, §§ 3º e 4º, com a redação dada pela Medida Provisória nº 2.158-35, de 2001, art. 72). 

Art. 20.  Os documentos instrutivos de declaração aduaneira ou necessários ao controle aduaneiro podem ser emitidos, transmitidos e recepcionados eletronicamente, na forma e nos prazos estabelecidos pela Secretaria da Receita Federal do Brasil (Lei no 10.833, de 2003, art. 64, caput). 

§ 1o  A outorga de poderes a representante legal, inclusive quando residente no Brasil, para emitir e firmar os documentos referidos no caput, também pode ser realizada por documento emitido e assinado eletronicamente (Lei nº 10.833, de 2003, art. 64, § 1º, com a redação dada pela Lei no 11.452, de 27 de fevereiro de 2007, art. 12). 

§ 2o  Os documentos eletrônicos referidos no caput são válidos para os efeitos fiscais e de controle aduaneiro, observado o disposto na legislação sobre certificação digital e atendidos os requisitos estabelecidos pela Secretaria da Receita Federal do Brasil (Lei nº 10.833, de 2003, art. 64, § 2º, com a redação dada pela Lei nº 11.452, de 2007, art. 12). 

Art. 21.  Para os efeitos da legislação tributária, não têm aplicação quaisquer disposições legais excludentes ou limitativas do direito de examinar mercadorias, livros, arquivos, documentos, papéis de efeitos comerciais ou fiscais, dos comerciantes, industriais ou produtores, ou da obrigação destes de exibi-los (Lei no 5.172, de 25 de outubro de 1966, art. 195, caput). 

Parágrafo único.  Os livros obrigatórios de escrituração comercial e fiscal e os comprovantes dos lançamentos neles efetuados serão conservados até que ocorra a prescrição dos créditos tributários decorrentes das operações a que se refiram (Lei nº 5.172, de 1966, art. 195, parágrafo único). 

Art. 22.  Mediante intimação escrita, são obrigados a prestar à autoridade fiscal todas as informações de que disponham com relação aos bens, negócios ou atividades de terceiros (Lei nº 5.172, de 1966, art. 197, caput):

I - os tabeliães, os escrivães e demais serventuários de ofício;

II - os bancos, as casas bancárias, as caixas econômicas e demais instituições financeiras;

III - as empresas de administração de bens;

IV - os corretores, os leiloeiros e os despachantes oficiais;

V - os inventariantes;

VI - os síndicos, os comissários e os liquidatários; e

VII - quaisquer outras entidades ou pessoas que a lei designe, em razão de seu cargo, ofício, função, ministério, atividade ou profissão. 

Parágrafo único.  A obrigação prevista no caput não abrange a prestação de informações quanto a fatos sobre os quais o informante esteja legalmente obrigado a observar segredo em razão de cargo, ofício, função, ministério, atividade ou profissão, nos termos da legislação específica (Lei nº 5.172, de 1966, art. 197, parágrafo único). 

Art. 23.  A autoridade aduaneira que proceder ou presidir a qualquer procedimento fiscal lavrará os termos necessários para que se documente o início do procedimento, na forma da legislação aplicável, que fixará prazo máximo para a sua conclusão (Lei nº 5.172, de 1966, art. 196, caput). 

§ 1o  Os termos a que se refere o caput serão lavrados, sempre que possível, em um dos livros fiscais exibidos pela pessoa sujeita à fiscalização (Lei nº 5.172, de 1966, art. 196, parágrafo único). 

§ 2o  Quando os termos forem lavrados em separado, deles se entregará, à pessoa sujeita à fiscalização, cópia autenticada pela autoridade aduaneira (Lei nº 5.172, de 1966, art. 196, parágrafo único). 

Art. 24.  No exercício de suas atribuições, a autoridade aduaneira terá livre acesso (Lei no 8.630, de 25 de fevereiro de 1993, art. 36, § 2o):I - a quaisquer dependências do porto e às embarcações, atracadas ou não; e

II - aos locais onde se encontrem mercadorias procedentes do exterior ou a ele destinadas. 

Parágrafo único.  Para o desempenho das atribuições referidas no caput, a autoridade aduaneira poderá requisitar papéis, livros e outros documentos, bem como o apoio de força pública federal, estadual ou municipal, quando julgar necessário (Lei nº 8.630, de 1993, art. 36, § 2º). 

Art. 25.  A estrutura, competência, denominação, sede e jurisdição das unidades da Secretaria da Receita Federal do Brasil que desempenham as atividades aduaneiras serão reguladas em ato do Ministro de Estado da Fazenda. 

TÍTULO II

DO CONTROLE ADUANEIRO DE VEÍCULOS 

CAPÍTULO I

DAS NORMAS GERAIS 

Seção I

Das Disposições Preliminares 

Art. 26.  A entrada ou a saída de veículos procedentes do exterior ou a ele destinados só poderá ocorrer em porto, aeroporto ou ponto de fronteira alfandegado. 

§ 1o  O controle aduaneiro do veículo será exercido desde o seu ingresso no território aduaneiro até a sua efetiva saída, e será estendido a mercadorias e a outros bens existentes a bordo, inclusive a bagagens de viajantes. 

§ 2o  O titular da unidade aduaneira jurisdicionante poderá autorizar a entrada ou a saída de veículos por porto, aeroporto ou ponto de fronteira não alfandegado, em casos justificados, e sem prejuízo do disposto no § 1o. 

Art. 27.  É proibido ao condutor de veículo procedente do exterior ou a ele destinado:

I - estacionar ou efetuar operações de carga ou descarga de mercadoria, inclusive transbordo, fora de local habilitado;

II - trafegar no território aduaneiro em situação ilegal quanto às normas reguladoras do transporte internacional correspondente à sua espécie; e

III - desviá-lo da rota estabelecida pela autoridade aduaneira, sem motivo justificado. 

Art. 28.  É proibido ao condutor do veículo colocá-lo nas proximidades de outro, sendo um deles procedente do exterior ou a ele destinado, de modo a tornar possível o transbordo de pessoa ou mercadoria, sem observância das normas de controle aduaneiro. 

Parágrafo único.  Excetuam-se da proibição prevista no caput, os veículos:

I - de guerra, salvo se utilizados no transporte comercial;

II - das repartições públicas, em serviço;

III - autorizados para utilização em operações portuárias ou aeroportuárias, inclusive de transporte de passageiros e tripulantes; e

IV - que estejam prestando ou recebendo socorro. 

Art. 29.  O ingresso em veículo procedente do exterior ou a ele destinado será permitido somente aos tripulantes e passageiros, às pessoas em serviço, devidamente identificadas, e às pessoas expressamente autorizadas pela autoridade aduaneira (Decreto-Lei nº 37, de 1966, art. 38). 

Art. 30.  Quando conveniente aos interesses da Fazenda Nacional, poderá ser determinado, pela autoridade aduaneira, o acompanhamento fiscal de veículo pelo território aduaneiro. 

Seção II

Da Prestação de Informações pelo Transportador 

Art. 31.  O transportador deve prestar à Secretaria da Receita Federal do Brasil, na forma e no prazo por ela estabelecidos, as informações sobre as cargas transportadas, bem como sobre a chegada de veículo procedente do exterior ou a ele destinado (Decreto-Lei nº 37, de 1966, art. 37, caput, com a redação dada pela Lei nº 10.833, de 2003, art. 77). 

§ 1o  Ao prestar as informações, o transportador, se for o caso, comunicará a existência, no veículo, de mercadorias ou de pequenos volumes de fácil extravio. 

§ 2o  O agente de carga, assim considerada qualquer pessoa que, em nome do importador ou do exportador, contrate o transporte de mercadoria, consolide ou desconsolide cargas e preste serviços conexos, e o operador portuário também devem prestar as informações sobre as operações que executem e as respectivas cargas (Decreto-Lei nº 37, de 1966, art. 37, § 1º, com a redação dada pela Lei nº 10.833, de 2003, art. 77). 

Art. 32.  Após a prestação das informações de que trata o art. 31, e a efetiva chegada do veículo ao País, será emitido o respectivo termo de entrada, na forma estabelecida pela Secretaria da Receita Federal do Brasil. 

Parágrafo único.  As operações de carga, descarga ou transbordo em embarcações procedentes do exterior somente poderão ser executadas depois de prestadas as informações referidas no art. 31 (Decreto-Lei nº 37, de 1"""

def importar_decreto_6759():
    """Importa o Decreto 6.759/2009 diretamente."""
    
    print("=" * 70)
    print("📚 IMPORTANDO DECRETO 6.759/2009 - REGULAMENTO ADUANEIRO")
    print("=" * 70)
    print()
    
    # Inicializar banco
    print("🔧 Inicializando banco de dados...")
    init_db()
    print("✅ Banco inicializado")
    print()
    
    # Criar serviço
    service = LegislacaoService()
    
    # Dados do decreto
    tipo_ato = "Decreto"
    numero = "6759"
    ano = 2009
    sigla_orgao = "PR"  # Presidência da República
    titulo_oficial = "Decreto 6.759/2009 - Regulamento Aduaneiro"
    fonte_url = "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2009/decreto/d6759.htm"
    
    print("📋 Dados do Decreto:")
    print(f"   Tipo: {tipo_ato}")
    print(f"   Número: {numero}")
    print(f"   Ano: {ano}")
    print(f"   Órgão: {sigla_orgao}")
    print(f"   Título: {titulo_oficial}")
    print()
    
    print("=" * 70)
    print("📥 Importando texto fornecido...")
    print("=" * 70)
    print(f"📏 Tamanho do texto: {len(TEXTO_DECRETO_6759)} caracteres")
    print("⏳ Processando...")
    print()
    
    try:
        resultado = service.importar_ato_de_texto(
            tipo_ato=tipo_ato,
            numero=numero,
            ano=ano,
            sigla_orgao=sigla_orgao,
            texto_bruto=TEXTO_DECRETO_6759,
            titulo_oficial=titulo_oficial,
            fonte_url=fonte_url
        )
        
        if resultado.get('sucesso'):
            print("=" * 70)
            print("✅✅✅ SUCESSO! Decreto importado com sucesso!")
            print("=" * 70)
            print(f"   📊 ID do ato: {resultado.get('legislacao_id')}")
            print(f"   📄 Trechos importados: {resultado.get('trechos_importados')}")
            print()
            print("🎉 O Regulamento Aduaneiro foi importado e está disponível para consulta!")
            print()
            print("💡 Agora você pode consultar no chat:")
            print("   - 'o que diz o Decreto 6759?'")
            print("   - 'o que o Decreto 6759 fala sobre despacho aduaneiro?'")
            print("   - 'busque no Decreto 6759 trechos sobre importação'")
        else:
            erro = resultado.get('erro', 'Erro desconhecido')
            print("=" * 70)
            print("❌ Erro ao importar texto")
            print("=" * 70)
            print(f"   ⚠️ Motivo: {erro}")
            print()
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERRO INESPERADO durante o processamento")
        print("=" * 70)
        print(f"   ⚠️ Erro: {str(e)}")
        print()
        import traceback
        print("📋 Detalhes técnicos:")
        traceback.print_exc()

if __name__ == '__main__':
    try:
        importar_decreto_6759()
    except KeyboardInterrupt:
        print("\n\n⚠️ Importação cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()



