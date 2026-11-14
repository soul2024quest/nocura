export type Inputs = { ambient_o2_percent: number; flow_velocity_cms: number; fuel_thickness_mm: number };
export type Prediction = { supported: boolean; reasons?: string[]; flame_hazard_state: number; sustained_flame_score: number; regime_label: string; physical_interpretation: string; scope_note: string };
export type Briefing = { supported: boolean; briefing: string; source: string };
export type Investigation = { psi_id: string; title: string; facility: string; fuels: string[]; oxygen_range_percent: number[]; flow_velocity_range_cms: number[]; primary_sensors: string[]; key_findings: string; citation: string; source_url: string; fire_safety_relevance_score: number };
export type Metadata = { model_version: string; telemetry_bounds: Record<string,{min:number;max:number}>; fuel_baseline_mm: number; evaluation_metrics: {test_accuracy:number}; provenance: {limitations:string;source_url:string;ntrs_citation:string} };
export async function request<T>(path: string, body?: Inputs, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  signal?.addEventListener('abort', cancel, {once:true});
  if (signal?.aborted) controller.abort();
  const timer = setTimeout(cancel, body && path.includes('briefing') ? 22000 : 12000);
  try {
    const res = await fetch(path, {method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal:controller.signal});
    if(!res.ok) throw new Error(`The research API returned ${res.status}. Please retry.`);
    return await res.json() as T;
  } catch(e) {
    if(signal?.aborted) throw e;
    throw new Error(e instanceof Error && e.name !== 'AbortError' ? e.message : 'The request timed out. Your inputs are saved; please retry.');
  } finally {clearTimeout(timer);signal?.removeEventListener('abort',cancel);}
}
