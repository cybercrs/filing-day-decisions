/** Original reporting decisions, sequential gauges, exact option orders and save format. */
import {DATA} from './content.js';
import {assert,copy,object,exact,int,PythonRandom,pyFixed,encodeJSON,decodeJSON} from './shared.js';
export {copy,canonicalJSON,pyFixed} from './shared.js';
export const RECORDS=DATA.rounds.flatMap((round,roundIndex)=>round.questions.map(question=>({roundIndex,question})));
export const questionById=Object.fromEntries(RECORDS.map(record=>[record.question.id,record.question]));
export const roundForId=Object.fromEntries(RECORDS.map(record=>[record.question.id,record.roundIndex]));
export const frontier=state=>state.page==='welcome'?0:state.page==='debrief'?7:state.round_index+1;
export function newState(seed=crypto.getRandomValues(new Uint32Array(1))[0]) {
  return {version:1,page:'welcome',round_index:0,round_submitted:false,choices:{},results:{},complete:false,order_seed:seed,revealed:[]};
}
function choices(raw) {
  assert(object(raw)&&Object.keys(raw).length<=RECORDS.length,'Invalid answer map');
  for(const [id,index] of Object.entries(raw))assert(Object.hasOwn(questionById,id)&&int(index,0,questionById[id].options.length-1),'Invalid saved choice');
  return copy(raw);
}
export function validateSnapshot(raw) {
  assert(exact(raw,['version','page','round_index','round_submitted','choices','results','complete','order_seed','revealed'])&&raw.version===1,'Unsupported filing snapshot');
  assert(['welcome','round','debrief'].includes(raw.page)&&int(raw.round_index,0,5),'Invalid filing position');
  assert(typeof raw.round_submitted==='boolean'&&typeof raw.complete==='boolean'&&int(raw.order_seed,0,4294967295),'Invalid filing status/seed');
  const selected=choices(raw.choices),submitted=choices(raw.results);
  assert(Array.isArray(raw.revealed)&&new Set(raw.revealed).size===raw.revealed.length&&raw.revealed.every(slug=>DATA.rounds.some(round=>round.slug===slug)),'Invalid revealed answers');
  let completedCount,allowedCount;
  if(raw.page==='welcome') {
    assert(raw.round_index===0&&!raw.round_submitted&&!raw.complete,'Inconsistent welcome');
    completedCount=allowedCount=0;
  }else if(raw.page==='round') {
    assert(!raw.complete,'Unfinished round cannot be complete');
    completedCount=raw.round_index+Number(raw.round_submitted);allowedCount=raw.round_index+1;
  }else {
    assert(raw.round_index===5&&raw.round_submitted&&raw.complete,'Inconsistent completion');
    completedCount=allowedCount=6;
  }
  const expected=RECORDS.filter(record=>record.roundIndex<completedCount).map(record=>record.question.id);
  assert(Object.keys(submitted).length===expected.length&&expected.every(id=>Object.hasOwn(submitted,id)),'Submitted results do not match the saved page');
  assert(Object.keys(selected).every(id=>roundForId[id]<allowedCount),'Future saved choice');
  assert(Object.entries(submitted).every(([id,index])=>selected[id]===index),'Saved drafts disagree with submitted results');
  assert(raw.revealed.every(slug=>DATA.rounds.findIndex(round=>round.slug===slug)<completedCount),'Future answer reveal');
  return {version:1,page:raw.page,round_index:raw.round_index,round_submitted:raw.round_submitted,
    choices:selected,results:submitted,complete:raw.complete,order_seed:raw.order_seed,revealed:[...raw.revealed]};
}
function pairMap(pairs) {
  assert(Array.isArray(pairs)&&pairs.length<=RECORDS.length,'Invalid compact answers');
  const map={};
  for(const pair of pairs) {
    assert(Array.isArray(pair)&&pair.length===2&&int(pair[0],0,RECORDS.length-1),'Invalid compact question');
    const id=RECORDS[pair[0]].question.id;assert(!Object.hasOwn(map,id),'Duplicate compact question');map[id]=pair[1];
  }return map;
}
const pairs=map=>RECORDS.flatMap((record,index)=>Object.hasOwn(map,record.question.id)?[[index,map[record.question.id]]]:[]);
export function compact(state) {
  const normalized=validateSnapshot(state);
  const raw={v:1,p:{welcome:'w',round:'r',debrief:'d'}[normalized.page],i:normalized.round_index,s:normalized.round_submitted,
    c:pairs(normalized.choices),r:pairs(normalized.results),d:normalized.complete,o:normalized.order_seed};
  if(normalized.revealed.length)raw.x=normalized.revealed.map(slug=>DATA.rounds.findIndex(round=>round.slug===slug));
  return raw;
}
export function expand(raw) {
  const required=['v','p','i','s','c','r','d','o'];
  assert(object(raw)&&required.every(key=>Object.hasOwn(raw,key))&&Object.keys(raw).every(key=>[...required,'x'].includes(key))&&raw.v===1,'Invalid compact snapshot');
  assert(['w','r','d'].includes(raw.p),'Invalid compact page');
  const revealed=raw.x??[];
  assert(Array.isArray(revealed)&&revealed.every(index=>int(index,0,5)),'Invalid compact reveal');
  return validateSnapshot({version:1,page:{w:'welcome',r:'round',d:'debrief'}[raw.p],round_index:raw.i,
    round_submitted:raw.s,choices:pairMap(raw.c),results:pairMap(raw.r),complete:raw.d,order_seed:raw.o,
    revealed:revealed.map(index=>DATA.rounds[index].slug)});
}
export const encodeState=state=>encodeJSON(compact(state),8192,4096);
export async function decodeState(token){try{return expand(await decodeJSON(token,8192,4096));}catch{return null;}}
export function createOptionOrder(seed) {
  assert(int(seed,0,4294967295),'Invalid shuffle seed');
  const rng=new PythonRandom(BigInt(seed));
  return Object.fromEntries(RECORDS.map(({question})=>[question.id,rng.sample(question.options.map((_,i)=>i))]));
}
export function evaluateQuestion(question,index) {
  assert(int(index,0,question.options.length-1),'Selected option is outside this question');
  const selected=question.options[index],correct_index=question.options.findIndex(option=>option.correct),correct=question.options[correct_index];
  return {question_id:question.id,prompt:question.prompt,concept:question.concept,selected_index:index,selected_text:selected.text,
    correct_index,correct_text:correct.text,is_correct:index===correct_index,feedback:selected.feedback,explanation:question.explanation,impacts:copy(selected.impacts)};
}
export function applyImpacts(current,impacts) {
  const updated={...current};
  for(const [key,value] of Object.entries(impacts)) {
    assert(Object.hasOwn(DATA.metricLabels,key),'Unknown reporting metric');
    updated[key]=Math.max(0,Math.min(100,(updated[key]??0)+value));
  }return updated;
}
export function applyResultsWithChanges(current,results) {
  let updated={...current};
  const changes=Object.fromEntries(Object.keys(DATA.metricLabels).map(key=>[key,{gained:0,lost:0}]));
  for(const result of results) {
    const previous={...updated};updated=applyImpacts(updated,result.impacts);
    for(const key of Object.keys(DATA.metricLabels)) {
      const difference=updated[key]-previous[key];
      if(difference>0)changes[key].gained+=difference;else if(difference<0)changes[key].lost-=difference;
    }
  }return [updated,changes];
}
export const applyResults=(current,results)=>applyResultsWithChanges(current,results)[0];
export function hydrate(state) {
  validateSnapshot(state);
  let metrics=copy(DATA.startingMetrics);
  const responses=[],baselines={};
  for(const round of DATA.rounds) {
    const results=round.questions.filter(question=>Object.hasOwn(state.results,question.id)).map(question=>
      ({...evaluateQuestion(question,state.results[question.id]),round_slug:round.slug,round_title:round.title}));
    if(results.length){baselines[round.slug]=copy(metrics);metrics=applyResults(metrics,results);responses.push(...results);}
  }return {metrics,responses,baselines};
}
export function summarizeResults(responses) {
  const correct=responses.filter(result=>result.is_correct).length,total=responses.length;
  const percent=total?Number(pyFixed(correct/total*100,0)):0,concept_totals={};
  for(const result of responses) {
    concept_totals[result.concept]??={correct:0,total:0};concept_totals[result.concept].total++;
    concept_totals[result.concept].correct+=Number(result.is_correct);
  }
  const strengths=Object.keys(concept_totals).filter(concept=>concept_totals[concept].correct===concept_totals[concept].total);
  const review=Object.keys(concept_totals).filter(concept=>concept_totals[concept].correct<concept_totals[concept].total);
  const status=percent>=85?'Filing ready':percent>=65?'Promising draft':'Needs another pass';
  const message=percent>=85?'Your report is useful, credible, and ready for a confident debrief.':
    percent>=65?'The foundation is strong. A few reporting choices deserve another look.':
    'Revisit the concepts below before releasing the report to users.';
  return {correct,total,percent,status,message,strengths,review,concept_totals};
}
export class Lesson {
  constructor(state=newState(),view) {
    this.state=validateSnapshot(state);const reached=frontier(this.state);
    const number=typeof view==='string'&&/^-?\d+$/.test(view)?Number(view):view;
    this.view=int(number,0,reached)?number:reached;this.orders=createOptionOrder(this.state.order_seed);this.warning=false;
  }
  get reviewing(){return this.view<frontier(this.state);}
  get report(){return hydrate(this.state);}
  get viewedRound(){return this.view>=1&&this.view<=6?DATA.rounds[this.view-1]:null;}
  get viewSubmitted(){return this.view>=1&&this.view<=6&&(this.reviewing||this.state.round_submitted);}
  get viewedMetrics() {
    const report=this.report,round=this.viewedRound;
    if(!round)return report.metrics;
    if(!this.viewSubmitted)return report.metrics;
    return applyResults(report.baselines[round.slug],report.responses.filter(result=>result.round_slug===round.slug));
  }
  move(direction) {
    if(![-1,1].includes(direction)||!int(this.view+direction,0,frontier(this.state)))return false;
    this.view+=direction;this.warning=false;return true;
  }
  restart() {
    if(this.reviewing||!['welcome','debrief'].includes(this.state.page))return false;
    this.state=newState();this.state.page='round';this.view=1;
    this.orders=createOptionOrder(this.state.order_seed);this.warning=false;return true;
  }
  draft(id,index) {
    if(this.reviewing||this.state.page!=='round'||this.state.round_submitted||roundForId[id]!==this.state.round_index||
      !Object.hasOwn(questionById,id)||!int(index,0,questionById[id].options.length-1))return false;
    this.state.choices[id]=index;this.warning=false;return true;
  }
  submit() {
    if(this.reviewing||this.state.page!=='round'||this.state.round_submitted)return false;
    const questions=DATA.rounds[this.state.round_index].questions;
    if(!questions.every(question=>Object.hasOwn(this.state.choices,question.id))){this.warning=true;return false;}
    questions.forEach(question=>{this.state.results[question.id]=this.state.choices[question.id];});
    this.state.round_submitted=true;this.warning=false;validateSnapshot(this.state);return true;
  }
  reveal() {
    if(this.reviewing||this.state.page!=='round'||!this.state.round_submitted)return false;
    const slug=DATA.rounds[this.state.round_index].slug;
    if(this.state.revealed.includes(slug))return false;this.state.revealed.push(slug);return true;
  }
  advance() {
    if(this.reviewing||this.state.page!=='round'||!this.state.round_submitted)return false;
    if(this.state.round_index===5){this.state.page='debrief';this.state.complete=true;this.view=7;}
    else {this.state.round_index++;this.state.round_submitted=false;this.view=frontier(this.state);}
    this.warning=false;validateSnapshot(this.state);return true;
  }
}
