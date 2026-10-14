import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {DATA} from '../content.js';
import {Lesson,RECORDS,newState,validateSnapshot,compact,expand,encodeState,decodeState,createOptionOrder,
  evaluateQuestion,applyImpacts,applyResultsWithChanges,hydrate,summarizeResults,frontier,canonicalJSON} from '../engine.js';
const oracle=JSON.parse(readFileSync(new URL('./python-oracles.json',import.meta.url)));
const legacy=JSON.parse(readFileSync(new URL('./legacy-links.json',import.meta.url)));
function complete(wrong=false,reveal=true) {
  const lesson=new Lesson(newState(42));assert.equal(lesson.restart(),true);
  for(const round of DATA.rounds) {
    for(const question of round.questions) {
      const answer=question.options.findIndex(option=>Boolean(option.correct)!==wrong);
      assert.equal(lesson.draft(question.id,answer),true);
    }
    assert.equal(lesson.submit(),true);if(reveal)assert.equal(lesson.reveal(),true);
    assert.equal(lesson.advance(),true);
  }return lesson;
}
test('all 57 option outcomes equal the original Python evaluations',()=>{
  assert.equal(oracle.outcomes.length,57);
  for(const fixture of oracle.outcomes) {
    const question=RECORDS.find(record=>record.question.id===fixture.id).question;
    assert.deepEqual(evaluateQuestion(question,fixture.index),fixture.result);
  }
});
test('80 independently generated trajectories preserve sequential clamps, baselines, metric traces and summaries',()=>{
  assert.equal(oracle.trajectories.length,80);
  for(const fixture of oracle.trajectories) {
    const report=hydrate(fixture.snapshot);
    assert.deepEqual(report.responses,fixture.responses);assert.deepEqual(report.metrics,fixture.metrics);
    assert.deepEqual(report.baselines,fixture.baselines);
    assert.deepEqual(summarizeResults(report.responses),fixture.summary);
    assert.deepEqual(applyResultsWithChanges(DATA.startingMetrics,report.responses),fixture.trace);
  }
  assert.equal(applyImpacts({usefulness:99},{usefulness:12}).usefulness,100);
  assert.equal(applyImpacts({faithfulness:1},{faithfulness:-12}).faithfulness,0);
  assert.throws(()=>applyImpacts({}, {unknown:1}));
});
test('every Python option permutation is reproduced exactly, including seeds 0 and uint32 maximum',()=>{
  for(const fixture of oracle.orders)assert.deepEqual(createOptionOrder(fixture.seed),fixture.order);
});
test('old submitted/unsubmitted/revealed snapshots and new native links remain Python-compatible',async()=>{
  for(const fixture of [...legacy,...oracle.snapshots]) {
    assert.deepEqual(await decodeState(fixture.token),fixture.snapshot);
    assert.deepEqual(await decodeState(await encodeState(fixture.snapshot)),fixture.snapshot);
    assert.deepEqual(expand(compact(fixture.snapshot)),fixture.snapshot);
  }
  const state=complete().state,token=await encodeState(state);
  const result=spawnSync(process.env.PYTHON??'python3',['-c',
    'import json,sys;from app.progress import decode_snapshot;print(json.dumps(decode_snapshot(sys.argv[1])))',token],
    {cwd:new URL('../../',import.meta.url),encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);assert.deepEqual(JSON.parse(result.stdout),state);
});
test('the original gates allow wrong decisions to advance and reject duplicate submissions/reveals',()=>{
  for(const wrong of [false,true]) {
    const lesson=new Lesson(newState(0));lesson.restart();assert.equal(lesson.advance(),false);
    assert.equal(lesson.submit(),false);assert.equal(lesson.warning,true);
    assert.equal(lesson.reveal(),false);
    for(const round of DATA.rounds) {
      for(const question of round.questions)lesson.draft(question.id,question.options.findIndex(option=>Boolean(option.correct)!==wrong));
      assert.equal(lesson.submit(),true);
      const before=canonicalJSON(lesson.report.metrics);
      assert.equal(lesson.submit(),false);assert.equal(canonicalJSON(lesson.report.metrics),before);
      assert.equal(lesson.reveal(),true);assert.equal(lesson.reveal(),false);
      assert.equal(lesson.draft(round.questions[0].id,0),false);
      assert.equal(lesson.advance(),true);
    }
    assert.equal(frontier(lesson.state),7);assert.equal(lesson.state.complete,true);
    assert.equal(summarizeResults(lesson.report.responses).correct,wrong?0:19);
  }
});
test('every older page is strictly readonly, with no new reveals or progress mutations',()=>{
  const lesson=complete(false,false),before=canonicalJSON(lesson.state),metrics=canonicalJSON(lesson.report.metrics);
  for(let view=6;view>=0;view--) {
    assert.equal(lesson.move(-1),true);assert.equal(lesson.view,view);
    for(const method of ['submit','reveal','advance','restart'])assert.equal(lesson[method](),false);
    assert.equal(lesson.draft(RECORDS[0].question.id,0),false);
    assert.equal(canonicalJSON(lesson.state),before);assert.equal(canonicalJSON(lesson.report.metrics),metrics);
  }
  for(let view=1;view<=7;view++){assert.equal(lesson.move(1),true);assert.equal(lesson.view,view);}
  assert.equal(lesson.move(1),false);assert.equal(canonicalJSON(lesson.state),before);
});
test('viewed gauges use that round baseline/results and reveal flags retain only deliberately opened answers',()=>{
  const lesson=complete();
  for(let view=6;view>=1;view--) {
    lesson.move(-1);const round=lesson.viewedRound,baseline=lesson.report.baselines[round.slug];
    const results=lesson.report.responses.filter(result=>result.round_slug===round.slug);
    assert.deepEqual(lesson.viewedMetrics,applyResultsWithChanges(baseline,results)[0]);
    assert.equal(lesson.state.revealed.includes(round.slug),true);
  }
  const unrevealed=complete(false,false);unrevealed.move(-1);assert.equal(unrevealed.state.revealed.length,0);assert.equal(unrevealed.reveal(),false);
});
test('draft choices, option seed and current submitted frontier survive without advancing on Forward',async()=>{
  const lesson=new Lesson(newState(4294967295));lesson.restart();
  const question=DATA.rounds[0].questions[0];lesson.draft(question.id,1);
  const restored=new Lesson(await decodeState(await encodeState(lesson.state)));
  assert.deepEqual(restored.state,lesson.state);assert.deepEqual(restored.orders,lesson.orders);
  for(const question of DATA.rounds[0].questions)lesson.draft(question.id,0);
  lesson.submit();assert.equal(lesson.move(1),false);assert.equal(frontier(lesson.state),1);
});
test('malformed prefixes, duplicate indexes, future choices/reveals/views and unknown fields are rejected',async()=>{
  for(const token of [null,'','bad!','a'.repeat(4097)])assert.equal(await decodeState(token),null);
  const state=newState(0);state.choices[RECORDS[4].question.id]=0;assert.throws(()=>validateSnapshot(state));
  const incomplete=newState(0);incomplete.page='round';incomplete.round_submitted=true;assert.throws(()=>validateSnapshot(incomplete));
  const revealed=newState(0);revealed.revealed=[DATA.rounds[0].slug];assert.throws(()=>validateSnapshot(revealed));
  const duplicate=compact(legacy[1].snapshot);duplicate.c=[[0,0],[0,1]];assert.throws(()=>expand(duplicate));
  for(const view of ['999','-1','x','2.5'])assert.equal(new Lesson(legacy[3].snapshot,view).view,3);
});
test('Start over returns directly to fresh round one while copied bookmarks and independent sessions survive',async()=>{
  const first=complete(),token=await encodeState(first.state),second=new Lesson(newState(0));
  assert.equal(first.restart(),true);assert.equal(first.state.page,'round');assert.equal(frontier(first.state),1);
  assert.equal(Object.keys(first.state.results).length,0);assert.equal(second.state.page,'welcome');
  assert.equal((await decodeState(token)).page,'debrief');
});
test('all original prompts/options/feedback and captured variants retain finalized app branding',()=>{
  const walk=value=>{
    if(Array.isArray(value))return value.forEach(walk);
    if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){
      if(['text','label','help','prompt','feedback','reflection_question','reflection_answer'].includes(key)&&typeof item==='string')
        assert.doesNotMatch(item,/\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b/i);
      else walk(item);
    }
  };
  walk(DATA);assert.equal(DATA.title,'Filing Day Decisions');assert.equal(RECORDS.length,19);
});
