
DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Strategy Miner - Dashboard</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="10">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Monaco, Courier New, monospace;
            background: #0a0a0a;
            color: #0f0;
            padding: 15px;
        }
        h1 {
            text-align: center;
            border-bottom: 2px solid #0f0;
            padding: 10px 0;
            font-size: 20px;
        }
        h2 {
            border-bottom: 1px solid #0f0;
            padding: 8px 0;
            margin: 15px 0 10px 0;
            font-size: 14px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
        }
        .stat-box {
            background: #000;
            border: 2px solid #0f0;
            padding: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 20px;
            font-weight: bold;
            color: #0f0;
        }
        .stat-label {
            font-size: 10px;
            color: #0f0;
            opacity: 0.7;
            margin-top: 3px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-top: 10px;
        }
        th, td {
            border: 1px solid #0f0;
            padding: 6px;
            text-align: left;
        }
        th { background: #0f0; color: #000; }
        tr:nth-child(even) { background: #0a0a0a; }
        .positive { color: #0f0; }
        .negative { color: #f00; }
        .best-section {
            background: #0a0a0a;
            border: 2px solid #0f0;
            padding: 15px;
            margin: 10px 0;
        }
        .best-params {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 10px;
        }
        .param {
            background: #000;
            padding: 8px;
            border: 1px solid #0a0;
        }
        .param-label {
            font-size: 9px;
            opacity: 0.7;
        }
        .param-value {
            font-size: 14px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <h1>🧬 STRATEGY MINER - COORDINATOR DASHBOARD</h1>
    
    <!-- ESTADO GENERAL -->
    <h2>📊 ESTADO GENERAL</h2>
    <div class="stats">
        <div class="stat-box">
            <div class="stat-value" id="total">-</div>
            <div class="stat-label">Total WUs</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="completed">-</div>
            <div class="stat-label">Completadas</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="pending">-</div>
            <div class="stat-label">Pendientes</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="workers">-</div>
            <div class="stat-label">Workers</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="results-total">-</div>
            <div class="stat-label">Resultados</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" id="results-pos">-</div>
            <div class="stat-label">Positivos</div>
        </div>
    </div>
    
    <!-- MEJOR ESTRATEGIA -->
    <h2>🏆 MEJOR ESTRATEGIA</h2>
    <div class="best-section">
        <div class="stats">
            <div class="stat-box">
                <div class="stat-value" id="best-pnl">$-</div>
                <div class="stat-label">PnL ($10k)</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-trades">-</div>
                <div class="stat-label">Trades</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-winrate">-%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-sharpe">-</div>
                <div class="stat-label">Sharpe</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-dd">-%</div>
                <div class="stat-label">Max DD</div>
            </div>
            <div class="stat-box">
                <div class="stat-value" id="best-lev">-x</div>
                <div class="stat-label">Leverage</div>
            </div>
        </div>
        <div class="best-params">
            <div class="param">
                <div class="param-label">Stop Loss</div>
                <div class="param-value" id="best-sl">-%</div>
            </div>
            <div class="param">
                <div class="param-label">Take Profit</div>
                <div class="param-value" id="best-tp">-%</div>
            </div>
            <div class="param">
                <div class="param-label">Contratos</div>
                <div class="param-value" id="best-contracts">-</div>
            </div>
            <div class="param">
                <div class="param-label">Return %</div>
                <div class="param-value" id="best-return">-%</div>
            </div>
        </div>
    </div>
    
    <!-- TOP RESULTS -->
    <h2>📈 TOP 10 RESULTADOS</h2>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>PnL</th>
                <th>Trades</th>
                <th>Win%</th>
                <th>Sharpe</th>
                <th>DD%</th>
                <th>Lev</th>
                <th>SL%</th>
                <th>TP%</th>
            </tr>
        </thead>
        <tbody id="results-body">
            <tr><td colspan="8">Cargando...</td></tr>
        </tbody>
    </table>
    
    <div style="text-align:center; margin-top:15px; opacity:0.5; font-size:11px;" id="timestamp"></div>

    <script>
        async function update() {
            try {
                const status = await fetch('/api/status').then(r => r.json());
                
                // General
                document.getElementById('total').textContent = status.work_units.total;
                document.getElementById('completed').textContent = status.work_units.completed;
                document.getElementById('pending').textContent = status.work_units.pending;
                document.getElementById('workers').textContent = status.workers.active;
                
                // Best strategy
                const bs = status.best_strategy;
                if (bs) {
                    document.getElementById('best-pnl').textContent = '$' + bs.pnl.toFixed(0);
                    document.getElementById('best-pnl').className = bs.pnl >= 0 ? 'stat-value positive' : 'stat-value negative';
                    document.getElementById('best-trades').textContent = bs.trades || '-';
                    document.getElementById('best-winrate').textContent = (bs.win_rate * 100).toFixed(1) + '%';
                    document.getElementById('best-sharpe').textContent = bs.sharpe_ratio ? bs.sharpe_ratio.toFixed(2) : '-';
                    document.getElementById('best-dd').textContent = bs.max_drawdown ? (bs.max_drawdown * 100).toFixed(1) + '%' : '-';
                    
                    const params = bs.strategy_params || {};
                    document.getElementById('best-sl').textContent = (params.stop_loss || '-') + '%';
                    document.getElementById('best-tp').textContent = (params.take_profit || '-') + '%';
                    document.getElementById('best-lev').textContent = (params.leverage || '-') + 'x';
                    document.getElementById('best-contracts').textContent = (params.contracts || []).length;
                    
                    const retorno = (bs.pnl / 10000 * 100).toFixed(1);
                    document.getElementById('best-return').textContent = retorno + '%';
                }
                
                // Results table
                const results = await fetch('/api/results').then(r => r.json());
                const tbody = document.getElementById('results-body');
                tbody.innerHTML = '';
                
                results.results.slice(0, 10).forEach((r, i) => {
                    const row = tbody.insertRow();
                    const params = r.strategy_params || {};
                    
                    row.insertCell(0).textContent = i + 1;
                    
                    const pnlCell = row.insertCell(1);
                    pnlCell.textContent = '$' + r.pnl.toFixed(0);
                    pnlCell.className = r.pnl >= 0 ? 'positive' : 'negative';
                    
                    row.insertCell(2).textContent = r.trades;
                    
                    const winCell = row.insertCell(3);
                    winCell.textContent = (r.win_rate * 100).toFixed(1) + '%';
                    winCell.className = r.win_rate >= 0.5 ? 'positive' : '';
                    
                    row.insertCell(4).textContent = r.sharpe_ratio ? r.sharpe_ratio.toFixed(2) : '-';
                    
                    const ddCell = row.insertCell(5);
                    ddCell.textContent = r.max_drawdown ? (r.max_drawdown * 100).toFixed(1) + '%' : '-';
                    
                    row.insertCell(6).textContent = params.leverage || '-';
                    row.insertCell(7).textContent = (params.stop_loss || '-') + '%';
                    row.insertCell(8).textContent = (params.take_profit || '-') + '%';
                });
                
                document.getElementById('timestamp').textContent = 'Actualizado: ' + new Date().toLocaleTimeString();
                
            } catch(e) {
                console.error(e);
            }
        }
        
        setInterval(update, 10000);
        update();
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
