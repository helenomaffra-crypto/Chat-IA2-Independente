SELECT
                        diH.idImportacao,
                        diDesp.dataHoraDesembaraco,
                        diDesp.canalSelecaoParametrizada,
                        ddg.situacaoDi,
                        ddg.numeroDi,
                        ddg.situacaoEntregaCarga,
                        ddg.updatedAt           AS updatedAtDiGerais,
                        diDesp.dataHoraRegistro,
                        ddg.dataHoraSituacaoDi,
                        DICM.tipoRecolhimento   AS tipoRecolhimentoIcms,
                        DA.nomeAdquirente,
                        DI.nomeImportador,
                        DVMD.totalDolares       AS dollar_VLMLD,
                        DVMD.totalReais         AS real_VLMD,
                        DVME.totalDolares       AS dollar_VLME,
                        DVME.totalReais         AS real_VLME,
                        DICM.dataPagamento,
                        diRoot.updatedAt        AS updatedi,
                        diH.updatedAt           AS updatehistdi
                    FROM Serpro.dbo.Hi_Historico_Di diH
                    JOIN Serpro.dbo.Di_Root_Declaracao_Importacao diRoot
                        ON diH.diId = diRoot.dadosDiId
                    JOIN Serpro.dbo.Di_Dados_Despacho diDesp
                        ON diRoot.dadosDespachoId = diDesp.dadosDespachoId
                    JOIN Serpro.dbo.Di_Dados_Gerais ddg 
                        ON diRoot.dadosGeraisId = ddg.dadosGeraisId
                    LEFT JOIN Serpro.dbo.Di_Icms DICM 
                        ON diRoot.dadosDiId = DICM.rootDiId
                    LEFT JOIN Serpro.dbo.Di_Adquirente DA 
                        ON diRoot.dadosDiId = DA.adquirenteId
                    LEFT JOIN Serpro.dbo.Di_Importador DI                            -- ← join para trazer nomeImportador
                        ON diRoot.importadorId = DI.importadorId
                    LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Descarga DVMD 
                        ON diRoot.valorMercadoriaDescargaId = DVMD.valorMercadoriaDescargaId
                    LEFT JOIN Serpro.dbo.Di_Valor_Mercadoria_Embarque DVME 
                        ON diRoot.valorMercadoriaEmbarqueId = DVME.valorMercadoriaEmbarqueId
                    LEFT JOIN comex.dbo.Importacoes i 
                    	ON i.id =  diH.idImportacao
                    LEFT JOIN make.dbo.PROCESSO_IMPORTACAO t 
                    	ON t.id_importacao = i.id
                    -- parâmetros para consulta 
                    where t.numero_processo ='alh.0169/25'
                    --where ddg.numeroDi ='' 