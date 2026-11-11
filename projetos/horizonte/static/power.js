'use strict';
// 3.11: explicit official-data dates; no remote finance data or hidden forecasts.
const powerBaseRender = render, powerBaseHandle = handle;
uxNames.power='Poder de compra';
uxPaths.power='M3 19h18M5 15l5-5 4 3 6-9M16 4h4v4';
let powerData=null, powerInputs=null, powerResult=null, powerFetching=false, powerTimer=null, powerStarted=false, powerDraftKey='';
const powerPct=n=>new Intl.NumberFormat('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n)+'%';
const powerMonth=m=>m?month31(m):'Aguardando divulgação';
function powerInitInputs(){
 if(powerInputs||!powerData?.available)return;
 const rows=powerData.rows,latest=rows.at(-1).month;
 powerInputs={start:rows[Math.max(0,rows.length-13)].month,end:latest,initial:1000,final:1000,oldIncome:0,newIncome:S.profile.income/100,netReturn:0,target:0,capital:0,monthly:0,years:10,annual:0,futureMode:'observed',futureInflation:5,...S.purchasingPower};
 powerDraftKey=JSON.stringify(S.purchasingPower||{});
}
function powerSource(){
 const d=powerData;
 if(!d)return '<section class="card power-source" role="status"><h2>Consultando a inflação oficial…</h2><p>Seus dados financeiros ficam neste aparelho.</p></section>';
 if(!d.available)return `<section class="card power-source" role="status"><h2>${d.updating?'Buscando o IPCA nas fontes oficiais…':'Sem índice oficial disponível'}</h2><p>${esc(d.warning||'Aguarde a primeira consulta. Nenhum índice será inventado.')}</p>${btn('power-refresh','Tentar atualizar','','secondary')}<small>Sem internet e sem consulta salva, os cálculos históricos ficam indisponíveis.</small></section>`;
 const check=d.checkedAt?new Date(d.checkedAt).toLocaleString('pt-BR'):'Não verificado';
 return `<section class="card power-source" role="status"><div class="split-heading"><div><span class="card-label">IPCA · Brasil · ${esc(powerMonth(d.latestMonth))}</span><h2>Inflação oficial mais recente consultada</h2></div>${btn('power-refresh',d.updating?'Atualizando…':'Atualizar agora','','secondary')}</div><div class="power-statline"><div><strong>${powerPct(d.monthly)}</strong><small>No mês divulgado</small></div><div><strong>${powerPct(d.annual)}</strong><small>${d.annualPublished?'Acumulado oficial em 12 meses':'Acumulado calculado em 12 meses'}</small></div></div><p class="muted">Fonte: ${esc(d.provider)} · Consulta confirmada em ${esc(check)}.</p>${d.warning?`<p class="power-warning">${esc(d.warning)}</p>`:''}${d.needsCheck&&!d.updating?'<p class="power-warning">Consulta salva: verificação de atualização pendente.</p>':''}${d.updating?'<p>Verificando se há nova divulgação… Os dados salvos continuam disponíveis.</p>':''}<details><summary>Fonte e período dos dados</summary><p>O IPCA é divulgado por competência mensal. Uma consulta feita hoje não mede a inflação de hoje nem completa meses ainda não publicados.</p><p>${esc(d.method)}</p><p>Atualização ao abrir o aplicativo e ao retornar à tela, respeitando um intervalo de seis horas. Falhas usam a última consulta salva com aviso e nova tentativa após 15 minutos. Com o aplicativo fechado, não há busca contínua.</p><a href="https://sidra.ibge.gov.br/tabela/1737" target="_blank" rel="noopener noreferrer">Consultar a série oficial do IBGE</a></details></section>`;
}
function powerField(name,label,options={}){
 const p=powerInputs,attrs=Object.entries({type:'number',step:'any',min:0,...options}).map(([k,v])=>`${k}="${esc(v)}"`).join(' ');
 return `<label class="field">${label}<input name="${name}" ${attrs} value="${esc(p[name])}" required></label>`;
}
function powerCapture(form){
 if(!powerInputs)return;
 for(const [k,v] of new FormData(form).entries())powerInputs[k]=['start','end','futureMode'].includes(k)?v:Number(v);
}
function powerReadAll(){for(const form of document.querySelectorAll('.power-form'))powerCapture(form);}
function powerHistory(){
 const d=powerData;if(!d?.available)return '';
 const complete=(S.history||[]).filter(h=>h.cash!==null&&Number.isFinite(h.cash)&&h.date.slice(0,7)<=d.latestMonth),byMonth=new Map();
 for(const h of complete){const m=h.date.slice(0,7);if(!byMonth.has(m)||byMonth.get(m).date<h.date)byMonth.set(m,h);}
 const indices=new Map(d.rows.map(r=>[r.month,r.index])),points=[...byMonth.entries()].sort((a,b)=>a[0].localeCompare(b[0])).filter(([m])=>indices.has(m)).slice(-12),first=points[0]?.[0];
 return `<details class="card power-history"><summary>Patrimônio registrado em poder de compra comparável</summary><p>Caixa + reserva + carteira − dívidas registradas. Usa o último retrato salvo em cada mês já divulgado. A variação inclui aportes, retiradas e ajustes: não é uma taxa de rentabilidade.</p>${points.length?`<div class="power-history-list">${points.map(([m,h])=>{const nominal=(h.cash+h.reserve+h.portfolio-h.debts)/100,real=nominal*indices.get(first)/indices.get(m);return `<div class="row"><div><strong>${esc(powerMonth(m))}</strong><small>Retrato de ${esc(h.date.split('-').reverse().join('/'))}</small></div><div><strong>${brl(real)}</strong><small>${brl(nominal)} nominais</small></div></div>`;}).join('')}</div><small>Valores corrigidos para ${esc(powerMonth(first))}. Retratos atuais de meses sem IPCA divulgado ficam fora. Não inclui bens não cadastrados.</small>`:empty('Ainda sem retratos completos de meses divulgados.','O histórico começa conforme você salva os dados. Não criamos patrimônio passado fictício; informe comparações abaixo se tiver seus registros.')}</details>`;
}
function powerView(){
 powerInitInputs();
 const introHtml=intro('Seu dinheiro está comprando mais?','Compare valores, salário e investimentos depois da inflação. Planeje metas em poder de compra de hoje.',btn('power-save','Salvar parâmetros')+btn('power-reset','Limpar comparação'));
 if(!powerData?.available||!powerInputs)return introHtml+`<div id="power-source">${powerSource()}</div>`;
 const p=powerInputs,r=powerResult,opts=value=>powerData.rows.slice().reverse().map(x=>`<option value="${x.month}" ${x.month===value?'selected':''}>${esc(powerMonth(x.month))}</option>`).join('');
 const available=new Set(powerData.rows.map(x=>x.month)),missing=!available.has(p.start)||!available.has(p.end);
 return introHtml+`<div id="power-source">${powerSource()}</div><section class="card"><h2>Escolha o período histórico</h2><form id="power-period" class="power-form form-grid"><label class="field">Mês inicial<select name="start">${!available.has(p.start)?`<option selected value="${esc(p.start)}">${esc(p.start)} · fora do histórico</option>`:''}${opts(p.start)}</select></label><label class="field">Mês final<select name="end">${!available.has(p.end)?`<option selected value="${esc(p.end)}">${esc(p.end)} · fora do histórico</option>`:''}${opts(p.end)}</select></label></form><small>Comparação entre o fim dos meses escolhidos: exclui a variação do mês inicial e inclui a do final. ${missing?'O período salvo não está disponível na consulta atual; ajuste-o para calcular.':''}</small>${r?`<p class="power-period-result">IPCA entre ${esc(powerMonth(r.start))} e ${esc(powerMonth(r.end))}: <strong>${powerPct(r.inflation)}</strong></p>`:''}</section>
 <section class="card power-section"><h2>Dinheiro e patrimônio</h2><p>Informe os saldos nos meses escolhidos. R$1.000 é um exemplo inicial editável; esta comparação não altera seu saldo cadastrado.</p><form id="power-money" class="power-form form-grid">${powerField('initial','Valor no mês inicial (R$)')}${powerField('final','Valor no mês final (R$)')}<button class="primary" type="submit">Comparar poder de compra</button></form>${r?`<div class="grid three power-results">${metric('Para preservar o valor inicial',brl(r.money.required),'Valor necessário no mês final')}${metric('Saldo final em valores iniciais',brl(r.money.realFinal),'Descontada a inflação do período')}${metric('Variação real do saldo',r.money.realChange===null?'Sem base inicial':powerPct(r.money.realChange),'Inclui depósitos e retiradas; não é rentabilidade')}</div>`:''}</section>
 ${powerHistory()}
 <details class="card power-section" id="power-income-section"><summary>Meu salário acompanhou a inflação?</summary><p>Compare sua renda mensal líquida total, somando os recebimentos do mês. Ainda não configura o calendário quinzenal.</p><form id="power-income" class="power-form form-grid">${powerField('oldIncome','Renda mensal no mês inicial (R$)')}${powerField('newIncome','Renda mensal no mês final (R$)')}<button class="primary" type="submit">Comparar renda real</button></form>${r?`<div class="grid three power-results">${metric('Renda para manter o poder de compra',brl(r.income.required),'Com o IPCA do período')}${metric('Renda final em valores iniciais',brl(r.income.realCurrent),'Comparação de renda mensal')}${metric('Variação real da renda',r.income.realChange===null?'Informe a renda inicial':powerPct(r.income.realChange),'Positivo: ganho de poder de compra')}</div>`:''}</details>
 <details class="card power-section" id="power-investment-section"><summary>Meu investimento rendeu acima da inflação?</summary><p>Informe a rentabilidade do mesmo período, já descontados impostos e taxas. Não use crescimento de saldo com aportes como rentabilidade.</p><form id="power-investment" class="power-form form-grid">${powerField('netReturn','Rentabilidade líquida do período (%)',{min:-90,max:100})}<button class="primary" type="submit">Calcular rendimento real</button></form>${r?`<div class="grid three power-results">${metric('Retorno líquido informado',powerPct(r.investment.netReturn),'Não consultado na corretora')}${metric('Inflação no mesmo intervalo',powerPct(r.inflation),'Índice oficial da consulta')}${metric('Rentabilidade real',powerPct(r.investment.realReturn),'(1 + retorno líquido) ÷ (1 + inflação) − 1')}</div>`:''}</details>
 <details class="card power-section" id="power-future-section"><summary>Quanto guardar para uma meta em valores de hoje?</summary><p>Simulação com aportes mensais fixos no fim do mês. Os valores abaixo são hipóteses; a inflação futura não é conhecida.</p>${S.goals.length?`<div class="power-goal-choice"><label class="field">Usar valores de uma meta cadastrada<select id="power-goal"><option value="">Escolha uma meta</option>${S.goals.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('')}</select></label>${btn('power-use-goal','Trazer valor e saldo')}</div>`:''}<form id="power-future" class="power-form form-grid">${powerField('target','Valor da meta em dinheiro de hoje (R$)')}${powerField('capital','Já reservado para a meta (R$)')}${powerField('monthly','Aporte mensal fixo (R$)')}${powerField('years','Prazo (anos)',{min:1,max:70,step:1})}${powerField('annual','Retorno líquido hipotético (% ao ano)',{min:-90,max:100})}<label class="field">Premissa de inflação futura<select name="futureMode"><option value="observed" ${p.futureMode==='observed'?'selected':''}>Repetir o IPCA dos últimos 12 meses · hipótese</option><option value="manual" ${p.futureMode==='manual'?'selected':''}>Informar minha hipótese</option></select></label>${powerField('futureInflation','Inflação anual personalizada (%)',{min:-20,max:50})}<button class="primary" type="submit">Projetar meta e aporte</button></form><small>Na opção de repetir o IPCA, o campo personalizado é ignorado. O índice recente serve apenas de hipótese constante para o futuro, sem garantia de repetição.</small>${r?`<div class="power-future-results"><p>Referência: inflação de ${powerPct(r.future.inflation)} a.a. e retorno líquido hipotético de ${powerPct(r.future.annual)} a.a. por ${r.future.years} anos.</p><div class="grid three power-results">${r.future.scenarios.map(x=>`<article class="power-scenario"><h3>${esc(x.label)}</h3><small>Inflação: ${powerPct(x.inflation)} a.a.</small><p>Meta futura <strong>${brl(x.futureTarget)}</strong></p><p>Saldo projetado <strong>${brl(x.nominal)}</strong></p><p>Em dinheiro de hoje <strong>${brl(x.real)}</strong></p><p class="power-required">Aporte mensal necessário <strong>${brl(Math.ceil(x.requiredMonthly*100)/100)}</strong></p></article>`).join('')}</div><small>Os cenários alteram só a inflação em ±2 pontos percentuais; não são probabilidades nem recomendações de aplicação. A simulação não registra aportes e não muda suas metas.</small></div>`:''}</details>
 <details class="card"><summary>Como interpretar e o que vem depois</summary><p>O IPCA representa a cesta média pesquisada pelo IBGE. Sua inflação pessoal pode ser diferente. Nesta versão não calculamos um índice pessoal a partir de notas fiscais.</p><p>Também não há recomendação automática de financiamento de imóvel. Comparar compra e aluguel exige contrato, custo efetivo total, indexadores, custos de manutenção e condições pessoais.</p><p>Salvar parâmetros preserva os campos no backup financeiro. A consulta oficial tem um cache separado neste aparelho e é buscada novamente ao restaurar em outro dispositivo.</p></details>`;
}
function powerPaint(){if(view!=='power')return;const opened=[...document.querySelectorAll('#content details[open][id]')].map(e=>e.id);$('#content').innerHTML=powerView();for(const id of opened){const e=document.getElementById(id);if(e)e.open=true;}}
async function powerLoad(force=false){
 if(powerFetching)return;
 powerFetching=true;
 try{
  const wasAvailable=powerData?.available,previous=powerData?.checkedAt;
  powerData=await api(force?'inflation/refresh':'inflation/status',force?{}:undefined);
  if(!powerInputs)powerInitInputs();
  const changed=previous&&previous!==powerData.checkedAt;
  if(changed){if(view==='power')powerReadAll();powerResult=null;}
  if(view==='power'){if((!wasAvailable&&powerData.available)||changed)powerPaint();else if($('#power-source'))$('#power-source').innerHTML=powerSource();}
  if(powerData.updating){clearTimeout(powerTimer);powerTimer=setTimeout(()=>powerLoad(),1800);}
 }catch(e){toast('Inflação: '+e.message);if(!powerData){powerData={available:false,warning:'Não foi possível consultar o serviço local. Tente atualizar novamente.'};powerPaint();}}
 finally{powerFetching=false;}
}
render=function(){
 const chosen=view;if(view==='power')view='settings';powerBaseRender();view=chosen;
 const group=$('#nav .nav-group31:nth-of-type(2)')||$('#nav .nav-group31');
 if(group)group.insertAdjacentHTML('beforeend',`<button data-view="power" title="Poder de compra" aria-label="Poder de compra" class="${view==='power'?'active':''}">${uxIcon('power')}<span class="ux-nav-text">Poder de compra</span></button>`);
 if(view==='power'){
  for(const el of document.querySelectorAll('#nav [data-view],#ux-bottom [data-target]')){const active=el.dataset.view==='power';el.classList.toggle('active',active);if(active)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');}
  $('#page-title').textContent='Poder de compra';document.title='Poder de compra • Horizonte';powerPaint();
  powerLoad();
 }
 $('footer').textContent=window.HorizonteAndroid?'Horizonte 3.11 · Dados neste aparelho · Sem sincronização automática':'Horizonte / IV · 3.11 · Finanças e casa';
 if(!powerStarted){powerStarted=true;powerLoad();}
};
handle=async function(action,el){
 if(action==='power-refresh')return powerLoad(true);
 if(action==='power-save'){
  if(!powerInputs)throw Error('Aguarde a consulta oficial.');powerReadAll();
  const values=clone(powerInputs);return mutate(s=>{s.purchasingPower=values;});
 }
 if(action==='power-reset'){if(!confirm('Limpar os parâmetros desta comparação? Seus saldos e lançamentos não mudam.'))return;powerInputs=null;powerResult=null;await mutate(s=>{s.purchasingPower={};});powerInitInputs();return powerPaint();}
 if(action==='power-use-goal'){
  powerReadAll();const g=S.goals.find(g=>g.id===$('#power-goal')?.value);if(!g)throw Error('Escolha uma meta.');powerInputs.target=g.target/100;powerInputs.capital=goalSaved39(g)/100;powerResult=null;powerPaint();$('#power-future-section').open=true;return toast('Valor-alvo e saldo da meta carregados. Confira prazo, taxas e aportes da simulação.');
 }
 if(action==='import'){powerInputs=null;powerResult=null;}
 return powerBaseHandle(action,el);
};
document.addEventListener('input',e=>{if(e.target.closest('.power-form')){powerReadAll();powerResult=null;document.querySelectorAll('.power-results,.power-future-results,.power-period-result').forEach(el=>el.remove());}});
document.addEventListener('change',e=>{if(e.target.closest('.power-form')){powerReadAll();powerResult=null;document.querySelectorAll('.power-results,.power-future-results,.power-period-result').forEach(el=>el.remove());}});
document.addEventListener('submit',async e=>{
 if(!e.target.classList.contains('power-form'))return;e.preventDefault();const button=e.submitter;if(button)button.disabled=true;
 try{powerReadAll();powerResult=await api('power/analyze',powerInputs);powerPaint();}
 catch(err){toast(err.message);}finally{if(button)button.disabled=false;}
});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)powerLoad();});
window.addEventListener('online',()=>powerLoad(true));
setInterval(()=>{if(!document.hidden)powerLoad();},15*60*1000);
uxBus.addEventListener('state:committed',()=>{if(powerInputs&&powerDraftKey!==JSON.stringify(S.purchasingPower||{})){powerInputs=null;powerResult=null;powerInitInputs();}});
