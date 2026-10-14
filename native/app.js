/** Original filing content and feedback rendered in native HTML. */
import {DATA} from './content.js';
import {Lesson,frontier,evaluateQuestion,summarizeResults,copy,decodeState,encodeState} from './engine.js';
const $=id=>document.getElementById(id);
const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
const escapeHTML=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
let lesson,sequence=0;
async function save() {
  const current=++sequence,state=copy(lesson.state),view=lesson.view;document.documentElement.dataset.saving='true';
  try {
    const token=await encodeState(state);if(current!==sequence)return;
    const url=new URL(location.href);url.searchParams.set('progress',token);url.searchParams.set('view',String(view));history.replaceState(null,'',url);$('save-error').hidden=true;
  }catch(error){if(current===sequence){$('save-error').textContent='Your address could not be updated. Keep this tab open; refreshing may not preserve the latest input.';$('save-error').hidden=false;console.error(error);}}
  finally{if(current===sequence)document.documentElement.dataset.saving='false';}
}
function scrollTop(){window.scrollTo({top:0,left:0,behavior:'instant'});$('lesson').focus({preventScroll:true});}
function update(scroll=false){render();save();if(scroll)scrollTop();}
function markdown(text) {
  const fragment=document.createDocumentFragment();let list=null;
  for(const line of text.split('\n').map(value=>value.trim()).filter(Boolean)) {
    const bullet=/^[-*]\s+(.+)/.exec(line),heading=/^(#{1,6})\s+(.+)/.exec(line);
    const item=el(bullet?'li':heading?'h'+heading[1].length:'p');
    item.innerHTML=escapeHTML(bullet?bullet[1]:heading?heading[2]:line).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
    if(bullet){if(!list){list=el('ul');fragment.append(list);}list.append(item);}else{list=null;fragment.append(item);}
  }return fragment;
}
function radio(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const id=node.key.replace(/^answer-/,''),question=lesson.viewedRound.questions.find(question=>question.id===id),fieldset=el('fieldset');
  fieldset.append(el('legend',node.label));
  for(const index of lesson.orders[id]) {
    const label=el('label',undefined,'choice'),input=el('input');input.type='radio';input.name=id;input.id=id+'_'+index;
    input.value=String(index);input.checked=lesson.state.choices[id]===index;
    input.addEventListener('change',()=>{if(lesson.draft(id,index))save();});
    label.append(input,el('span',question.options[index].text));fieldset.append(label);
  }return fieldset;
}
function action(node) {
  if(lesson.reviewing)return document.createDocumentFragment();
  const button=el('button',node.label,node.action==='reset_activity'&&lesson.view!==0?'':'primary');button.type='button';
  button.addEventListener('click',()=>{
    let changed=false,scroll=false;
    if(node.action==='reset_activity'){changed=lesson.restart();scroll=true;}
    else if(node.action==='submit_round'){changed=lesson.submit();scroll=true;}
    else if(node.action==='advance_round'){changed=lesson.advance();scroll=true;}
    else if(node.action==='reveal_answer')changed=lesson.reveal();
    if(changed||lesson.warning)update(scroll&&changed);
  });return button;
}
function gauges(node) {
  const section=el('section');section.append(el('h3',node.heading));
  const report=lesson.report,metrics=lesson.viewedMetrics,round=lesson.viewedRound;
  const baseline=node.baseline?(lesson.view===7?DATA.startingMetrics:report.baselines[round.slug]):null;
  const grid=el('div',undefined,'metric-grid');
  for(const [key,label] of Object.entries(DATA.metricLabels)) {
    const value=metrics[key],card=el('div',undefined,'metric-card'),display=el('div',String(value),'metric-value'),track=el('div',undefined,'metric-track');
    track.setAttribute('role','progressbar');track.setAttribute('aria-label',label);track.setAttribute('aria-valuemin','0');track.setAttribute('aria-valuemax','100');track.setAttribute('aria-valuenow',String(value));
    const segment=(kind,width)=>{const part=el('div',undefined,'metric-segment '+kind);part.style.width=width+'%';track.append(part);};
    if(baseline) {
      const delta=value-baseline[key],status=delta>0?'positive':delta<0?'negative':'neutral';
      display.append(el('span',(delta>=0?'+':'')+delta,'metric-delta '+status));
      if(delta>0){segment('carried',baseline[key]);segment('gained',delta);}
      else if(delta<0){segment('carried',value);segment('lost',-delta);}else segment('carried',value);
    }else segment('carried',value);
    card.append(el('div',label,'metric-label'),display,track);grid.append(card);
  }
  section.append(grid);
  if(baseline) {
    const legend=el('div',undefined,'metric-legend');
    for(const [kind,text] of [['carried','Points already there'],['lost','Net points lost'],['gained','Net points gained']]) {
      const item=el('span',undefined,'legend-item');item.append(el('span',undefined,'legend-swatch '+kind),document.createTextNode(text));legend.append(item);
    }section.append(legend);
  }return section;
}
function roundFeedback() {
  const round=lesson.viewedRound,report=lesson.report,results=report.responses.filter(result=>result.round_slug===round.slug),fragment=document.createDocumentFragment();
  const correct=results.filter(result=>result.is_correct).length;
  const message=el('p','Round complete: '+correct+' of '+results.length+' decisions matched the strongest reporting choice.','notice success');message.setAttribute('role','status');fragment.append(message);
  for(const result of results) {
    const status=result.is_correct?'correct':'review',card=el('div',undefined,'feedback-card '+status),prompt=el('p');
    prompt.append(el('strong',result.prompt));
    card.append(el('p',result.is_correct?'Strong decision':'Review this decision','feedback-label '+status),prompt,el('p',result.feedback));
    if(!result.is_correct){const stronger=el('p');stronger.append(el('strong','Stronger choice: '),document.createTextNode(result.correct_text));card.append(stronger);}
    card.append(el('p',result.explanation),el('span',result.concept,'concept-pill'));fragment.append(card);
  }
  const reflection=el('div',undefined,'reflection-card');
  reflection.append(el('p','Test your thinking','eyebrow'),el('p',round.reflection_question,'reflection-question'));fragment.append(reflection);
  if(lesson.state.revealed.includes(round.slug))fragment.append(el('div',round.reflection_answer,'revealed-answer'));
  else if(!lesson.reviewing)fragment.append(action({label:'Reveal answer',action:'reveal_answer'}));
  fragment.append(gauges({heading:'Gauges after this round',baseline:true}));
  if(!lesson.reviewing)fragment.append(action({label:lesson.view===6?'Open the final review':'Continue to the next round',action:'advance_round'}));
  return fragment;
}
function trail(round) {
  const results=lesson.report.responses.filter(result=>result.round_slug===round.slug),details=el('details');
  details.append(el('summary',round.title+' · '+results.filter(result=>result.is_correct).length+'/'+results.length+' strongest decisions'));
  for(const result of results) {
    const heading=el('p');heading.append(el('strong',(result.is_correct?'✓ ':'↻ ')+result.prompt));details.append(heading,el('p','Your decision: '+result.selected_text));
    if(!result.is_correct)details.append(el('p','Stronger choice: '+result.correct_text));
    details.append(el('p',result.concept+' · '+result.explanation,'caption'));
  }return details;
}
function renderNode(node) {
  if(node.kind==='radio')return radio(node);
  if(node.kind==='button')return action(node);
  if(node.kind==='gauges')return gauges(node);
  if(node.kind==='round-feedback')return roundFeedback();
  if(node.kind==='html') {
    const template=document.createElement('template');template.innerHTML=node.text;
    if(lesson.view===7) {
      const summary=summarizeResults(lesson.report.responses),hero=template.content.querySelector('.debrief-hero');
      if(hero){hero.querySelector('h1').textContent=summary.status;hero.querySelector('.debrief-score').textContent=summary.correct+' of '+summary.total+' strongest decisions · '+summary.percent+'%';hero.querySelector('p:last-child').textContent=summary.message;}
      const card=template.content.querySelector('.debrief-card');
      if(card) {
        const isStrength=card.querySelector('h3').textContent==='Concept strengths',values=isStrength?summary.strengths:summary.review;
        const fallback=isStrength?'Keep building across every concept area':'No concept area requires immediate review';
        card.querySelector('ul').replaceChildren(...(values.length?values:[fallback]).map(value=>el('li',value)));
      }
    }return template.content;
  }
  if(node.kind==='columns'||node.kind==='column') {
    const box=el('div',undefined,node.kind==='columns'?'columns':null);if(node.kind==='columns')box.style.setProperty('--columns',node.children.length);
    node.children.forEach(child=>box.append(renderNode(child)));return box;
  }
  if(node.kind==='details') {
    if(lesson.view===7){const round=DATA.rounds.find(round=>node.label.startsWith(round.title+' · '));if(round)return trail(round);}
    const details=el('details');details.open=Boolean(node.expanded);details.append(el('summary',node.label));node.children.forEach(child=>details.append(renderNode(child)));return details;
  }
  if(node.kind==='markdown'||node.kind==='write')return markdown(node.text);
  const item=el(node.kind==='title'?'h1':node.kind==='header'?'h2':node.kind==='subheader'?'h3':'p',node.text,
    ['success','warning','info'].includes(node.kind)?'notice '+node.kind:node.kind==='caption'?'caption':null);
  if(['success','warning','info'].includes(node.kind))item.setAttribute('role','status');return item;
}
function render() {
  $('back').disabled=lesson.view===0;$('forward').disabled=lesson.view>=frontier(lesson.state);
  $('page-counter').textContent='Page '+(lesson.view+1)+' of 8';
  $('review-message').replaceChildren(...(lesson.reviewing?[el('p','Review only. Return to your current page to continue the filing review.','notice info')]:[]));
  const nodes=DATA.screens[lesson.view][lesson.viewSubmitted?'correct':'unanswered'];
  $('lesson').replaceChildren(...nodes.map(renderNode));
  if(lesson.warning){const message=el('p','Make a decision for every item before submitting this round.','notice warning');message.setAttribute('role','alert');$('lesson').append(message);}
  $('lesson').setAttribute('aria-busy','false');document.documentElement.dataset.view=String(lesson.view);document.documentElement.dataset.reached=String(frontier(lesson.state));
}
async function initialize() {
  const query=new URL(location.href).searchParams,token=query.get('progress'),state=token?await decodeState(token):null;
  lesson=new Lesson(state??undefined,query.get('view')??undefined);render();
  if(token&&!state)$('lesson').prepend(el('p','This saved link could not be restored. A new filing review has been opened.','notice warning'));
  await save();document.documentElement.dataset.ready='true';performance.mark('filing-ready');
}
$('back').addEventListener('click',()=>{if(lesson.move(-1))update(true);});
$('forward').addEventListener('click',()=>{if(lesson.move(1))update(true);});
window.addEventListener('popstate',()=>{document.documentElement.dataset.ready='false';initialize();});
initialize().catch(error=>{$('lesson').replaceChildren(el('p','This browser could not open the filing review. Use a current browser with JavaScript and Compression Streams enabled.','notice warning'));$('lesson').setAttribute('aria-busy','false');console.error(error);});
