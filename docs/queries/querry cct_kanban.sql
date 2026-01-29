select 
	t.numero_processo,
	carae.codigoAeroportoDestinoConhecimento as cct_aeroporto_dest, 
	carae.codigoAeroportoOrigemConhecimento as cct_aeroporto_orig,
	carae.identificacao as cct_awb,
	cape.dataHoraSituacaoAtual as cct_data_hr_situacao,
	cape.situacaoAtual as cct_situacao,
	cape.identificacaoViagem as cct_viagem,
	cape.recintoAduaneiro as cct_recinto_adua,
	cape.unidadeRfb as cct_unidade_rbf,
	cape.numeroDocumentoSaida as cct_numero_doc_saida,
	cape.pesoBrutoEstoque as cct_peso_bruto,
	cape.quantidadeVolumesEstoque as cct_qtd_vol,
	caba.dataHoraBloqueio  as cct_data_rh_bloq,
	caba.justificativaBloqueio cct_just_bloq ,
	caba.motivoBloqueio as cct_motivo_bloq,
	caba.responsavelBloqueio as cct_resp_bloq,
	caba.tipoBloqueio as cct_tipo_bloq,
	caba.alcanceBloqueio as cct_calcance_bloq,
	cabb.dataHoraBloqueio as cct_data_rh_bloq_bx,
	cabb.dataHoraDesbloqueio as cct_data_rh_desbloq_bx,
	cabb.justificativaBloqueio as cct_just_bloq_bx,
	cabb.justificativaDesbloqueio as cct_just_desbloq_bx ,
	cabb.motivoBloqueio as cct_motivo_bloq_bx ,
	cabb.responsavelBloqueio as cct_resp_bloq_bx,
	cabb.responsavelDesbloqueio cct_resp_desbloq_bx,
	cabb.tipoBloqueio as cct_tipo_bloq_bx
from duimp.dbo.CCT_Aereo_RootAereoEntity carae
left join CCT_Aereo_PartesEstoque cape 
	on carae.id = cape.rootAereoEntityId
left join CCT_Aereo_BloqueiosAtivo caba 
	on caba.rootAereoEntityId  = carae.id 
left join CCT_Aereo_BloqueiosBaixado cabb 
	on cabb.rootAereoEntityId  = carae.id 
left join make.dbo.PROCESSO_IMPORTACAO t 
	on t.id_processo_importacao = carae.idImportacao 
left join Comex.dbo.Importacoes i
	on i.id = t.id_importacao 
-- parâmetros de consulta
where t.numero_processo ='GLT.0041/25'
--where carae.identificacao=''
