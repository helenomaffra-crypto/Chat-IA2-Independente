SELECT
	t.numero_processo ,
	ceH.idImportacao,
	ceRoot.valorFreteTotal,
	ceRoot.afrmmTUMPago,
	ceRoot.pendenciaAFRMM,
	ceRoot.indicadorPendenciaFrete,
	ceRoot.dataArmazenamentoCarga,
	ceRoot.dataDestinoFinal,
	ceRoot.situacaoCarga AS situacaoCargaCe,
	ceRoot.dataSituacaoCarga AS dataSituacaoCargaCeField,
	ceRoot.numero AS numeroCE,
	pf.pendenciaFrete,
	ceRoot.rootConsultaEmbarqueId,
	ceRoot.portoDestino,
	ceRoot.portoOrigem,
	ceRoot.portoAtracacaoAtual,
	ceRoot.updatedAt AS updatece,
	ceH.updatedAt AS updatehistce
FROM
	Serpro.dbo.Hi_Historico_Ce ceH
JOIN Serpro.dbo.Ce_Root_Conhecimento_Embarque ceRoot 
ON
	ceH.ceId = ceRoot.rootConsultaEmbarqueId
join Serpro.dbo.Ce_Pendencia_Frete pf 
    ON
	ceRoot.rootConsultaEmbarqueId = pf.rootConsultaEmbarqueId
JOIN comex.dbo.Importacoes i 
	ON I.id = ceH.idImportacao 
JOIN make.dbo.PROCESSO_IMPORTACAO t 
	on T.id_importacao = I.ID
	
--Parâmetros disponíveis para consulta
where t.numero_processo ='ALH.0169/25'
-- where ceRoot.numero=''