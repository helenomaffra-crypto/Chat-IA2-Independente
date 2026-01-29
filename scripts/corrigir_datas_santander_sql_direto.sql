-- Script SQL direto para corrigir datas dos lançamentos do Santander
-- que foram salvos com data 07/01/2026 mas deveriam ser 08/01/2026
-- 
-- Este script atualiza diretamente no banco de dados baseado nos valores conhecidos
-- do dia 08/01/2026 que aparecem no chat mas estão salvos como 07/01/2026

USE mAIke_assistente;
GO

-- Lista de lançamentos do dia 08/01/2026 (valores conhecidos do chat)
-- Atualizar apenas lançamentos do Santander com data 07/01/2026 que correspondem aos valores do dia 08

-- 1. PIX ENVIADO - 4pl Apoio Administrativo (R$ 7,880.48)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 7880.48) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%4pl Apoio Administrativo%'
  AND descricao_movimentacao NOT LIKE '%4pl Apoio Administrativo -%';  -- Excluir os que já têm complemento completo

-- 2. PIX ENVIADO - MASSY DO BRASIL COMERCIO (R$ 272,902.70)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 272902.70) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%MASSY DO BRASIL COMERCIO%';

-- 3. PIX ENVIADO - RIO BRASIL TERMINAL (R$ 17,465.73)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 17465.73) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%RIO BRASIL TERMINAL%';

-- 4. PIX RECEBIDO - 02378779000109 (R$ 498.00)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 498.00) < 0.01
  AND sinal_movimentacao = 'C'
  AND descricao_movimentacao LIKE '%02378779000109%';

-- 5. PIX RECEBIDO - 55046509000167 (R$ 81,166.63)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 81166.63) < 0.01
  AND sinal_movimentacao = 'C'
  AND descricao_movimentacao LIKE '%55046509000167%'
  AND id_movimentacao NOT IN (
      -- Excluir se já existe outro com mesmo valor e data 08/01
      SELECT id_movimentacao 
      FROM dbo.MOVIMENTACAO_BANCARIA 
      WHERE CAST(data_movimentacao AS DATE) = '2026-01-08'
        AND ABS(valor_movimentacao - 81166.63) < 0.01
        AND sinal_movimentacao = 'C'
  );

-- 6. PIX RECEBIDO - 55046509000167 (R$ 58,471.06)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 58471.06) < 0.01
  AND sinal_movimentacao = 'C'
  AND descricao_movimentacao LIKE '%55046509000167%'
  AND id_movimentacao NOT IN (
      SELECT id_movimentacao 
      FROM dbo.MOVIMENTACAO_BANCARIA 
      WHERE CAST(data_movimentacao AS DATE) = '2026-01-08'
        AND ABS(valor_movimentacao - 58471.06) < 0.01
        AND sinal_movimentacao = 'C'
  );

-- 7. PIX RECEBIDO - 55046509000167 (R$ 69,009.44)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 69009.44) < 0.01
  AND sinal_movimentacao = 'C'
  AND descricao_movimentacao LIKE '%55046509000167%'
  AND id_movimentacao NOT IN (
      SELECT id_movimentacao 
      FROM dbo.MOVIMENTACAO_BANCARIA 
      WHERE CAST(data_movimentacao AS DATE) = '2026-01-08'
        AND ABS(valor_movimentacao - 69009.44) < 0.01
        AND sinal_movimentacao = 'C'
  );

-- 8. PIX RECEBIDO - 55046509000167 (R$ 64,255.57)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 64255.57) < 0.01
  AND sinal_movimentacao = 'C'
  AND descricao_movimentacao LIKE '%55046509000167%'
  AND id_movimentacao NOT IN (
      SELECT id_movimentacao 
      FROM dbo.MOVIMENTACAO_BANCARIA 
      WHERE CAST(data_movimentacao AS DATE) = '2026-01-08'
        AND ABS(valor_movimentacao - 64255.57) < 0.01
        AND sinal_movimentacao = 'C'
  );

-- 9. PIX ENVIADO - 4pl Apoio Administrativo (R$ 7,885.55)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 7885.55) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%4pl Apoio Administrativo%';

-- 10. PIX ENVIADO - 4pl Apoio Administrativo (R$ 786.22)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 786.22) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%4pl Apoio Administrativo%';

-- 11. PIX ENVIADO - BARDAM MEDIA (R$ 5,989.90)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 5989.90) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%BARDAM MEDIA%';

-- 12. TRANSF VALOR P/ CONTA DIF TITULAR - 08895016700 (R$ 2,000.00)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 2000.00) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%TRANSF VALOR P/ CONTA DIF TITULAR%'
  AND descricao_movimentacao LIKE '%08895016700%';

-- 13. PAGAMENTO DE BOLETO OUTROS BANCOS - JM TRANSPORTES (R$ 2,800.00)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 2800.00) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%PAGAMENTO DE BOLETO OUTROS BANCOS%'
  AND descricao_movimentacao LIKE '%JM TRANSPORTES%';

-- 14. PAGAMENTO DE BOLETO - MSC MEDITERRANEAN (R$ 8,202.79)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 8202.79) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%PAGAMENTO DE BOLETO%'
  AND descricao_movimentacao LIKE '%MSC MEDITERRANEAN%';

-- 15. PIX ENVIADO - FUTURO FERTIL (R$ 573.00)
UPDATE dbo.MOVIMENTACAO_BANCARIA
SET data_movimentacao = '2026-01-08 00:00:00',
    data_lancamento = '2026-01-08 00:00:00'
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-07'
  AND ABS(valor_movimentacao - 573.00) < 0.01
  AND sinal_movimentacao = 'D'
  AND descricao_movimentacao LIKE '%FUTURO FERTIL%';

-- Verificar quantos foram atualizados
SELECT 
    'Lançamentos atualizados para 08/01/2026' as resultado,
    COUNT(*) as total
FROM dbo.MOVIMENTACAO_BANCARIA
WHERE banco_origem = 'SANTANDER'
  AND CAST(data_movimentacao AS DATE) = '2026-01-08';


