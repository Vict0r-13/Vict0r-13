"""Local, explainable category suggestions. No model or external request."""
import re
import unicodedata


def normalized(text):
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))).split())


def suggest(state, description, kind='expense'):
    if not isinstance(description,str) or len(description)>160 or kind not in ('expense','income','investment'):
        raise ValueError('Descrição ou tipo inválido')
    key=normalized(description)
    if not key:return {'category':None,'reason':'Digite uma descrição.'}
    matches={t['category'] for t in state['transactions'] if t['type']==kind and normalized(t['name'])==key}
    if len(matches)==1:return {'category':matches.pop(),'reason':'Mesma descrição e tipo no seu histórico.'}
    if len(matches)>1:return {'category':None,'reason':'Seu histórico tem categorias diferentes para esta descrição.'}
    rules=[('Alimentação',r'\b(mercado|supermercado|padaria|restaurante|ifood|lanche|almoco)\b'),('Transporte',r'\b(uber|99|onibus|combustivel|gasolina|estacionamento)\b'),('Moradia',r'\b(aluguel|condominio)\b'),('Educação',r'\b(faculdade|curso|mensalidade|livro|uninter|unifor)\b'),('Saúde',r'\b(farmacia|medicamento|consulta|dentista)\b'),('Lazer',r'\b(cinema|netflix|spotify|passeio)\b')]
    if kind=='income':rules=[('Salário',r'\b(salario|pagamento salarial)\b')]
    if kind=='investment':rules=[('Investimentos',r'\b(aporte|tesouro|cdb|investimento)\b')]
    found=[category for category,pattern in rules if re.search(pattern,key)]
    return {'category':found[0] if len(found)==1 else None,'reason':'Sugestão por palavra-chave; confira antes de salvar.' if len(found)==1 else 'Sem correspondência segura; escolha a categoria.'}
