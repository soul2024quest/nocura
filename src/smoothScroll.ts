import {useEffect} from 'react';
import Lenis from 'lenis';
import 'lenis/dist/lenis.css';

let active:Lenis|null=null;

/** Keep wheel inertia and in-page navigation on the same scroll controller. */
export function scrollPageTo(target:number|HTMLElement,immediate=false){
 if(active){
  active.resize();
  active.scrollTo(target,{immediate,offset:typeof target==='number'?0:-110});
 }else{
  const top=typeof target==='number'?target:window.scrollY+target.getBoundingClientRect().top-110;
  window.scrollTo({top,behavior:immediate||window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
 }
}

export function useSmoothScrolling(reduced:boolean){
 useEffect(()=>{
  if(reduced)return;
  const controller=new Lenis({
   autoRaf:true,
   smoothWheel:true,
   lerp:0.085,
   wheelMultiplier:0.9,
   syncTouch:false,
   anchors:{offset:-110},
   stopInertiaOnNavigate:true,
   // Conversation history and editable fields keep their own native scrolling.
   prevent:node=>node.classList.contains('followup-transcript')||node.tagName==='TEXTAREA',
  });
  active=controller;
  return()=>{if(active===controller)active=null;controller.destroy();};
 },[reduced]);
}
