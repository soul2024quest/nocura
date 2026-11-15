import {useEffect,useRef,useState} from 'react';
import {motion,useMotionValueEvent,useScroll,useTransform} from 'motion/react';
import {ArrowDown,ArrowDownRight,ArrowRight,ArrowUpRight,Wind,FlaskConical,Layers} from 'lucide-react';
import type {Inputs} from './api';
import {scrollPageTo} from './smoothScroll';

const chapters=[
 {label:'A different world',kicker:'01 / THE QUESTION',title:<>What happens<br/>to fire <em>in space?</em></>,body:'The danger is familiar. The environment is not. Explore how oxygen and airflow can change whether a flame keeps burning in microgravity.'},
 {label:'The conditions',kicker:'02 / THE CONDITIONS',title:<>No rising air.<br/><em>Different rules.</em></>,body:'In microgravity, buoyant flow is greatly reduced. Ventilation and oxygen become central to the way a flame receives fresh air. Change the conditions. Ask a different question.'},
 {label:'The experiment',kicker:'03 / THE EVIDENCE',title:<>Real science.<br/><em>A closer look.</em></>,body:'BASS-II studied burning solid materials aboard the International Space Station. This is an actual experiment photograph—not a render. It is the visual reference behind our illustration.'},
 {label:'Your laboratory',kicker:'04 / YOUR TURN',title:<>Less guessing.<br/><em>More exploring.</em></>,body:'Set oxygen and airflow. See an experimental estimate of sustained burning or extinction, explore an illustrative flame, and ask what the result means.'},
];

export const scenarios=[
 {name:'Start with the baseline',tag:'01 / ORIENTATION',oxygen:16.1,flow:4.5,description:'A starting point inside the tested range. Get familiar with the controls, then change one condition at a time.'},
 {name:'Explore lower oxygen',tag:'02 / OXYGEN',oxygen:13.5,flow:4.5,description:'Keep airflow fixed and lower oxygen to the supported minimum. Compare the result with the baseline.'},
 {name:'Explore faster airflow',tag:'03 / VENTILATION',oxygen:16.1,flow:16.298,description:'Keep oxygen fixed and move airflow to the supported maximum. Find out what the estimator returns.'},
];

type Props={onReady:()=>void;onError:()=>void;reduced:boolean;onEnter:()=>void;onScenario:(inputs:Inputs)=>void;onEvidence:()=>void;onResearch:()=>void};

export default function Story({onReady,onError,reduced,onEnter,onScenario,onEvidence,onResearch}:Props){
 const track=useRef<HTMLElement>(null);
 const flamePhoto=useRef<HTMLImageElement>(null);
 useEffect(()=>{
  let active=true,frame=0;
  const image=flamePhoto.current;
  if(!image)return;
  // Wait for the actual displayed image to be downloaded and decoded, including cached images.
  image.decode().then(()=>{if(active)frame=requestAnimationFrame(()=>{if(active)onReady();});}).catch(()=>{if(active)onError();});
  return()=>{active=false;cancelAnimationFrame(frame);};
 },[onReady,onError]);
 const [chapter,setChapter]=useState(0);
 const {scrollYProgress}=useScroll({target:track,offset:['start start','end end']});
 useMotionValueEvent(scrollYProgress,'change',value=>{const next=Math.min(3,Math.floor(value*4));setChapter(previous=>previous===next?previous:next);});
 const imageX=useTransform(scrollYProgress,[0,.35,.7,1],['4%','-3%','-7%','0%']);
 const imageScale=useTransform(scrollYProgress,[0,.35,.7,1],[.88,1,1.12,.95]);
 const ringRotate=useTransform(scrollYProgress,[0,1],[-24,36]);
 function jump(index:number){const el=track.current;if(!el)return;const top=window.scrollY+el.getBoundingClientRect().top;scrollPageTo(top+(el.offsetHeight-window.innerHeight)*(index/4+.025),reduced);}
 return <div className="discovery">
  <section className={`story-track${reduced?' story-reduced':''}`} ref={track} aria-label="The story of fire in microgravity">
   <div className="story-stage">
    <div className="story-grid" aria-hidden="true"/>
    <div className="story-topline"><span>NASA SPACE APPS CHALLENGE / 2026</span><span>FLAME IN FREEFALL <i/></span></div>
    <div className="story-copy">
     <div className="story-narrative">{chapters.map((item,index)=><div key={item.label} className={`story-chapter-copy${chapter===index?' is-active':''}`} aria-hidden={chapter!==index}>
      <div className="eyebrow">{item.kicker}</div>
      {index===0?<h1>{item.title}</h1>:<h2>{item.title}</h2>}
      <p>{item.body}</p>
     </div>)}</div>
     <button className="primary story-cta" onClick={onEnter}>Enter the laboratory <ArrowUpRight size={18}/></button>
     <div className="story-subnote">A research exploration tool. Not an onboard fire detector.</div>
    </div>
    <div className={`story-visual story-chapter-${chapter}`}>
     <motion.div className="orbit-instrument" style={reduced?undefined:{rotate:ringRotate}} aria-hidden="true">
      <svg viewBox="0 0 600 600" fill="none"><circle cx="300" cy="300" r="272"/><circle cx="300" cy="300" r="262" strokeDasharray="1 17"/><circle cx="300" cy="300" r="220"/><ellipse cx="300" cy="300" rx="220" ry="83" transform="rotate(-25 300 300)"/><ellipse cx="300" cy="300" rx="90" ry="220" transform="rotate(-25 300 300)"/><path d="M15 300h45m480 0h45M300 15v45m0 480v45M100 100l25 25m350 350 25 25M100 500l25-25m350-350 25-25"/><circle cx="300" cy="300" r="4"/></svg>
     </motion.div>
     <motion.figure className="story-flame" style={reduced?undefined:{x:imageX,scale:imageScale}}><img ref={flamePhoto} src="/bass-ii-esa-nasa.jpg" alt="Real BASS-II microgravity flame: a rounded front and curling flame around a dark solid specimen." fetchPriority="high" width="1024" height="575"/></motion.figure>
     <span className="specimen-callout"><i/>BASS-II / ISS<br/><small>EXPERIMENT PHOTOGRAPH</small></span>
     <div className="visual-axis" aria-hidden="true"><span>μg</span><div/><span>MICROGRAVITY</span></div>
    </div>
    <nav className="chapter-nav" aria-label="Introduction chapters">{chapters.map((item,index)=><button key={item.label} onClick={()=>jump(index)} aria-label={`Chapter ${index+1}: ${item.label}`} aria-current={chapter===index?'step':undefined}><span>0{index+1}</span><i/><span>{item.label}</span></button>)}</nav>
    <div className="story-bottomline"><span><ArrowDown size={13}/> SCROLL TO EXPLORE</span><a href="https://www.esa.int/media/microgravity-flame" target="_blank" rel="noreferrer">IMAGE: ESA/NASA <ArrowUpRight size={12}/></a><span>{String(chapter+1).padStart(2,'0')} <b>/ 04</b></span></div>
    <motion.div className="story-progress" style={{scaleX:scrollYProgress}}/>
   </div>
  </section>

  <section className="scope-strip" aria-label="Experimental scope"><div><span>THE MATERIAL</span><strong>PMMA <small>solid rod</small></strong></div><div><span>SPECIMEN DIAMETER</span><strong>6.35 <small>mm</small></strong></div><div><span>OXYGEN RANGE</span><strong>13.5–21.9 <small>%</small></strong></div><div><span>AIRFLOW RANGE</span><strong>0.106–16.298 <small>cm/s</small></strong></div></section>

  <section className="editorial-section experiment-story" id="experiment">
   <div className="section-heading"><div className="eyebrow">01 / FROM ORBIT TO YOUR SCREEN</div><span>THE RESEARCH BEHIND NOCURA</span></div>
   <div className="experiment-layout"><div><h2>A small flame.<br/><em>A bigger question.</em></h2><p>What keeps a solid fuel burning when gravity no longer drives the familiar upward flow of hot air?</p><p>NASA’s Burning and Suppression of Solids II experiment explored solid-fuel combustion in microgravity. Nocura makes one narrow part of that research easier to explore: the influence of oxygen and airflow on a 6.35 mm PMMA rod.</p><button className="secondary" onClick={onResearch}>Explore the research library <ArrowUpRight size={16}/></button></div><figure className="reference-plate"><div className="plate-top"><span>FIG. 01 / OBSERVED IN ORBIT</span><FlaskConical size={14}/></div><img src="/bass-ii-esa-nasa.jpg" width="1024" height="575" loading="lazy" alt="ESA/NASA photograph of a flame generated during BASS-II aboard the ISS."/><figcaption><span>Real BASS-II experiment · International Space Station</span><a href="https://www.esa.int/media/microgravity-flame" target="_blank" rel="noreferrer">ESA/NASA, 2014 <ArrowUpRight size={12}/></a></figcaption><p>The photograph’s oxygen and airflow settings are not specified on its source page. It is a reference image, not a match to a selected scenario.</p></figure></div>
  </section>

  <section className="editorial-section workflow-story">
   <div className="section-heading"><div className="eyebrow">02 / HOW IT WORKS</div><span>THREE LAYERS. CLEAR BOUNDARIES.</span></div>
   <h2>From conditions<br/>to <em>understanding.</em></h2>
   <div className="workflow-grid">{[
    {icon:Wind,title:'Set the environment.',body:'Choose oxygen and airflow within the experimental range. The fuel and specimen diameter stay fixed.',note:'INPUT / TWO CONDITIONS'},
    {icon:Layers,title:'Explore the estimate.',body:'The predictor estimates sustained burning or extinction. A separate 3D illustration helps you explore the scenario.',note:'OUTPUT / ESTIMATE + ILLUSTRATION'},
    {icon:FlaskConical,title:'Ask a better question.',body:'Read an interpretation, ask a follow-up, and inspect the research. AI availability and fallback answers are labelled.',note:'CONTEXT / BRIEFING + SOURCES'},
   ].map(({icon:Icon,title,body,note},index)=><article key={title}><div className="workflow-top"><Icon size={24} strokeWidth={1}/><span>0{index+1}</span></div><h3>{title}</h3><p>{body}</p><small>{note}</small></article>)}</div>
  </section>

  <section className="editorial-section scenario-story">
   <div className="section-heading"><div className="eyebrow">03 / PICK A STARTING POINT</div><span>GUIDED EXPLORATION</span></div><div className="split-heading"><h2>One change.<br/><em>A new perspective.</em></h2><p>Start with a question, not an empty control panel. Each scenario uses supported inputs; its result is calculated when you open it.</p></div>
   <div className="scenario-grid">{scenarios.map(item=><button className="scenario-card" key={item.name} onClick={()=>onScenario({ambient_o2_percent:item.oxygen,flow_velocity_cms:item.flow,fuel_thickness_mm:6.35})}><span className="eyebrow">{item.tag}</span><div className="scenario-schematic" aria-hidden="true"><span style={{width:`${item.oxygen/21.9*100}%`}}/><span style={{width:`${Math.max(8,item.flow/16.298*100)}%`}}/></div><h3>{item.name}</h3><p>{item.description}</p><div className="scenario-values"><span>{item.oxygen}% O₂</span><span>{item.flow} cm/s</span><ArrowUpRight size={20}/></div></button>)}</div>
  </section>

  <section className="honesty-story"><div className="eyebrow">04 / BUILT TO BE QUESTIONED</div><div className="split-heading"><h2>A useful estimate.<br/><em>An honest boundary.</em></h2><div><p>Our model is small, specific, and experimental. The fire you see is an illustration. Neither is a real-time measurement of a spacecraft cabin.</p><button className="secondary" onClick={onEvidence}>Inspect the evidence & limitations <ArrowUpRight size={16}/></button></div></div><div className="honesty-facts"><span><b>51</b> digitized experimental points</span><span><b>11</b> held-out test samples</span><span><b>1</b> material & specimen baseline</span></div></section>

  <section className="final-invitation"><div className="eyebrow">YOUR NEXT QUESTION STARTS HERE</div><h2>Change the conditions.<br/><em>See what changes.</em></h2><button className="primary" onClick={onEnter}>Open the laboratory <ArrowRight size={20}/></button><span><ArrowDownRight size={15}/> No account needed. Explore at your own pace.</span></section>
 </div>;
}
