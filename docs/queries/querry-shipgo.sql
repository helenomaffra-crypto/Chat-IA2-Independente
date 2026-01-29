@select
	t2.criado_em, 
	t.numero_ce ,
	t.numero_duimp ,
	t.numero_processo,
	t2.id_externo_shipsgo,
	t2.atual_data_evento,
	t2.atual_evento,
	t2.atual_nome as atual_porto,
	t2.atual_codigo as cod_porto,
	t2.destino_data_chegada as frist_eta,
	t2.destino_nome as porto_final,
	t2.evento_status as status_evento,
	t2.status ,
	t2.quantidade_conteineres ,
	t2.navio as nome_navio,
	t2.numero_container ,
	t2.numero_booking,
	t2.numero_awb ,
	t2.id_movimento AS seq_movimento
from
	PROCESSO_IMPORTACAO t
left join TRANSPORTE t2 
	on t2.id_processo_importacao  = t.id_processo_importacao 

	order by id_externo_shipsgo desc