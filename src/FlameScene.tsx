import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {Pause,Play,RotateCcw,Minus,Plus} from 'lucide-react';
import {request,type Inputs,type Prediction} from './api';
// Procedural radiance volume; this renders an illustration, not a combustion solver.
const fragment=`
precision highp float;
varying vec2 vUv;
uniform vec2 resolution;
uniform vec3 eye;
uniform mat4 basis;
uniform float time,flow,oxygen,burn,steps;
uniform highp sampler3D noiseVolume;
float noise(vec3 p){return texture(noiseVolume,(p+.5)/32.).r;}
float fbm(vec3 p){return .7*noise(p)+.3*noise(p*2.03);}
void main(){
 vec2 uv=vUv*2.-1.;uv.x*=resolution.x/resolution.y;
 vec3 rd=normalize(mat3(basis)*vec3(uv*.344,-1.)),ro=eye;
 vec3 a=(vec3(-2.2,-1.5,-1.5)-ro)/rd,b=(vec3(2.6,1.5,1.5)-ro)/rd;
 vec3 lo=min(a,b),hi=max(a,b);
 float nearT=max(max(lo.x,lo.y),lo.z),farT=min(min(hi.x,hi.y),hi.z);
 if(farT<max(nearT,0.)){gl_FragColor=vec4(0,0,0,1);return;}
 float ds=(farT-max(nearT,0.))/steps;
 vec3 acc=vec3(0);float trans=1.;
 for(int i=0;i<80;i++){
  if(float(i)>=steps||trans<.015)break;
  vec3 p=ro+rd*(max(nearT,0.)+(float(i)+.5)*ds);
  float r0=length(p.yz);
  // Slim specimen with a longer, roughly conical consumed tip and static texture.
  float taper=clamp((p.x+1.12)/.72,0.,1.);
  float rodRadius=(.082+.012*smoothstep(-.4,1.6,p.x))*taper;
  rodRadius+=(noise(vec3(p.x*42.,atan(p.z,p.y)*9.,2.))-.5)*.014*taper;
  if(p.x>-1.12&&p.x<2.35&&r0<rodRadius){
   float hot=exp(-pow((p.x+.62)*3.,2.))*burn;
   float grain=.65+.5*noise(vec3(p.x*75.,p.y*150.,p.z*150.));
   acc+=trans*((vec3(.018)+vec3(.035)*smoothstep(-.09,.09,p.y))*grain+hot*vec3(.065,.014,.004));trans=0.;break;
  }
  vec3 adv=vec3(p.x*2.7-time*(.35+flow*.8),p.y*4.,p.z*4.);
  float n=fbm(adv),fine=noise(adv*3.);
  float tail=smoothstep(-.45,1.65,p.x);
  vec2 bend=vec2(sin(p.x*3.-time*1.4),sin(p.x*2.7-time))*.11*tail;
  float r=length(p.yz-bend);
  float cap=sqrt(max(0.,1.-pow(min(p.x+.55,0.)/.82,2.)));
  float angle=atan(p.z,p.y);
  float curl=sin(p.x*5.-time*1.7+angle*3.);
  float radius=(.48+oxygen*.12+flow*.13)*cap;
  radius+=(n-.5)*(.015+tail*.26)+tail*(.075+curl*.18);
  float shell=exp(-pow((r-radius)/(.028+.025*tail),2.));
  float env=smoothstep(-1.4,-1.15,p.x)*(1.-smoothstep(.35+flow*.25,2.1+flow*.25,p.x));
  // An edge-weighted hollow envelope preserves the dark gap around the rod.
  // This is an artistic radiance control, not a solid obstacle in the experiment.
  vec3 normal=normalize(vec3(min(p.x+.55,0.)/.6724,(p.y-bend.x)/.3025,(p.z-bend.y)/.3025));
  float rim=pow(1.-abs(dot(normal,rd)),2.8);
  float ribbons=mix(1.,smoothstep(.32,.72,n+curl*.16),tail);
  float density=shell*3.4*(.035+rim*.965)*env*ribbons*burn;
  if(radius<.02)density=0.;
  float heat=clamp(rim*.65+(1.-tail)*.25+fine*.12,0.,1.);
  vec3 color=mix(vec3(.62,.018,.001),vec3(2.7,.45,.012),heat);
  color=mix(color,vec3(3.2,1.4,.12),pow(heat,5.)*(1.-tail*.65));
  float blue=exp(-pow((r-.115)/.025,2.))*env*burn*.035;
  acc+=trans*(color*density+blue*vec3(.025,.12,.8))*ds*2.1;
  trans*=exp(-density*ds*.75);
 }
 gl_FragColor=vec4(pow(vec3(1.)-exp(-acc*1.25),vec3(.82)),1.);
}`;
type Props={onReady:()=>void;reduced:boolean;inputs:Inputs;onPrediction:(prediction:Prediction,inputs:Inputs)=>void};
export default function FlameScene({onReady,reduced,inputs,onPrediction}:Props){
 const host=useRef<HTMLDivElement>(null),api=useRef<{reset:()=>void;zoom:(n:number)=>void}|undefined>(undefined);
 const [view,setView]=useState<'illustration'|'experiment'>('illustration');
 const wakeRenderer=useRef<()=>void>(()=>{});
 const [paused,setPaused]=useState(false),[failed,setFailed]=useState(false),[pending,setPending]=useState(true),[message,setMessage]=useState('Preparing flame view'),[failure,setFailure]=useState('');
 const target=useRef({flow:.28,oxygen:.31,burn:0}),pause=useRef(paused||reduced);
 useEffect(()=>{pause.current=paused||reduced;wakeRenderer.current();},[paused,reduced]);
 useEffect(()=>{
  const controller=new AbortController();setPending(true);setFailure('');
  if(!Number.isFinite(inputs.ambient_o2_percent)||!Number.isFinite(inputs.flow_velocity_cms)){setPending(false);setFailure('Enter valid conditions.');target.current.burn=0;return;}
  const timer=setTimeout(()=>{request<Prediction>('/api/predict',inputs,controller.signal).then(p=>{
   if(controller.signal.aborted)return;
   onPrediction(p,{...inputs});
   if(!p.supported){target.current.burn=0;wakeRenderer.current();setMessage('Outside experimental range');setFailure('Adjust conditions into the supported range.');return;}
   target.current={flow:THREE.MathUtils.clamp(inputs.flow_velocity_cms/16.298,0,1),oxygen:THREE.MathUtils.clamp((inputs.ambient_o2_percent-13.5)/8.4,0,1),burn:p.flame_hazard_state===1?1:0};
   wakeRenderer.current();
   setMessage(p.flame_hazard_state===1?'Sustained flame predicted':'Extinction predicted');
  }).catch(e=>{if(!controller.signal.aborted){setFailure(e.message);setMessage('Flame update unavailable');target.current.burn=0;}}).finally(()=>{if(!controller.signal.aborted)setPending(false);});},350);
  return()=>{clearTimeout(timer);controller.abort();};
 },[inputs.ambient_o2_percent,inputs.flow_velocity_cms,inputs.fuel_thickness_mm,onPrediction]);
 useEffect(()=>{
  const el=host.current;if(!el)return;let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({alpha:false,antialias:false,powerPreference:'low-power'});}catch{setFailed(true);onReady();return;}
  el.appendChild(renderer.domElement);
  const camera=new THREE.PerspectiveCamera(38,1,.1,100);camera.position.set(0,.65,6.2);
  const controls=new OrbitControls(camera,renderer.domElement);controls.enablePan=false;controls.enableDamping=true;controls.enableZoom=false;controls.minDistance=4;controls.maxDistance=10;controls.target.set(.25,0,0);controls.update();
  const scene=new THREE.Scene(),screen=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
  // Precompute noise once; hardware interpolation replaces repeated shader hash calculations.
  const noiseData=new Uint8Array(32*32*32);let seed=137;
  for(let i=0;i<noiseData.length;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;noiseData[i]=seed>>>24;}
  const noiseTexture=new THREE.Data3DTexture(noiseData,32,32,32);
  noiseTexture.format=THREE.RedFormat;noiseTexture.minFilter=THREE.LinearFilter;noiseTexture.magFilter=THREE.LinearFilter;
  noiseTexture.wrapS=noiseTexture.wrapT=noiseTexture.wrapR=THREE.RepeatWrapping;noiseTexture.unpackAlignment=1;noiseTexture.needsUpdate=true;
  const uniforms={noiseVolume:{value:noiseTexture},resolution:{value:new THREE.Vector2(1,1)},eye:{value:camera.position},basis:{value:camera.matrixWorld},time:{value:0},flow:{value:target.current.flow},oxygen:{value:target.current.oxygen},burn:{value:target.current.burn},steps:{value:32}};
  const geometry=new THREE.PlaneGeometry(2,2),material=new THREE.ShaderMaterial({uniforms,vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}',fragmentShader:fragment,depthTest:false,depthWrite:false});
  scene.add(new THREE.Mesh(geometry,material));
  let raf=0,last=0,visible=false,dirty=true,firstFrameReady=false;
  const interval=1000/22;
  const wake=()=>{dirty=true;if(!raf&&!document.hidden&&visible)raf=requestAnimationFrame(frame);};
  const frame=(now:number)=>{
   raf=0;if(document.hidden||!visible){last=0;return;}
   if(last&&now-last<interval){raf=requestAnimationFrame(frame);return;}
   const elapsed=last?now-last:interval,dt=Math.min(elapsed/1000,.1);last=now;
   let blending=false;const mix=1.-Math.exp(-dt*5.);
   for(const key of ['flow','oxygen','burn'] as const){const difference=Math.abs(uniforms[key].value-target.current[key]);blending ||= difference>.001;uniforms[key].value=difference<.001?target.current[key]:THREE.MathUtils.lerp(uniforms[key].value,target.current[key],mix);}
   const animated=!pause.current&&uniforms.burn.value>.001;
   if(animated)uniforms.time.value+=dt;
   const wasDirty=dirty;dirty=false;controls.update();
   if(animated||blending||wasDirty||dirty){camera.updateMatrixWorld();renderer.render(scene,screen);if(!firstFrameReady){firstFrameReady=true;onReady();}}
   if((animated||blending||dirty)&&!raf)raf=requestAnimationFrame(frame);
  };
  const resize=()=>{const {width,height}=el.getBoundingClientRect();if(!width||!height)return;renderer.setPixelRatio(Math.min(.55,360/width,240/height));renderer.setSize(width,height);uniforms.resolution.value.set(width,height);wake();};
  const observer=new ResizeObserver(resize);observer.observe(el);resize();
  const io=new IntersectionObserver(([entry])=>{visible=entry.isIntersecting;last=0;if(visible)wake();else{cancelAnimationFrame(raf);raf=0;}},{threshold:.05});io.observe(el);
  const visibility=()=>{last=0;if(document.hidden){cancelAnimationFrame(raf);raf=0;}else wake();};
  controls.addEventListener('change',wake);document.addEventListener('visibilitychange',visibility);wakeRenderer.current=wake;
  api.current={reset:()=>{camera.position.set(0,.65,6.2);controls.target.set(.25,0,0);controls.update();},zoom:n=>{camera.position.sub(controls.target).multiplyScalar(n).clampLength(4,10).add(controls.target);controls.update();}};
  const lost=(e:Event)=>{e.preventDefault();setFailed(true);};renderer.domElement.addEventListener('webglcontextlost',lost);
  return()=>{cancelAnimationFrame(raf);io.disconnect();observer.disconnect();controls.removeEventListener('change',wake);document.removeEventListener('visibilitychange',visibility);controls.dispose();geometry.dispose();material.dispose();noiseTexture.dispose();renderer.dispose();renderer.domElement.remove();api.current=undefined;wakeRenderer.current=()=>{};};
 },[onReady]);
 return <div className="scene-wrap flame-volume"><div className="scene-header"><span>02 / INTERACTIVE FLAME</span><span>μg / LIVE VIEW</span></div><div className="view-switch" aria-label="Flame view">{([ ['illustration','Illustration'],['experiment','Real experiment'] ] as const).map(([id,label])=><button key={id} aria-pressed={view===id} onClick={()=>setView(id)}>{label}</button>)}</div><div hidden={view!=='illustration'} ref={host} className="scene-canvas" role="img" aria-label="Physics-inspired flame around a horizontal PMMA rod. Drag to rotate. Shape and colors are illustrative."/>{view==='experiment'&&<figure className="experiment-photo"><img src="/bass-ii-esa-nasa.jpg" alt="Actual BASS-II flame photographed aboard the International Space Station: rounded luminous front, dark central specimen, and curling orange flame downstream."/><figcaption><strong>BASS-II / International Space Station</strong><p>Actual experiment photograph, published 8 August 2014. Credit: ESA/NASA. This fixed reference does not change with your inputs; its exact oxygen and airflow settings are not given on the image page.</p><a href="https://www.esa.int/ESA_Multimedia/Images/2014/08/Microgravity_flame" target="_blank" rel="noreferrer">View original photograph ↗</a></figcaption></figure>}{failed&&view==='illustration'&&<div className="scene-fallback"><p>Interactive rendering unavailable.<br/>Predictions remain available in the results panel.</p></div>}{pending&&view==='illustration'&&<div className="flame-loading" role="status"><span className="flame-spinner"/>Updating conditions</div>}<div hidden={view!=='illustration'} className="scene-caption" aria-live="polite"><span className="specimen-tag">{message}</span><p>{failure||'PMMA · 6.35 mm / Drag to orbit'}</p></div><div hidden={view!=='illustration'} className="scene-toolbar"><span>PHYSICS-INSPIRED · SHAPE & COLOR ILLUSTRATIVE</span><div><button className="icon-button" aria-label="Zoom in" onClick={()=>api.current?.zoom(.9)}><Plus size={15}/></button><button className="icon-button" aria-label="Zoom out" onClick={()=>api.current?.zoom(1.1)}><Minus size={15}/></button><button className="icon-button" aria-label="Reset 3D view" onClick={()=>api.current?.reset()}><RotateCcw size={15}/></button><button className="icon-button" aria-label={paused?'Resume motion':'Pause motion'} disabled={reduced} onClick={()=>setPaused(!paused)}>{paused||reduced?<Play size={15}/>:<Pause size={15}/>}</button></div></div><details className="flame-sources"><summary>Sources &amp; visual assumptions</summary><div><p><strong>Research basis.</strong> NASA BASS-II (PSI-25) studied solid-fuel combustion aboard the ISS. Our predictor uses 51 digitized points for 6.35 mm PMMA rods across oxygen and airflow conditions.</p><a href="https://psi.nasa.gov/physci/repo/data/investigations/PSI-25" target="_blank" rel="noreferrer">NASA PSI investigation ↗</a><a href="https://ntrs.nasa.gov/citations/20160000593" target="_blank" rel="noreferrer">NASA research &amp; experimental images ↗</a><a href="https://ntrs.nasa.gov/citations/20160000593" target="_blank" rel="noreferrer">Experimental research record ↗</a><p><strong>Visual assumptions.</strong> The rounded hollow envelope, specimen taper, surface texture and curling trails are artistically shaped to resemble the photograph. The invisible shaping boundary is not experimental hardware. Geometry, color, and temperature are not predicted. Only the sustained/extinction state comes from the backend.</p></div></details></div>;
}
