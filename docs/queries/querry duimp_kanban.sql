SELECT distinct
    d.numero,
--    d.data_registro                                   AS data_registro_mais_recente,
    d.id_processo_importacao,
    d.numero_processo,
    d.versao,
--    d.criado_em,
--    d.atualizado_em,
    d.data_ultimo_evento                              AS data_ultimo_evento_hook,
    d.ultima_situacao                                 AS ultima_situacao_hook,
    d.ultimo_evento                                   AS ultimo_evento_hook,
    drar.canal_consolidado                            AS canal_duimp,
    dd.situacao                                       AS situacao_diagnostico,
    dd.data_geracao                                   AS data_geracao_diagnostico,
    dd.situacao_duimp                                 AS situacao_duimp,
    drr.orgao                                         AS orgao,
    drr.resultado                                     AS resultado,
    dp.data_pagamento                                 AS data_pagamento,
    dp.tributo_tipo                                   AS tributo_tipo,
    dp.valor                                          AS valor,
    ds.situacao_analise_retificacao                   AS situacao_analise_retificacao,
    ds.situacao_duimp                                 AS situacao_duimp_agr,
    ds.situacao_licenciamento                         AS situacao_licenciamento,
    dsca.indicador_autorizacao_entrega                AS indicador_aut_entrega,
    dsca.situacao                                     AS situacao_conferencia_aduaneira,
    dsca.indicador_desembaraco_decisao_judicial       AS indicador_des_judicial
FROM Duimp.dbo.duimp d WITH (NOLOCK)
LEFT JOIN Duimp.dbo.duimp_diagnostico dd WITH (NOLOCK)
    ON dd.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_situacao ds WITH (NOLOCK)
    ON ds.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_pagamentos dp WITH (NOLOCK)
    ON dp.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_situacao_conferencia_aduaneira dsca WITH (NOLOCK)
    ON dsca.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_resultado_analise_risco drar WITH (NOLOCK)
    ON drar.duimp_id = d.duimp_id
LEFT JOIN Duimp.dbo.duimp_resultado_rfb drr WITH (NOLOCK)
    ON drr.duimp_id = d.duimp_id
  -- where d.numero_processo ='SLL.0003/25'
