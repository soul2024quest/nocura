import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Pause, Play, RotateCcw, Minus, Plus } from 'lucide-react';
type Props={onReady:()=>void; reduced:boolean};
export default function FlameScene({onReady,reduced}:Props){
 const host=useRef<HTMLDivElement>(null),api=useRef<{reset:()=>void;zoom:(n:number)=>void}|undefined>(undefined);
 const [paused,setPaused]=useState(false),[failed,setFailed]=useState(false);const pause=useRef(paused||reduced);
 useEffect(()=>{pause.current=paused||reduced;},[paused,reduced]);
 useEffect(()=>{
  const el=host.current;if(!el)return;let renderer:THREE.WebGLRenderer;
  try{renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});}catch{setFailed(true);onReady();return;}
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.7));el.appendChild(renderer.domElement);
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.1,100);camera.position.set(0,.45,7.5);
  const orbit=new OrbitControls(camera,renderer.domElement);orbit.enablePan=false;orbit.enableDamping=true;orbit.minDistance=4;orbit.maxDistance=11;orbit.enableZoom=false;orbit.autoRotateSpeed=.35;
  const group=new THREE.Group();scene.add(group);const count=window.innerWidth<600?1700:3000,positions=new Float32Array(count*3),colors=new Float32Array(count*3);
  const warm=new THREE.Color('#D25C1B'),cool=new THREE.Color('#8fbccc');
  for(let i=0;i<count;i++){const y=1-2*(i+.5)/count,rr=Math.sqrt(1-y*y),a=i*2.3999632297,r=1.55*(1+.025*Math.sin(i*.76));positions.set([Math.cos(a)*rr*r,y*r*.92,Math.sin(a)*rr*r],i*3);const c=positions[i*3]<-.65?cool:warm;colors.set([c.r,c.g,c.b],i*3);}
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(positions,3));geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
  const mat=new THREE.PointsMaterial({size:.021,vertexColors:true,transparent:true,opacity:.88,sizeAttenuation:true});group.add(new THREE.Points(geo,mat));
  const disposable:(THREE.BufferGeometry|THREE.Material)[]=[geo,mat];
  for(const angle of [0,1.1,-.8]){const path=new THREE.EllipseCurve(0,0,2.0,.62,0,Math.PI*2,false,0);const g=new THREE.BufferGeometry().setFromPoints(path.getPoints(180));const m=new THREE.LineBasicMaterial({color:'#465362',transparent:true,opacity:.55});const ring=new THREE.LineLoop(g,m);ring.rotation.z=angle;ring.rotation.y=.25;group.add(ring);disposable.push(g,m);}
  const rodGeo=new THREE.CylinderGeometry(.035,.035,1.15,16),rodMat=new THREE.MeshStandardMaterial({color:'#c4d0d8',metalness:.7,roughness:.35});const rod=new THREE.Mesh(rodGeo,rodMat);scene.add(rod);disposable.push(rodGeo,rodMat);scene.add(new THREE.AmbientLight('#ffffff',2));const light=new THREE.PointLight('#ffffff',30);light.position.set(2,3,4);scene.add(light);
  const resize=()=>{const {width,height}=el.getBoundingClientRect();if(!width||!height)return;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();renderer.render(scene,camera);};const observer=new ResizeObserver(resize);observer.observe(el);resize();
  let visible=true,raf=0,last=0;const frame=(now:number)=>{raf=requestAnimationFrame(frame);if(document.hidden||!visible||now-last<30)return;last=now;orbit.autoRotate=!pause.current;orbit.update();renderer.render(scene,camera);};raf=requestAnimationFrame(frame);const io=new IntersectionObserver(([entry])=>visible=entry.isIntersecting);io.observe(el);
  api.current={reset:()=>{camera.position.set(0,.45,7.5);orbit.target.set(0,0,0);orbit.update();},zoom:n=>{camera.position.multiplyScalar(n);const length=camera.position.length();camera.position.setLength(THREE.MathUtils.clamp(length,4,11));orbit.update();}};
  const lost=(e:Event)=>{e.preventDefault();setFailed(true);};renderer.domElement.addEventListener('webglcontextlost',lost);onReady();
  return()=>{cancelAnimationFrame(raf);observer.disconnect();io.disconnect();orbit.dispose();disposable.forEach(x=>x.dispose());renderer.dispose();renderer.domElement.removeEventListener('webglcontextlost',lost);renderer.domElement.remove();api.current=undefined;};
 },[onReady]);
 return <div className="scene-wrap"><div className="scene-header"><span>02 / COMBUSTION FIELD</span><span>μg / 3D</span></div><div ref={host} className="scene-canvas" role="img" aria-label="Conceptual spherical flame envelope around a PMMA rod. Drag to rotate. Colors do not measure temperature."/>{failed&&<div className="scene-fallback"><div className="static-orb"/><p>Static flame concept · 3D unavailable</p></div>}<div className="scene-caption"><span className="specimen-tag">PMMA <b>6.35 mm</b></span><p>Drag to orbit · use + / − to zoom</p></div><div className="scene-toolbar"><span>CONCEPTUAL VIEW · NOT A PHYSICS SIMULATION</span><div><button className="icon-button" aria-label="Zoom in" onClick={()=>api.current?.zoom(.9)}><Plus size={15}/></button><button className="icon-button" aria-label="Zoom out" onClick={()=>api.current?.zoom(1.1)}><Minus size={15}/></button><button className="icon-button" aria-label="Reset 3D view" onClick={()=>api.current?.reset()}><RotateCcw size={15}/></button><button className="icon-button" aria-label={paused?'Resume motion':'Pause motion'} disabled={reduced} onClick={()=>setPaused(!paused)}>{paused||reduced?<Play size={15}/>:<Pause size={15}/>}</button></div></div></div>;
}
