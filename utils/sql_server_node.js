/**
 * Serviço Node.js para conexões SQL Server
 * 
 * Este módulo fornece funções para conectar ao SQL Server usando mssql,
 * que funciona perfeitamente onde pyodbc não funciona (especialmente no Mac).
 * 
 * Baseado na solução do projeto "CHAT IA" que teve problemas de compatibilidade
 * do Python (pyodbc) com Mac e acabou usando Node.js como solução.
 * 
 * Uso:
 *   node sql_server_node.js <comando> <args...>
 * 
 * Comandos:
 *   query <sql> [database] - Executa uma query SQL e retorna JSON
 *   test - Testa a conexão
 */

// Carregar variáveis de ambiente do arquivo .env
const path = require('path');
const fs = require('fs');

// Função para carregar .env manualmente (sem dependência de dotenv)
function loadEnvFile(filepath) {
    try {
        const envPath = path.resolve(filepath);
        if (fs.existsSync(envPath)) {
            const envContent = fs.readFileSync(envPath, 'utf8');
            envContent.split('\n').forEach(line => {
                const trimmed = line.trim();
                if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
                    const [key, ...valueParts] = trimmed.split('=');
                    const value = valueParts.join('=').trim().replace(/^["']|["']$/g, '');
                    if (key && value) {
                        process.env[key.trim()] = value;
                    }
                }
            });
            return true;
        }
    } catch (error) {
        // Ignora erro silenciosamente
    }
    return false;
}

// Tentar carregar .env de vários locais possíveis
// ✅ CORREÇÃO: Sempre tentar carregar do .env primeiro (para pegar mudanças recentes)
// Se variáveis já foram passadas via env do Python, elas terão prioridade
const possibleEnvPaths = [
    path.resolve(__dirname, '../.env'),
    path.resolve(process.cwd(), '.env'),
    '.env'
];

for (const envPath of possibleEnvPaths) {
    if (loadEnvFile(envPath)) {
        break;
    }
}

const sql = require('mssql');

// ✅ Configuração da conexão com valores padrão (como no protótipo que funciona)
// Os valores serão sobrescritos por variáveis de ambiente se fornecidos
const config = {
    server: '172.16.10.8',
    database: 'Make',
    user: 'sa',
    password: 'Z1mb@bu3BD',  // Valor padrão (será sobrescrito se SQL_PASSWORD estiver definido)
    options: {
        encrypt: false,  // IMPORTANTE: false para redes internas
        trustServerCertificate: true,
        instanceName: 'SQLEXPRESS',
        enableArithAbort: true,
        requestTimeout: 60000,  // 60 segundos
        connectionTimeout: 60000,
    },
    pool: {
        max: 20,
        min: 2,
        idleTimeoutMillis: 300000,  // 5 minutos
        acquireTimeoutMillis: 60000,
        createTimeoutMillis: 30000,
        reapIntervalMillis: 1000,
        createRetryIntervalMillis: 200
    }
};

// ✅ NOVO (19/01/2026): Permitir override de timeouts via env (útil para probes rápidos/ambiente VPN)
try {
    if (process.env.SQL_NODE_REQUEST_TIMEOUT_MS) {
        const v = parseInt(process.env.SQL_NODE_REQUEST_TIMEOUT_MS, 10);
        if (!Number.isNaN(v) && v > 0) config.options.requestTimeout = v;
    }
    if (process.env.SQL_NODE_CONNECTION_TIMEOUT_MS) {
        const v = parseInt(process.env.SQL_NODE_CONNECTION_TIMEOUT_MS, 10);
        if (!Number.isNaN(v) && v > 0) config.options.connectionTimeout = v;
    }
} catch (_) {}

// ✅ PERMITE SOBRESCREVER via variáveis de ambiente (igual ao protótipo)
// Isso garante que quando Python passa as variáveis, elas são usadas
if (process.env.SQL_SERVER) {
    const sqlServerValue = process.env.SQL_SERVER;
    // Extrair servidor e instância se houver barra invertida
    if (sqlServerValue.includes('\\')) {
        const parts = sqlServerValue.split('\\');
        config.server = parts[0];
        config.options.instanceName = parts[1];
    } else {
        config.server = sqlServerValue;
    }
    // ✅ CORREÇÃO: Log apenas para stderr (não misturar com stdout/JSON)
    // console.error vai para stderr, não interfere no JSON do stdout
    console.error(`[SQL Server Node] Conectando a: ${config.server}${config.options.instanceName ? '\\' + config.options.instanceName : ''}`);
}
if (process.env.SQL_DATABASE) {
    config.database = process.env.SQL_DATABASE;
}
if (process.env.SQL_USERNAME) {
    config.user = process.env.SQL_USERNAME;
}
if (process.env.SQL_PASSWORD) {
    config.password = process.env.SQL_PASSWORD;
}
if (process.env.SQL_INSTANCE && !config.options.instanceName) {
    config.options.instanceName = process.env.SQL_INSTANCE;
}

/**
 * Executa uma query SQL e retorna o resultado como JSON
 */
async function executeQuery(sqlQuery, database = null) {
    const dbConfig = { ...config };
    if (database) {
        dbConfig.database = database;
    }

    // Usa pool global para evitar criar/fechar conexões constantemente
    let pool = null;
    try {
        // Tenta reutilizar pool existente ou cria novo
        if (!global.sqlPool || !global.sqlPool.connected) {
            global.sqlPool = await sql.connect(dbConfig);
        }
        pool = global.sqlPool;
        
        const result = await pool.request().query(sqlQuery);
        
        // NÃO fecha o pool - mantém conexão para próximas queries
        // O pool será fechado apenas quando o processo Node.js terminar
        
        return {
            success: true,
            data: result.recordset,
            rowsAffected: result.rowsAffected || []
        };
    } catch (error) {
        // Se erro de conexão, tenta recriar pool
        if (error.code === 'ECONNRESET' || error.code === 'ETIMEDOUT' || error.message.includes('Connection is closed')) {
            try {
                if (global.sqlPool) {
                    await global.sqlPool.close();
                }
                global.sqlPool = await sql.connect(dbConfig);
                pool = global.sqlPool;
                const result = await pool.request().query(sqlQuery);
                return {
                    success: true,
                    data: result.recordset,
                    rowsAffected: result.rowsAffected || []
                };
            } catch (retryError) {
                return {
                    success: false,
                    error: retryError.message,
                    code: retryError.code
                };
            }
        }
        return {
            success: false,
            error: error.message,
            code: error.code
        };
    }
}

/**
 * Testa a conexão
 */
async function testConnection() {
    try {
        const pool = await sql.connect(config);
        const result = await pool.request()
            .query('SELECT DB_NAME() as db_name, @@VERSION as version');
        await pool.close();
        
        return {
            success: true,
            message: 'Conexão bem-sucedida',
            database: result.recordset[0].db_name,
            version: result.recordset[0].version.substring(0, 100)
        };
    } catch (error) {
        return {
            success: false,
            error: error.message,
            code: error.code
        };
    }
}

// Interface de linha de comando
if (require.main === module) {
    const command = process.argv[2];
    
    (async () => {
        try {
            if (command === 'test') {
                const result = await testConnection();
                console.log(JSON.stringify(result, null, 2));
                process.exit(result.success ? 0 : 1);
            } else if (command === 'query') {
                const sqlQuery = process.argv[3];
                const database = process.argv[4] || null;
                
                if (!sqlQuery) {
                    console.log(JSON.stringify({
                        success: false,
                        error: 'Query SQL não fornecida'
                    }, null, 2));
                    process.exit(1);
                }
                
                const result = await executeQuery(sqlQuery, database);
                console.log(JSON.stringify(result, null, 2));
                process.exit(result.success ? 0 : 1);
            } else {
                console.log(JSON.stringify({
                    success: false,
                    error: 'Comando inválido. Use: test ou query <sql> [database]'
                }, null, 2));
                process.exit(1);
            }
        } catch (error) {
            console.log(JSON.stringify({
                success: false,
                error: error.message
            }, null, 2));
            process.exit(1);
        }
    })();
}

// Exporta funções para uso como módulo
module.exports = {
    executeQuery,
    testConnection,
    config
};
