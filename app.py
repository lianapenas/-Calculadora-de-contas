import json
import decimal
from datetime import datetime
import locale
from flask import Flask, render_template, request, redirect, url_for, session
from babel.numbers import format_currency

app = Flask(__name__)

# Definir uma chave secreta para a sessão
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração do decimal para garantir precisão nos cálculos
decimal.getcontext().prec = 10  # Define a precisão de 10 casas decimais

# Tentar configurar a localidade de maneira mais robusta
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')  # Fallback para o inglês, caso o brasileiro não esteja disponível
    except locale.Error:
        pass  # Se não conseguir configurar, o sistema continuará com localidade padrão

# Função para carregar dados da sessão
def carregar_dados():
    contas = session.get('contas', [])
    historico = session.get('historico', {})
    return contas, historico

# Função para salvar dados na sessão
def salvar_dados(contas, historico):
    session['contas'] = contas
    session['historico'] = historico

# Função para calcular o total das contas
def calcular_total(contas):
    total = decimal.Decimal('0.00')
    for conta in contas:
        try:
            total += decimal.Decimal(conta['valor'])
        except decimal.InvalidOperation:
            continue  # Se houver erro ao converter, ignora a conta
    return total

# Função para formatar o valor como moeda brasileira (R$)
def formatar_reais(valor):
    return format_currency(valor, 'BRL', locale='pt_BR')

# Função de formatação de data
@app.template_filter('format_date')
def format_date(value, format='%d/%m/%Y'):
    if isinstance(value, datetime):
        return value.strftime(format)
    return value

# Função de formatação de moeda (filtro corrigido)
@app.template_filter('formatar_moeda')
def formatar_moeda(value):
    try:
        valor = decimal.Decimal(value)
        return format_currency(valor, 'BRL', locale='pt_BR')
    except (decimal.InvalidOperation, TypeError):
        return value

# Rota para a página inicial
@app.route('/')
def index():
    contas, historico = carregar_dados()  # Carregar os dados da sessão
    total_contas = calcular_total(contas)  # Calcular o total das contas
    return render_template('index.html', contas=contas, historico=historico, total_contas=total_contas)

# Rota para adicionar uma nova conta
@app.route('/adicionar_conta', methods=['GET', 'POST'])
def adicionar_conta():
    contas, historico = carregar_dados()

    if request.method == 'POST':
        nome_conta = request.form.get('nome_conta')
        valor_conta_str = request.form.get('valor_conta')
        vencimento = request.form.get('vencimento')

        # Verificar se algum campo está ausente
        if not nome_conta or not valor_conta_str or not vencimento:
            return render_template('index.html', error_message="Erro: Todos os campos são obrigatórios.", contas=contas, historico=historico)

        try:
            vencimento_date = datetime.strptime(vencimento, "%Y-%m-%d")
        except ValueError:
            return render_template('index.html', error_message="Erro: O formato da data de vencimento está incorreto.", contas=contas, historico=historico)

        # Validar se o valor é numérico antes de tentar converter para Decimal
        try:
            valor_conta = decimal.Decimal(valor_conta_str)
        except decimal.InvalidOperation:
            return render_template('index.html', error_message="Erro: O valor da conta não é válido. Por favor, insira um número válido.", contas=contas, historico=historico)

        # Adicionar a conta à lista de contas
        contas.append({'id': len(contas), 'nome': nome_conta, 'valor': valor_conta, 'vencimento': vencimento_date})

        salvar_dados(contas, historico)  # Salvar os dados na sessão

        return redirect(url_for('index'))

    # Se for GET, apenas renderiza o formulário
    return render_template('index.html', contas=contas, historico=historico)

# Rota para pagar uma conta
@app.route('/pagar_conta/<int:conta_id>', methods=['POST'])
def pagar_conta(conta_id):
    contas, historico = carregar_dados()

    conta = next((item for item in contas if item['id'] == conta_id), None)
    if conta:
        contas.remove(conta)
        pagamento_data = datetime.now()
        month_year = get_month_year(pagamento_data)

        if month_year not in historico:
            historico[month_year] = []

        conta['data_pagamento'] = pagamento_data
        historico[month_year].append(conta)

        salvar_dados(contas, historico)

    return redirect(url_for('index'))

# Rota para excluir uma conta
@app.route('/excluir_conta/<int:conta_id>', methods=['POST'])
def excluir_conta(conta_id):
    contas, historico = carregar_dados()

    conta_a_excluir = next((item for item in contas if item['id'] == conta_id), None)
    if conta_a_excluir:
        contas.remove(conta_a_excluir)

    salvar_dados(contas, historico)

    return redirect(url_for('index'))  # Redireciona de volta para a página inicial

# Função auxiliar para obter mês e ano
def get_month_year(data):
    return data.strftime("%Y-%m")

# Rota para exibir o histórico de contas pagas
@app.route('/historico')
def historico():
    contas, historico = carregar_dados()
    return render_template('historico.html', historico=historico)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
