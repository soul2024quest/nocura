import {useEffect,useRef,useState} from 'react';
import {ArrowUpRight,ChevronDown,LoaderCircle,MessageCircle} from 'lucide-react';
import {request,type Inputs,type FollowUpAnswer} from './api';

type Exchange={question:string;answer:string;source:string};
type Props={inputs:Inputs;briefing:string;disabled:boolean};
export default function FollowUpQuestions({inputs,briefing,disabled}:Props){
 const [open,setOpen]=useState(false),[question,setQuestion]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[exchanges,setExchanges]=useState<Exchange[]>([]);
 const active=useRef<AbortController|null>(null),latest=useRef<HTMLDivElement>(null);
 useEffect(()=>()=>active.current?.abort(),[]);
 useEffect(()=>{if(disabled){active.current?.abort();active.current=null;setBusy(false);}},[disabled]);
 useEffect(()=>{latest.current?.scrollIntoView({block:'nearest',behavior:'auto'});},[exchanges.length]);
 async function ask(){
  const text=question.trim();if(disabled||active.current||text.length<2||text.length>500)return;
  const controller=new AbortController();active.current=controller;setBusy(true);setError('');
  // Keep the original briefing and recent exchanges within the endpoint's context limit.
  const recent=exchanges.slice(-2).map(x=>`Question: ${x.question}\nAnswer: ${x.answer}`).join('\n\n').slice(-950);
  const context=`Original briefing:\n${briefing.slice(0,1450)}${recent?'\nRecent conversation:\n'+recent:''}`.slice(0,2500);
  try{
   const result=await request<FollowUpAnswer>('/api/followup',{...inputs,question:text,previous_briefing:context},controller.signal);
   if(controller.signal.aborted)return;
   if(!result.supported)throw new Error(result.answer||'This scenario is outside the supported range.');
   if(!result.answer?.trim())throw new Error('No answer was returned. Please retry.');
   setExchanges(xs=>[...xs,{question:text,answer:result.answer,source:result.source}]);setQuestion('');
  }catch(e){if(!controller.signal.aborted)setError((e as Error).message);}
  finally{if(!controller.signal.aborted){active.current=null;setBusy(false);}}
 }
 return <section className="followup" aria-label="Briefing follow-up questions">
  <button className="followup-toggle secondary full" aria-expanded={open} aria-controls="followup-content" onClick={()=>setOpen(x=>!x)}><MessageCircle size={16}/><span>Ask Follow Up Questions</span><ChevronDown size={15} className={open?'expanded':''}/></button>
  {open&&<div id="followup-content" className="followup-content">
   <p className="followup-context">About this briefing: {inputs.ambient_o2_percent}% O₂ · {inputs.flow_velocity_cms} cm/s. Answers use this scenario and your recent questions.</p>
   {exchanges.length>0&&<div className="followup-transcript" role="log" aria-label="Follow-up conversation" aria-live="polite" aria-relevant="additions">{exchanges.map((x,i)=><article className="followup-exchange" key={i} ref={i===exchanges.length-1?latest:undefined}><p className="followup-question"><span>YOU</span>{x.question}</p><div className="followup-answer"><span>{x.source.startsWith('groq:')?'NOCURA · AI RESPONSE':'NOCURA · AI UNAVAILABLE'}</span><p>{x.answer.replace(/\*\*/g,'')}</p>{!x.source.startsWith('groq:')&&<small>This is general context, not a generated answer to your question. Please retry later.</small>}</div></article>)}</div>}
   <form onSubmit={e=>{e.preventDefault();void ask();}}>
    <label htmlFor="followup-question">Your question</label>
    <textarea id="followup-question" rows={3} maxLength={500} minLength={2} value={question} disabled={busy||disabled} placeholder="What would change if the airflow dropped?" onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)){e.preventDefault();void ask();}}} aria-describedby="followup-help"/>
    <div className="followup-compose"><small id="followup-help">{question.length}/500 · Ctrl/⌘ + Enter to send</small><button type="submit" className="primary" disabled={busy||disabled||question.trim().length<2}>{busy?<><LoaderCircle size={15} className="spin"/>Thinking…</>:<>Ask question<ArrowUpRight size={15}/></>}</button></div>
   </form>
   {busy&&<p className="followup-status" role="status">Preparing an answer for this scenario…</p>}
   {error&&<p className="error" role="alert">{error} Your question is kept above; send it again to retry.</p>}
   {disabled&&<p className="scope-short">Conditions changed. Generate a briefing for the updated scenario to continue.</p>}
   <p className="followup-footnote">Research interpretation for the tested PMMA material. AI answers can be mistaken; use the experimental sources to verify claims.</p>
  </div>}
 </section>;
}
